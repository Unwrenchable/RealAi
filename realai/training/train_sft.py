"""RealAI fixed SFT recipe: Qwen2.5-1.5B-Instruct + LoRA on a dataset_builder output.

Fixes the old runs (64-token seq, 40-60 steps, duplicated data, loss on prompt tokens):
  * Qwen chat template, loss on assistant tokens only
  * max_len 1024 (DirectML OOM backoff 1024 -> 768 -> 512; never below 512)
  * LoRA r16 / alpha32 / dropout 0.05 on q,k,v,o + gate,up,down
  * AdamW lr 1e-4, cosine, 3% warmup, 3 epochs, grad accumulation
  * eval loss on eval.jsonl every epoch, best adapter kept
  * DirectML adapter picked BY NAME (default "RX 6700"), never silently the Vega iGPU

Subcommands (all write only under REALAI_HOME):
  plan     validate dataset + print plan (also: train --dry-run)
  train    LoRA train -> <out>/adapter_best
  eval     eval loss base vs adapter on eval.jsonl -> <out>/eval_report.json (pass bar)
  export   merge on CPU -> GGUF f16 -> Q5_K_M (reuses realai/scripts/train_to_chat_gguf.py)
  register honest candidate entry in REALAI_HOME/models/trained_catalog.json (never default)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"  # Apache-2.0
BASE_LICENSE = "Apache-2.0"
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
LEN_BACKOFF = [1024, 768, 512]
PASS_BAR = {"min_rel_improvement": 0.10, "max_eval_loss": 1.5}


@dataclass
class Recipe:
    base_model: str = BASE_MODEL
    max_len: int = 1024
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_targets: List[str] = field(default_factory=lambda: list(LORA_TARGETS))
    lr: float = 1e-4
    warmup_ratio: float = 0.03
    epochs: int = 3
    batch_size: int = 1
    grad_accum: int = 16
    weight_decay: float = 0.0
    max_grad_norm: float = 1.0
    seed: int = 1337
    device: str = "auto"
    dml_adapter: str = "RX 6700"


def realai_home() -> Path:
    return Path(os.environ.get("REALAI_HOME") or Path.cwd()).resolve()


def _inside_home(p: Path) -> Path:
    p = p.resolve()
    home = realai_home()
    if p != home and home not in p.parents:
        raise SystemExit(f"refusing to write outside REALAI_HOME ({home}): {p}")
    return p


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------- data
def load_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        msgs = r.get("messages")
        if not isinstance(msgs, list) or not msgs:
            raise ValueError(f"{path.name}:{i} has no messages")
        roles = [m.get("role") for m in msgs]
        if "assistant" not in roles or any(x not in {"system", "user", "assistant"} for x in roles):
            raise ValueError(f"{path.name}:{i} bad roles {roles}")
        if any(not str(m.get("content", "")).strip() for m in msgs):
            raise ValueError(f"{path.name}:{i} empty content")
        rows.append(r)
    return rows


def validate_dataset(ds_dir: Path) -> Dict[str, Any]:
    ds_dir = ds_dir.resolve()
    man_p = ds_dir / "manifest.json"
    train_p, eval_p = ds_dir / "train.jsonl", ds_dir / "eval.jsonl"
    for p in (man_p, train_p, eval_p):
        if not p.is_file():
            raise SystemExit(f"missing {p} - build it with python -m realai.training.dataset_builder")
    man = json.loads(man_p.read_text(encoding="utf-8"))
    issues = []
    for name, p in (("train.jsonl", train_p), ("eval.jsonl", eval_p)):
        want = (man.get("sha256") or {}).get(name)
        if want and want != sha256_file(p):
            issues.append(f"{name} sha256 differs from manifest")
    train, ev = load_rows(train_p), load_rows(eval_p)
    key = lambda r: json.dumps(r["messages"], sort_keys=True)
    overlap = len({key(r) for r in train} & {key(r) for r in ev})
    if overlap:
        issues.append(f"{overlap} eval rows also in train")
    return {"dir": str(ds_dir), "train": len(train), "eval": len(ev), "issues": issues,
            "manifest_sha256": sha256_file(man_p), "manifest_name": man.get("name"), "date": man.get("date")}


def _tmpl(tok, msgs, gen=False) -> List[int]:
    if not msgs:
        return []
    r = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=gen)
    if hasattr(r, "keys") and "input_ids" in r:  # transformers >= 5 returns BatchEncoding
        r = r["input_ids"]
    return list(r)


def encode_assistant_only(tok, messages: List[Dict[str, str]], max_len: int):
    """input_ids + labels where only assistant-turn tokens are trained (-100 elsewhere).

    Prefix rendering: tokens added by message i belong to message i. Truncated from the left
    of the prompt is avoided; overly long rows are cut at max_len (labels kept aligned)."""
    ids: List[int] = []
    labels: List[int] = []
    prev: List[int] = []
    for i, m in enumerate(messages):
        cur = _tmpl(tok, messages[: i + 1])
        if m["role"] == "assistant":
            # the "<|im_start|>assistant\n" header is prompt, not target
            head = _tmpl(tok, messages[:i], gen=True)
            n_head = len(head) if head[: len(prev)] == prev else len(prev)
            new = cur[len(prev):]
            hdr = n_head - len(prev)
            ids += new
            labels += [-100] * hdr + new[hdr:]
        else:
            new = cur[len(prev):]
            ids += new
            labels += [-100] * len(new)
        prev = cur
    ids, labels = ids[:max_len], labels[:max_len]
    return ids, labels


# ----------------------------------------------------------------------------- device
def pick_device(kind: str, dml_adapter: str):
    import torch

    kind = (kind or "auto").lower()
    if kind in {"auto", "directml", "dml"}:
        try:
            import torch_directml as dml

            names = [dml.device_name(i).replace("\x00", "").strip() for i in range(dml.device_count())]
            hit = [i for i, n in enumerate(names) if dml_adapter.lower() in n.lower()]
            if hit:
                return dml.device(hit[0]), f"directml:{hit[0]}:{names[hit[0]]}"
            if kind != "auto":
                raise SystemExit(f"DirectML adapter matching {dml_adapter!r} not found in {names} (refusing iGPU fallback)")
        except ImportError:
            if kind != "auto":
                raise SystemExit("torch-directml not installed")
    if kind in {"auto", "cuda"} and torch.cuda.is_available():
        return torch.device("cuda"), "cuda"
    if kind not in {"auto", "cpu"}:
        raise SystemExit(f"device {kind} unavailable")
    return torch.device("cpu"), "cpu"


def _is_oom(exc: BaseException) -> bool:
    s = str(exc).lower()
    return any(k in s for k in ("out of memory", "not enough memory", "failed to allocate", "could not allocate",
                                "video memory", "e_outofmemory", "887a0005", "device removed"))


# ----------------------------------------------------------------------------- plan
def plan(args, recipe: Recipe) -> Dict[str, Any]:
    info = validate_dataset(Path(args.dataset))
    eff = recipe.batch_size * recipe.grad_accum
    steps_per_epoch = math.ceil(info["train"] / eff)
    total = steps_per_epoch * recipe.epochs
    out = {
        "recipe": asdict(recipe),
        "dataset": info,
        "optimizer_steps": {"per_epoch": steps_per_epoch, "total": total,
                            "warmup": max(1, int(total * recipe.warmup_ratio))},
        "len_backoff": [n for n in LEN_BACKOFF if n <= recipe.max_len],
        "out_dir": str(Path(args.out).resolve()),
        "pass_bar": PASS_BAR,
        "base_license": BASE_LICENSE,
    }
    if out["dataset"]["issues"]:
        out["ok"] = False
    else:
        out["ok"] = True
    return out


# ----------------------------------------------------------------------------- train
def _parts(model):
    """(backbone, lm_head) for a plain or PEFT-wrapped causal LM."""
    m = model.get_base_model() if hasattr(model, "get_base_model") else model
    return m.model, m.lm_head


def sft_loss(model, ids: List[int], labels: List[int], device):
    """Next-token CE on assistant positions only; returns (sum_loss_tensor, n_tokens).

    Labels are NOT pre-shifted: position t predicts labels[t+1]. We gather the hidden states of
    the positions that matter and run lm_head only there, so logits are [n_target, vocab] instead
    of [seq, vocab] (151936 vocab -> ~600 MB per 1k tokens otherwise). The CE is written with
    logsumexp/gather because torch-directml's cross_entropy(ignore_index=-100) returns garbage
    (measured: ~12 vs 3-4 on CPU for the same logits)."""
    import torch

    pos = [t for t in range(len(ids) - 1) if labels[t + 1] != -100]
    if not pos:
        return None, 0
    backbone, head = _parts(model)
    h = backbone(input_ids=torch.tensor([ids], device=device)).last_hidden_state[0]
    h = h.index_select(0, torch.tensor(pos, device=device))
    logits = head(h).float()
    tgt = torch.tensor([labels[t + 1] for t in pos], device=device)
    nll = torch.logsumexp(logits, dim=-1) - logits.gather(1, tgt[:, None]).squeeze(1)
    return nll.sum(), len(pos)


def _encode_all(rows, tok, max_len):
    out = []
    for r in rows:
        ids, lab = encode_assistant_only(tok, r["messages"], max_len)
        if any(x != -100 for x in lab[1:]):
            out.append((ids, lab))
    return out


def eval_loss(model, tok, rows, max_len, device) -> float:
    import torch

    model.eval()
    tot, n = 0.0, 0
    with torch.no_grad():
        for ids, lab in _encode_all(rows, tok, max_len):
            loss, k = sft_loss(model, ids, lab, device)
            if k:
                tot += float(loss.to("cpu"))
                n += k
    model.train()
    return tot / max(n, 1)


class DmlAdamW:
    """AdamW with only mul_/add_/addcmul_/addcdiv_ (no lerp_, which torch-directml runs on CPU)."""

    def __init__(self, params, lr, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0):
        import torch

        self.params = [p for p in params]
        self.param_groups = [{"lr": lr, "initial_lr": lr, "params": self.params}]
        self.defaults = {"lr": lr}
        self.b1, self.b2, self.eps, self.wd, self.t = betas[0], betas[1], eps, weight_decay, 0
        self.m = [torch.zeros_like(p) for p in self.params]
        self.v = [torch.zeros_like(p) for p in self.params]
        self.state = {}

    def zero_grad(self, set_to_none=True):
        for p in self.params:
            p.grad = None

    def step(self):
        import torch

        self.t += 1
        lr = self.param_groups[0]["lr"]
        bc1, bc2 = 1 - self.b1 ** self.t, 1 - self.b2 ** self.t
        with torch.no_grad():
            for p, m, v in zip(self.params, self.m, self.v):
                if p.grad is None:
                    continue
                g = p.grad
                if self.wd:
                    p.mul_(1 - lr * self.wd)
                m.mul_(self.b1).add_(g, alpha=1 - self.b1)
                v.mul_(self.b2).addcmul_(g, g, value=1 - self.b2)
                denom = (v / bc2).sqrt_().add_(self.eps)
                p.addcdiv_(m, denom, value=-lr / bc1)

    def state_dict(self):
        return {}


class CosineWarmup:
    """Linear warmup then cosine to 0 (same curve as transformers.get_cosine_schedule_with_warmup)."""

    def __init__(self, opt, warmup: int, total: int):
        self.opt, self.warmup, self.total, self.n = opt, max(1, warmup), max(1, total), 0
        self.base = opt.param_groups[0]["lr"]
        self._set()

    def lr_at(self, n: int) -> float:
        if n < self.warmup:
            return self.base * n / self.warmup
        prog = min(1.0, (n - self.warmup) / max(1, self.total - self.warmup))
        return self.base * 0.5 * (1 + math.cos(math.pi * prog))

    def _set(self):
        for g in self.opt.param_groups:
            g["lr"] = self.lr_at(self.n)

    def step(self):
        self.n += 1
        self._set()

    def get_last_lr(self):
        return [self.opt.param_groups[0]["lr"]]


def _vram_gb():
    """Dedicated GPU memory in use (Windows perf counter, whole adapter); None elsewhere."""
    if os.name != "nt":
        return None
    import subprocess

    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "((Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage').CounterSamples | "
                              "Measure-Object CookedValue -Maximum).Maximum"], capture_output=True, text=True, timeout=20)
        return round(float(out.stdout.strip()) / 2 ** 30, 2)
    except Exception:
        return None


def _train_once(args, recipe: Recipe, max_len: int, log) -> Dict[str, Any]:
    import gc

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(recipe.seed)
    device, dev_name = pick_device(recipe.device, recipe.dml_adapter)
    log(f"device={dev_name} max_len={max_len}")
    ds = Path(args.dataset)
    train_rows, eval_rows = load_rows(ds / "train.jsonl"), load_rows(ds / "eval.jsonl")
    tok = AutoTokenizer.from_pretrained(recipe.base_model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    # fp32 on every device: DirectML fp16 training is unstable and the 1.5B fits (6.2 GB) with :8080 stopped.
    model = AutoModelForCausalLM.from_pretrained(recipe.base_model, torch_dtype=torch.float32)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=recipe.lora_r, lora_alpha=recipe.lora_alpha,
                                             lora_dropout=recipe.lora_dropout, target_modules=recipe.lora_targets,
                                             bias="none", task_type="CAUSAL_LM"))
    model.to(device)
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = DmlAdamW(params, lr=recipe.lr, weight_decay=recipe.weight_decay)
    total = math.ceil(len(train_rows) / recipe.grad_accum) * recipe.epochs
    if args.max_steps:
        total = min(total, args.max_steps)
    full_total = math.ceil(len(train_rows) / recipe.grad_accum) * recipe.epochs
    sched = CosineWarmup(opt, int(full_total * recipe.warmup_ratio), full_total)  # smoke uses the real curve
    out = _inside_home(Path(args.out))
    out.mkdir(parents=True, exist_ok=True)
    if not args.max_steps or args.eval_smoke:
        log(f"base eval_loss (step 0) {eval_loss(model, tok, eval_rows[: args.eval_rows or None], max_len, device):.4f}")
    best, history, step, t0, skipped, peak = float("inf"), [], 0, time.time(), 0, None
    win_loss, win_tok = 0.0, 0
    done = False
    for ep in range(recipe.epochs):
        enc = _encode_all(train_rows, tok, max_len)
        random.Random(recipe.seed + ep).shuffle(enc)
        micro = 0
        for ids, lab in enc:
            for attempt_len in [n for n in LEN_BACKOFF if n <= max_len] + [None]:
                if attempt_len is None:
                    skipped += 1
                    log(f"skip row (OOM even at 512 tokens), skipped={skipped}")
                    break
                i2, l2 = ids[:attempt_len], lab[:attempt_len]
                try:
                    loss, k = sft_loss(model, i2, l2, device)
                    if not k:
                        break
                    # mean over this row's target tokens, averaged over the accumulation window
                    (loss / k / recipe.grad_accum).backward()
                    win_loss += float(loss.detach().to("cpu"))
                    win_tok += k
                    break
                except RuntimeError as exc:
                    if not _is_oom(exc):
                        raise
                    loss = None
                    opt.zero_grad()
                    gc.collect()
                    log(f"OOM on a {len(ids)}-token row at len {attempt_len}: retrying shorter")
            micro += 1
            if micro % recipe.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(params, recipe.max_grad_norm)
                opt.step(); sched.step(); opt.zero_grad()
                step += 1
                if step in (1, 2, 5) or step % 5 == 0 or (args.max_steps and step <= args.max_steps):
                    rate = (time.time() - t0) / step
                    full = math.ceil(len(train_rows) / recipe.grad_accum) * recipe.epochs
                    v = _vram_gb()
                    peak = max(peak or 0, v or 0) or None
                    log(f"ep {ep + 1} step {step}/{total} loss {win_loss / max(win_tok, 1):.4f} "
                        f"lr {sched.get_last_lr()[0]:.2e} {rate:.1f}s/step vram {v}GB "
                        f"eta(full {full} steps) {rate * (full - step) / 60:.0f} min")
                win_loss, win_tok = 0.0, 0
                if args.max_steps and step >= args.max_steps:
                    done = True
                    break
        if done:
            if args.eval_smoke:
                el = eval_loss(model, tok, eval_rows[: args.eval_rows or None], max_len, device)
                log(f"smoke eval_loss {el:.4f}")
                history.append({"epoch": ep + 1, "eval_loss": el, "step": step})
            break
        if micro % recipe.grad_accum:
            torch.nn.utils.clip_grad_norm_(params, recipe.max_grad_norm)
            opt.step(); sched.step(); opt.zero_grad(); step += 1
        el = eval_loss(model, tok, eval_rows, max_len, device)
        history.append({"epoch": ep + 1, "eval_loss": el, "step": step})
        log(f"epoch {ep + 1} eval_loss {el:.4f}")
        if el < best:
            best = el
            model.save_pretrained(str(out / "adapter_best"))
            tok.save_pretrained(str(out / "adapter_best"))
    if not args.max_steps:
        model.save_pretrained(str(out / "adapter_last"))
    return {"device": dev_name, "max_len": max_len, "best_eval_loss": best, "history": history, "steps": step,
            "skipped_rows": skipped, "peak_vram_gb": peak, "sec_per_step": (time.time() - t0) / max(step, 1),
            "smoke": bool(args.max_steps)}


def train(args, recipe: Recipe) -> int:
    p = plan(args, recipe)
    if not p["ok"]:
        print(json.dumps(p, indent=2)); return 2
    out = _inside_home(Path(args.out)); out.mkdir(parents=True, exist_ok=True)
    logf = (out / "train.log").open("a", encoding="utf-8")

    def log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True); logf.write(line + "\n"); logf.flush()

    last = None
    for n in p["len_backoff"]:
        try:
            res = _train_once(args, recipe, n, log)
            res.update(recipe=asdict(recipe), dataset=p["dataset"], base_license=BASE_LICENSE)
            name = "smoke_result.json" if args.max_steps else "train_result.json"
            (out / name).write_text(json.dumps(res, indent=2), encoding="utf-8")
            if args.max_steps:
                log(f"smoke done ({res['steps']} steps, {res['sec_per_step']:.1f}s/step) -> {out / name}; no adapter saved")
            else:
                log(f"done best_eval_loss={res['best_eval_loss']:.4f} -> {out / 'adapter_best'}")
            return 0
        except Exception as exc:  # DirectML OOM -> shorter sequences
            if not _is_oom(exc):
                raise
            last = exc
            log(f"OOM at max_len={n}: {str(exc)[:160]} - backing off")
            import gc; gc.collect()
    log(f"OOM even at 512: {last}")
    return 3


def evaluate(args, recipe: Recipe) -> int:
    from peft import PeftModel
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out = _inside_home(Path(args.out))
    res = json.loads((out / "train_result.json").read_text(encoding="utf-8"))
    max_len = res["max_len"]
    device, dev_name = pick_device(recipe.device, recipe.dml_adapter)
    rows = load_rows(Path(args.dataset) / "eval.jsonl")
    tok = AutoTokenizer.from_pretrained(recipe.base_model)
    dtype = torch.float32
    base = AutoModelForCausalLM.from_pretrained(recipe.base_model, torch_dtype=dtype).to(device)
    base_loss = eval_loss(base, tok, rows, max_len, device)
    tuned = PeftModel.from_pretrained(base, str(out / "adapter_best")).to(device)
    tuned_loss = eval_loss(tuned, tok, rows, max_len, device)
    rel = (base_loss - tuned_loss) / base_loss if base_loss else 0.0
    passed = rel >= PASS_BAR["min_rel_improvement"] and tuned_loss <= PASS_BAR["max_eval_loss"]
    rep = {"base_eval_loss": base_loss, "tuned_eval_loss": tuned_loss, "rel_improvement": rel,
           "pass_bar": PASS_BAR, "passed": passed, "eval_rows": len(rows), "max_len": max_len, "device": dev_name}
    (out / "eval_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))
    return 0 if passed else 1


def export(args, recipe: Recipe) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import train_to_chat_gguf as t2g  # existing merge/convert/quantize helpers

    out = _inside_home(Path(args.out))
    merged = t2g.merge_adapter(recipe.base_model, out / "adapter_best", out / "merged")
    f16 = t2g.convert_to_gguf(merged, out / "gguf" / f"{args.model_id}-f16.gguf")
    q = t2g.quantize_gguf(f16, out / "gguf" / f"{args.model_id}-{args.quant}.gguf", args.quant)
    print(json.dumps({"gguf": str(q), "sha256": sha256_file(q)}, indent=2))
    return 0


def register(args, recipe: Recipe) -> int:
    out = _inside_home(Path(args.out))
    tr = json.loads((out / "train_result.json").read_text(encoding="utf-8"))
    ev_p = out / "eval_report.json"
    ev = json.loads(ev_p.read_text(encoding="utf-8")) if ev_p.is_file() else None
    gguf = out / "gguf" / f"{args.model_id}-{args.quant}.gguf"
    entry = {
        "id": args.model_id, "base_model": recipe.base_model, "base_license": BASE_LICENSE,
        "trained": True, "method": "lora-sft merged", "quant": args.quant,
        "gguf_path": str(gguf) if gguf.is_file() else None,
        "gguf_sha256": sha256_file(gguf) if gguf.is_file() else None,
        "dataset": tr["dataset"]["dir"], "dataset_manifest_sha256": tr["dataset"]["manifest_sha256"],
        "best_eval_loss": tr["best_eval_loss"], "eval": ev,
        "status": "candidate-passed" if ev and ev.get("passed") else "candidate-not-passed",
        "default": False, "loaded_now": False,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    cat_p = _inside_home(realai_home() / "models" / "trained_catalog.json")
    cat_p.parent.mkdir(parents=True, exist_ok=True)
    cat = json.loads(cat_p.read_text(encoding="utf-8")) if cat_p.is_file() else {"models": []}
    cat["models"] = [m for m in cat["models"] if m.get("id") != args.model_id] + [entry]
    cat_p.write_text(json.dumps(cat, indent=2), encoding="utf-8")
    print(json.dumps(entry, indent=2))
    return 0


# ----------------------------------------------------------------------------- cli
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m realai.training.train_sft", description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["plan", "train", "eval", "export", "register"])
    ap.add_argument("--dataset", required=True, help="dataset_builder output dir (train.jsonl, eval.jsonl, manifest.json)")
    ap.add_argument("--out", default=None, help="run dir (default REALAI_HOME/runs/sft-<dataset name>)")
    ap.add_argument("--dry-run", action="store_true", help="validate data and print plan; no model load")
    ap.add_argument("--base-model", default=BASE_MODEL)
    ap.add_argument("--max-len", type=int, default=1024, choices=LEN_BACKOFF)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--device", default="auto", choices=["auto", "directml", "cuda", "cpu"])
    ap.add_argument("--dml-adapter", default="RX 6700", help="substring of the DirectML adapter name")
    ap.add_argument("--max-steps", type=int, default=0, help="smoke: stop after N optimizer steps (no adapter saved)")
    ap.add_argument("--eval-smoke", action="store_true", help="with --max-steps: eval loss before/after on --eval-rows")
    ap.add_argument("--eval-rows", type=int, default=0, help="limit eval rows (0 = all)")
    ap.add_argument("--model-id", default="realai-sft-1.5b")
    ap.add_argument("--quant", default="Q5_K_M")
    return ap


def recipe_from(args) -> Recipe:
    return Recipe(base_model=args.base_model, max_len=args.max_len, epochs=args.epochs, lr=args.lr,
                  grad_accum=args.grad_accum, batch_size=args.batch_size, lora_r=args.lora_r,
                  lora_alpha=args.lora_alpha, device=args.device, dml_adapter=args.dml_adapter)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.out is None:
        args.out = str(realai_home() / "runs" / f"sft-{Path(args.dataset).resolve().name}")
    _inside_home(Path(args.out))
    recipe = recipe_from(args)
    if args.command == "plan" or args.dry_run:
        p = plan(args, recipe)
        print(json.dumps(p, indent=2))
        return 0 if p["ok"] else 2
    return {"train": train, "eval": evaluate, "export": export, "register": register}[args.command](args, recipe)


if __name__ == "__main__":
    raise SystemExit(main())
