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
    return any(k in s for k in ("out of memory", "not enough memory", "failed to allocate", "e_outofmemory", "887a0005", "device removed"))


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
def _batches(rows, tok, max_len, bs, shuffle, seed):
    order = list(range(len(rows)))
    if shuffle:
        random.Random(seed).shuffle(order)
    enc = []
    for i in order:
        ids, lab = encode_assistant_only(tok, rows[i]["messages"], max_len)
        if any(x != -100 for x in lab):
            enc.append((ids, lab))
    for k in range(0, len(enc), bs):
        chunk = enc[k: k + bs]
        L = max(len(c[0]) for c in chunk)
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        yield ([c[0] + [pad] * (L - len(c[0])) for c in chunk],
               [c[1] + [-100] * (L - len(c[1])) for c in chunk],
               [[1] * len(c[0]) + [0] * (L - len(c[0])) for c in chunk])


def eval_loss(model, tok, rows, max_len, device) -> float:
    import torch

    model.eval()
    tot, n = 0.0, 0
    with torch.no_grad():
        for ids, lab, att in _batches(rows, tok, max_len, 1, False, 0):
            t = lambda x: torch.tensor(x, device=device)
            out = model(input_ids=t(ids), attention_mask=t(att), labels=t(lab))
            k = sum(1 for x in lab[0][1:] if x != -100)
            tot += float(out.loss.detach().to("cpu")) * k
            n += k
    model.train()
    return tot / max(n, 1)


def _train_once(args, recipe: Recipe, max_len: int, log) -> Dict[str, Any]:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

    torch.manual_seed(recipe.seed)
    device, dev_name = pick_device(recipe.device, recipe.dml_adapter)
    log(f"device={dev_name} max_len={max_len}")
    ds = Path(args.dataset)
    train_rows, eval_rows = load_rows(ds / "train.jsonl"), load_rows(ds / "eval.jsonl")
    tok = AutoTokenizer.from_pretrained(recipe.base_model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    dtype = torch.float32 if dev_name == "cpu" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(recipe.base_model, torch_dtype=dtype)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=recipe.lora_r, lora_alpha=recipe.lora_alpha,
                                             lora_dropout=recipe.lora_dropout, target_modules=recipe.lora_targets,
                                             bias="none", task_type="CAUSAL_LM"))
    for p in model.parameters():  # trainable LoRA weights in fp32 for stable AdamW
        if p.requires_grad:
            p.data = p.data.float()
    model.to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=recipe.lr, weight_decay=recipe.weight_decay, foreach=False)
    eff = recipe.batch_size * recipe.grad_accum
    total = math.ceil(len(train_rows) / eff) * recipe.epochs
    sched = get_cosine_schedule_with_warmup(opt, max(1, int(total * recipe.warmup_ratio)), total)
    out = _inside_home(Path(args.out))
    out.mkdir(parents=True, exist_ok=True)
    best, history, step, t0 = float("inf"), [], 0, time.time()
    for ep in range(recipe.epochs):
        micro = 0
        for ids, lab, att in _batches(train_rows, tok, max_len, recipe.batch_size, True, recipe.seed + ep):
            t = lambda x: torch.tensor(x, device=device)
            loss = model(input_ids=t(ids), attention_mask=t(att), labels=t(lab)).loss / recipe.grad_accum
            loss.backward()
            micro += 1
            if micro % recipe.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(params, recipe.max_grad_norm)
                opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
                step += 1
                if step % 5 == 0 or step == 1:
                    rate = (time.time() - t0) / step
                    log(f"ep {ep + 1} step {step}/{total} loss {float(loss.detach().to('cpu')) * recipe.grad_accum:.4f} "
                        f"lr {sched.get_last_lr()[0]:.2e} {rate:.1f}s/step eta {rate * (total - step) / 60:.0f} min")
        if micro % recipe.grad_accum:
            torch.nn.utils.clip_grad_norm_(params, recipe.max_grad_norm)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True); step += 1
        el = eval_loss(model, tok, eval_rows, max_len, device)
        history.append({"epoch": ep + 1, "eval_loss": el, "step": step})
        log(f"epoch {ep + 1} eval_loss {el:.4f}")
        if el < best:
            best = el
            model.save_pretrained(str(out / "adapter_best"))
            tok.save_pretrained(str(out / "adapter_best"))
    model.save_pretrained(str(out / "adapter_last"))
    return {"device": dev_name, "max_len": max_len, "best_eval_loss": best, "history": history, "steps": step}


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
            (out / "train_result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
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
    dtype = torch.float32 if dev_name == "cpu" else torch.float16
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
