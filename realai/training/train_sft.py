"""RealAI fixed SFT recipe: Qwen2.5-1.5B-Instruct + LoRA on a dataset_builder output.

Fixes the old runs (64-token seq, 40-60 steps, duplicated data, loss on prompt tokens):
  * Qwen chat template, loss on assistant tokens only
  * max_len 1024 (DirectML OOM backoff 1024 -> 768 -> 512; never below 512)
  * LoRA r16 / alpha32 / dropout 0.05 on q,k,v,o + gate,up,down
  * AdamW lr 1e-4, cosine, 3% warmup, 3 epochs, grad accumulation
  * eval loss on eval.jsonl every epoch, best adapter kept
  * DirectML adapter picked BY NAME (default "RX 6700"), never silently the Vega iGPU
  * --dtype float32 (default, stable on DirectML) or float16/bfloat16 (for 3B on 12 GB); alias of --base-dtype

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
    base_dtype: str = "fp32"  # frozen base weights; LoRA params, optimizer state and loss stay fp32
    ce_chunk: int = 256  # CE over target positions in checkpointed chunks (0 = all at once)


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
        if "assistant" not in roles or any(x not in {"system", "user", "assistant", "tool"} for x in roles):
            raise ValueError(f"{path.name}:{i} bad roles {roles}")
        if any(not str(m.get("content", "")).strip() and not m.get("tool_calls") for m in msgs):
            raise ValueError(f"{path.name}:{i} empty content")
        if "tool" in roles and not r.get("tools"):
            raise ValueError(f"{path.name}:{i} tool messages without row.tools")
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


def _tmpl(tok, msgs, gen=False, tools=None) -> List[int]:
    if not msgs:
        return []
    kw = {"tools": tools} if tools else {}
    r = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=gen, **kw)
    if hasattr(r, "keys") and "input_ids" in r:  # transformers >= 5 returns BatchEncoding
        r = r["input_ids"]
    return list(r)


def encode_assistant_only(tok, messages: List[Dict[str, Any]], max_len: int, tools=None):
    """input_ids + labels where only assistant-turn tokens are trained (-100 elsewhere).

    Tool rows: pass ``tools`` (row["tools"]); assistant tool-call turns are targets, role=tool output is
    prompt (never trained). Prefix rendering: tokens added by message i belong to message i. Truncated from the left
    of the prompt is avoided; overly long rows are cut at max_len (labels kept aligned)."""
    ids: List[int] = []
    labels: List[int] = []
    prev: List[int] = []
    for i, m in enumerate(messages):
        cur = _tmpl(tok, messages[: i + 1], tools=tools)
        if m["role"] == "assistant":
            # the "<|im_start|>assistant\n" header is prompt, not target
            head = _tmpl(tok, messages[:i], gen=True, tools=tools)
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


# ----------------------------------------------------------------------------- dtype / memory
DTYPE_BYTES = {"fp32": 4, "fp16": 2, "bf16": 2}
# --dtype (PC launcher spelling, e.g. train_3b.bat --dtype float16) -> --base-dtype
DTYPE_MAP = {"float32": "fp32", "float16": "fp16", "bfloat16": "bf16"}


def torch_dtype(name: str):
    import torch

    return {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[name]


def dtype_probe(device, name: str) -> List[str]:
    """Run the ops training needs at `name` precision on `device` and compare to CPU fp32.

    Returns failures ([] = usable). Covers matmul/linear, RMSNorm (pow/mean/rsqrt), RoPE-style mul/cat,
    softmax/SDPA, SiLU, embedding, index_select, fp32 upcast + logsumexp/gather CE, and a backward pass
    through an fp32 LoRA branch over a frozen low-precision weight."""
    import torch
    import torch.nn.functional as F

    if name == "fp32":
        return []
    dt = torch_dtype(name)
    g = torch.Generator().manual_seed(0)
    x = torch.randn(8, 64, generator=g)
    W = torch.randn(96, 64, generator=g) * 0.1
    A = torch.randn(4, 64, generator=g) * 0.1
    B = torch.randn(96, 4, generator=g) * 0.1
    emb = torch.randn(50, 64, generator=g)
    tgt = torch.randint(0, 96, (8,), generator=g)

    def run(dev, d):
        xd, Wd, embd = x.to(dev, d), W.to(dev, d), emb.to(dev, d)
        Ad = A.to(dev).clone().requires_grad_(True)
        Bd = B.to(dev).clone().requires_grad_(True)
        h = embd.index_select(0, torch.arange(8, device=dev)) + xd
        h = h * torch.rsqrt(h.float().pow(2).mean(-1, keepdim=True) + 1e-6).to(d)
        h = torch.cat([h[:, 32:] * -1, h[:, :32]], dim=-1) * 0.5 + h * 0.5
        q = h.view(1, 2, 8, 32)
        att = F.scaled_dot_product_attention(q, q, q, is_causal=True).reshape(8, 64)
        y = F.linear(att, Wd) + (F.linear(F.linear(att.float(), Ad), Bd)).to(d)
        y = F.silu(y)
        lg = y.float()
        nll = torch.logsumexp(lg, -1) - lg.gather(1, tgt.to(dev)[:, None]).squeeze(1)
        loss = nll.mean()
        loss.backward()
        return float(loss.detach().to("cpu")), Ad.grad.detach().to("cpu"), Bd.grad.detach().to("cpu")

    fails = []
    try:
        ref = run("cpu", torch.float32)
        got = run(device, dt)
    except Exception as exc:
        return [f"{name}: {type(exc).__name__}: {str(exc)[:120]}"]
    if not torch.isfinite(torch.tensor(got[0])) or abs(got[0] - ref[0]) > 0.05 * max(1.0, abs(ref[0])):
        fails.append(f"{name}: loss {got[0]:.4f} vs cpu {ref[0]:.4f}")
    for nm, a, b in (("grad_A", got[1], ref[1]), ("grad_B", got[2], ref[2])):
        if not torch.isfinite(a).all():
            fails.append(f"{name}: {nm} non-finite")
        elif (a - b).norm() > 0.1 * (b.norm() + 1e-6):
            fails.append(f"{name}: {nm} rel err {float((a - b).norm() / (b.norm() + 1e-6)):.3f}")
    return fails


def choose_dtype(device, wanted: str, log=print) -> str:
    """wanted -> first of [wanted, fp16, fp32] that passes the probe on this device (CPU never uses fp16)."""
    order = [wanted] + [d for d in ("fp16", "fp32") if d != wanted]
    if str(device) == "cpu":
        order = [d for d in order if d != "fp16"]
    for d in order:
        f = dtype_probe(device, d)
        if not f:
            if d != wanted:
                log(f"base dtype {wanted} not usable on {device}; falling back to {d}")
            return d
        log(f"dtype probe failed: {'; '.join(f)}")
    return "fp32"


def read_model_config(base_model: str) -> Optional[Dict[str, Any]]:
    from realai.training.hf_paths import resolve_model_path

    p = Path(resolve_model_path(base_model)) / "config.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


# DirectML allocator caching + desktop on the same adapter: measured 1.5B fp32 @1024 peak 11.91 GB vs ~8.9 GB modelled.
DML_OVERHEAD_GB = 3.0


def estimate_memory(cfg: Dict[str, Any], base_dtype: str, max_len: int, lora_r: int, targets: List[str],
                    ce_chunk: int = 256, vram_gb: float = 12.0) -> Dict[str, Any]:
    h, L, I = cfg["hidden_size"], cfg["num_hidden_layers"], cfg["intermediate_size"]
    V, nh = cfg["vocab_size"], cfg["num_attention_heads"]
    kv = cfg.get("num_key_value_heads", nh) * (h // nh)
    tied = cfg.get("tie_word_embeddings", False)
    per_layer = h * h * 2 + h * kv * 2 + 3 * h * I + 2 * h
    n_params = V * h * (1 if tied else 2) + L * per_layer + h
    shapes = {"q_proj": (h, h), "k_proj": (h, kv), "v_proj": (h, kv), "o_proj": (h, h),
              "gate_proj": (h, I), "up_proj": (h, I), "down_proj": (I, h)}
    n_lora = L * sum(lora_r * (i + o) for t, (i, o) in shapes.items() if t in targets)
    b = DTYPE_BYTES[base_dtype]
    S = max_len
    gb = 1e9
    weights = n_params * b / gb
    lora = n_lora * 16 / gb  # fp32 param + grad + adam m + v
    act = (L * S * h * b + S * (12 * h + 6 * I) * b + nh * S * S * b * 3) / gb  # checkpointed layer inputs + one live layer
    logits = (min(ce_chunk or S, S)) * V * 4 * 3 / gb  # fp32 logits, logsumexp, grad
    model = weights + lora + act + logits
    total = model + DML_OVERHEAD_GB
    return {"params_b": round(n_params / 1e9, 2), "lora_params_m": round(n_lora / 1e6, 1), "base_dtype": base_dtype,
            "max_len": S, "ce_chunk": ce_chunk, "weights_gb": round(weights, 2), "lora_optim_gb": round(lora, 2),
            "activations_gb": round(act, 2), "logits_gb": round(logits, 2), "dml_overhead_gb": DML_OVERHEAD_GB,
            "est_peak_gb": round(total, 1), "vram_gb": vram_gb, "fits": total <= vram_gb * 0.95,
            "note": "estimate; peak calibrated on 1.5B fp32 DirectML run (11.9 GB). Needs :8080/:8081 stopped."}


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
    cfg = read_model_config(recipe.base_model)
    if cfg:
        out["memory"] = {d: estimate_memory(cfg, d, recipe.max_len, recipe.lora_r, recipe.lora_targets, recipe.ce_chunk,
                                            getattr(args, "vram_gb", 12.0)) for d in dict.fromkeys([recipe.base_dtype, "fp16", "fp32"])}
        out["memory_note"] = (f"{recipe.base_dtype}: est. peak {out['memory'][recipe.base_dtype]['est_peak_gb']} GB of "
                              f"{getattr(args, 'vram_gb', 12.0)} GB -> {'fits' if out['memory'][recipe.base_dtype]['fits'] else 'WILL LIKELY OOM'}")
    else:
        out["memory_note"] = f"no config.json for {recipe.base_model} (hub id or missing path); memory not estimated"
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


def sft_loss(model, ids: List[int], labels: List[int], device, ce_chunk: int = 0):
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
    tgt = torch.tensor([labels[t + 1] for t in pos], device=device)

    def ce(hh, tt):
        logits = head(hh).float()  # loss always in fp32, whatever the base dtype
        return (torch.logsumexp(logits, dim=-1) - logits.gather(1, tt[:, None]).squeeze(1)).sum()

    if not ce_chunk or len(pos) <= ce_chunk or not torch.is_grad_enabled():
        return ce(h, tgt), len(pos)
    from torch.utils.checkpoint import checkpoint

    tot = None
    for i in range(0, len(pos), ce_chunk):  # logits [chunk, vocab] recomputed in backward instead of held
        part = checkpoint(ce, h[i:i + ce_chunk], tgt[i:i + ce_chunk], use_reentrant=False)
        tot = part if tot is None else tot + part
    return tot, len(pos)


def _encode_all(rows, tok, max_len):
    out = []
    for r in rows:
        ids, lab = encode_assistant_only(tok, r["messages"], max_len, tools=r.get("tools"))
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


def save_adapter(model, tok, dest: Path) -> Path:
    """Standard PEFT adapter dir from a model living on any device (DirectML tensors are opaque:
    PeftModel.save_pretrained -> safetensors cannot read their storage). Copies LoRA weights to CPU."""
    from peft import get_peft_model_state_dict
    from safetensors.torch import save_file

    dest = _inside_home(Path(dest))
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    sd = {k: v.detach().to("cpu").contiguous().clone() for k, v in get_peft_model_state_dict(model).items()}
    save_file(sd, str(tmp / "adapter_model.safetensors"), metadata={"format": "pt"})
    model.peft_config["default"].save_pretrained(str(tmp))
    if tok is not None:
        tok.save_pretrained(str(tmp))
    if dest.exists():
        import shutil

        shutil.rmtree(dest)
    tmp.replace(dest)
    return dest


def load_adapter_weights(model, src: Path) -> None:
    """Load adapter_model.safetensors into an existing PEFT model (before or after .to(device))."""
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file

    res = set_peft_model_state_dict(model, load_file(str(Path(src) / "adapter_model.safetensors")))
    bad = [k for k in getattr(res, "unexpected_keys", []) or []]
    if bad:
        raise RuntimeError(f"adapter keys not in model: {bad[:3]}")


def save_checkpoint(out: Path, model, tok, opt, sched, state: Dict[str, Any]) -> Path:
    """ckpt-ep<N>/: adapter + optimizer moments (CPU) + trainer state; latest pointer in checkpoint.json."""
    import torch

    d = save_adapter(model, tok, out / f"ckpt-ep{state['epoch']}")
    torch.save({"t": opt.t, "m": [x.detach().to("cpu").clone() for x in opt.m],
                "v": [x.detach().to("cpu").clone() for x in opt.v], "sched_n": sched.n}, str(d / "optimizer.pt"))
    (d / "trainer_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    (out / "checkpoint.json").write_text(json.dumps({"latest": d.name, **state}, indent=2), encoding="utf-8")
    return d


def load_checkpoint(d: Path, model, opt, sched) -> Dict[str, Any]:
    import torch

    load_adapter_weights(model, d)
    o = torch.load(str(d / "optimizer.pt"), map_location="cpu")
    opt.t = o["t"]
    for dst, src in zip(opt.m, o["m"]):
        dst.copy_(src.to(dst.device))
    for dst, src in zip(opt.v, o["v"]):
        dst.copy_(src.to(dst.device))
    sched.n = o["sched_n"]
    sched._set()
    return json.loads((d / "trainer_state.json").read_text(encoding="utf-8"))


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
    from realai.training.hf_paths import resolve_model_path

    base_path = resolve_model_path(recipe.base_model)
    tok = AutoTokenizer.from_pretrained(base_path)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    # Frozen base in --base-dtype (probed on this device; falls back fp16 -> fp32). LoRA params, Adam state and
    # the CE loss stay fp32. fp32 is the proven 1.5B setting; fp16 halves weight memory for 3B on 12 GB.
    bdt = choose_dtype(device, recipe.base_dtype, log)
    log(f"base={base_path} base_dtype={bdt} ce_chunk={recipe.ce_chunk}")
    model = AutoModelForCausalLM.from_pretrained(base_path, torch_dtype=torch_dtype(bdt))
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=recipe.lora_r, lora_alpha=recipe.lora_alpha,
                                             lora_dropout=recipe.lora_dropout, target_modules=recipe.lora_targets,
                                             bias="none", task_type="CAUSAL_LM"))
    for n_, p_ in model.named_parameters():  # trainable LoRA weights in fp32 regardless of base dtype
        if p_.requires_grad and p_.dtype != torch.float32:
            p_.data = p_.data.float()
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
    start_ep = 0
    if args.resume:
        ck = out / "checkpoint.json"
        rdir = Path(args.resume) if args.resume != "auto" else (out / json.loads(ck.read_text())["latest"] if ck.is_file() else None)
        if rdir and rdir.is_dir():
            st = load_checkpoint(rdir, model, opt, sched)
            start_ep, step, best, history = st["epoch"], st["step"], st["best"], st["history"]
            log(f"resumed from {rdir.name}: epoch {start_ep} done, step {step}, best {best:.4f}")
        else:
            log("resume requested but no checkpoint found; starting fresh")
    win_loss, win_tok = 0.0, 0
    nonfinite = 0
    done = False
    for ep in range(start_ep, recipe.epochs):
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
                    loss, k = sft_loss(model, i2, l2, device, recipe.ce_chunk)
                    if not k:
                        break
                    if not math.isfinite(float(loss.detach().to("cpu"))):
                        nonfinite += 1
                        opt.zero_grad()
                        log(f"non-finite loss ({bdt}) on a {len(i2)}-token row; skipped (n={nonfinite})")
                        if nonfinite >= 5 and nonfinite > 0.02 * max(micro, 1):
                            raise RuntimeError(f"too many non-finite losses with base dtype {bdt}; rerun with --base-dtype fp32 "
                                               "(or a shorter --max-len) - fp16 activations overflowed")
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
            if args.save_smoke:
                d = save_checkpoint(out, model, tok, opt, sched, {"epoch": 0, "step": step, "best": best, "history": history})
                log(f"smoke checkpoint saved -> {d}")
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
            save_adapter(model, tok, out / "adapter_best")
            log(f"saved adapter_best (eval_loss {el:.4f})")
        save_checkpoint(out, model, tok, opt, sched, {"epoch": ep + 1, "step": step, "best": best, "history": history})
        log(f"checkpoint ckpt-ep{ep + 1} saved (resume with --resume auto)")
    if not args.max_steps:
        save_adapter(model, tok, out / "adapter_last")
    return {"device": dev_name, "max_len": max_len, "best_eval_loss": best, "history": history, "steps": step,
            "skipped_rows": skipped, "peak_vram_gb": peak, "sec_per_step": (time.time() - t0) / max(step, 1),
            "smoke": bool(args.max_steps), "base_dtype": bdt, "nonfinite_rows": nonfinite}


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
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
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
                from realai.training import ledger
                ledger.safe(ledger.on_train, out, res, started=started, model_id=args.model_id)
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
    from realai.training.hf_paths import resolve_model_path

    base_path = resolve_model_path(recipe.base_model)
    tok = AutoTokenizer.from_pretrained(base_path)
    dtype = torch_dtype(res.get("base_dtype") or DTYPE_MAP.get(res.get("dtype", ""), "") or recipe.base_dtype)
    base = AutoModelForCausalLM.from_pretrained(base_path, torch_dtype=dtype).to(device)
    base_loss = eval_loss(base, tok, rows, max_len, device)
    base = base.to("cpu")  # attach LoRA on CPU (plain tensors), then move as one module
    tuned = PeftModel.from_pretrained(base, str(out / "adapter_best")).to(device)
    tuned_loss = eval_loss(tuned, tok, rows, max_len, device)
    rel = (base_loss - tuned_loss) / base_loss if base_loss else 0.0
    passed = rel >= PASS_BAR["min_rel_improvement"] and tuned_loss <= PASS_BAR["max_eval_loss"]
    rep = {"base_eval_loss": base_loss, "tuned_eval_loss": tuned_loss, "rel_improvement": rel,
           "pass_bar": PASS_BAR, "passed": passed, "eval_rows": len(rows), "max_len": max_len, "device": dev_name}
    (out / "eval_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))
    from realai.training import ledger
    ledger.safe(ledger.on_eval, out, rep)
    return 0 if passed else 1


def export(args, recipe: Recipe) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import train_to_chat_gguf as t2g  # existing merge/convert/quantize helpers

    out = _inside_home(Path(args.out))
    from realai.training.hf_paths import resolve_model_path

    merged = t2g.merge_adapter(resolve_model_path(recipe.base_model), out / "adapter_best", out / "merged")
    f16 = t2g.convert_to_gguf(merged, out / "gguf" / f"{args.model_id}-f16.gguf")
    q = t2g.quantize_gguf(f16, out / "gguf" / f"{args.model_id}-{args.quant}.gguf", args.quant)
    sha = sha256_file(q)
    print(json.dumps({"gguf": str(q), "sha256": sha}, indent=2))
    from realai.training import ledger
    ledger.safe(ledger.on_export, out, q, args.quant, args.model_id, sha)
    return 0


def register(args, recipe: Recipe) -> int:
    out = _inside_home(Path(args.out))
    tr = json.loads((out / "train_result.json").read_text(encoding="utf-8"))
    ev_p = out / "eval_report.json"
    ev = json.loads(ev_p.read_text(encoding="utf-8")) if ev_p.is_file() else None
    gguf = out / "gguf" / f"{args.model_id}-{args.quant}.gguf"
    sc = None
    sc_p = Path(args.spotcheck) if getattr(args, "spotcheck", None) else None
    if sc_p is None:
        cands = sorted((realai_home() / "runs").glob("spotcheck-*.json"), key=lambda p: p.stat().st_mtime) if (realai_home() / "runs").is_dir() else []
        sc_p = cands[-1] if cands else None
    if sc_p and sc_p.is_file():
        sc = json.loads(sc_p.read_text(encoding="utf-8"))
    min_pass = float(getattr(args, "min_pass", 0.8))
    want_default = bool(getattr(args, "default", False))
    if want_default and (not sc or float(sc.get("pass_rate", 0)) < min_pass):
        got = "no spot-check report" if not sc else f"spot-check pass rate {sc.get('pass_rate')}"
        print(f"REFUSED: --default needs spot-check pass rate >= {min_pass} ({got}). Run python -m realai.training.spotcheck first.")
        return 2
    entry = {
        "id": args.model_id, "base_model": recipe.base_model, "base_license": BASE_LICENSE,
        "trained": True, "method": "lora-sft merged", "quant": args.quant,
        "gguf_path": str(gguf) if gguf.is_file() else None,
        "gguf_sha256": sha256_file(gguf) if gguf.is_file() else None,
        "dataset": tr["dataset"]["dir"], "dataset_manifest_sha256": tr["dataset"]["manifest_sha256"],
        "best_eval_loss": tr["best_eval_loss"], "eval": ev,
        "status": ("promoted" if want_default else "candidate-passed") if ev and ev.get("passed") and sc and float(sc.get("pass_rate", 0)) >= min_pass
        else "candidate-not-passed",
        "spotcheck": {"report": str(sc_p), "pass_rate": sc.get("pass_rate"), "passed": sc.get("passed"), "n": sc.get("n"),
                      "min_pass": min_pass} if sc else None,
        "default": want_default, "loaded_now": False,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    cat_p = _inside_home(realai_home() / "models" / "trained_catalog.json")
    cat_p.parent.mkdir(parents=True, exist_ok=True)
    cat = json.loads(cat_p.read_text(encoding="utf-8")) if cat_p.is_file() else {"models": []}
    cat["models"] = [m for m in cat["models"] if m.get("id") != args.model_id] + [entry]
    cat_p.write_text(json.dumps(cat, indent=2), encoding="utf-8")
    print(json.dumps(entry, indent=2))
    from realai.training import ledger
    ledger.safe(ledger.on_register, out, entry)
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
    ap.add_argument("--base-dtype", default="fp32", choices=["fp32", "fp16", "bf16"],
                    help="frozen base precision (LoRA/optimizer/loss stay fp32); probed on device, falls back fp16 -> fp32")
    ap.add_argument("--dtype", default=None, choices=list(DTYPE_MAP),
                    help="alias of --base-dtype: float32 (stable on DirectML, fits 1.5B), float16/bfloat16 (needed for 3B on 12GB)")
    ap.add_argument("--ce-chunk", type=int, default=256, help="CE over target tokens in checkpointed chunks (0 = off)")
    ap.add_argument("--vram-gb", type=float, default=12.0, help="dry-run: GPU memory to plan against")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--device", default="auto", choices=["auto", "directml", "cuda", "cpu"])
    ap.add_argument("--dml-adapter", default="RX 6700", help="substring of the DirectML adapter name")
    ap.add_argument("--spotcheck", help="register: spot-check report (default newest REALAI_HOME/runs/spotcheck-*.json)")
    ap.add_argument("--min-pass", type=float, default=0.8, help="register: spot-check pass rate needed for --default")
    ap.add_argument("--default", action="store_true", help="register as default (refused unless spot-check >= --min-pass)")
    ap.add_argument("--max-steps", type=int, default=0, help="smoke: stop after N optimizer steps (no adapter saved)")
    ap.add_argument("--eval-smoke", action="store_true", help="with --max-steps: eval loss before/after on --eval-rows")
    ap.add_argument("--save-smoke", action="store_true", help="with --max-steps: write a checkpoint (tests the save path)")
    ap.add_argument("--resume", default="", help="'auto' (latest ckpt in --out) or a ckpt-ep<N> dir")
    ap.add_argument("--eval-rows", type=int, default=0, help="limit eval rows (0 = all)")
    ap.add_argument("--model-id", default="realai-sft-1.5b")
    ap.add_argument("--quant", default="Q5_K_M")
    return ap


def recipe_from(args) -> Recipe:
    return Recipe(base_model=args.base_model, max_len=args.max_len, epochs=args.epochs, lr=args.lr,
                  grad_accum=args.grad_accum, batch_size=args.batch_size, lora_r=args.lora_r,
                  lora_alpha=args.lora_alpha, device=args.device, dml_adapter=args.dml_adapter,
                  base_dtype=DTYPE_MAP[args.dtype] if getattr(args, "dtype", None) else args.base_dtype,
                  ce_chunk=args.ce_chunk)


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
