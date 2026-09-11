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
import os
import sys
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

# Repo root: .../realai package parent
_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

VULKAN_BASE = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")
TRAINING_DATA = Path(os.environ.get("REALAI_TRAINING_DATA", str(_ROOT / "training" / "data")))
AGENTS_PATH = Path(os.environ.get("REALAI_AGENTS_PATH", str(_ROOT / "agents" / "agentx" / "agents.json")))
MEMORY_DIR = Path(os.environ.get("REALAI_MEMORY_DIR", str(_ROOT / "recovered" / "from_archive" / "memory_snapshots")))
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
OPERATOR_SYSTEM = os.environ.get(
    "REALAI_OPERATOR_SYSTEM",
    "You are RealAI 3.0 — a local-first, operator-grade assistant. "
    "Be capable, direct, and amplify the user's tools, code, and infrastructure. "
    "Prefer action and structure over chatty filler. You run on local AMD Vulkan inference. "
    "You can request self-heal actions (discover/assemble/promote) when the user asks to fix the multi-repo mess.",
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


def _load_agents() -> List[Dict[str, Any]]:
    global _AGENTS_CACHE
    if _AGENTS_CACHE is not None:
        return _AGENTS_CACHE
    if not AGENTS_PATH.is_file():
        _AGENTS_CACHE = []
        return _AGENTS_CACHE
    try:
        data = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
        _AGENTS_CACHE = data if isinstance(data, list) else data.get("agents") or []
    except Exception:
        _AGENTS_CACHE = []
    return _AGENTS_CACHE


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
            return assess_agent_profile(
                str(arguments.get("agent_id") or ""),
                str(arguments.get("profile") or "balanced"),
            )
        if name == "multi_agent_run":
            from realai.v3_runtime_bridge import run_multi_agent
            return run_multi_agent(
                str(arguments.get("task") or ""),
                mode=str(arguments.get("mode") or "pipeline"),
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
        return {"error": f"unknown_tool:{name}"}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()[-500:]}


def _enrich_chat_body(body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Operator system + optional agent + memory inject + multi-agent flag + default model."""
    headers = headers or {}
    body = dict(body)
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
    # Keep existing system messages as base
    existing_systems = [m.get("content", "") for m in msgs if m.get("role") == "system"]
    non_system = [m for m in msgs if m.get("role") != "system"]
    if existing_systems:
        system_parts.extend(existing_systems)
    else:
        system_parts.append(OPERATOR_SYSTEM)

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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _json(self, code: int, obj: Any) -> None:
        data = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
            }
            try:
                from realai.recovery_registry import resolve_lora_root
                health_payload["lora_root"] = str(resolve_lora_root() or "")
            except Exception:
                pass
            self._json(200, health_payload)
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

        if path == "/v1/agents":
            agents = _load_agents()
            self._json(200, {
                "object": "list",
                "data": [
                    {
                        "id": a.get("id"),
                        "role": a.get("role"),
                        "description": (a.get("description") or "")[:240],
                        "capabilities": a.get("capabilities") or [],
                        "risk_level": a.get("risk_level"),
                        "preferred_profile": a.get("preferred_profile"),
                    }
                    for a in agents
                ],
                "count": len(agents),
                "source": str(AGENTS_PATH),
            })
            return

        if path.startswith("/v1/agents/"):
            aid = path.split("/v1/agents/", 1)[-1]
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

        if path == "/v1/chat/completions":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            hdrs_in = {k: self.headers.get(k) for k in self.headers.keys()}
            # Normalize header keys for our helpers
            hdrs_norm = {str(k): str(v) for k, v in hdrs_in.items() if v is not None}
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
                    "realai_model",
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
                        "model": rmodel,
                    })
                    obj["realai_meta"] = meta
                    # Client-facing model id is RealAI, not raw gguf
                    if rmodel.get("resolved_id"):
                        obj["model"] = rmodel["resolved_id"]
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

        if path == "/v1/multi-agent/run":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            try:
                from realai.v3_runtime_bridge import run_multi_agent
                self._json(200, run_multi_agent(
                    str(body.get("task") or body.get("prompt") or ""),
                    mode=str(body.get("mode") or "pipeline"),
                    max_tokens=int(body.get("max_tokens") or 384),
                    temperature=float(body.get("temperature") or 0.3),
                ))
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
            self._json(200, {"tool": name, "result": _run_tool(str(name), body.get("arguments") or {})})
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

    print("=" * 60)
    print("RealAI v3 Orchestrator")
    print("=" * 60)
    print(f"  Listen:        http://{args.host}:{args.port}")
    print(f"  Vulkan backend:{VULKAN_BASE}")
    print(f"  Training data: {TRAINING_DATA}")
    print(f"  Self-improve:  {_self_improve_on()}")
    print(f"  Default model: {DEFAULT_MODEL}")
    print()
    print("  GET  /health")
    print("  GET  /v1/models          -> RealAI model facade (realai-* ids)")
    print("  POST /v1/chat/completions-> RealAI + Vulkan backend")
    print("  POST /v1/embeddings      -> local embeddings (recovered)")
    print("  POST /v1/audio/transcriptions|speech -> stubs (recovered paths)")
    print("  GET  /v1/recovery        -> kilo/realai2 recovery inventory")
    print("  GET  /v1/lora            -> PEFT LoRA adapters (checkpoints_lora)")
    print("  POST /v1/recovery/promote-> promote staged recovery into live tree")
    print("  GET  /v1/training/status")
    print("  GET  /v1/training/samples")
    print("  GET  /v1/training/plan")
    print("  GET  /v1/self-improve/status")
    print("  POST /v1/self-improve/evaluate  (REALAI_SELF_IMPROVE=true)")
    print("  GET  /v1/capabilities     -> ability catalog + coverage %")
    print("  GET  /v1/tools            -> tool catalog (agent_tools + self-heal)")
    print("  GET  /v1/agent-tools/status")
    print("  POST /v1/tools/execute")
    print("  POST /v1/multi-agent/run  -> planner/worker/critic (Vulkan)")
    print("  POST /v1/chat/completions multi_agent=true optional")
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
