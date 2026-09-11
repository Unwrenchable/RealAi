#!/usr/bin/env python3
"""Phase 4 verification matrix for RealAI v3 live stack + self-heal."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(os.environ.get("REALAI_ROOT", r"C:\realai"))
OUT = ROOT / "scan_results" / "phase4_verify_matrix.json"
OUT_MD = ROOT / "scan_results" / "phase4_verify_matrix.md"

ORCH = os.environ.get("REALAI_ORCH_BASE", "http://127.0.0.1:8001").rstrip("/")
VULKAN = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")
UI = os.environ.get("REALAI_UI_BASE", "http://127.0.0.1:3000").rstrip("/")


def get(url: str, timeout: float = 15) -> Tuple[bool, int, Any]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                body = raw.decode("utf-8", errors="ignore")[:300]
            return True, resp.status, body
    except urllib.error.HTTPError as e:
        return False, e.code, str(e)
    except Exception as e:
        return False, 0, str(e)


def post(url: str, payload: dict, timeout: float = 120) -> Tuple[bool, int, Any]:
    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=data, method="POST", headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                body = raw.decode("utf-8", errors="ignore")[:300]
            return True, resp.status, body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")[:500]
        except Exception:
            body = str(e)
        return False, e.code, body
    except Exception as e:
        return False, 0, str(e)


def check_file(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file()


def main() -> int:
    rows: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None):
        rows.append({"check": name, "ok": ok, "detail": detail})
        print(("PASS" if ok else "FAIL"), name, str(detail)[:120] if detail is not None else "")

    # Live stack
    ok, code, body = get(f"{VULKAN}/health")
    add("vulkan_health", ok and code == 200, body)

    ok, code, body = get(f"{ORCH}/health")
    add("orchestrator_health", ok and code in (200, 503), body)

    ok, code, body = get(f"{UI}/")
    add("ui_http", ok and code == 200, {"status": code})

    ok, code, body = post(
        f"{ORCH}/v1/chat/completions",
        {
            "model": "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
            "messages": [{"role": "user", "content": "Say only: matrix ok"}],
            "max_tokens": 16,
            "temperature": 0.1,
        },
        timeout=180,
    )
    content = ""
    if isinstance(body, dict):
        try:
            content = body["choices"][0]["message"]["content"]
        except Exception:
            content = str(body)[:200]
    add("orch_chat", ok and code == 200, content)

    # Training / self-improve / self-heal
    ok, code, body = get(f"{ORCH}/v1/training/status")
    add("training_status", ok and code == 200 and isinstance(body, dict) and body.get("finetune_dataset"), body if not ok else {"files": len(body.get("files") or [])})

    ok, code, body = get(f"{ORCH}/v1/self-improve/status")
    add("self_improve_status", ok and code == 200, body if isinstance(body, dict) else body)

    ok, code, body = get(f"{ORCH}/v1/self-heal/status")
    add("self_heal_status", ok and code == 200 and isinstance(body, dict), body.get("abilities") if isinstance(body, dict) else body)

    ok, code, body = get(f"{ORCH}/v1/self-heal/abilities")
    add("self_heal_abilities", ok and code == 200, body.get("name") if isinstance(body, dict) else body)

    # Phase 5F: ability catalog / coverage honesty
    ok, code, body = get(f"{ORCH}/v1/capabilities")
    cap_ok = (
        ok and code == 200 and isinstance(body, dict)
        and (body.get("weighted_pct") is not None or body.get("coverage") or body.get("capabilities"))
    )
    add(
        "capabilities_catalog",
        cap_ok,
        {
            "weighted_pct": body.get("weighted_pct") if isinstance(body, dict) else None,
            "ability_count": body.get("ability_count") if isinstance(body, dict) else None,
            "external_roots_exist": body.get("external_roots_exist") if isinstance(body, dict) else None,
        },
    )

    ok, code, body = get(f"{ORCH}/v1/tools")
    tools_ok = ok and code == 200 and isinstance(body, dict) and isinstance(body.get("tools"), list) and len(body.get("tools") or []) >= 4
    add("tools_catalog", tools_ok, {"n": len(body.get("tools") or []) if isinstance(body, dict) else 0})

    ok, code, body = get(f"{ORCH}/v1/agent-tools/status")
    at_ok = ok and code == 200 and isinstance(body, dict) and int(body.get("agents_count") or 0) > 0
    add("agent_tools_status", at_ok, {
        "agents_count": body.get("agents_count") if isinstance(body, dict) else None,
        "packages": len(body.get("packages") or []) if isinstance(body, dict) else 0,
    })

    ok, code, body = post(
        f"{ORCH}/v1/tools/execute",
        {"name": "agent_tools_list_agents", "arguments": {"query": "documentation", "limit": 5}},
        timeout=30,
    )
    list_ok = ok and code == 200 and isinstance(body, dict)
    add("tools_agent_tools_list", list_ok, body.get("result", {}).get("count") if isinstance(body, dict) else body)

    ok, code, body = get(f"{ORCH}/v1/models")
    models_ok = False
    model_ids = []
    if ok and code == 200 and isinstance(body, dict):
        data = body.get("data") or []
        model_ids = [m.get("id") for m in data if isinstance(m, dict)]
        models_ok = any(str(i).startswith("realai") for i in model_ids) or bool(
            (body.get("realai") or {}).get("provider") == "realai-v3"
        )
    add("models_realai_facade", models_ok, {"ids": model_ids[:8], "default": (body.get("realai") or {}).get("default_model") if isinstance(body, dict) else None})

    ok, code, body = get(f"{ORCH}/v1/agents")
    agents_ok = ok and code == 200 and isinstance(body, dict) and int(body.get("count") or 0) > 0
    add("agents_list", agents_ok, {"count": body.get("count") if isinstance(body, dict) else None})

    ok, code, body = post(
        f"{ORCH}/v1/tools/execute",
        {"name": "list_agents"},
        timeout=30,
    )
    add("tools_list_agents", ok and code == 200, body if isinstance(body, dict) else body)

    ok, code, body = post(
        f"{ORCH}/v1/chat/completions",
        {
            "model": "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
            "agent_id": "agent-tools-documentation-pilot",
            "memory": "on",
            "messages": [{"role": "user", "content": "Reply with only: agent ok"}],
            "max_tokens": 16,
            "temperature": 0.1,
        },
        timeout=180,
    )
    meta = body.get("realai_meta") if isinstance(body, dict) else None
    add(
        "chat_with_agent_memory",
        ok and code == 200,
        {"meta": meta, "snip": str(body)[:120] if not isinstance(body, dict) else (body.get("choices") or [{}])[0]},
    )

    ok, code, body = post(f"{ORCH}/v1/self-improve/evaluate", {}, timeout=90)
    # 200 with scores, or 403 when flag off — both acceptable
    eval_ok = code in (200, 403) or (
        isinstance(body, dict) and (body.get("ok") or body.get("error") == "self_improve_disabled")
    )
    add("self_improve_evaluate", eval_ok, body if isinstance(body, dict) else body)

    # Artifacts on disk
    for rel in [
        "scan_results/era_map.json",
        "scan_results/gold_index.json",
        "scan_results/promote_queue.json",
        "scan_results/ability_catalog.json",
        "scan_results/ability_keywords_learned.json",
        "training/data/realai_finetune_dataset.jsonl",
        "training/data/ability_surface.jsonl",
        "realai/self_heal.py",
        "realai/self_improvement.py",
        "realai/ability_catalog.py",
        "realai/v3_orchestrator.py",
        "docs/ABILITY_SURFACE.md",
        "scanners/assemble_gold_index.py",
        "scanners/promote_gold.py",
        "scanners/dds3_missing_files.py",
    ]:
        add(f"artifact:{rel}", check_file(rel), rel)

    passed = sum(1 for r in rows if r["ok"])
    total = len(rows)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "total": total,
        "all_ok": passed == total,
        "endpoints": {"ui": UI, "orchestrator": ORCH, "vulkan": VULKAN},
        "checks": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        "# Phase 4 Verify Matrix",
        "",
        f"Generated: `{report['generated_at']}`",
        f"**{passed}/{total} passed** — {'ALL OK' if report['all_ok'] else 'SOME FAILED'}",
        "",
        f"- UI: `{UI}`",
        f"- Orchestrator: `{ORCH}`",
        f"- Vulkan: `{VULKAN}`",
        "",
        "| Check | Result | Detail |",
        "|-------|--------|--------|",
    ]
    for r in rows:
        det = json.dumps(r["detail"]) if not isinstance(r["detail"], str) else r["detail"]
        det = (det or "")[:80].replace("|", "/")
        md.append(f"| `{r['check']}` | {'PASS' if r['ok'] else 'FAIL'} | {det} |")
    md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"-> {OUT}")
    print(f"-> {OUT_MD}")
    print(f"RESULT {passed}/{total}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
