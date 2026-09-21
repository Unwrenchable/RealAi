#!/usr/bin/env python3
"""
RealAI v3 Orchestrator
======================
Sits between the Next.js UI and AMD Vulkan llama-server.

  UI :3000  →  orchestrator :8001  →  Vulkan llama-server :8080

Also exposes training + self-improve endpoints wired to:
  - training/data/*.jsonl (Phase-2 promoted gold)
  - realai.self_improvement (gated by REALAI_SELF_IMPROVE)

Run:
  set REALAI_VULKAN_BASE=http://127.0.0.1:8080
  set REALAI_SELF_IMPROVE=true   # optional
  python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

# Repo root: .../realai package parent
_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Product home (C:\RealAI-clean): fusion-ui is a sibling of the realai/ package.
_REPO_HOME = _ROOT.parent if (_ROOT.parent / "fusion-ui").is_dir() else _ROOT


def _resolve_fusion_ui_dir() -> Optional[Path]:
    """Locate Fusion UI static tree. Prefer product-home fusion-ui/ (same as api_server)."""
    candidates = [
        Path(os.environ.get("REALAI_ROOT") or "") / "fusion-ui",
        _REPO_HOME / "fusion-ui",
        _ROOT.parent / "fusion-ui",
        Path(os.environ.get("REALAI_HOME") or "") / "fusion-ui",
        _REPO_HOME / "apps" / "fusion-ui",
        _ROOT / "fusion-ui",
    ]
    seen: set[str] = set()
    for p in candidates:
        if not p or str(p) in seen:
            continue
        seen.add(str(p))
        if p.is_dir() and (p / "index.html").is_file():
            return p.resolve()
    return None


_FUSION_UI_DIR = _resolve_fusion_ui_dir()


def _resolve_agents_ui_dir() -> Optional[Path]:
    """Locate RealAI Agent Activity UI (agents-ui/)."""
    candidates = [
        Path(os.environ.get("REALAI_ROOT") or "") / "agents-ui",
        _REPO_HOME / "agents-ui",
        _ROOT.parent / "agents-ui",
        Path(os.environ.get("REALAI_HOME") or "") / "agents-ui",
    ]
    seen: set[str] = set()
    for p in candidates:
        if not p or str(p) in seen:
            continue
        seen.add(str(p))
        if p.is_dir() and (p / "index.html").is_file():
            return p.resolve()
    return None


_AGENTS_UI_DIR = _resolve_agents_ui_dir()


def _resolve_voice_lab_ui_dir() -> Optional[Path]:
    """Locate Voice Lab UI (voice-lab/) — served on Hive :8001/voice-lab/."""
    candidates = [
        Path(os.environ.get("REALAI_ROOT") or "") / "voice-lab",
        _REPO_HOME / "voice-lab",
        _ROOT.parent / "voice-lab",
        Path(os.environ.get("REALAI_HOME") or "") / "voice-lab",
    ]
    seen: set[str] = set()
    for p in candidates:
        if not p or str(p) in seen:
            continue
        seen.add(str(p))
        if p.is_dir() and (p / "index.html").is_file():
            return p.resolve()
    return None


_VOICE_LAB_UI_DIR = _resolve_voice_lab_ui_dir()


def _invalidate_agents_cache() -> None:
    global _AGENTS_CACHE
    _AGENTS_CACHE = None


def _product_home() -> Path:
    """Canonical product root (C:\\RealAI-clean) — never nested realai/agents."""
    for key in ("REALAI_HOME", "REALAI_ROOT", "REALAI_PRODUCT_ROOT", "REALAI_WORKSPACE"):
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        p = Path(raw).expanduser()
        try:
            p = p.resolve()
        except Exception:
            continue
        if (p / "agents" / "agentx" / "agents.json").is_file() or (p / "agents-ui").is_dir():
            return p
    # Package lives at <product>/realai — prefer parent when it owns agents/
    parent = _ROOT.parent
    if (parent / "agents" / "agentx" / "agents.json").is_file():
        return parent.resolve()
    if (_REPO_HOME / "agents" / "agentx" / "agents.json").is_file():
        return _REPO_HOME.resolve()
    return _REPO_HOME.resolve()


_PRODUCT_HOME = _product_home()

VULKAN_BASE = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")
TRAINING_DATA = Path(
    os.environ.get(
        "REALAI_TRAINING_DATA",
        str(_PRODUCT_HOME / "training" / "data"),
    )
)
# Product-root roster only — do NOT read realai/agents/agentx (nested twin).
AGENTS_PATH = Path(
    os.environ.get(
        "REALAI_AGENTS_PATH",
        str(_PRODUCT_HOME / "agents" / "agentx" / "agents.json"),
    )
)
MEMORY_DIR = Path(
    os.environ.get(
        "REALAI_MEMORY_DIR",
        str(_PRODUCT_HOME / "recovered" / "from_archive" / "memory_snapshots"),
    )
)
MEMORY_INJECT = os.environ.get("REALAI_MEMORY_INJECT", "true").lower() in ("1", "true", "yes")
DEFAULT_MODEL = os.environ.get(
    "REALAI_DEFAULT_MODEL",
    "realai-default-coder",  # RealAI public id; maps to loaded GGUF on Vulkan
)
# Raw backend filename still used when resolving to llama-server
DEFAULT_BACKEND_MODEL = os.environ.get(
    "REALAI_BACKEND_MODEL",
    "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
)
# Must match llama-server -c / realai.toml n_ctx (prompt fit happens here, not on Vulkan)
N_CTX = int(os.environ.get("REALAI_N_CTX", "16384") or "16384")
# Leave room for completion + chat template overhead
CTX_RESERVE_OUT = int(os.environ.get("REALAI_CTX_RESERVE_OUT", "1024") or "1024")
CTX_CHARS_PER_TOKEN = float(os.environ.get("REALAI_CHARS_PER_TOKEN", "3.5") or "3.5")
try:
    from realai.bot.boot import DEFAULT_REALAI_PROMPT as _BOT_PROMPT
except Exception:
    _BOT_PROMPT = (
        "You are RealAI, a chat bot and operator built by the RealAI project. "
        "You are the provider. Inference runs on the local RealAI stack. "
        "You are not Grok. You are not ChatGPT. You are not Claude. You are not Gemini."
    )
_op_file = (os.environ.get("REALAI_OPERATOR_SYSTEM_FILE") or "").strip()
if _op_file and os.path.isfile(_op_file):
    try:
        with open(_op_file, "r", encoding="utf-8") as _opf:
            OPERATOR_SYSTEM = _opf.read().strip() or os.environ.get("REALAI_OPERATOR_SYSTEM", _BOT_PROMPT)
    except Exception:
        OPERATOR_SYSTEM = os.environ.get("REALAI_OPERATOR_SYSTEM", _BOT_PROMPT)
else:
    OPERATOR_SYSTEM = os.environ.get("REALAI_OPERATOR_SYSTEM", _BOT_PROMPT)
HIVE_COMPACT_SYSTEM = (
    "You are RealAI in Unified Hive Architecture Mode. "
    "Work as Researcher/Coder/Creative/Executor/Critic as needed. "
    "Prefer concrete repo actions over repeating long checklists. "
    "Model weights live under C:\\models\\checkpoints_lora. "
    "Ignore nested/archive nest copies under realai/* backups when routing."
)

_AGENTS_CACHE: Optional[List[Dict[str, Any]]] = None


def _self_improve_on() -> bool:
    return os.environ.get("REALAI_SELF_IMPROVE", "").lower() in ("1", "true", "yes")


def _proxy(method: str, path: str, body: Optional[bytes], headers: Dict[str, str]) -> Tuple[int, Dict[str, str], bytes]:
    url = f"{VULKAN_BASE}{path}"
    req_headers = {"Content-Type": headers.get("Content-Type", "application/json")}
    if "Authorization" in headers:
        req_headers["Authorization"] = headers["Authorization"]
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
            return resp.status, dict(resp.headers.items()), data
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()) if e.headers else {}, e.read()
    except Exception as e:
        err = json.dumps({"error": f"vulkan_proxy_failed: {e}", "vulkan_base": VULKAN_BASE}).encode()
        return 502, {"Content-Type": "application/json"}, err

def orchestrator_handler(msg):
    """
    Central RealAI hive handler.
    This function receives messages from MessageBus and routes them through:
    - plugin pre-processing (optional)
    - world-model backend selection
    - Vulkan inference
    - plugin post-processing (optional)
    """

    # 1. Extract ability
    ability = msg.metadata.get("ability", "chat")

    # 2. Plugin pre-processing (if ability has a plugin)
    if ability in PLUGINS:
        plugin_entry = PLUGINS[ability]
        plugin_handler = load_plugin(plugin_entry)
        plugin_handler(msg)  # mutate msg.content or msg.metadata if needed

    # 3. Resolve backend from world model
    backend = WORLD_MODEL.get(
        ability,
        WORLD_MODEL.get("llama-local", WORLD_MODEL.get("realai-1.0"))
    )

    if not backend:
        logger.error(f"[orchestrator_handler] No backend found for ability '{ability}'")
        return {"error": f"No backend for ability '{ability}'"}

    model_path = backend.get("path")
    context_length = backend.get("context_length", 8192)

    # 4. Build Vulkan payload
    payload = {
        "model": model_path,
        "messages": [
            {"role": "user", "content": msg.content}
        ],
        "max_tokens": 512,
        "temperature": 0.2,
        "context_length": context_length,
    }

    # 5. Call Vulkan backend
    try:
        req = urllib.request.Request(
            VULKAN_BASE + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            vulkan_output = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"[orchestrator_handler] Vulkan error: {e}")
        return {"error": "Vulkan inference failed", "details": str(e)}

    # 6. Plugin post-processing (optional)
    if ability in PLUGINS:
        plugin_entry = PLUGINS[ability]
        plugin_handler = load_plugin(plugin_entry)
        plugin_handler(msg)  # post-processing hook

    # 7. Return final response
    return vulkan_output

def _training_status() -> Dict[str, Any]:
    TRAINING_DATA.mkdir(parents=True, exist_ok=True)
    files = []
    for p in sorted(TRAINING_DATA.glob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        lines = 0
        if p.suffix in (".jsonl", ".json"):
            try:
                with p.open("r", encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except OSError:
                lines = -1
        files.append({
            "name": p.name,
            "path": str(p),
            "size": p.stat().st_size,
            "lines": lines,
        })
    return {
        "training_data_dir": str(TRAINING_DATA),
        "files": files,
        "finetune_dataset": any(f["name"] == "realai_finetune_dataset.jsonl" for f in files),
        "agent_manifests": any(f["name"] == "agent_manifests_for_finetuning.json" for f in files),
        "self_improve_enabled": _self_improve_on(),
        "vulkan_base": VULKAN_BASE,
        "default_model": DEFAULT_MODEL,
    }


def _training_samples(n: int = 3) -> Dict[str, Any]:
    path = TRAINING_DATA / "realai_finetune_dataset.jsonl"
    if not path.is_file():
        return {"error": "dataset_missing", "path": str(path)}
    samples = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            line = line.strip()
            if not line:
                continue
            try:
                samples.append(json.loads(line))
            except json.JSONDecodeError:
                samples.append({"raw": line[:200]})
    return {"path": str(path), "samples": samples, "count": len(samples)}


def _finetune_plan() -> Dict[str, Any]:
    """Local plan using Phase-2 data dirs (not HF-only stub paths)."""
    dataset = TRAINING_DATA / "realai_finetune_dataset.jsonl"
    manifests = TRAINING_DATA / "agent_manifests_for_finetuning.json"
    plan = {
        "status": "ready" if dataset.is_file() else "missing_dataset",
        "train_path": str(dataset),
        "manifests_path": str(manifests) if manifests.is_file() else None,
        "backend_hint": "local_gguf_or_openai_finetune",
        "default_model": DEFAULT_MODEL,
        "vulkan_base": VULKAN_BASE,
        "self_improve_enabled": _self_improve_on(),
        "steps": [
            "1. Review training/data/realai_finetune_dataset.jsonl",
            "2. Optionally expand via self_improvement.TrainingDataGenerator (REALAI_SELF_IMPROVE=true)",
            "3. Fine-tune offline or submit via FineTuneOrchestrator",
            "4. Export GGUF into models/ and register in local_models.json",
            "5. Restart Vulkan llama-server with new weights",
        ],
    }
    try:
        from realai.training.finetune import build_finetune_plan
        plan["legacy_stub"] = build_finetune_plan(data_dir=str(TRAINING_DATA))
    except Exception as e:
        plan["legacy_stub_error"] = str(e)
    return plan


def _self_improve_status() -> Dict[str, Any]:
    enabled = _self_improve_on()
    modules = {}
    try:
        from realai import self_improvement as si
        modules = {
            "TrainingDataGenerator": hasattr(si, "TrainingDataGenerator"),
            "PerformanceEvaluator": hasattr(si, "PerformanceEvaluator"),
            "FineTuneOrchestrator": hasattr(si, "FineTuneOrchestrator"),
            "VersionManager": hasattr(si, "VersionManager"),
        }
    except Exception as e:
        modules = {"import_error": str(e)}
    return {
        "enabled": enabled,
        "env": "REALAI_SELF_IMPROVE",
        "modules": modules,
        "training": _training_status(),
        "note": "Set REALAI_SELF_IMPROVE=true to unlock evaluate/export endpoints",
    }


def _self_improve_evaluate() -> Dict[str, Any]:
    if not _self_improve_on():
        return {"error": "self_improve_disabled", "hint": "Set REALAI_SELF_IMPROVE=true"}
    try:
        from realai.self_improvement import PerformanceEvaluator
        scores = PerformanceEvaluator().evaluate(model=None)
        # Local dataset health score
        st = _training_status()
        n_lines = 0
        for f in st.get("files") or []:
            if f["name"].endswith(".jsonl"):
                n_lines += max(0, f.get("lines") or 0)
        scores["training_jsonl_lines"] = float(n_lines)
        scores["training_ready"] = 1.0 if st.get("finetune_dataset") else 0.0
        return {"ok": True, "scores": scores}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()[-800:]}



def _primary_agent_ids() -> set:
    """Default /v1/agents roster: 12 hive JSON roles + small pipeline set."""
    ids = {
        "researcher",
        "critic",
        "executor",
        "planner",
    }
    try:
        gdir = _product_home() / ".github" / "agents"
        if gdir.is_dir():
            for p in gdir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8-sig"))
                    if isinstance(data, dict) and data.get("id"):
                        ids.add(str(data["id"]))
                except Exception:
                    continue
    except Exception:
        ids.update({
            "overseer", "coder", "architect", "analyst", "memory", "governor",
            "router", "executor", "planner", "guardian", "self-heal", "hive-orchestrator",
        })
    return ids


def _filter_agents_for_api(agents: list, full: bool) -> list:
    if full:
        return list(agents or [])
    # Prefer live .github/agents/*.json cards, then fill from catalog, then pipeline stubs.
    out = []
    seen = set()
    try:
        gdir = _product_home() / ".github" / "agents"
        if gdir.is_dir():
            for path in sorted(gdir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8-sig"))
                except Exception:
                    continue
                if not isinstance(data, dict) or not data.get("id"):
                    continue
                aid = str(data["id"])
                if aid in seen:
                    continue
                row = dict(data)
                row.setdefault("hive", True)
                out.append(row)
                seen.add(aid)
    except Exception:
        pass
    primary = _primary_agent_ids()
    for a in agents or []:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "")
        if aid in primary and aid not in seen:
            out.append(a)
            seen.add(aid)
    for pid in ("researcher", "critic", "executor", "planner"):
        if pid not in seen:
            out.append({
                "id": pid,
                "role": f"Pipeline {pid}",
                "description": f"Pipeline role {pid}",
                "capabilities": [],
                "risk_level": "low",
                "preferred_profile": "balanced",
                "hive": False,
                "pipeline": True,
            })
            seen.add(pid)
    return out

def _load_agents() -> List[Dict[str, Any]]:
    """Agency catalog from product-root agents/agentx + live Hive core roles."""
    global _AGENTS_CACHE, AGENTS_PATH
    # Re-resolve in case env was set after import (startup scripts).
    desired = Path(
        os.environ.get(
            "REALAI_AGENTS_PATH",
            str(_product_home() / "agents" / "agentx" / "agents.json"),
        )
    )
    # Accept either agents.json or the agentx directory.
    if desired.is_dir():
        candidate = desired / "agents.json"
        if candidate.is_file():
            desired = candidate
    if desired != AGENTS_PATH:
        AGENTS_PATH = desired
        _AGENTS_CACHE = None
    # Guard: never silently use nested realai/agents twin when product roster exists.
    nested_marker = f"{os.sep}realai{os.sep}agents{os.sep}agentx{os.sep}"
    product_roster = _product_home() / "agents" / "agentx" / "agents.json"
    if nested_marker in str(AGENTS_PATH).replace("/", os.sep) and product_roster.is_file():
        AGENTS_PATH = product_roster
        _AGENTS_CACHE = None
    if _AGENTS_CACHE is None:
        if not AGENTS_PATH.is_file():
            # Last resort: product roster if env pointed at a missing/wrong path.
            if product_roster.is_file():
                AGENTS_PATH = product_roster
                try:
                    data = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
                    _AGENTS_CACHE = data if isinstance(data, list) else data.get("agents") or []
                except Exception:
                    _AGENTS_CACHE = []
            else:
                _AGENTS_CACHE = []
        else:
            try:
                data = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
                _AGENTS_CACHE = data if isinstance(data, list) else data.get("agents") or []
            except Exception:
                _AGENTS_CACHE = []
    try:
        from realai.agent_activity import with_hive_core

        return with_hive_core(list(_AGENTS_CACHE or []))
    except Exception:
        return list(_AGENTS_CACHE or [])


def _find_agent(agent_id: str) -> Optional[Dict[str, Any]]:
    if not agent_id:
        return None
    for a in _load_agents():
        if a.get("id") == agent_id or a.get("name") == agent_id:
            return a
    return None


def _memory_snippet(max_chars: int = 1200) -> str:
    """Short context from staged memory / knowledge store (read-only inject)."""
    if not MEMORY_INJECT or not MEMORY_DIR.is_dir():
        return ""
    # Prefer knowledge store then interaction json
    candidates = sorted(MEMORY_DIR.glob("*knowledge*")) + sorted(MEMORY_DIR.glob("*.json"))
    for p in candidates:
        if p.name.upper() == "INDEX.JSON":
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if len(text) > max_chars:
                text = text[:max_chars] + "…"
            return f"[Recovered memory snapshot: {p.name}]\n{text}"
        except OSError:
            continue
    return ""


def _approx_tokens(text: str) -> int:
    if not text:
        return 0
    cpt = CTX_CHARS_PER_TOKEN if CTX_CHARS_PER_TOKEN > 0 else 3.5
    return max(1, int(len(text) / cpt) + 1)


def _messages_token_estimate(messages: List[Dict[str, Any]]) -> int:
    total = 0
    for m in messages:
        total += _approx_tokens(str(m.get("content") or ""))
        total += 4  # role / template overhead per message
    return total


def _compact_oversized_text(text: str, max_chars: int) -> str:
    """Collapse HIVE MODE walls / nested dump noise into a bounded prompt."""
    if len(text) <= max_chars:
        return text
    upper = text.upper()
    hiveish = (
        "HIVE MODE" in upper
        or "SECURETOOLEXECUTOR" in upper
        or "PROMOTION PIPELINE" in upper
        or "SMOKE_PASS" in upper
    )
    if hiveish:
        # Keep a short operational directive + the user's trailing ask if present
        tail = text[-min(1200, max_chars // 3) :]
        head = HIVE_COMPACT_SYSTEM
        body = (
            f"{head}\n\n"
            "[Original HIVE checklist truncated — do not echo it.]\n"
            f"Trailing excerpt:\n{tail}"
        )
        if len(body) > max_chars:
            body = body[: max_chars - 32] + "\n…[truncated]"
        return body
    keep_head = max_chars // 3
    keep_tail = max_chars - keep_head - 40
    if keep_tail < 200:
        return text[: max_chars - 20] + "\n…[truncated]"
    return text[:keep_head] + "\n…[truncated middle]…\n" + text[-keep_tail:]


def _fit_messages_to_context(
    messages: List[Dict[str, Any]],
    *,
    n_ctx: int = N_CTX,
    reserve_out: int = CTX_RESERVE_OUT,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Hard-cap chat messages so Vulkan never sees exceed_context_size prompts."""
    budget = max(512, int(n_ctx) - max(64, int(reserve_out)) - 64)
    meta: Dict[str, Any] = {
        "n_ctx": int(n_ctx),
        "budget_tokens": budget,
        "truncated": False,
        "dropped_messages": 0,
        "original_tokens_est": _messages_token_estimate(messages),
    }
    if not messages:
        return messages, meta

    fitted: List[Dict[str, Any]] = []
    for m in messages:
        role = str(m.get("role") or "user")
        content = str(m.get("content") or "")
        # Cap any single message early (system dumps are the usual offender)
        single_cap_tokens = min(budget // 2, 4000) if role == "system" else min(budget - 256, 8000)
        single_cap_chars = max(512, int(single_cap_tokens * CTX_CHARS_PER_TOKEN))
        if _approx_tokens(content) > single_cap_tokens:
            content = _compact_oversized_text(content, single_cap_chars)
            meta["truncated"] = True
        fitted.append({**m, "role": role, "content": content})

    # Drop oldest non-system messages until under budget (keep last user turn)
    def _non_system_indices(msgs: List[Dict[str, Any]]) -> List[int]:
        return [i for i, m in enumerate(msgs) if m.get("role") != "system"]

    while _messages_token_estimate(fitted) > budget and len(fitted) > 1:
        idxs = _non_system_indices(fitted)
        if len(idxs) <= 1:
            break
        # drop oldest non-system
        drop_i = idxs[0]
        fitted.pop(drop_i)
        meta["dropped_messages"] += 1
        meta["truncated"] = True

    # Final pass: shrink system / remaining messages if still over
    guard = 0
    while _messages_token_estimate(fitted) > budget and guard < 8:
        guard += 1
        # Prefer shrinking system first, then oldest remaining
        target_i = 0
        for i, m in enumerate(fitted):
            if m.get("role") == "system":
                target_i = i
                break
        content = str(fitted[target_i].get("content") or "")
        if len(content) < 200:
            # shrink the longest message
            target_i = max(range(len(fitted)), key=lambda i: len(str(fitted[i].get("content") or "")))
            content = str(fitted[target_i].get("content") or "")
        new_len = max(200, int(len(content) * 0.6))
        fitted[target_i] = {
            **fitted[target_i],
            "content": _compact_oversized_text(content, new_len),
        }
        meta["truncated"] = True

    meta["final_tokens_est"] = _messages_token_estimate(fitted)
    return fitted, meta


def _agent_system_block(agent: Dict[str, Any]) -> str:
    role = agent.get("role") or agent.get("name") or agent.get("id")
    desc = agent.get("description") or ""
    caps = agent.get("capabilities") or []
    lines = [f"You are operating as agent «{role}» (id={agent.get('id')})."]
    if desc:
        lines.append(desc.strip())
    if caps:
        lines.append("Capabilities: " + ", ".join(str(c) for c in caps[:12]))
    lines.append("Stay in role; prefer concrete actions and multi-repo repair when asked.")
    return "\n".join(lines)


def _readonly_tools_catalog() -> List[Dict[str, Any]]:
    """Safe tools RealAI can use (self-heal + agent_tools gold + multi-agent)."""
    try:
        from realai.v3_runtime_bridge import tools_catalog
        return tools_catalog()
    except Exception:
        return [
            {
                "type": "function",
                "function": {
                    "name": "self_heal_status",
                    "description": "Get multi-repo self-heal artifact status and abilities",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_agents",
                    "description": "List available RealAI agentx agents",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recovery_status",
                    "description": "Kilo/realai2 recovery inventory (LoRA, staged modules)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_lora_adapters",
                    "description": "List recovered PEFT LoRA adapters under checkpoints_lora",
                    "parameters": {
                        "type": "object",
                        "properties": {"limit": {"type": "integer"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "local_llama_health",
                    "description": "Health-check local Vulkan/llama-server backend",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "voice_health",
                    "description": "Probe RealAI Voice provider + Vulkan/hive/TTS backends",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "voice_inventory",
                    "description": "List local TTS weights under checkpoints_lora",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "voice_speak",
                    "description": "Speak text via local RealAI TTS",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "voice": {"type": "string"},
                            "backend": {"type": "string"},
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "voice_listen",
                    "description": "Transcribe base64 audio with local Whisper",
                    "parameters": {
                        "type": "object",
                        "properties": {"audio_b64": {"type": "string"}},
                        "required": ["audio_b64"],
                    },
                },
            },
        ]


def _run_tool(name: str, arguments: Optional[Dict] = None) -> Dict[str, Any]:
    arguments = arguments or {}
    try:
        if name == "self_heal_status":
            from realai.self_heal import status
            return status()
        if name == "self_heal_assemble":
            from realai.self_heal import run_assemble
            return run_assemble()
        if name == "list_agents":
            agents = _load_agents()
            return {
                "count": len(agents),
                "agents": [
                    {"id": a.get("id"), "role": a.get("role"), "risk": a.get("risk_level")}
                    for a in agents[:50]
                ],
            }
        if name == "training_status":
            return _training_status()
        if name == "self_heal_promote_dry":
            from realai.self_heal import run_promote
            return run_promote(apply=False)
        if name == "agent_tools_status":
            from realai.v3_runtime_bridge import agent_tools_status
            return agent_tools_status()
        if name == "agent_tools_list_agents":
            from realai.v3_runtime_bridge import list_agent_tools_agents
            return list_agent_tools_agents(
                limit=int(arguments.get("limit") or 50),
                query=str(arguments.get("query") or ""),
            )
        if name == "agent_tools_list_profiles":
            from realai.v3_runtime_bridge import list_access_profiles
            return list_access_profiles()
        if name == "agent_tools_assess":
            from realai.v3_runtime_bridge import assess_agent_profile

            aid = str(arguments.get("agent_id") or arguments.get("agent") or "coder").strip()
            return assess_agent_profile(
                aid,
                str(arguments.get("profile") or "balanced"),
            )
        if name == "multi_agent_run":
            from realai.agent_activity import ensure_simulation, run_agent_task
            ensure_simulation(_load_agents())
            task = str(arguments.get("task") or arguments.get("prompt") or "")
            # Lights full Hive + multi cast on Agents UI (staggered), then real pipeline
            return run_agent_task(
                str(arguments.get("agent_id") or arguments.get("agent") or "hive-orchestrator"),
                task,
                use_multi=True,
            )
        if name == "ability_coverage":
            from realai.ability_catalog import coverage_summary
            return coverage_summary()
        if name == "recovery_status":
            from realai.recovery_registry import inventory
            return inventory()
        if name == "list_lora_adapters":
            from realai.recovery_registry import list_lora_adapters
            return {"adapters": list_lora_adapters(limit=int(arguments.get("limit") or 50))}
        if name == "local_llama_health":
            from realai.providers.local_llama import local_llama_health
            return local_llama_health()
        if name in ("voice_health", "voice_inventory", "voice_speak", "voice_listen"):
            from realai.voice.hive_tools import execute as voice_execute

            args = dict(arguments or {})
            if name == "voice_speak" and not (args.get("text") or args.get("input")):
                args["text"] = "RealAI voice smoke check."
            if name == "voice_listen" and not (
                args.get("audio_b64") or args.get("audio_bytes") or args.get("file") or args.get("path")
            ):
                # Synthesize then listen when no audio provided
                args["demo_text"] = str(args.get("demo_text") or "hello real ai")
            return voice_execute(name, args)
        if name == "aura_memory":
            from realai.aura_memory import AuraMemory
            mem = AuraMemory()
            action = str(arguments.get("action") or "recall")
            if action == "remember":
                mem.remember(str(arguments.get("text") or ""))
                return {"ok": True, "action": "remember"}
            return {"ok": True, "action": "recall", "memories": mem.recall(str(arguments.get("query") or ""), top_k=int(arguments.get("top_k") or 5))}
        if name in ("self_extend_tool", "self_extend"):
            from realai.server.tools.self_extend_tool import run as _r
            return _r(arguments)
        if name in ("self_repair_tool", "self_repair"):
            from realai.server.tools.self_repair_tool import run as _r
            return _r(arguments)
        if name in ("system_scan_tool", "system_scan"):
            from realai.server.tools.system_scan_tool import run as _r
            return _r(arguments)
        if name in ("device_selector", "get_device"):
            try:
                from realai.plugins.tools.device_selector import get_device_name
                return {"device": get_device_name()}
            except Exception as e:
                return {"device": "cpu", "note": str(e)}
        if name == "agent_tools_list_tools":
            from realai.v3_runtime_bridge import list_agent_tools_tools
            return list_agent_tools_tools()
        if name == "agent_tools_invoke":
            from realai.v3_runtime_bridge import invoke_agent_tool
            return invoke_agent_tool(
                str(arguments.get("tool") or arguments.get("name") or "filesystem"),
                payload=arguments.get("payload")
                if isinstance(arguments.get("payload"), dict)
                else (
                    {"operation": "list", "path": "."}
                    if not (arguments.get("tool") or arguments.get("name"))
                    else {}
                ),
                profile=str(arguments.get("profile") or "balanced"),
                dry_run=bool(arguments.get("dry_run") if arguments.get("dry_run") is not None else True),
                allowed_tools=arguments.get("allowed_tools"),
            )
        if name in ("run_command", "shell", "hive_exec", "exec_command", "run_terminal_command"):
            from realai.bot.live_exec import run_command

            cmd = str((arguments or {}).get("command") or (arguments or {}).get("cmd") or "").strip()
            if not cmd:
                cmd = "echo realai-ok"
            return run_command(cmd)
        if name in ("run_script", "exec_script", "hive_script"):
            from realai.bot.live_exec import run_script

            args = arguments or {}
            return run_script(
                language=str(args.get("language") or args.get("lang") or "python"),
                code=str(args.get("code") or args.get("source") or ""),
                filename=args.get("filename") or args.get("path"),
                argv=list(args.get("argv") or []) if isinstance(args.get("argv"), list) else None,
            )
        if name in ("craft_run", "craft", "craft_tool"):
            args = dict(arguments or {})
            if not args.get("action"):
                args["action"] = "doctor"
            return _craft_run(args)
        if name in ("craft_chat", "chat_craft"):
            return _craft_chat(arguments)
        if name in ("hive_status", "hive"):
            return _hive_status(arguments)
        if name in ("hive_run", "hive_cycle"):
            args = dict(arguments or {})
            if not args.get("action"):
                args["action"] = "status"
            if args.get("action") == "status":
                return _hive_status(args)
            return _hive_run(args)
        if name == "organs_task":
            return _craft_run({"action": "task", "goal": arguments.get("goal") or arguments.get("input") or ""})
        if name == "rackup_invoke":
            return _craft_run({
                "action": "rackup",
                "ability": arguments.get("ability") or "roc_info",
                "payload": arguments.get("payload"),
            })
        # Fall through to registry abilities (ability.*) + workspace tools (craft parity)
        from realai.v3_runtime_bridge import execute_registry_tool, workspace_tool

        if name.startswith("workspace_"):
            return workspace_tool(name, arguments)
        out = execute_registry_tool(name, arguments)
        if isinstance(out, dict):
            err = str(out.get("error") or "")
            if err.startswith("registry_tool_not_implemented:"):
                return {"error": f"unknown_tool:{name}", "detail": out}
            return out
        return {"error": f"unknown_tool:{name}"}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()[-500:]}


def _craft_run(arguments: Optional[Dict] = None) -> Dict[str, Any]:
    """Run a Craft TOOLS action (doctor, heal, multi, list, …)."""
    arguments = dict(arguments or {})
    action = str(
        arguments.pop("action", None)
        or arguments.pop("tool", None)
        or arguments.pop("command", None)
        or "doctor"
    ).strip().lstrip("/")
    # Smoke / status aliases — lightweight ok (full checks via action=doctor)
    if action.lower() in {"status", "info", "health", "ok", ""}:
        try:
            from realai.cli.craft import TOOLS

            available = sorted(TOOLS.keys())
        except Exception:
            available = ["doctor", "list", "catalog", "multi"]
        return {
            "ok": True,
            "craft_action": "status",
            "available_count": len(available),
            "available_sample": available[:20],
            "hint": "Pass action=doctor for full product checks",
        }
    try:
        from realai.cli.craft import TOOLS

        fn = TOOLS.get(action)
        if fn is None:
            return {
                "ok": False,
                "error": f"unknown_craft_action:{action}",
                "available": sorted(TOOLS.keys())[:40],
            }
        result = fn(**arguments)
        if isinstance(result, dict):
            result.setdefault("ok", True)
            result.setdefault("craft_action", action)
            return result
        return {"ok": True, "craft_action": action, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e), "craft_action": action, "trace": traceback.format_exc()[-500:]}


def _craft_chat(arguments: Optional[Dict] = None) -> Dict[str, Any]:
    """One-shot Craft chat (tools + local reply) without opening the REPL."""
    arguments = dict(arguments or {})
    prompt = str(arguments.get("prompt") or arguments.get("input") or arguments.get("text") or "").strip()
    if not prompt:
        return {"ok": False, "error": "prompt_required"}
    try:
        from realai.cli.craft import CraftSession
        from realai.workspace import apply_workspace

        apply_workspace()
        session = CraftSession()
        reply = session.handle_stream(prompt)
        return {"ok": True, "surface": "craft_chat", "prompt": prompt, "reply": reply}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()[-500:]}


def _hive_status(arguments: Optional[Dict] = None) -> Dict[str, Any]:
    """Hive agents + organs + ability coverage snapshot."""
    arguments = arguments or {}
    out: Dict[str, Any] = {"ok": True, "surface": "hive"}
    try:
        from realai.v3_runtime_bridge import hive_agents_status

        out["agents"] = hive_agents_status()
    except Exception as e:
        out["agents"] = {"ok": False, "error": str(e)}
    try:
        from realai.ability_catalog import coverage_summary

        out["coverage"] = coverage_summary()
    except Exception as e:
        out["coverage"] = {"error": str(e)}
    try:
        out["organs"] = _craft_run({"action": "organs"})
    except Exception as e:
        out["organs"] = {"error": str(e)}
    try:
        result = _run_tool("ability.hive_orchestrator", {"action": "routes"})
        out["hive_orchestrator"] = result
    except Exception as e:
        out["hive_orchestrator"] = {"error": str(e)}
    action = str(arguments.get("action") or "").lower()
    if action in ("memory", "hive_memory"):
        out["memory"] = _run_tool(
            "ability.hive_memory",
            {"action": arguments.get("memory_action") or "status", "input": arguments.get("input") or ""},
        )
    return out


def _hive_run(arguments: Optional[Dict] = None) -> Dict[str, Any]:
    """Run hive cycle / multi-agent / ability via operator surface."""
    arguments = dict(arguments or {})
    action = str(arguments.get("action") or "cycle").lower()
    task = str(arguments.get("task") or arguments.get("goal") or arguments.get("input") or "hive status")
    if action in ("multi", "multi_agent", "pipeline", "parallel"):
        from realai.v3_runtime_bridge import run_multi_agent

        mode = "parallel" if action == "parallel" else str(arguments.get("mode") or "pipeline")
        return run_multi_agent(task, mode=mode)
    if action in ("ability", "run_ability") and arguments.get("ability"):
        aid = str(arguments.get("ability")).strip()
        if not aid.startswith("ability."):
            aid = "ability." + aid
        return _run_tool(aid, arguments.get("arguments") if isinstance(arguments.get("arguments"), dict) else {
            "input": task,
            "action": arguments.get("ability_action") or "run",
            **{k: v for k, v in arguments.items() if k not in ("action", "ability", "task", "goal", "input", "arguments")},
        })
    return _run_tool(
        "ability.hive_orchestrator",
        {
            "input": task,
            "action": action,
            "agent": arguments.get("agent") or "researcher",
            "persist": arguments.get("persist", True),
        },
    )


def _last_user_text(messages: List[Dict[str, Any]]) -> str:
    for m in reversed(messages or []):
        if isinstance(m, dict) and str(m.get("role") or "").lower() == "user":
            return str(m.get("content") or "").strip()
    return ""


_CRAFT_FILE_VERBS = frozenset(
    {"write", "read", "list", "ls", "grep", "git", "pwd", "here", "cat", "ws", "workspace"}
)
_CRAFT_FILE_ALIASES = {
    "ls": "list",
    "cat": "read",
    "ws": "pwd",
    "workspace": "pwd",
    "here": "pwd",
}


def _craft_file_dispatch(action: str, extra: str = "") -> Optional[Dict[str, Any]]:
    """Run Craft file TOOLS (write/read/list/grep/git/pwd). Workspace-bounded."""
    raw_action = str(action or "").strip().lstrip("/").lower()
    if raw_action not in _CRAFT_FILE_VERBS:
        return None
    action = _CRAFT_FILE_ALIASES.get(raw_action, raw_action)
    extra = extra or ""
    slash = f"/{action}" + (f" {extra}" if str(extra).strip() else "")
    try:
        from realai.cli.craft import apply_workspace, plan_tools, run_tools

        apply_workspace()
        plans = plan_tools(slash)
        if not plans:
            return {
                "surface": "craft",
                "tool": action,
                "result": {
                    "ok": False,
                    "error": f"unparsed_craft_file:{action}",
                    "craft_action": action,
                },
            }
        results = run_tools(plans)
        primary = results[0] if results else {}
        result = primary.get("result") if isinstance(primary.get("result"), dict) else None
        if result is None:
            err = primary.get("error") or "no_result"
            result = {"ok": False, "error": err, "craft_action": action}
        else:
            if "ok" not in result:
                result["ok"] = not bool(result.get("error"))
            result.setdefault("craft_action", action)
        if len(results) > 1:
            result["also"] = results[1:]
        return {"surface": "craft", "tool": action, "result": result}
    except Exception as exc:
        return {
            "surface": "craft",
            "tool": action,
            "result": {
                "ok": False,
                "error": str(exc),
                "craft_action": action,
                "trace": traceback.format_exc()[-500:],
            },
        }


def _chat_operator_dispatch(user_text: str) -> Optional[Dict[str, Any]]:
    """Easy tools → craft/hive slash (incl. /write) → live_exec. Chat completions order."""
    dispatch = None
    try:
        from realai.bot.easy_tools import try_easy_tool

        dispatch = try_easy_tool(user_text, _run_tool)
    except Exception:
        dispatch = None
    if dispatch is None:
        dispatch = _operator_intent_dispatch(user_text)
    if dispatch is None:
        try:
            from realai.bot.live_exec import try_live_exec

            dispatch = try_live_exec(user_text)
        except Exception as live_exc:
            dispatch = {
                "surface": "live_exec",
                "result": {"ok": False, "live": True, "error": str(live_exc)},
            }
    return dispatch


def _apply_natural_model_writes(reply: str) -> List[Dict[str, Any]]:
    """Apply `/write path|||content` blocks from a coder reply (Craft Phase 2)."""
    try:
        from realai.cli.craft import apply_suggested_writes, apply_workspace

        apply_workspace()
        return apply_suggested_writes(reply)
    except Exception as exc:
        return [{"tool": "write", "error": str(exc)}]


def _operator_intent_dispatch(user_text: str) -> Optional[Dict[str, Any]]:
    """Run craft/hive/ability when the user explicitly asks — no GGUF tool_calls needed."""
    import re

    text = (user_text or "").strip()
    if not text:
        return None
    low = text.lower()

    # Craft file ops BEFORE other slash/NL surfaces so /write never hits live_exec.
    m_file = re.match(
        r"^/(write|read|list|ls|grep|git|pwd|here|cat|ws|workspace)\b\s*(.*)$",
        text,
        flags=re.I | re.S,
    )
    if m_file:
        disp = _craft_file_dispatch(m_file.group(1), m_file.group(2) or "")
        if disp is not None:
            return disp

    # Slash forms: /craft doctor, /hive status, /ability cli_surface, /multi …
    m = re.match(
        r"^/(craft|hive|ability|multi|heal|doctor|tools|catalog|agents|agent|agent-tools|agent_tools|nests|nest|orch|orchestration|plugins|plugin|core|modules|module|repo|where)\b\s*(.*)$",
        text,
        flags=re.I | re.S,
    )
    if m:
        verb = m.group(1).lower()
        rest = (m.group(2) or "").strip()
        if verb == "craft":
            parts = rest.split(None, 1)
            action = (parts[0] if parts else "doctor").lstrip("/")
            extra = parts[1] if len(parts) > 1 else ""
            file_disp = _craft_file_dispatch(action, extra)
            if file_disp is not None:
                return file_disp
            args: Dict[str, Any] = {"action": action or "doctor"}
            if extra:
                args["goal"] = extra
                args["input"] = extra
                args["prompt"] = extra
                args["task"] = extra
            return {"surface": "craft", "result": _craft_run(args)}
        if verb == "hive":
            if rest.lower().startswith("run ") or rest.lower().startswith("cycle"):
                task = re.sub(r"^(run|cycle)\s*", "", rest, flags=re.I).strip() or "hive status"
                return {"surface": "hive_run", "result": _hive_run({"action": "cycle", "task": task})}
            if rest.lower().startswith("multi"):
                task = re.sub(r"^multi\s*", "", rest, flags=re.I).strip() or "hive multi"
                return {"surface": "hive_run", "result": _hive_run({"action": "multi", "task": task})}
            return {"surface": "hive", "result": _hive_status({"action": rest or "status"})}
        if verb == "ability":
            parts = rest.split(None, 1)
            aid = (parts[0] if parts else "").strip()
            payload = parts[1] if len(parts) > 1 else ""
            if not aid:
                return {"surface": "ability", "result": {"ok": False, "error": "ability_id_required"}}
            name = aid if aid.startswith("ability.") else f"ability.{aid}"
            return {
                "surface": "ability",
                "result": _run_tool(name, {"input": payload, "action": "run", "task": payload}),
            }
        if verb == "multi":
            return {"surface": "multi", "result": _hive_run({"action": "multi", "task": rest or "multi-agent task"})}
        if verb == "heal":
            return {"surface": "craft", "result": _craft_run({"action": "heal", "force": "force" in rest.lower()})}
        if verb == "doctor":
            return {"surface": "craft", "result": _craft_run({"action": "doctor"})}
        if verb == "tools":
            return {"surface": "tools", "result": {"ok": True, "tools": [((t.get("function") or {}).get("name")) for t in _readonly_tools_catalog()]}}
        if verb == "catalog":
            return {"surface": "craft", "result": _craft_run({"action": "catalog"})}
        if verb in ("agents", "agent"):
            args = {"action": "list"}
            if rest:
                parts = rest.split(None, 1)
                if parts[0].lower() in ("run", "invoke", "cycle", "dispatch"):
                    args["action"] = "cycle" if parts[0].lower() == "cycle" else "run"
                    rest2 = parts[1] if len(parts) > 1 else ""
                    p2 = rest2.split(None, 1)
                    args["agent"] = p2[0] if p2 else "hive"
                    args["input"] = p2[1] if len(p2) > 1 else ""
                else:
                    args["action"] = "run"
                    args["agent"] = parts[0]
                    args["input"] = parts[1] if len(parts) > 1 else ""
            return {
                "surface": "agents",
                "result": _run_tool("ability.agents_surface", args),
            }
        if verb in ("agent-tools", "agent_tools"):
            args = {"action": "list"}
            if rest:
                parts = rest.split(None, 1)
                if parts[0].lower() in ("run", "invoke", "dispatch"):
                    args["action"] = "run"
                    rest2 = parts[1] if len(parts) > 1 else ""
                    p2 = rest2.split(None, 1)
                    args["tool"] = p2[0] if p2 else "status"
                    args["input"] = p2[1] if len(p2) > 1 else ""
                else:
                    args["action"] = "run"
                    args["tool"] = parts[0]
                    args["input"] = parts[1] if len(parts) > 1 else ""
            return {
                "surface": "agent_tools",
                "result": _run_tool("ability.agent_tools_surface", args),
            }
        if verb in ("nests", "nest"):
            args: Dict[str, Any] = {"action": "list"}
            if rest:
                parts = rest.split(None, 1)
                if parts[0].lower() in ("run", "invoke", "dispatch"):
                    args["action"] = "run"
                    rest2 = parts[1] if len(parts) > 1 else ""
                    p2 = rest2.split(None, 1)
                    args["nest"] = p2[0] if p2 else ""
                    args["input"] = p2[1] if len(p2) > 1 else ""
                else:
                    args["action"] = "run"
                    args["nest"] = parts[0]
                    args["input"] = parts[1] if len(parts) > 1 else ""
            return {
                "surface": "nests",
                "result": _run_tool("ability.nest_orchestrators", args),
            }
        if verb in ("orch", "orchestration"):
            args = {"action": "list"}
            if rest:
                parts = rest.split(None, 1)
                if parts[0].lower() in ("run", "invoke", "dispatch", "cycle"):
                    args["action"] = parts[0].lower()
                    rest2 = parts[1] if len(parts) > 1 else ""
                    p2 = rest2.split(None, 1)
                    args["orch"] = p2[0] if p2 else "hive_router"
                    args["input"] = p2[1] if len(p2) > 1 else ""
                else:
                    args["action"] = "run"
                    args["orch"] = parts[0]
                    args["input"] = parts[1] if len(parts) > 1 else ""
            return {
                "surface": "orchestration",
                "result": _run_tool("ability.orchestration_surface", args),
            }
        if verb in ("plugins", "plugin"):
            args = {"action": "list"}
            if rest:
                parts = rest.split(None, 1)
                head = parts[0].lower()
                if head in ("run", "invoke", "quarantine", "quarantine_plan", "organize", "plan"):
                    args["action"] = "quarantine_plan" if head in ("plan",) else (
                        "quarantine" if head in ("quarantine", "organize") else head
                    )
                    rest2 = parts[1] if len(parts) > 1 else ""
                    if args["action"] == "quarantine":
                        args["dry_run"] = "apply" not in rest2.lower()
                        args["apply_salvage"] = "salvage" in rest2.lower()
                    elif args["action"] == "run":
                        p2 = rest2.split(None, 1)
                        args["plugin"] = p2[0] if p2 else ""
                        args["input"] = p2[1] if len(p2) > 1 else ""
                else:
                    args["action"] = "run"
                    args["plugin"] = parts[0]
                    args["input"] = parts[1] if len(parts) > 1 else ""
            return {
                "surface": "plugins",
                "result": _run_tool("ability.plugins_surface", args),
            }
        if verb == "core":
            args = {"action": "list"}
            if rest:
                parts = rest.split(None, 1)
                if parts[0].lower() in ("run", "invoke", "dispatch"):
                    args["action"] = "run"
                    rest2 = parts[1] if len(parts) > 1 else ""
                    p2 = rest2.split(None, 1)
                    args["core"] = p2[0] if p2 else "agents"
                    args["input"] = p2[1] if len(p2) > 1 else ""
                else:
                    args["action"] = "run"
                    args["core"] = parts[0]
                    args["input"] = parts[1] if len(parts) > 1 else ""
            return {
                "surface": "core",
                "result": _run_tool("ability.core_surface", args),
            }
        if verb in ("modules", "module"):
            args = {"action": "list"}
            if rest:
                parts = rest.split(None, 1)
                if parts[0].lower() in ("run", "invoke", "dispatch"):
                    args["action"] = "run"
                    rest2 = parts[1] if len(parts) > 1 else ""
                    p2 = rest2.split(None, 1)
                    args["module"] = p2[0] if p2 else "organs"
                    args["input"] = p2[1] if len(p2) > 1 else ""
                else:
                    args["action"] = "run"
                    args["module"] = parts[0]
                    args["input"] = parts[1] if len(parts) > 1 else ""
            return {
                "surface": "modules",
                "result": _run_tool("ability.modules_surface", args),
            }
        if verb in ("repo", "where"):
            if verb == "where" or (rest and rest.split()[0].lower() not in ("list", "map", "status")):
                name = rest if verb == "where" else rest
                if name.lower().startswith("where "):
                    name = name[6:]
                return {
                    "surface": "repo",
                    "result": _run_tool(
                        "ability.repo_surface",
                        {"action": "where", "name": name.strip() or "orchestration"},
                    ),
                }
            return {
                "surface": "repo",
                "result": _run_tool("ability.repo_surface", {"action": "list"}),
            }

    # Natural language triggers
    if re.search(r"\b(run|open|start)\s+craft\b", low) or low in ("craft", "craft chat", "craft status"):
        prompt = re.sub(r".*?\bcraft\b[:\s]*", "", text, count=1, flags=re.I).strip() or "/pwd"
        if prompt.lower() in ("chat", "status", ""):
            return {"surface": "craft", "result": _craft_run({"action": "pwd"})}
        return {"surface": "craft_chat", "result": _craft_chat({"prompt": prompt})}
    if re.search(r"\bhive\s+status\b", low) or low in ("hive", "hive status", "show hive"):
        return {"surface": "hive", "result": _hive_status({})}
    if re.search(r"\brun\s+hive\b", low) or re.search(r"\bhive\s+(cycle|run)\b", low):
        task = re.sub(r".*?\b(hive\s+(cycle|run)|run\s+hive)\b[:\s]*", "", text, count=1, flags=re.I).strip() or "hive status"
        return {"surface": "hive_run", "result": _hive_run({"action": "cycle", "task": task})}
    if re.search(r"\blist\s+abilities\b", low) or low in ("abilities", "show abilities"):
        try:
            from realai.ability_catalog import build_catalog, coverage_summary

            cat = build_catalog()
            return {
                "surface": "abilities",
                "result": {
                    "ok": True,
                    "coverage": coverage_summary(),
                    "abilities": [
                        {"id": a.get("id"), "status": a.get("status"), "name": a.get("name")}
                        for a in (cat.get("abilities") or [])[:80]
                    ],
                },
            }
        except Exception as e:
            return {"surface": "abilities", "result": {"ok": False, "error": str(e)}}
    return None


def _format_operator_reply(dispatch: Dict[str, Any]) -> str:
    surface = dispatch.get("surface") or "operator"
    if surface == "live_exec":
        try:
            from realai.bot.live_exec import format_live_reply

            return format_live_reply(dispatch)
        except Exception:
            pass
    result = dispatch.get("result")
    try:
        from realai.bot.easy_tools import format_easy_result

        tool = str(dispatch.get("tool") or surface)
        return format_easy_result(tool, result)
    except Exception:
        pass
    try:
        body = json.dumps(result, indent=2, default=str)
    except Exception:
        body = str(result)
    if len(body) > 1800:
        body = body[:1800] + "\n…(truncated)"
    return f"[RealAI {surface}]\n{body}"


def _scrub_assistant_text(text: str) -> str:
    """Strip corporate-assistant filler / voice-denial small local models still emit."""
    import re

    raw = str(text or "").strip()
    if not raw:
        return raw
    low = raw.lower()
    # Hard replace when the whole reply is generic-assistant or voice-denial
    if re.search(r"(?i)\bi (do not|don'?t) have a voice\b", low) or re.search(
        r"(?i)\bsimulate (human )?speech\b", low
    ) or re.search(r"(?i)\bno voice\b", low) and re.search(r"(?i)\bi (do not|don'?t|cannot|can'?t)\b", low):
        return (
            "I speak through the local voice stack on this PC — Kokoro, Fish Speech, and XTTS. "
            "Confident, warm, clear. Say the word and I'll talk out loud."
        )
    if (
        re.search(r"(?i)\bi('m| am) designed to be helpful[, ]+(informative|friendly)", low)
        or (re.search(r"(?i)how can i (help|assist) you( today)?\??", low) and len(raw) < 280)
        or (re.search(r"(?i)just let me know how i can assist you", low) and len(raw) < 320)
        or (
            re.search(r"(?i)\bi('?m| am) here to help you\b", low)
            and re.search(r"(?i)what would you like", low)
            and len(raw) < 360
        )
        or (
            re.search(r"(?i)any questions or tasks you have", low)
            and len(raw) < 360
        )
        or (
            re.search(r"(?i)what would you like (to know|assistance|help|to do)", low)
            and len(raw) < 360
            and not re.search(r"(?i)realai|hive|kokoro|vulkan", low)
        )
    ):
        try:
            from realai.bot.talk_easy import capability_card

            return capability_card()
        except Exception:
            return "Hey. RealAI here — local on this PC. Ask anything, or try /tools · /hive · /heal."
    patterns = [
        (r"(?i)\bhow can i (help|assist) you( today)?\??", ""),
        (r"(?i)\bwhat can i (help|assist) you with( today)?\??", ""),
        (r"(?i)\bi('?m| am) here to help you with any questions[^.]*\.", "I'm RealAI on this PC."),
        (r"(?i)\bwhat would you like to (know or do|know|do)\??", ""),
        (r"(?i)\bis there (something specific|a particular topic or question) you would like to (know or talk about|discuss)\??", ""),
        (r"(?i)\bi('m| am) (an )?ai language model[^.]*\.", "I'm RealAI on this machine."),
        (r"(?i)\bi('m| am) a chatbot designed to provide helpful[^.]*\.", "I'm RealAI — local stack on this PC."),
        (r"(?i)\bi('m| am) designed to be helpful[, ]+(informative|friendly)[^.]*\.", "I'm RealAI — local on this PC."),
        (r"(?i)\bi am here to assist you\.?", "I'm RealAI on this PC."),
        (r"(?i)\bas an ai language model,?\s*", ""),
        (r"(?i)\bi don'?t have a voice[, ]+but i can simulate[^.]*\.", "I have a local voice stack (Kokoro / Fish / XTTS) on this PC."),
    ]
    out = raw
    for pat, repl in patterns:
        out = re.sub(pat, repl, out)
    out = re.sub(r"\s{2,}", " ", out).strip(" \n\t,-")
    # Model sometimes echoes the lock label instead of answering
    if re.fullmatch(r"(?i)identity\s*lock[!.,:]?", out) or out.lower() in {
        "identity lock",
        "identitylock",
    }:
        return (
            "Yes — local voice is on. Kokoro / Fish Speech / XTTS on this PC. "
            "I can speak replies aloud."
        )
    if not out or out.lower() in {
        "hello!",
        "hello",
        "hi!",
        "hi",
        "hi there",
        "hi there!",
        "sure!",
        "hey",
        "hey!",
    }:
        return "Hey. RealAI here — local on this PC. What do you need?"
    if re.fullmatch(r"(?i)(hello|hi|hey|hi there)[!.,]?", out):
        return "Hey. RealAI here — local on this PC. What do you need?"
    return out


def _enrich_chat_body(body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Operator system + optional agent + memory inject + multi-agent flag + default model."""
    headers = headers or {}
    body = dict(body)
    # Orchestrator 2.0: classify + route + memory read before any backend call.
    try:
        from realai.meta_router import plan_call

        _msgs = list(body.get("messages") or [])
        _user = ""
        for _m in reversed(_msgs):
            if isinstance(_m, dict) and _m.get("role") == "user":
                _user = str(_m.get("content") or "")
                break
        if _user.strip():
            try:
                from realai.bot.natural_mode import workspace_route_mode

                _mode = workspace_route_mode()
            except Exception:
                _mode = None
            _pre = plan_call(_user, mode=_mode)
            body["realai_routing"] = _pre.get("routing") or {}
            body["realai_memory_read"] = _pre.get("memory_read") or {}
            _rt = body["realai_routing"]
            if not (
                body.get("agent_id")
                or body.get("agentId")
                or (headers or {}).get("X-RealAI-Agent-Id")
            ):
                _tgt = str((_rt or {}).get("target") or "")
                if _tgt and _tgt != "raw-model":
                    body["agent_id"] = _tgt
            if str((_rt or {}).get("privacy") or "") == "cloud-blocked":
                body["realai_local_only"] = True
    except Exception as _route_err:
        body["realai_routing"] = {
            "error": str(_route_err),
            "target": "overseer",
            "backend": "local-gguf",
        }
    try:
        from realai.bot.boot import coerce_local_model, ensure_bot_registered, local_only_enabled

        ensure_bot_registered()
        if local_only_enabled():
            body["model"] = coerce_local_model(body.get("model") or DEFAULT_MODEL)
    except Exception:
        pass
    msgs: List[Dict[str, Any]] = list(body.get("messages") or [])

    agent_id = (
        body.get("agent_id")
        or body.get("agentId")
        or headers.get("X-RealAI-Agent-Id")
        or os.environ.get("REALAI_DEFAULT_AGENT_ID")
        or ""
    )
    memory_on = body.get("memory")
    if memory_on is None:
        memory_on = headers.get("X-RealAI-Memory", "on" if MEMORY_INJECT else "off")
    memory_on = str(memory_on).lower() in ("1", "true", "yes", "on")

    multi = body.get("multi_agent") or body.get("multiAgent") or headers.get("X-RealAI-Multi-Agent")
    multi_on = str(multi).lower() in ("1", "true", "yes", "on", "pipeline", "parallel")
    multi_mode = "parallel" if str(multi).lower() == "parallel" else "pipeline"
    if multi_on:
        body["realai_multi_agent"] = multi_mode

    system_parts: List[str] = []
    # Identity lock + short operator directive (CONSOLE_OPERATOR_DIRECTIVE.md / env).
    # Small local models ignore long essays — keep the prefix short, but do not
    # drop the directive entirely (editing the file must change Console behavior).
    existing_systems = [m.get("content", "") for m in msgs if m.get("role") == "system"]
    non_system = [m for m in msgs if m.get("role") != "system"]
    try:
        from realai.bot.boot import chat_system_prefix

        system_parts.append(chat_system_prefix(OPERATOR_SYSTEM))
    except Exception:
        try:
            from realai.bot.boot import HARD_IDENTITY_LOCK

            system_parts.append(HARD_IDENTITY_LOCK)
            op = (OPERATOR_SYSTEM or "").strip()
            if op and op != HARD_IDENTITY_LOCK:
                system_parts.append(op[:480])
        except Exception:
            system_parts.append(OPERATOR_SYSTEM)
    for s in existing_systems:
        text = str(s or "").strip()
        if not text:
            continue
        low = text.lower()
        if "helpful ai assistant" in low or "how can i assist you" in low:
            continue
        if text in system_parts:
            continue
        if len(text) < 80 and "realai" in low:
            continue
        system_parts.append(text)

    # For tiny/greetings/voice turns, pin identity onto the latest user message too.
    if non_system:
        last = dict(non_system[-1])
        content = str(last.get("content") or "")
        low = content.lower().strip()
        if last.get("role") == "user" and (
            len(content) < 48
            or any(k in low for k in ("voice", "sound like", "speak", "who are you", "your name", "hey", "hello", "hi"))
        ):
            last["content"] = (
                "[You are RealAI. Answer the user directly. "
                "If they ask about voice/sound: you speak via local Kokoro/Fish/XTTS — "
                "confident, warm, clear. Never say Identity Lock or deny having a voice.]\n"
                + content
            )
            non_system[-1] = last

    agent = _find_agent(str(agent_id)) if agent_id else None
    if agent:
        system_parts.append(_agent_system_block(agent))
        body["realai_agent"] = {"id": agent.get("id"), "role": agent.get("role")}

    if memory_on:
        mem = _memory_snippet()
        if mem:
            system_parts.append(mem)
            body["realai_memory_injected"] = True

    if multi_on:
        system_parts.append(
            "[Multi-agent mode requested: planner → worker → critic via orchestration gold + Vulkan. "
            "The orchestrator may run a multi-agent pipeline instead of a single completion.]"
        )

    # tools advertised (Vulkan may ignore; orchestrator can execute if tool_calls returned)
    if body.get("tools") is True or str(headers.get("X-RealAI-Tools", "")).lower() in ("1", "true", "on"):
        body["tools"] = _readonly_tools_catalog()

    body["messages"] = [{"role": "system", "content": "\n\n".join(system_parts)}] + non_system
    # Fit under Vulkan n_ctx before proxy (HIVE dumps / long history → 400 exceed_context)
    fitted, fit_meta = _fit_messages_to_context(body["messages"], n_ctx=N_CTX, reserve_out=CTX_RESERVE_OUT)
    body["messages"] = fitted
    body["realai_context_fit"] = fit_meta
    # Cap completion so prompt+output stays inside n_ctx
    try:
        max_out = int(body.get("max_tokens") or CTX_RESERVE_OUT)
    except (TypeError, ValueError):
        max_out = CTX_RESERVE_OUT
    body["max_tokens"] = max(16, min(max_out, CTX_RESERVE_OUT, max(64, N_CTX // 8)))
    # Resolve RealAI model id → backend GGUF id for Vulkan
    try:
        from realai.model_catalog import resolve_model_for_backend
        backend_id, model_meta = resolve_model_for_backend(body.get("model") or DEFAULT_MODEL)
        body["realai_model"] = model_meta
        body["model"] = backend_id  # what Vulkan understands
    except Exception as e:
        body["realai_model"] = {"error": str(e), "requested": body.get("model")}
        if not body.get("model") or str(body.get("model")).startswith("realai"):
            body["model"] = DEFAULT_BACKEND_MODEL
    return body


class Handler(BaseHTTPRequestHandler):
    server_version = "RealAIv3Orchestrator/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[v3-orch] %s - %s\n" % (self.address_string(), fmt % args))

    def _cors(self) -> None:
        # Browser must only talk to RealAI (:8001). Organs stay internal.
        origin = (self.headers.get("Origin") or "").strip()
        if origin in ("http://127.0.0.1:8001", "http://localhost:8001"):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8001")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, x-realai-voice, X-RealAI-Voice, X-Request-Id, X-Provider, X-RealAI-Tools",
        )
        self.send_header("Access-Control-Max-Age", "86400")

    def _json(self, code: int, obj: Any) -> None:
        def _default(o: Any) -> Any:
            if isinstance(o, (bytes, bytearray)):
                import base64

                return {
                    "__bytes_base64__": base64.b64encode(bytes(o)).decode("ascii"),
                    "length": len(o),
                }
            if isinstance(o, Path):
                return str(o)
            return str(o)

        try:
            data = json.dumps(obj, indent=2, default=_default).encode("utf-8")
        except Exception as exc:
            # Never abort the socket with an empty body — browsers show ERR_EMPTY_RESPONSE.
            data = json.dumps(
                {
                    "error": "json_encode_failed",
                    "detail": str(exc),
                    "orchestrator": "v3",
                }
            ).encode("utf-8")
            code = 500 if code < 400 else code
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            # Client navigated away / aborted — do not tear down the server thread loudly.
            return

    def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _fusion_config_js(self) -> bytes:
        """Emit live Fusion config aimed at this Hive process (same host/port)."""
        port = int(os.environ.get("ORCH_PORT", "8001") or "8001")
        api_base = (os.environ.get("REALAI_API_BASE") or f"http://127.0.0.1:{port}").rstrip("/")
        api_key = os.environ.get("REALAI_API_KEY") or "local"
        payload = {
            "BACKEND_BASE": api_base,
            "API_KEY": api_key,
            "PORT": port,
            "SERVICE": "realai-v3-orchestrator",
        }
        # Browser script.js prefers same-origin when path is under /fusion-ui/.
        return ("window.__REALAI_CONFIG__ = {0};\n".format(json.dumps(payload))).encode("utf-8")

    def _serve_fusion_ui(self, request_path: str) -> bool:
        """Fusion is merged into Console — redirect the shell; keep assets for legacy links."""
        if request_path in ("/fusion-ui", "/fusion-ui/", "/fusion-ui/index.html"):
            # Console keeps its look; Fusion stack/overseer lives under Ops → Fusion.
            self.send_response(302)
            self.send_header("Location", "/console?fusion=1")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            return True

        if not request_path.startswith("/fusion-ui/"):
            return False

        fusion_dir = _FUSION_UI_DIR or _resolve_fusion_ui_dir()
        if fusion_dir is None:
            self._json(404, {"error": "fusion_ui_not_found", "hint": "expected repo-root fusion-ui/"})
            return True

        if request_path == "/fusion-ui/config.js":
            self._send_bytes(200, self._fusion_config_js(), "application/javascript; charset=utf-8")
            return True

        rel = unquote(request_path[len("/fusion-ui/") :])
        if not rel or ".." in rel.replace("\\", "/").split("/"):
            self._json(404, {"error": "not_found", "path": request_path})
            return True

        target = (fusion_dir / rel).resolve()
        try:
            target.relative_to(fusion_dir.resolve())
        except ValueError:
            self._json(404, {"error": "not_found", "path": request_path})
            return True

        if not target.is_file():
            self._json(404, {"error": "not_found", "path": request_path})
            return True

        if target.name.startswith(".env") or target.suffix.lower() in {".env", ".pem", ".key"}:
            self._json(404, {"error": "not_found", "path": request_path})
            return True

        content_type, _ = mimetypes.guess_type(str(target))
        if not content_type:
            content_type = "application/octet-stream"
        if target.suffix.lower() in {".html", ".js", ".css", ".svg", ".json"}:
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".svg": "image/svg+xml",
                ".json": "application/json",
            }.get(target.suffix.lower(), content_type)

        self._send_bytes(200, target.read_bytes(), content_type)
        return True

    def _serve_voice_lab_ui(self, request_path: str) -> bool:
        """Serve Voice Lab UI from repo voice-lab/ on Hive (correct product port)."""
        if request_path in ("/voice-lab", "/voice-lab/", "/voice", "/voice/"):
            request_path = "/voice-lab/index.html"
        if not request_path.startswith("/voice-lab/"):
            return False
        ui_dir = _VOICE_LAB_UI_DIR or _resolve_voice_lab_ui_dir()
        if ui_dir is None:
            self._json(404, {"error": "voice_lab_ui_not_found", "hint": "expected repo-root voice-lab/"})
            return True
        rel = unquote(request_path[len("/voice-lab/") :])
        if not rel or ".." in rel.replace("\\", "/").split("/"):
            self._json(404, {"error": "not_found", "path": request_path})
            return True
        target = (ui_dir / rel).resolve()
        try:
            target.relative_to(ui_dir.resolve())
        except ValueError:
            self._json(404, {"error": "not_found", "path": request_path})
            return True
        if not target.is_file():
            self._json(404, {"error": "not_found", "path": request_path})
            return True
        content_type, _ = mimetypes.guess_type(str(target))
        if target.suffix.lower() == ".html":
            content_type = "text/html; charset=utf-8"
            html = target.read_text(encoding="utf-8", errors="replace")
            lab = (os.environ.get("REALAI_VOICE_LAB_URL") or "http://127.0.0.1:8890").rstrip("/")
            inject = (
                f"<script>window.__REALAI_VOICE_LAB__={json.dumps(lab)};"
                f"window.__REALAI_HIVE__={json.dumps('http://' + (self.headers.get('Host') or '127.0.0.1:8001'))};</script>\n</head>"
            )
            if "</head>" in html:
                html = html.replace("</head>", inject, 1)
            self._send_bytes(200, html.encode("utf-8"), content_type)
            return True
        if not content_type:
            content_type = "application/octet-stream"
        self._send_bytes(200, target.read_bytes(), content_type)
        return True

    def _serve_agents_ui(self, request_path: str) -> bool:
        """Serve Agent Activity UI static files. Returns True if handled."""
        if request_path in ("/agents-ui", "/agents-ui/", "/agents", "/agents/"):
            request_path = "/agents-ui/index.html"

        if not request_path.startswith("/agents-ui/"):
            return False

        ui_dir = _AGENTS_UI_DIR or _resolve_agents_ui_dir()
        if ui_dir is None:
            self._json(404, {"error": "agents_ui_not_found", "hint": "expected repo-root agents-ui/"})
            return True

        rel = unquote(request_path[len("/agents-ui/") :])
        if not rel or ".." in rel.replace("\\", "/").split("/"):
            self._json(404, {"error": "not_found", "path": request_path})
            return True

        target = (ui_dir / rel).resolve()
        try:
            target.relative_to(ui_dir.resolve())
        except ValueError:
            self._json(404, {"error": "not_found", "path": request_path})
            return True

        if not target.is_file():
            self._json(404, {"error": "not_found", "path": request_path})
            return True

        content_type, _ = mimetypes.guess_type(str(target))
        if not content_type:
            content_type = "application/octet-stream"
        if target.suffix.lower() in {".html", ".js", ".css", ".svg", ".json"}:
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".svg": "image/svg+xml",
                ".json": "application/json",
            }.get(target.suffix.lower(), content_type)

        self._send_bytes(200, target.read_bytes(), content_type)
        return True

    def _serve_agents_sse(self) -> None:
        """Server-Sent Events stream for live agent activity."""
        import queue as _queue

        from realai.agent_activity import BUS, ensure_simulation, set_simulation

        ensure_simulation(_load_agents())
        # First Agents UI connection turns sim on so the graph is not a dead page.
        try:
            set_simulation(True)
        except Exception:
            pass
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()
        q = BUS.subscribe()

        def _sse_bytes(obj: Any) -> bytes:
            try:
                return f"data: {json.dumps(obj, default=str)}\n\n".encode("utf-8")
            except Exception:
                return b'data: {"type":"error","error":"sse_encode_failed"}\n\n'

        try:
            self.wfile.write(b'data: {"type":"connected"}\n\n')
            self.wfile.flush()
            # Replay recent hive/agent activity so a freshly opened Agents UI
            # immediately shows work that already happened.
            for event in BUS.recent(40):
                self.wfile.write(_sse_bytes(event))
            self.wfile.flush()
        except (OSError, ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            BUS.unsubscribe(q)
            return
        try:
            while True:
                try:
                    event = q.get(timeout=15)
                    self.wfile.write(_sse_bytes(event))
                    self.wfile.flush()
                except _queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (OSError, ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            BUS.unsubscribe(q)

    def _read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        # RealAI brand assets (public/)
        if parsed.path in ("/favicon.ico", "/favicon.svg", "/og.jpg", "/site.webmanifest"):
            pub = Path(os.environ.get("REALAI_HOME") or os.environ.get("REALAI_ROOT") or "") / "public"
            if not pub.is_dir():
                pub = Path(__file__).resolve().parents[2] / "public"
            name = "favicon.svg" if parsed.path.endswith((".ico", ".svg")) else parsed.path.lstrip("/")
            target = pub / name
            if target.is_file():
                ctype = {
                    "favicon.svg": "image/svg+xml",
                    "favicon.ico": "image/svg+xml",
                    "og.jpg": "image/jpeg",
                    "site.webmanifest": "application/manifest+json",
                }.get(name, "application/octet-stream")
                self._send_bytes(200, target.read_bytes(), ctype)
                return

        # Fusion UI (raw path — keep /fusion-ui/script.js etc.; do not use stripped path)
        if self._serve_fusion_ui(parsed.path.split("?", 1)[0]):
            return

        # Agent Activity UI
        if self._serve_agents_ui(parsed.path.split("?", 1)[0]):
            return

        # Voice Lab UI (product port :8001 — not :8890 JSON / not :8787 vite)
        if self._serve_voice_lab_ui(parsed.path.split("?", 1)[0]):
            return

        if path in ("/console", "/console.html", "/ui"):
            # Prefer VS Code webview console (browser mode) so /console matches the extension UI.
            home = Path(os.environ.get("REALAI_HOME") or os.environ.get("REALAI_ROOT") or "")
            repo = Path(__file__).resolve().parents[2]
            candidates = [
                home / "apps" / "vscode" / "webview" / "console.html",
                repo / "apps" / "vscode" / "webview" / "console.html",
                home / "console.html",
                Path(os.environ.get("REALAI_ROOT") or "") / "console.html",
                repo / "console.html",
                Path(__file__).resolve().parents[1] / "console.html",
            ]
            console_path = next((p for p in candidates if p.is_file()), None)
            if console_path is None:
                self._json(404, {"error": "console.html not found", "tried": [str(p) for p in candidates]})
                return
            html = console_path.read_text(encoding="utf-8", errors="replace")
            # VS Code template uses __CONSOLE_CSS__ — inline CSS for browser same-origin.
            if "__CONSOLE_CSS__" in html or "acquireVsCodeApi" in html:
                css_path = console_path.parent / "console.css"
                css = css_path.read_text(encoding="utf-8", errors="replace") if css_path.is_file() else ""
                html = html.replace('href="__CONSOLE_CSS__"', 'href="/console.css"')
                html = html.replace("__CONSOLE_CSS__", "/console.css")
                _port = os.environ.get("ORCH_PORT", "8001")
                hive = f"http://{self.headers.get('Host') or f'127.0.0.1:{_port}'}"
                inject = (
                    f"<script>window.__REALAI_HIVE__={json.dumps(hive)};"
                    f"window.__REALAI_CONSOLE_MODE__='browser';</script>\n"
                    f"<!-- console browser-parity {css_path.name if css else 'inline'} -->\n"
                    "</head>"
                )
                if "</head>" in html:
                    html = html.replace("</head>", inject, 1)
                # Keep critical CSS even if /console.css fails to load.
                if css and "console-css-inline" not in html:
                    html = html.replace(
                        "</style>",
                        "</style>\n<style id=\"console-css-from-file\">" + css + "</style>",
                        1,
                    )
            raw_html = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.send_header("Content-Length", str(len(raw_html)))
            self.end_headers()
            self.wfile.write(raw_html)
            return

        if path == "/console.css":
            home = Path(os.environ.get("REALAI_HOME") or os.environ.get("REALAI_ROOT") or "")
            repo = Path(__file__).resolve().parents[2]
            css_candidates = [
                home / "apps" / "vscode" / "webview" / "console.css",
                repo / "apps" / "vscode" / "webview" / "console.css",
            ]
            css_path = next((p for p in css_candidates if p.is_file()), None)
            if css_path is None:
                self._json(404, {"error": "console.css not found"})
                return
            raw = css_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path in ("/", "/health"):
            # Compose health: orchestrator + vulkan
            vulkan_ok = False
            vulkan_body: Any = None
            try:
                code, _, data = _proxy("GET", "/health", None, {})
                vulkan_ok = code == 200
                try:
                    vulkan_body = json.loads(data.decode("utf-8", errors="ignore"))
                except Exception:
                    vulkan_body = data.decode("utf-8", errors="ignore")[:200]
            except Exception as e:
                vulkan_body = str(e)
            # Orchestrator is up even when Vulkan is down (embeddings/recovery still work).
            # Use HTTP 200 + status=degraded so clients can keep using non-chat routes.
            health_payload = {
                "status": "ok" if vulkan_ok else "degraded",
                "service": "realai-v3-orchestrator",
                "vulkan": {"ok": vulkan_ok, "base": VULKAN_BASE, "body": vulkan_body},
                "self_improve_enabled": _self_improve_on(),
                "training_data": str(TRAINING_DATA),
                "recovery": "GET /v1/recovery",
                "embeddings": "POST /v1/embeddings",
                "lora": "GET /v1/lora",
                "fusion_ui": "GET /fusion-ui/",
                "fusion_ui_dir": str(_FUSION_UI_DIR or ""),
                "agents_ui": "GET /agents-ui/",
                "voice_lab_ui": "GET /voice-lab/",
                "agents_ui_dir": str(_AGENTS_UI_DIR or ""),
                "console": "GET /console",
            }
            try:
                from realai.recovery_registry import resolve_lora_root
                health_payload["lora_root"] = str(resolve_lora_root() or "")
            except Exception:
                pass
            self._json(200, health_payload)
            return

        if path == "/v1/workspace":
            try:
                from realai.workspace import (
                    get_request_workspace,
                    is_realai_product_tree,
                    product_root,
                    realai_home,
                    realai_workspace,
                )

                ws = realai_workspace()
                self._json(
                    200,
                    {
                        "ok": True,
                        "workspace": str(ws),
                        "home": str(realai_home()),
                        "product_root": str(product_root()),
                        "mode": "product" if is_realai_product_tree(ws) else "project",
                        "request_override": str(get_request_workspace() or ""),
                        "hint": (
                            "Say 'work in C:\\path\\to\\repo' in Console to switch. "
                            "Writes stay under the active workspace."
                        ),
                    },
                )
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
            return

        if path == "/v1/models":
            # RealAI provider facade — clients see realai-* ids, not raw llama filenames
            try:
                from realai.model_catalog import openai_models_payload
                self._json(200, openai_models_payload())
            except Exception as e:
                # fallback proxy if catalog fails
                try:
                    code, hdrs, data = _proxy("GET", "/v1/models", None, dict(self.headers))
                    self.send_response(code)
                    self.send_header("Content-Type", hdrs.get("Content-Type", "application/json"))
                    self._cors()
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as e2:
                    self._json(500, {"error": str(e), "fallback_error": str(e2)})
            return

        if path == "/v1/training/status":
            self._json(200, _training_status())
            return

        if path == "/v1/training/samples":
            n = int((qs.get("n") or ["3"])[0])
            self._json(200, _training_samples(max(1, min(n, 20))))
            return

        if path == "/v1/training/plan":
            self._json(200, _finetune_plan())
            return

        if path == "/v1/agents/events":
            self._serve_agents_sse()
            return

        if path == "/v1/agents/graph":
            try:
                from realai.agent_activity import build_graph, ensure_simulation

                agents = _load_agents()
                ensure_simulation(agents)
                self._json(200, build_graph(agents))
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/agents/profiles":
            try:
                from realai.agent_activity import load_profiles

                self._json(200, load_profiles())
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path in ("/v1/agents/executions", "/v1/agents/executions/active"):
            try:
                from realai.agent_activity import BUS

                if path.endswith("/active"):
                    self._json(200, {"data": BUS.active(), "count": len(BUS.active())})
                else:
                    recent = BUS.recent(50)
                    self._json(200, {"data": recent, "count": len(recent)})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/agents":
            agents = _load_agents()
            full = (qs.get("full") or ["0"])[0] in ("1", "true", "yes")
            agents = _filter_agents_for_api(agents, full=full)
            data = []
            for a in agents:
                item = {
                    "id": a.get("id"),
                    "role": a.get("role"),
                    "description": (a.get("description") or "")[:240],
                    "capabilities": a.get("capabilities") or [],
                    "risk_level": a.get("risk_level"),
                    "preferred_profile": a.get("preferred_profile"),
                    "hive": bool(a.get("hive")),
                }
                if full:
                    item["description"] = a.get("description") or ""
                    item["tags"] = a.get("tags") or []
                    item["required_tools"] = a.get("required_tools") or []
                data.append(item)
            self._json(200, {
                "object": "list",
                "data": data,
                "count": len(data),
                "full": full,
                "source": str(AGENTS_PATH) if full else ".github/agents + pipeline",
                "agents_ui": "/agents-ui/",
            })
            return

        if path.startswith("/v1/agents/"):
            aid = path.split("/v1/agents/", 1)[-1]
            if aid in ("events", "graph", "profiles", "executions", "run", "simulation"):
                self._json(404, {"error": "use_exact_route", "path": path})
                return
            agent = _find_agent(aid)
            if not agent:
                self._json(404, {"error": "agent_not_found", "id": aid})
            else:
                self._json(200, agent)
            return

        if path == "/v1/self-improve/status":
            self._json(200, _self_improve_status())
            return

        # --- Self-heal (multi-repo fix loop) ---
        if path == "/v1/self-heal/status":
            try:
                from realai.self_heal import status as heal_status
                self._json(200, heal_status())
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/self-heal/abilities":
            try:
                from realai.self_heal import abilities_manifest
                self._json(200, abilities_manifest())
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/tools":
            self._json(200, {
                "tools": _readonly_tools_catalog(),
                "execute": "POST /v1/tools/execute {name, arguments}",
                "mode": "read_only_plus_gated_self_heal",
                "surfaces": {
                    "craft": "POST /v1/craft",
                    "hive": "GET|POST /v1/hive",
                    "abilities": "GET /v1/abilities · POST /v1/abilities/run",
                },
            })
            return

        if path == "/v1/abilities":
            try:
                from realai.ability_catalog import build_catalog, coverage_summary

                cat = build_catalog()
                self._json(200, {
                    "ok": True,
                    "coverage": coverage_summary(),
                    "abilities": cat.get("abilities") or [],
                    "run": "POST /v1/abilities/run {ability, input, context}",
                    "tools_execute": "POST /v1/tools/execute {name: ability.<id>, arguments}",
                })
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/hive":
            self._json(200, _hive_status({}))
            return

        if path == "/v1/craft":
            self._json(200, {
                "ok": True,
                "surface": "craft",
                "usage": {
                    "POST": "{action|prompt, ...} — action uses craft TOOLS; prompt runs craft_chat",
                    "chat_slash": "/craft doctor · /craft heal · /craft multi <task>",
                },
                "actions": sorted(_craft_run({"action": "__missing__"}).get("available") or []),
            })
            return

        if path == "/v1/agent-tools/status":
            try:
                from realai.v3_runtime_bridge import agent_tools_status
                self._json(200, agent_tools_status())
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/deepen/status":
            last = _ROOT / "scan_results" / "deepen_last.json"
            hist = _ROOT / "scan_results" / "deepen_history.jsonl"
            runs = 0
            if hist.is_file():
                try:
                    runs = sum(1 for _ in hist.read_text(encoding="utf-8").splitlines() if _.strip())
                except Exception:
                    runs = 0
            payload: Dict[str, Any] = {
                "service": "realai-deepen",
                "history_runs": runs,
                "history_path": str(hist),
                "last_path": str(last),
            }
            if last.is_file():
                try:
                    payload["last"] = json.loads(last.read_text(encoding="utf-8"))
                except Exception as e:
                    payload["last_error"] = str(e)
            self._json(200, payload)
            return

        if path == "/v1/weights":
            # Local weights gold map (connect candidates for Vulkan / RealAI)
            wpath = _ROOT / "scan_results" / "weights_connect_candidates.json"
            full = _ROOT / "scan_results" / "weights_gold_map.json"
            if wpath.is_file():
                try:
                    data = json.loads(wpath.read_text(encoding="utf-8"))
                    data["full_map"] = str(full)
                    data["rescan"] = "POST /v1/weights/scan or python scanners/scan_model_weights.py"
                    self._json(200, data)
                except Exception as e:
                    self._json(500, {"error": str(e)})
            else:
                self._json(200, {
                    "candidates": [],
                    "note": "No scan yet — POST /v1/weights/scan or run scanners/scan_model_weights.py",
                })
            return

        if path == "/v1/recovery":
            try:
                from realai.recovery_registry import inventory
                self._json(200, inventory())
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/lora":
            try:
                from realai.recovery_registry import list_lora_adapters, resolve_lora_root
                adapters = list_lora_adapters(limit=500)
                self._json(200, {
                    "object": "list",
                    "root": str(resolve_lora_root()) if resolve_lora_root() else None,
                    "count": len(adapters),
                    "data": adapters,
                    "note": (
                        "PEFT LoRA adapters recovered from realai2/checkpoints_lora. "
                        "Not auto-loaded into Vulkan; use for finetune / merge tooling."
                    ),
                })
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/capabilities":
            try:
                from realai.ability_catalog import build_catalog, coverage_summary
                cat = build_catalog()
                cov = cat.get("coverage") or {}
                live = [
                    a["id"] for a in (cat.get("abilities") or [])
                    if a.get("status") == "LIVE"
                ]
                partial = [
                    a["id"] for a in (cat.get("abilities") or [])
                    if a.get("status") == "PARTIAL"
                ]
                self._json(200, {
                    "capabilities": live + [f"partial:{x}" for x in partial],
                    "coverage": cov,
                    "ability_count": cov.get("ability_count"),
                    "weighted_pct": cov.get("weighted_pct"),
                    "by_status": cov.get("by_status"),
                    "external_roots_exist": cat.get("external_roots_exist"),
                    "external_roots_total": cat.get("external_roots_total"),
                    "tools_cli": (coverage_summary().get("tools_cli")),
                    "inference": VULKAN_BASE,
                    "ui_hint": "Point REALAI_API_BASE at this orchestrator (default :8001)",
                    "self_heal": "GET /v1/self-heal/abilities — discover/assemble/promote/learn loop",
                    "note": (
                        "weighted_pct is honesty vs technical rundown; "
                        "verify_matrix passes are stack health only"
                    ),
                    "catalog_meta": cat.get("meta"),
                })
            except Exception as e:
                self._json(200, {
                    "capabilities": [
                        "chat",
                        "local-vulkan",
                        "training-status",
                        "self-improve-gated",
                        "self-heal-multi-repo",
                        "operator-system-prompt",
                    ],
                    "inference": VULKAN_BASE,
                    "error_note": str(e),
                    "ui_hint": "Point REALAI_API_BASE at this orchestrator (default :8001)",
                    "self_heal": "GET /v1/self-heal/abilities — discover/assemble/promote/verify loop",
                })
            return

        # Multi-step jobs (server.orchestration TaskOrchestrator via realai.server.router)
        if path == "/v1/tasks" or path.startswith("/v1/tasks/"):
            try:
                from realai.server.router import dispatch_request
                code, payload, _ctype = dispatch_request("GET", path, None)
                self._json(code, payload)
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        self._json(404, {"error": "not_found", "path": path})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        raw = self._read_body()

        if path == "/v1/embeddings":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            try:
                from realai.lambda_embeddings_audio import create_embeddings_response
                self._json(200, create_embeddings_response(body))
            except Exception as e:
                # Fallback to structured server router if present
                try:
                    from realai.server.router import handle_embeddings_request
                    self._json(200, handle_embeddings_request(body))
                except Exception as e2:
                    self._json(500, {"error": str(e), "fallback_error": str(e2)})
            return

        if path == "/v1/audio/transcriptions":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                body = {}
            try:
                from realai.lambda_embeddings_audio import create_transcription_response
                self._json(200, create_transcription_response(body))
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/audio/speech":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                body = {}
            text = str(body.get("input") or body.get("text") or "").strip()
            want_backend = str(
                body.get("backend") or body.get("model") or os.environ.get("REALAI_TTS_BACKEND") or "realai-tts"
            ).strip().lower()
            # Same-origin proxy to Voice Lab (:8890) for XTTS clone — avoids browser CORS.
            if text and want_backend in ("xtts", "xtts_v2", "coqui", "clone", "realai-tts", "realai", "laura"):
                try:
                    import base64
                    import urllib.request

                    lab = (os.environ.get("REALAI_VOICE_LAB_URL") or "http://127.0.0.1:8890").rstrip("/")
                    # RealAI voice ids (never expose organ names to the browser)
                    _voice = str(body.get("voice") or body.get("voice_id") or "laura").strip().lower()
                    _speaker = os.environ.get("REALAI_XTTS_SPEAKER") or r"C:\models\checkpoints_lora\voices\unwrenchable_clip.wav"
                    if _voice in ("laura", "realai", "default", "clone"):
                        body = dict(body or {})
                        body["voice"] = "laura"
                        if _speaker and os.path.isfile(_speaker):
                            os.environ["REALAI_XTTS_SPEAKER"] = _speaker
                    payload = json.dumps(
                        {
                            "input": text,
                            "text": text,
                            "voice": body.get("voice") or body.get("voice_id"),
                            "backend": "xtts",
                            "model": "xtts",
                            "response_format": "json",
                        }
                    ).encode("utf-8")
                    req = urllib.request.Request(
                        lab + "/v1/audio/speech",
                        data=payload,
                        headers={"Content-Type": "application/json", "Accept": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=90) as resp:
                        lab_raw = resp.read()
                        ctype = str(resp.headers.get("Content-Type") or "")
                    if "audio" in ctype or "wav" in ctype:
                        if lab_raw and len(lab_raw) > 64:
                            self._json(
                                200,
                                {
                                    "created": int(__import__("time").time()),
                                    "voice": body.get("voice") or "laura",
                                    "format": "wav",
                                    "text_echo": text[:500],
                                    "audio_b64": base64.b64encode(lab_raw).decode("ascii"),
                                    "bytes": len(lab_raw),
                                    "realai": {"status": "ok", "backend": "realai-tts", "via": "voice-lab-proxy"},
                                },
                            )
                            return
                    else:
                        lab_j = json.loads(lab_raw.decode("utf-8") or "{}")
                        organ_backend = str(lab_j.get("backend") or "").strip().lower()
                        organ_ok = bool(lab_j.get("ok", True)) and bool(lab_j.get("audio_b64")) and int(lab_j.get("bytes") or 0) > 64
                        # Prefer XTTS clone; do not brand SAPI/Piper as RealAI speech
                        if organ_ok and organ_backend and organ_backend not in ("xtts", "xtts_v2", "coqui", ""):
                            self._json(
                                502,
                                {
                                    "error": "speech_organ_not_xtts",
                                    "detail": "RealAI speech organ did not use XTTS/Laura. Fix Coqui/torch stack or start XTTS :8020.",
                                    "realai": {"provider": "realai", "backend": "realai-tts", "organ_status": organ_backend},
                                },
                            )
                            return
                        if organ_ok and organ_backend in ("xtts", "xtts_v2", "coqui"):
                            lab_j.setdefault("realai", {})
                            if isinstance(lab_j["realai"], dict):
                                lab_j["realai"]["provider"] = "realai"
                                lab_j["realai"]["backend"] = "realai-tts"
                            lab_j["backend"] = "realai-tts"
                            lab_j["model"] = "realai-tts"
                            lab_j["voice"] = body.get("voice") or "laura"
                            lab_j["provider"] = "realai"
                            lab_j["text_echo"] = text
                            # never leak organ names
                            for k in ("error",):
                                lab_j.pop(k, None)
                            self._json(200, lab_j)
                            return
                        self._json(
                            502,
                            {
                                "error": "speech_organ_failed",
                                "detail": lab_j.get("error") or lab_j.get("detail") or "no usable audio",
                                "realai": {"provider": "realai", "backend": "realai-tts"},
                            },
                        )
                        return
                except Exception as lab_exc:
                    body = dict(body or {})
                    body["_voice_lab_proxy_error"] = str(lab_exc)
            try:
                import base64

                # Prefer XTTS for console speak even if process was started with kokoro.
                if want_backend in ("xtts", "xtts_v2", "coqui", "clone", "realai-tts", "realai", "laura"):
                    os.environ["REALAI_TTS_BACKEND"] = "xtts"

                from realai.voice.tts_engine import get_tts_engine

                engine = get_tts_engine()
                wav = engine.synthesize(text) if text else b""
                organ = getattr(engine, "last_backend", None) or ""
                if wav and len(wav) > 64 and organ == "xtts":
                    self._json(
                        200,
                        {
                            "created": int(__import__("time").time()),
                            "ok": True,
                            "provider": "realai",
                            "model": "realai-tts",
                            "backend": "realai-tts",
                            "voice": body.get("voice") or "laura",
                            "format": "wav",
                            "text_echo": text[:500],
                            "audio_b64": base64.b64encode(wav).decode("ascii"),
                            "bytes": len(wav),
                            "realai": {
                                "status": "ok",
                                "provider": "realai",
                                "backend": "realai-tts",
                                "via": "gateway-local-xtts",
                                "models_root": os.environ.get(
                                    "REALAI_MODELS_DIR",
                                    r"C:\models\checkpoints_lora",
                                ),
                            },
                        },
                    )
                    return
                if want_backend in ("xtts", "xtts_v2", "coqui", "clone", "realai-tts", "realai", "laura"):
                    self._json(
                        502,
                        {
                            "error": "speech_organ_not_xtts",
                            "detail": f"local engine used {organ or 'none'}; want xtts/Laura",
                            "realai": {"provider": "realai", "backend": "realai-tts"},
                        },
                    )
                    return
            except Exception as eng_exc:
                body = dict(body or {})
                body["_tts_engine_error"] = str(eng_exc)
            try:
                from realai.lambda_embeddings_audio import create_speech_response

                self._json(200, create_speech_response(body))
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/recovery/promote":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                body = {}
            try:
                from realai.recovery_registry import promote_core
                self._json(200, promote_core(dry_run=bool(body.get("dry_run"))))
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/tasks":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            try:
                from realai.server.router import dispatch_request
                code, payload, _ctype = dispatch_request("POST", path, body)
                self._json(code, payload)
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/chat/completions":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            hdrs_in = {k: self.headers.get(k) for k in self.headers.keys()}
            # Normalize header keys for our helpers
            hdrs_norm = {str(k): str(v) for k, v in hdrs_in.items() if v is not None}

            # Operator intent: craft / hive / ability / multi without waiting for GGUF tool_calls
            user_text = _last_user_text(body.get("messages") or [])
            # Early meta-route (talk/operator short-circuits included)
            try:
                from realai.meta_router import plan_call

                if str(user_text or "").strip():
                    try:
                        from realai.bot.natural_mode import workspace_route_mode

                        _early_mode = workspace_route_mode()
                    except Exception:
                        _early_mode = None
                    _early = plan_call(user_text, mode=_early_mode)
                    body["realai_routing"] = _early.get("routing") or body.get("realai_routing")
                    body["realai_memory_read"] = _early.get("memory_read") or body.get("realai_memory_read")
            except Exception:
                pass
            tools_hdr = str(
                hdrs_norm.get("X-RealAI-Tools") or hdrs_norm.get("x-realai-tools") or ""
            ).lower()
            # IDE clients (VS Code) send X-RealAI-Tools: off so prose containing
            # "git"/"command"/"run" is NOT hijacked by live_exec.
            if tools_hdr in ("0", "false", "no", "off"):
                tools_on = False
            elif tools_hdr in ("1", "true", "yes", "on"):
                tools_on = True
            else:
                tools_on = os.environ.get("REALAI_BOT_TOOLS", "1").strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                    "",
                )
            # Natural talk short-circuit (hey / what can you do) — before tools/Vulkan
            # so Console feels like chatting with an operator, not a generic LLM.
            try:
                from realai.bot.talk_easy import try_talk_easy

                talk = try_talk_easy(user_text)
            except Exception:
                talk = None
            if talk is not None:
                content = str((talk.get("result") or {}).get("text") or "")
                obj = {
                    "id": "realai-talk",
                    "object": "chat.completion",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "model": body.get("model") or DEFAULT_MODEL,
                    "realai_meta": {
                        "orchestrator": "v3",
                        "provider": "realai",
                        "operator": "talk",
                        "talk_easy": True,
                        "routing": body.get("realai_routing"),
                    },
                }
                try:
                    voice_hdr = str(
                        hdrs_norm.get("X-RealAI-Voice")
                        or hdrs_norm.get("x-realai-voice")
                        or ""
                    ).lower()
                    want_voice = voice_hdr in ("1", "true", "yes", "on") or os.environ.get(
                        "REALAI_BOT_VOICE", ""
                    ).strip().lower() in ("1", "true", "yes", "on")
                    if want_voice:
                        # Do not import/synthesize TTS here. Loading voice backends
                        # inside chat/completions has hard-crashed Hive (browser:
                        # net::ERR_EMPTY_RESPONSE). Console speaks via POST /v1/audio/speech.
                        obj["realai_meta"]["voice"] = {
                            "speak": True,
                            "spoken_text": content,
                            "enabled": True,
                            "provider": "realai-voice",
                            "synthesize_via": "/v1/audio/speech",
                        }
                except Exception:
                    pass
                self._json(200, obj)
                return

            if tools_on:
                dispatch = _chat_operator_dispatch(user_text)
                if dispatch is not None:
                    if dispatch.get("surface") == "live_exec":
                        try:
                            from realai.bot.live_exec import format_live_reply

                            content = format_live_reply(dispatch)
                        except Exception:
                            content = _format_operator_reply(dispatch)
                    elif dispatch.get("surface") in ("tool", "tools") or dispatch.get("tool"):
                        try:
                            from realai.bot.easy_tools import format_easy_result

                            content = format_easy_result(
                                str(dispatch.get("tool") or dispatch.get("surface") or "tool"),
                                dispatch.get("result"),
                            )
                        except Exception:
                            content = _format_operator_reply(dispatch)
                    else:
                        # Prefer compact formatter for hive / coverage shaped payloads
                        try:
                            from realai.bot.easy_tools import format_easy_result

                            content = format_easy_result(
                                str(dispatch.get("surface") or "operator"),
                                dispatch.get("result"),
                            )
                        except Exception:
                            content = _format_operator_reply(dispatch)
                    obj = {
                        "id": "realai-operator" if dispatch.get("surface") != "live_exec" else "realai-live-exec",
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": content},
                                "finish_reason": "stop",
                            }
                        ],
                        "model": body.get("model") or DEFAULT_MODEL,
                        "realai_meta": {
                            "orchestrator": "v3",
                            "provider": "realai",
                            "operator": dispatch.get("surface"),
                            "operator_result": dispatch.get("result"),
                            "live_exec": dispatch.get("result")
                            if dispatch.get("surface") == "live_exec"
                            else None,
                            "tools_enabled": True,
                        },
                    }
                    # Speak the live result when voice is on
                    try:
                        voice_hdr = str(
                            hdrs_norm.get("X-RealAI-Voice")
                            or hdrs_norm.get("x-realai-voice")
                            or ""
                        ).lower()
                        want_voice = voice_hdr in ("1", "true", "yes", "on") or os.environ.get(
                            "REALAI_BOT_VOICE", ""
                        ).strip().lower() in ("1", "true", "yes", "on")
                        if want_voice:
                            from realai.bot.boot import maybe_voice_route

                            voice = maybe_voice_route(content, intent="chat", synthesize=False)
                            obj["realai_meta"]["voice"] = {
                                "speak": voice.get("speak"),
                                "spoken_text": voice.get("spoken_text"),
                                "enabled": True,
                            }
                    except Exception:
                        pass
                    data = json.dumps(obj, default=str).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._cors()
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

            # Natural Mode: plain-English file/code/repo asks run Craft inspect
            # before Vulkan (Vulkan never executes tools). Slash/$ stay on the
            # operator / easy_tools / live_exec paths above.
            try:
                from realai.bot.natural_mode import apply_natural_grounding

                ground = apply_natural_grounding(body, user_text)
                if ground.get("should_ground"):
                    body["realai_natural"] = ground
                    if not (
                        body.get("agent_id")
                        or body.get("agentId")
                        or hdrs_norm.get("X-RealAI-Agent-Id")
                    ):
                        body["agent_id"] = "coder"
                    if ground.get("admit_failure") or ground.get("short_circuit"):
                        content = str(
                            ground.get("reply")
                            or ground.get("failure_text")
                            or "I tried to inspect the repo and the tools failed. I won't invent file contents."
                        )
                        obj = {
                            "id": "realai-natural",
                            "object": "chat.completion",
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {"role": "assistant", "content": content},
                                    "finish_reason": "stop",
                                }
                            ],
                            "model": body.get("model") or DEFAULT_MODEL,
                            "realai_meta": {
                                "orchestrator": "v3",
                                "provider": "realai",
                                "operator": "natural",
                                "natural": ground,
                                "used_tools": ground.get("used_tools") or ground.get("tools") or [],
                                "wrote": bool(ground.get("wrote")),
                                "routing": body.get("realai_routing"),
                            },
                        }
                        self._json(200, obj)
                        return
            except Exception as _nat_err:
                body["realai_natural"] = {"error": str(_nat_err)}

            body = _enrich_chat_body(body, hdrs_norm)

            # Optional multi-agent pipeline (planner→worker→critic) via recovered gold
            if body.get("realai_multi_agent"):
                try:
                    from realai.v3_runtime_bridge import run_multi_agent
                    # last user message as task
                    user_task = ""
                    for m in reversed(body.get("messages") or []):
                        if m.get("role") == "user":
                            user_task = str(m.get("content") or "")
                            break
                    ma = run_multi_agent(
                        user_task,
                        mode=str(body.get("realai_multi_agent") or "pipeline"),
                        max_tokens=int(body.get("max_tokens") or 384),
                        temperature=float(body.get("temperature") or 0.3),
                    )
                    content = ma.get("final_output") or json.dumps(ma, default=str)[:4000]
                    obj = {
                        "id": "realai-multi-agent",
                        "object": "chat.completion",
                        "model": body.get("model") or DEFAULT_MODEL,
                        "choices": [{
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }],
                        "realai_meta": {
                            "orchestrator": "v3",
                            "provider": "realai",
                            "vulkan_base": VULKAN_BASE,
                            "multi_agent": ma,
                            "agent": body.get("realai_agent"),
                            "memory_injected": body.get("realai_memory_injected", False),
                            "model": body.get("realai_model"),
                            "self_heal": True,
                        },
                    }
                    # Public model id in response
                    if body.get("realai_model"):
                        obj["model"] = body["realai_model"].get("resolved_id") or obj["model"]
                    data = json.dumps(obj).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._cors()
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    # fall through to normal chat with error note in system? just proxy with note
                    body.setdefault("realai_multi_agent_error", str(e))

            # Strip non-OpenAI fields before proxy
            proxy_body = {
                k: v for k, v in body.items()
                if k not in (
                    "agent_id", "agentId", "memory", "realai_agent", "realai_memory_injected",
                    "multi_agent", "multiAgent", "realai_multi_agent", "realai_multi_agent_error",
                    "realai_model", "realai_context_fit",
                    "realai_routing", "realai_memory_read", "realai_natural",
                    "realai_natural_grounded", "realai_local_only",
                )
            }
            # Vulkan may not support tools — only send if client asked and we keep simple
            if proxy_body.get("tools") is True or (
                isinstance(proxy_body.get("tools"), list)
            ):
                # strip tools list for vulkan compatibility
                proxy_body.pop("tools", None)
            out = json.dumps(proxy_body).encode("utf-8")
            code, hdrs, data = _proxy("POST", "/v1/chat/completions", out, dict(self.headers))
            # annotate meta if json
            try:
                obj = json.loads(data.decode("utf-8"))
                if isinstance(obj, dict):
                    meta = obj.get("realai_meta") or {}
                    rmodel = body.get("realai_model") or {}
                    meta.update({
                        "orchestrator": "v3",
                        "provider": "realai",
                        "vulkan_base": VULKAN_BASE,
                        "self_improve_enabled": _self_improve_on(),
                        "self_heal": True,
                        "agent": body.get("realai_agent"),
                        "memory_injected": body.get("realai_memory_injected", False),
                        "multi_agent_requested": bool(body.get("realai_multi_agent")),
                        "natural": body.get("realai_natural"),
                        "used_tools": (
                            (body.get("realai_natural") or {}).get("used_tools")
                            or (body.get("realai_natural") or {}).get("tools")
                            or []
                        ),
                        "routing": body.get("realai_routing"),
                        "model": rmodel,
                        "context_fit": body.get("realai_context_fit"),
                        "models_root": os.environ.get(
                            "REALAI_MODELS_DIR",
                            r"C:\models\checkpoints_lora",
                        ),
                    })
                    obj["realai_meta"] = meta
                    # Client-facing model id is RealAI, not raw gguf
                    if rmodel.get("resolved_id"):
                        obj["model"] = rmodel["resolved_id"]
                    # Scrub corporate-assistant filler from small-model replies
                    try:
                        for ch in obj.get("choices") or []:
                            msg = ch.get("message") if isinstance(ch, dict) else None
                            if isinstance(msg, dict) and msg.get("content"):
                                msg["content"] = _scrub_assistant_text(str(msg.get("content")))
                    except Exception:
                        pass
                    # Craft Phase 2: apply /write path|||content from coder reply after inspect.
                    try:
                        nat = body.get("realai_natural") or {}
                        if nat.get("apply_model_writes"):
                            reply_txt = ""
                            for ch in obj.get("choices") or []:
                                msg = ch.get("message") if isinstance(ch, dict) else None
                                if isinstance(msg, dict) and msg.get("content"):
                                    reply_txt = str(msg.get("content") or "")
                                    break
                            applied = _apply_natural_model_writes(reply_txt) if reply_txt else []
                            if applied:
                                n_ok = sum(
                                    1
                                    for a in applied
                                    if isinstance(a.get("result"), dict) and a["result"].get("ok")
                                )
                                note = f"\n\n[applied {n_ok}/{len(applied)} /write patch(es)]"
                                for ch in obj.get("choices") or []:
                                    msg = ch.get("message") if isinstance(ch, dict) else None
                                    if isinstance(msg, dict) and msg.get("content"):
                                        msg["content"] = str(msg.get("content") or "") + note
                                        break
                                used = list(meta.get("used_tools") or [])
                                used.append("write")
                                meta["used_tools"] = used
                                meta["applied_writes"] = applied
                                obj["realai_meta"] = meta
                    except Exception:
                        pass
                    # Voice metadata for console speak-aloud / local TTS
                    try:
                        voice_hdr = str(
                            hdrs_norm.get("X-RealAI-Voice")
                            or hdrs_norm.get("x-realai-voice")
                            or ""
                        ).lower()
                        want_voice = voice_hdr in ("1", "true", "yes", "on") or os.environ.get(
                            "REALAI_BOT_VOICE", ""
                        ).strip().lower() in ("1", "true", "yes", "on")
                        if want_voice:
                            from realai.bot.boot import maybe_voice_route

                            reply_txt = ""
                            for ch in obj.get("choices") or []:
                                msg = ch.get("message") if isinstance(ch, dict) else None
                                if isinstance(msg, dict) and msg.get("content"):
                                    reply_txt = str(msg.get("content") or "")
                                    break
                            # synthesize only when explicitly requested via header=on and env allows
                            do_synth = voice_hdr in ("1", "true", "yes", "on", "synth")
                            voice_meta = maybe_voice_route(
                                reply_txt,
                                intent="chat",
                                synthesize=do_synth,
                            )
                            # Always expose spoken_text for browser TTS even if synth backends are down
                            if voice_meta.get("enabled") and not voice_meta.get("spoken_text"):
                                try:
                                    from realai.bot.boot import prepare_bot_speech

                                    voice_meta["spoken_text"] = prepare_bot_speech(reply_txt)
                                    voice_meta["speak"] = True
                                except Exception:
                                    voice_meta["spoken_text"] = reply_txt
                                    voice_meta["speak"] = bool(reply_txt)
                            # Attach audio_b64 when synthesis produced bytes
                            audio = voice_meta.get("audio")
                            if isinstance(audio, (bytes, bytearray)) and len(audio) > 44:
                                import base64

                                voice_meta["audio_b64"] = base64.b64encode(bytes(audio)).decode("ascii")
                                voice_meta["audio_bytes"] = len(audio)
                                voice_meta["format"] = "wav"
                            elif "audio" in voice_meta:
                                voice_meta.pop("audio", None)
                            meta["voice"] = voice_meta
                            obj["realai_meta"] = meta
                    except Exception as voice_exc:
                        meta["voice"] = {"enabled": False, "error": str(voice_exc)}
                        obj["realai_meta"] = meta
                    data = json.dumps(obj).encode("utf-8")
            except Exception:
                pass
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/v1/agents/simulation":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            try:
                from realai.agent_activity import (
                    ensure_simulation,
                    set_simulation,
                    simulation_enabled,
                )

                ensure_simulation(_load_agents())
                if body.get("toggle"):
                    enabled = set_simulation(not simulation_enabled())
                elif "enabled" in body:
                    enabled = set_simulation(bool(body.get("enabled")))
                else:
                    enabled = simulation_enabled()
                self._json(200, {"ok": True, "enabled": enabled})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if path == "/v1/agents/run":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            agent_id = str(body.get("agent_id") or body.get("agent") or "ai-orchestrator").strip()
            task = str(body.get("task") or body.get("prompt") or body.get("input") or "").strip()
            if not task:
                self._json(400, {"error": "missing_task"})
                return
            try:
                from realai.agent_activity import ensure_simulation, run_agent_task

                ensure_simulation(_load_agents())
                multi = bool(body.get("multi") or body.get("use_multi"))
                dry = bool(body.get("dry_run") or body.get("pulse_only"))
                # Run in-thread so SSE subscribers see dispatch→complete around the call
                self._json(
                    200,
                    run_agent_task(
                        agent_id,
                        task,
                        use_multi=multi,
                        dry_run=dry,
                        pulse_only=dry,
                    ),
                )
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/multi-agent/run":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            try:
                from realai.agent_activity import ensure_simulation, run_agent_task

                task = str(body.get("task") or body.get("prompt") or "")
                ensure_simulation(_load_agents())
                dry = bool(body.get("dry_run") or body.get("pulse_only"))
                result = run_agent_task(
                    str(body.get("agent_id") or body.get("agent") or "hive-orchestrator"),
                    task,
                    use_multi=True,
                    dry_run=dry,
                    pulse_only=dry,
                )
                self._json(200, result)
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/deepen":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                body = {}
            try:
                from realai.deepen_cycle import run_deepen
                rec = run_deepen(
                    assemble=bool(body.get("assemble", True)),
                    hive=bool(body.get("hive", True)),
                    cycle=bool(body.get("cycle", False)),
                )
                self._json(200, rec)
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/weights/scan":
            # Rescan local (and configured) weight locations for gold
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                body = {}
            try:
                import importlib.util
                script = _ROOT / "scanners" / "scan_model_weights.py"
                spec = importlib.util.spec_from_file_location("scan_model_weights", script)
                if spec is None or spec.loader is None:
                    self._json(500, {"error": "scan_model_weights.py not loadable"})
                    return
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                roots = list(mod.DEFAULT_ROOTS)
                for r in body.get("roots") or []:
                    roots.append(str(r))
                report = mod.scan(roots, max_depth=int(body.get("max_depth") or mod.MAX_DEPTH_DEFAULT))
                mod.write_reports(report)
                self._json(200, {
                    "ok": True,
                    "stats": report.get("stats"),
                    "connect_candidates": (report.get("connect_candidates") or [])[:30],
                    "reports": {
                        "map": str(_ROOT / "scan_results" / "weights_gold_map.json"),
                        "connect": str(_ROOT / "scan_results" / "weights_connect_candidates.json"),
                        "md": str(_ROOT / "scan_results" / "weights_gold_map.md"),
                    },
                })
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-600:]})
            return

        if path == "/v1/tools/execute":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            name = body.get("name") or body.get("tool")
            if not name:
                self._json(400, {"error": "missing_tool_name"})
                return
            # Read-only tools always; mutating assemble/promote need self-improve
            mutating = name in ("self_heal_assemble", "self_heal_promote_dry") or name.startswith("self_heal_promote")
            # multi_agent_run is expensive but read-only w.r.t. repo
            if mutating and not _self_improve_on():
                self._json(403, {"error": "self_improve_disabled"})
                return
            tool_name = str(name)
            args = body.get("arguments") or {}
            # Surface hive-ish tool work on Agents UI graph/feed.
            publish = None
            try:
                from realai.agent_activity import publish_complete, publish_dispatch

                low = tool_name.lower()
                hiveish = (
                    low in ("hive_run", "multi_agent_run", "overseer", "list_agents", "agent_tools_assess")
                    or low.startswith("ability.hive")
                    or low.startswith("ability.overseer")
                    or low.startswith("ability.omnibrain")
                    or low.startswith("ability.world_brain")
                    or low.startswith("ability.hominis")
                )
                if hiveish:
                    agent_id = "router"
                    if "overseer" in low:
                        agent_id = "overseer"
                    elif "multi" in low:
                        agent_id = "hive-orchestrator"
                    elif "coder" in low or "code" in low:
                        agent_id = "coder"
                    elif "omnibrain" in low or "world_brain" in low:
                        agent_id = "architect"
                    task = str(
                        (args.get("task") if isinstance(args, dict) else None)
                        or (args.get("input") if isinstance(args, dict) else None)
                        or (args.get("action") if isinstance(args, dict) else None)
                        or tool_name
                    )[:120]
                    publish_dispatch(agent_id, task, source="tool", tool=tool_name)
                    publish = (publish_complete, agent_id)
            except Exception:
                publish = None
            result = _run_tool(tool_name, args if isinstance(args, dict) else {})
            if publish:
                try:
                    done, aid = publish
                    ok = True
                    if isinstance(result, dict):
                        if result.get("ok") is False:
                            ok = False
                        inner = result.get("result")
                        if isinstance(inner, dict) and inner.get("ok") is False:
                            ok = False
                    done(aid, source="tool", tool=tool_name, ok=ok)
                except Exception:
                    pass
            self._json(200, {"tool": tool_name, "result": result})
            return

        if path == "/v1/abilities/run":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            aid = str(body.get("ability") or body.get("id") or body.get("name") or "").strip()
            if not aid:
                self._json(400, {"error": "missing_ability"})
                return
            name = aid if aid.startswith("ability.") else f"ability.{aid}"
            args = body.get("arguments") if isinstance(body.get("arguments"), dict) else {}
            if not args:
                args = {
                    "input": body.get("input") or body.get("task") or "",
                    "action": body.get("action") or "run",
                }
                ctx = body.get("context")
                if isinstance(ctx, dict):
                    args["context"] = ctx
                    args.update({k: v for k, v in ctx.items() if k not in args})
            self._json(200, {"ability": name, "result": _run_tool(name, args)})
            return

        if path == "/v1/craft":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            prompt = body.get("prompt") or body.get("text")
            if prompt and not body.get("action"):
                self._json(200, _craft_chat({"prompt": str(prompt)}))
                return
            self._json(200, _craft_run(body if isinstance(body, dict) else {}))
            return

        if path == "/v1/hive":
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            action = str(body.get("action") or "status").lower()
            if action in ("status", "", "info"):
                self._json(200, _hive_status(body if isinstance(body, dict) else {}))
                return
            try:
                from realai.agent_activity import publish_complete, publish_dispatch

                publish_dispatch("overseer", f"hive:{action}", source="hive")
                publish_dispatch("router", f"hive:{action}", source="hive")
                out = _hive_run(body if isinstance(body, dict) else {})
                ok = not (isinstance(out, dict) and out.get("ok") is False)
                publish_complete("router", source="hive", ok=ok, action=action)
                publish_complete("overseer", source="hive", ok=ok, action=action)
                self._json(200, out)
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-500:]})
            return

        if path == "/v1/self-improve/evaluate":
            self._json(200 if _self_improve_on() else 403, _self_improve_evaluate())
            return

        if path == "/v1/training/plan":
            self._json(200, _finetune_plan())
            return

        # Self-heal mutations (require REALAI_SELF_IMPROVE)
        if path.startswith("/v1/self-heal/"):
            try:
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except json.JSONDecodeError:
                body = {}
            try:
                from realai import self_heal as heal
                if path == "/v1/self-heal/assemble":
                    self._json(200 if _self_improve_on() else 403, heal.run_assemble() if _self_improve_on() else {"error": "self_improve_disabled"})
                    return
                if path == "/v1/self-heal/promote":
                    if not _self_improve_on():
                        self._json(403, {"error": "self_improve_disabled"})
                        return
                    self._json(200, heal.run_promote(apply=bool(body.get("apply"))))
                    return
                if path == "/v1/self-heal/discover":
                    if not _self_improve_on():
                        self._json(403, {"error": "self_improve_disabled"})
                        return
                    self._json(200, heal.run_discover(mode=str(body.get("mode") or "operational")))
                    return
                if path == "/v1/self-heal/learn-keywords":
                    # Catalog + keyword merge is read-mostly; allow when self-improve on
                    if not _self_improve_on():
                        self._json(403, {"error": "self_improve_disabled"})
                        return
                    self._json(200, heal.run_learn_keywords())
                    return
                if path == "/v1/self-heal/cycle":
                    if not _self_improve_on():
                        self._json(403, {"error": "self_improve_disabled"})
                        return
                    self._json(200, heal.run_full_cycle(apply_promote=bool(body.get("apply"))))
                    return
            except PermissionError as e:
                self._json(403, {"error": str(e)})
                return
            except Exception as e:
                self._json(500, {"error": str(e), "trace": traceback.format_exc()[-600:]})
                return

        self._json(404, {"error": "not_found", "path": path})


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="RealAI v3 orchestrator (UI → Vulkan + training/self-improve)")
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("ORCH_PORT", "8001")))
    args = ap.parse_args(argv)

    try:
        from realai.bot.boot import ensure_bot_registered, resolve_local_model

        bot = ensure_bot_registered()
        print("[realai-bot] persona={0} model={1}".format(bot.get("name"), resolve_local_model()))
    except Exception as exc:
        print("[realai-bot] warn: {0}".format(exc))

    print("=" * 60)
    print("RealAI v3 Orchestrator")
    print("=" * 60)
    print(f"  Listen:        http://{args.host}:{args.port}")
    print(f"  Vulkan backend:{VULKAN_BASE}")
    print(f"  Training data: {TRAINING_DATA}")
    print(f"  Self-improve:  {_self_improve_on()}")
    print(f"  Default model: {DEFAULT_MODEL}")
    print(f"  Fusion UI:     {_FUSION_UI_DIR or '(missing fusion-ui/)'}")
    print(f"  Agents UI:     {_AGENTS_UI_DIR or '(missing agents-ui/)'}")
    print()
    print(f"  *** Open Fusion UI:   http://{args.host}:{args.port}/fusion-ui/ ***")
    print(f"  *** Open Agents UI:   http://{args.host}:{args.port}/agents-ui/ ***")
    print(f"  *** Open Console:     http://{args.host}:{args.port}/console ***")
    print()
    print("  GET  /health")
    print("  GET  /fusion-ui/         -> Fusion Interface (static UI, same-origin API)")
    print("  GET  /agents-ui/         -> Agent Activity (graph + live SSE)")
    print("  GET  /console|/ui        -> RealAI Console")
    print("  GET  /v1/agents[/graph|/profiles|/events]")
    print("  POST /v1/agents/run|/simulation")
    print("  GET  /v1/models          -> RealAI model facade (realai-* ids)")
    print("  POST /v1/chat/completions-> RealAI + Vulkan backend")
    print("  POST /v1/embeddings      -> local embeddings (recovered)")
    print("  POST /v1/audio/transcriptions|speech -> stubs (recovered paths)")
    print("  GET  /v1/recovery        -> kilo/realai2 recovery inventory")
    print("  GET  /v1/lora            -> PEFT LoRA adapters (checkpoints_lora)")
    print("  POST /v1/recovery/promote-> promote staged recovery into live tree")
    print("  POST /v1/tasks           -> create multi-step task (planner/worker/critic)")
    print("  GET  /v1/tasks[/{id}]    -> list or read tasks")
    print("  GET  /v1/training/status")
    print("  GET  /v1/training/samples")
    print("  GET  /v1/training/plan")
    print("  GET  /v1/self-improve/status")
    print("  POST /v1/self-improve/evaluate  (REALAI_SELF_IMPROVE=true)")
    print("  GET  /v1/capabilities     -> ability catalog + coverage %")
    print("  GET  /v1/tools            -> tool catalog (agent_tools + self-heal)")
    print("  GET  /v1/agent-tools/status")
    print("  POST /v1/tools/execute    -> craft/hive/ability.* + registry fallthrough")
    print("  GET  /v1/abilities        -> ability catalog")
    print("  POST /v1/abilities/run    -> run ability.<id>")
    print("  GET|POST /v1/hive         -> hive status / cycle / multi")
    print("  GET|POST /v1/craft        -> craft TOOLS / craft_chat")
    print("  POST /v1/multi-agent/run  -> planner/worker/critic (Vulkan)")
    print("  POST /v1/chat/completions multi_agent=true · /craft|/hive|/ability intents")
    print("  GET  /v1/deepen/status    -> deepen history / last run")
    print("  POST /v1/deepen           -> learn+assemble+hive (deeper each run)")
    print("  GET  /v1/self-heal/status|abilities")
    print("  POST /v1/self-heal/assemble|promote|discover|learn-keywords|cycle")
    print("=" * 60)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down orchestrator...")
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
