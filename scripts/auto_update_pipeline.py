#!/usr/bin/env python3
"""
RealAI Auto-Update Pipeline
===========================
One-shot (or scheduled) pipeline that:

1. Runs the full 7-phase dispatcher (via Craft's dispatch_prompt_actions)
2. Runs the self-heal loop
3. Optionally pulls latest git (if clean) and re-runs validation
4. Writes a single machine-readable report under REALAI_HOME/logs/

Safe by default: never force-pushes, never deletes recovered/, never
commits unless --commit is passed (and even then only with explicit message).

Usage:
  python scripts/auto_update_pipeline.py
  python scripts/auto_update_pipeline.py --skip-git
  python scripts/auto_update_pipeline.py --rounds=3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


def _home() -> Path:
    env = os.environ.get("REALAI_HOME")
    if env:
        return Path(env)
    for c in (Path(r"C:\RealAI-clean"), Path.home() / "RealAI-clean", Path(__file__).resolve().parents[1]):
        if c.is_dir():
            return c
    return Path.cwd()


HOME = _home()
LOG_DIR = HOME / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
REPORT = LOG_DIR / f"auto_update_{datetime.now():%Y%m%d_%H%M%S}.json"
LATEST = LOG_DIR / "last_auto_update.json"


def log(msg: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with (LOG_DIR / "auto_update.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except OSError:
        pass


def load_craft():
    """Import dispatch + heal tools from the live craft.py."""
    candidates = [
        HOME / "realai" / "cli" / "craft.py",
        HOME / "realai" / "craft.py",
        HOME / "craft.py",
    ]
    for craft_path in candidates:
        if not craft_path.is_file():
            continue
        import importlib.util
        spec = importlib.util.spec_from_file_location("realai_craft_pipeline", craft_path)
        if not (spec and spec.loader):
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            return mod
        except Exception as e:
            log(f"failed to load {craft_path}: {e}")
    return None


def run_git_safe(skip: bool = False) -> dict[str, Any]:
    if skip:
        return {"skipped": True}
    out: dict[str, Any] = {"cwd": str(HOME)}
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(HOME), text=True, stderr=subprocess.DEVNULL
        )
        out["dirty"] = bool(status.strip())
        if out["dirty"]:
            out["note"] = "working tree dirty — skipping fetch/pull"
            return out

        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(HOME), text=True
        ).strip()
        out["branch"] = branch

        subprocess.check_call(["git", "fetch", "--all", "--prune"], cwd=str(HOME),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # only fast-forward
        rc = subprocess.call(
            ["git", "merge", "--ff-only", f"origin/{branch}"],
            cwd=str(HOME),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        out["ff_merge"] = rc == 0
        if rc != 0:
            out["note"] = "could not fast-forward (diverged or no upstream)"
    except Exception as e:
        out["error"] = str(e)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="RealAI auto-update + heal pipeline")
    parser.add_argument("--skip-git", action="store_true")
    parser.add_argument("--rounds", type=int, default=3, help="self-heal rounds")
    parser.add_argument("--no-dispatch", action="store_true", help="skip the 7-phase dispatcher")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "started": datetime.now().isoformat(),
        "home": str(HOME),
        "ok": False,
        "steps": {},
    }

    log("=" * 60)
    log(f"RealAI Auto-Update Pipeline  HOME={HOME}")
    log("=" * 60)

    # 1. Git (safe)
    log("STEP 1 — git status / optional ff-only pull")
    report["steps"]["git"] = run_git_safe(skip=args.skip_git)
    log(f"git → {report['steps']['git']}")

    # 2. Load Craft
    log("STEP 2 — load craft.py tools")
    craft = load_craft()
    if craft is None:
        log("FATAL: craft.py not loadable")
        report["error"] = "craft.py missing or broken"
        _write_report(report)
        return 1
    log("craft.py loaded")

    # 3. Full dispatcher (all 7 phases)
    if not args.no_dispatch:
        log("STEP 3 — full automation (dispatcher all 7 phases)")
        try:
            dispatch = getattr(craft, "dispatch_prompt_actions", None)
            if dispatch:
                result = dispatch(prompt="full automation", run_all=True)
                report["steps"]["dispatch"] = {
                    "ok": result.get("ok"),
                    "summary": result.get("summary"),
                    "errors": result.get("errors"),
                    "scripts_run": [r.get("script") for r in (result.get("results") or [])],
                }
                log(f"dispatch → {result.get('summary')}")
            else:
                report["steps"]["dispatch"] = {"error": "dispatch_prompt_actions not found"}
                log("dispatch function missing")
        except Exception as e:
            report["steps"]["dispatch"] = {"error": str(e), "traceback": traceback.format_exc()[-400:]}
            log(f"dispatch exception: {e}")
    else:
        report["steps"]["dispatch"] = {"skipped": True}

    # 4. Self-heal loop (import the sibling script if possible)
    log("STEP 4 — self-heal loop")
    try:
        # Prefer the dedicated script so logic stays in one place
        loop_path = HOME / "scripts" / "self_heal_loop.py"
        if loop_path.is_file():
            rc = subprocess.call(
                [sys.executable, str(loop_path), f"--rounds={args.rounds}"],
                cwd=str(HOME),
            )
            report["steps"]["self_heal"] = {"exit_code": rc, "via": "script"}
            # pick up the status file the loop writes
            status_file = LOG_DIR / "last_self_heal.json"
            if status_file.is_file():
                report["steps"]["self_heal"]["status"] = json.loads(status_file.read_text(encoding="utf-8"))
        else:
            # inline fallback using craft tools
            heal = getattr(craft, "tool_heal", lambda **k: {})()
            improve = getattr(craft, "tool_improve", lambda **k: {})()
            doctor = getattr(craft, "tool_doctor", lambda **k: {})()
            report["steps"]["self_heal"] = {
                "via": "inline",
                "heal": heal.get("summary") if isinstance(heal, dict) else str(heal),
                "improve": improve.get("summary") if isinstance(improve, dict) else str(improve),
                "doctor_ok": doctor.get("ok") if isinstance(doctor, dict) else None,
            }
        log(f"self_heal → {report['steps']['self_heal']}")
    except Exception as e:
        report["steps"]["self_heal"] = {"error": str(e)}
        log(f"self_heal exception: {e}")

    # 5. Final doctor snapshot
    log("STEP 5 — final doctor")
    try:
        doctor = getattr(craft, "tool_doctor", lambda **k: {"ok": False})()
        report["steps"]["final_doctor"] = {
            "ok": doctor.get("ok") if isinstance(doctor, dict) else False,
            "mode": doctor.get("mode") if isinstance(doctor, dict) else None,
            "workspace": doctor.get("workspace") if isinstance(doctor, dict) else None,
        }
        log(f"final doctor → ok={report['steps']['final_doctor']['ok']}")
    except Exception as e:
        report["steps"]["final_doctor"] = {"error": str(e)}

    report["finished"] = datetime.now().isoformat()
    report["ok"] = bool(
        (report["steps"].get("final_doctor") or {}).get("ok")
        or (report["steps"].get("self_heal") or {}).get("status", {}).get("healthy")
    )

    _write_report(report)
    log("=" * 60)
    log(f"Pipeline finished  ok={report['ok']}  report={REPORT}")
    log("=" * 60)
    return 0 if report["ok"] else 3


def _write_report(report: dict) -> None:
    try:
        data = json.dumps(report, indent=2, default=str)
        REPORT.write_text(data, encoding="utf-8")
        LATEST.write_text(data, encoding="utf-8")
    except OSError as e:
        log(f"could not write report: {e}")


if __name__ == "__main__":
    raise SystemExit(main())
