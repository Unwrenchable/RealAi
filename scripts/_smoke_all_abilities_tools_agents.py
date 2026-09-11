"""Smoke Hive abilities, tools, and agents — local only, write JSON report."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:8001"
OUT = Path(r"C:\RealAI-clean\scan_results\SMOKE_ALL_ABILITIES_TOOLS_AGENTS.json")
OUT_MD = Path(r"C:\RealAI-clean\docs\sessions\SMOKE_ALL.md")

# Safe args for known mutating / expensive tools
SAFE_ARGS = {
    "workspace_list": {"path": "."},
    "workspace_grep": {"pattern": "hive_governance", "path": "abilities", "glob": "*.py"},
    "workspace_read": {"path": "docs/RUN_SERVERS.md", "limit": 40},
    "list_agents": {},
    "self_heal_status": {},
    "ability_coverage": {},
    "training_status": {},
    "recovery_status": {},
    "agent_tools_status": {},
    "local_llama_health": {},
    "voice_health": {},
    "voice_speak": {"text": "RealAI voice smoke check."},
    "voice_listen": {"demo_text": "hello real ai"},
    "multi_agent_run": {
        "task": "Reply with exactly: SMOKE_MULTI_OK",
        "mode": "pipeline",
    },
    "craft_run": {"action": "status"},
    "craft_chat": {"prompt": "Say SMOKE_CRAFT_OK"},
    "hive_status": {},
    "hive_run": {"action": "status"},
    "overseer": {"action": "status"},
    "execute_code": {"code": "print(2+2)"},
    "web_research": {"query": "RealAI local hive"},
    "run_terminal_command": {"command": "echo realai-ok"},
    "agent_tools_assess": {"agent": "coder"},
    "agent_tools_list_tools": {},
    "agent_tools_invoke": {
        "tool": "filesystem",
        "payload": {"operation": "list", "path": "."},
        "dry_run": True,
    },
    "core.file_tool": {"action": "read", "path": "README.md"},
}

# Abilities that need specific inputs
ABILITY_ARGS = {
    "image_generation": {"prompt": "smoke test purple square"},
    "video_generation": {"prompt": "smoke ring", "frames": 4},
    "image_analysis": {},  # filled after image gen
    "audio_speech": {"text": "Smoke test voice."},
    "audio_transcription": {"demo_text": "smoke test"},
    "voice_streaming": {"mode": "status"},
    "translation": {"text": "hello", "target": "Spanish"},
    "business_planning": {"brief": "local AI smoke shop"},
    "therapy_counseling": {"text": "I am testing the system."},
    "hive_governance": {"action": "status"},
    "hominis_enterprise": {"action": "status"},
    "web_research": {"query": "RealAI local hive"},
    "chat_completion": {"input": "Reply SMOKE_CHAT_OK"},
    "text_generation": {"input": "Reply SMOKE_TEXT_OK"},
    "code_generation": {"input": "print(1) only"},
    "code_execution": {"code": "print(2+2)"},
    "embeddings": {"input": "smoke"},
    "sotd_contribute": {"input": "Hive smoke practice shot", "action": "status"},
    "code_engineer_cli": {"action": "status"},
    "quarantine_reconstruct": {"action": "status"},
    "overseer": {"action": "status"},
}


def http_json(method: str, path: str, body: dict | None = None, timeout: float = 90.0):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "X-RealAI-Tools": "on", "X-RealAI-Voice": "off"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return resp.status, json.loads(raw) if raw else {}


def ok_result(payload) -> bool:
    """Treat nested ``result.ok`` as authoritative for tools/execute wraps."""
    if not isinstance(payload, dict):
        return True
    inner = payload.get("result") if isinstance(payload.get("result"), dict) else None
    # Prefer nested tool/ability result when it declares ok
    if inner is not None and "ok" in inner:
        return bool(inner.get("ok"))
    if payload.get("ok") is False:
        return False
    if payload.get("error") and payload.get("ok") is not True:
        return False
    if isinstance(inner, dict) and inner.get("error") and inner.get("ok") is not True:
        return False
    return True


def main() -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "health": None,
        "abilities": {"pass": [], "fail": []},
        "tools": {"pass": [], "fail": [], "skipped": []},
        "agents": {"pass": [], "fail": []},
        "summary": {},
    }

    try:
        _, health = http_json("GET", "/health", timeout=5)
        report["health"] = health
    except Exception as e:
        report["health"] = {"error": str(e)}
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("HIVE DOWN", e)
        return

    # --- abilities from catalog ---
    _, caps = http_json("GET", "/v1/capabilities", timeout=15)
    ability_ids = []
    for c in caps.get("capabilities") or []:
        if isinstance(c, str):
            ability_ids.append(c.replace("partial:", ""))
        elif isinstance(c, dict) and c.get("id"):
            ability_ids.append(str(c["id"]))
    # unique preserve order
    seen = set()
    ability_ids = [a for a in ability_ids if not (a in seen or seen.add(a))]

    img_path = None
    t0 = time.time()
    for aid in ability_ids:
        name = aid if aid.startswith("ability.") else f"ability.{aid}"
        bare = name.replace("ability.", "")
        args = dict(ABILITY_ARGS.get(bare) or {"input": f"smoke {bare}", "action": "status"})
        if bare == "image_analysis" and img_path:
            args = {"path": img_path}
        try:
            status, payload = http_json(
                "POST",
                "/v1/tools/execute",
                {"name": name, "arguments": args},
                timeout=120,
            )
            passed = status == 200 and ok_result(payload)
            # capture image path for analysis
            if bare == "image_generation" and passed:
                try:
                    img_path = (
                        (payload.get("result") or {}).get("result") or {}
                    ).get("path")
                except Exception:
                    pass
            row = {"id": bare, "tool": name, "ok": passed, "bytes": len(json.dumps(payload))}
            if not passed:
                row["error"] = str(payload.get("error") or (payload.get("result") or {}).get("error") or payload)[:300]
            (report["abilities"]["pass"] if passed else report["abilities"]["fail"]).append(row)
            print(("PASS" if passed else "FAIL"), "ability", bare)
        except Exception as e:
            report["abilities"]["fail"].append({"id": bare, "tool": name, "ok": False, "error": str(e)[:300]})
            print("FAIL ability", bare, e)

    # --- tools catalog ---
    _, tools_payload = http_json("GET", "/v1/tools", timeout=15)
    raw_tools = list(tools_payload.get("tools") or [])
    tool_names: list[str] = []
    for t in raw_tools:
        if isinstance(t, str):
            tool_names.append(t)
        elif isinstance(t, dict):
            fn = t.get("function") if isinstance(t.get("function"), dict) else {}
            n = (
                t.get("name")
                or t.get("id")
                or t.get("tool")
                or (fn.get("name") if isinstance(fn, dict) else None)
            )
            if n:
                tool_names.append(str(n))
    # unique
    _seen_t: set[str] = set()
    tool_names = [n for n in tool_names if not (n in _seen_t or _seen_t.add(n))]

    # Skip obviously destructive / long-running unless we have safe args
    SKIP_PREFIX = ("self_heal_promote", "rollout", "harden_repos", "weights/scan")
    SKIP_EXACT = {
        "run_command",
        "shell",
        "hive_exec",
        "exec_command",
        "run_script",
        "exec_script",
        "self_heal_assemble",
        "self_extend",
        "self_repair",
    }

    for name in tool_names:
        if name in SKIP_EXACT or any(name.startswith(p) for p in SKIP_PREFIX):
            report["tools"]["skipped"].append({"name": name, "reason": "destructive_or_unbounded"})
            continue
        if name.startswith("ability."):
            # already covered in abilities loop
            report["tools"]["skipped"].append({"name": name, "reason": "covered_as_ability"})
            continue
        args = SAFE_ARGS.get(name)
        if args is None:
            # try empty / status-style
            args = {"action": "status"} if "status" in name or name.endswith("_status") else {}
        try:
            status, payload = http_json(
                "POST",
                "/v1/tools/execute",
                {"name": name, "arguments": args},
                timeout=90,
            )
            passed = status == 200 and ok_result(payload)
            row = {"name": name, "ok": passed, "bytes": len(json.dumps(payload))}
            if not passed:
                row["error"] = str(payload.get("error") or (payload.get("result") or {}).get("error") or "")[:300]
            (report["tools"]["pass"] if passed else report["tools"]["fail"]).append(row)
            print(("PASS" if passed else "FAIL"), "tool", name)
        except Exception as e:
            report["tools"]["fail"].append({"name": name, "ok": False, "error": str(e)[:300]})
            print("FAIL tool", name, e)

    # --- agents: list + sample detail + optional run for a few ---
    _, agents_payload = http_json("GET", "/v1/agents?full=1", timeout=20)
    agents = agents_payload.get("data") or []
    for a in agents:
        aid = a.get("id")
        if not aid:
            continue
        try:
            status, detail = http_json("GET", f"/v1/agents/{aid}", timeout=15)
            passed = status == 200 and (detail.get("id") == aid or detail.get("role"))
            row = {"id": aid, "ok": passed}
            if not passed:
                row["error"] = str(detail)[:200]
            (report["agents"]["pass"] if passed else report["agents"]["fail"]).append(row)
        except Exception as e:
            report["agents"]["fail"].append({"id": aid, "ok": False, "error": str(e)[:200]})

    # Spot-run a few key agents via /v1/agents/run
    for aid in ("vault77-overseer", "overseer-content-creator", "coder", "ai-orchestrator"):
        try:
            status, payload = http_json(
                "POST",
                "/v1/agents/run",
                {"agent_id": aid, "task": "Reply with exactly: AGENT_SMOKE_OK", "multi": False},
                timeout=120,
            )
            passed = status == 200 and ok_result(payload)
            report.setdefault("agent_runs", {"pass": [], "fail": []})
            row = {"id": aid, "ok": passed, "bytes": len(json.dumps(payload))}
            if not passed:
                row["error"] = str(payload.get("error") or "")[:300]
            (report["agent_runs"]["pass"] if passed else report["agent_runs"]["fail"]).append(row)
            print(("PASS" if passed else "FAIL"), "agent_run", aid)
        except Exception as e:
            report.setdefault("agent_runs", {"pass": [], "fail": []})
            report["agent_runs"]["fail"].append({"id": aid, "ok": False, "error": str(e)[:300]})
            print("FAIL agent_run", aid, e)

    elapsed = round(time.time() - t0, 1)
    report["summary"] = {
        "elapsed_sec": elapsed,
        "abilities_pass": len(report["abilities"]["pass"]),
        "abilities_fail": len(report["abilities"]["fail"]),
        "tools_pass": len(report["tools"]["pass"]),
        "tools_fail": len(report["tools"]["fail"]),
        "tools_skipped": len(report["tools"]["skipped"]),
        "agents_listed_pass": len(report["agents"]["pass"]),
        "agents_listed_fail": len(report["agents"]["fail"]),
        "agent_runs_pass": len((report.get("agent_runs") or {}).get("pass") or []),
        "agent_runs_fail": len((report.get("agent_runs") or {}).get("fail") or []),
        "coverage_pct": (caps.get("weighted_pct") or caps.get("coverage", {}).get("weighted_pct")),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    s = report["summary"]
    md = [
        "# Smoke — all abilities / tools / agents",
        "",
        f"Generated: `{report['generated_at']}`  ",
        f"Hive: `{BASE}`  elapsed **{s['elapsed_sec']}s**",
        "",
        "## Summary",
        "",
        f"| Surface | Pass | Fail | Skipped |",
        f"|---------|-----:|-----:|--------:|",
        f"| Abilities | {s['abilities_pass']} | {s['abilities_fail']} | — |",
        f"| Tools | {s['tools_pass']} | {s['tools_fail']} | {s['tools_skipped']} |",
        f"| Agents (GET) | {s['agents_listed_pass']} | {s['agents_listed_fail']} | — |",
        f"| Agent runs (spot) | {s['agent_runs_pass']} | {s['agent_runs_fail']} | — |",
        "",
        f"Coverage honesty: **{s.get('coverage_pct')}%**",
        "",
    ]
    if report["abilities"]["fail"]:
        md += ["## Failed abilities", ""]
        for f in report["abilities"]["fail"]:
            md.append(f"- `{f['id']}` — {f.get('error', '')}")
        md.append("")
    if report["tools"]["fail"]:
        md += ["## Failed tools", ""]
        for f in report["tools"]["fail"]:
            md.append(f"- `{f['name']}` — {f.get('error', '')}")
        md.append("")
    if report["agents"]["fail"]:
        md += ["## Failed agent lookups", ""]
        for f in report["agents"]["fail"][:40]:
            md.append(f"- `{f['id']}` — {f.get('error', '')}")
        md.append("")
    md += [f"Full JSON: `{OUT}`", ""]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print("wrote", OUT)
    print("wrote", OUT_MD)


if __name__ == "__main__":
    main()
