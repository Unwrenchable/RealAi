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
DEFAULT_MODEL = os.environ.get(
    "REALAI_DEFAULT_MODEL",
    "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
)
OPERATOR_SYSTEM = os.environ.get(
    "REALAI_OPERATOR_SYSTEM",
    "You are RealAI 3.0 — a local-first, operator-grade assistant. "
    "Be capable, direct, and amplify the user's tools, code, and infrastructure. "
    "Prefer action and structure over chatty filler. You run on local AMD Vulkan inference.",
)


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


def _enrich_chat_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure operator system prompt + default model for v3 feel."""
    msgs: List[Dict[str, Any]] = list(body.get("messages") or [])
    has_system = any(m.get("role") == "system" for m in msgs)
    if not has_system and OPERATOR_SYSTEM:
        msgs = [{"role": "system", "content": OPERATOR_SYSTEM}] + msgs
        body = dict(body)
        body["messages"] = msgs
    if not body.get("model"):
        body = dict(body)
        body["model"] = DEFAULT_MODEL
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
            self._json(200 if vulkan_ok else 503, {
                "status": "ok" if vulkan_ok else "degraded",
                "service": "realai-v3-orchestrator",
                "vulkan": {"ok": vulkan_ok, "base": VULKAN_BASE, "body": vulkan_body},
                "self_improve_enabled": _self_improve_on(),
                "training_data": str(TRAINING_DATA),
            })
            return

        if path == "/v1/models":
            code, hdrs, data = _proxy("GET", "/v1/models", None, dict(self.headers))
            self.send_response(code)
            self.send_header("Content-Type", hdrs.get("Content-Type", "application/json"))
            self._cors()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
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

        if path == "/v1/self-improve/status":
            self._json(200, _self_improve_status())
            return

        if path == "/v1/capabilities":
            self._json(200, {
                "capabilities": [
                    "chat",
                    "local-vulkan",
                    "training-status",
                    "self-improve-gated",
                    "operator-system-prompt",
                ],
                "inference": VULKAN_BASE,
                "ui_hint": "Point REALAI_API_BASE at this orchestrator (default :8001)",
            })
            return

        self._json(404, {"error": "not_found", "path": path})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        raw = self._read_body()

        if path == "/v1/chat/completions":
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            body = _enrich_chat_body(body)
            out = json.dumps(body).encode("utf-8")
            code, hdrs, data = _proxy("POST", "/v1/chat/completions", out, dict(self.headers))
            # annotate meta if json
            try:
                obj = json.loads(data.decode("utf-8"))
                if isinstance(obj, dict):
                    meta = obj.get("realai_meta") or {}
                    meta.update({
                        "orchestrator": "v3",
                        "vulkan_base": VULKAN_BASE,
                        "self_improve_enabled": _self_improve_on(),
                    })
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

        if path == "/v1/self-improve/evaluate":
            self._json(200 if _self_improve_on() else 403, _self_improve_evaluate())
            return

        if path == "/v1/training/plan":
            self._json(200, _finetune_plan())
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
    print("  GET  /v1/models          → proxy Vulkan")
    print("  POST /v1/chat/completions→ proxy Vulkan (+ operator system)")
    print("  GET  /v1/training/status")
    print("  GET  /v1/training/samples")
    print("  GET  /v1/training/plan")
    print("  GET  /v1/self-improve/status")
    print("  POST /v1/self-improve/evaluate  (REALAI_SELF_IMPROVE=true)")
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
