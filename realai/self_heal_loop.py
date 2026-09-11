#!/usr/bin/env python3
"""
RealAI Self-Heal Loop
=====================
Repeatedly runs doctor → gaps → heal → improve until the product tree
is healthy or max_rounds is reached.

Designed to be called from:
  - Craft:  /exec self_heal_loop   (or just run the file)
  - CLI:    python scripts/self_heal_loop.py
  - Pipeline / master prompt

Never raises to the caller. Always prints a clear summary and exits 0/1.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve REALAI_HOME the same way Craft does
# ---------------------------------------------------------------------------
def _home() -> Path:
    env = os.environ.get("REALAI_HOME")
    if env:
        return Path(env)
    # common Windows locations
    for candidate in (
        Path(r"C:\RealAI-clean"),
        Path.home() / "RealAI-clean",
        Path(__file__).resolve().parents[1],
    ):
        if candidate.is_dir():
            return candidate
    return Path.cwd()


HOME = _home()
LOG_DIR = HOME / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "self_heal_loop.log"


def log(msg: str) -> None:
    from datetime import datetime
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def try_import_craft_tools():
    """Best-effort import of the live Craft tool functions."""
    # Prefer the real package if already on PYTHONPATH
    try:
        from realai.cli.craft import (  # type: ignore
            tool_doctor,
            tool_gaps,
            tool_heal,
            tool_improve,
            tool_pwd,
        )
        return {
            "doctor": tool_doctor,
            "gaps": tool_gaps,
            "heal": tool_heal,
            "improve": tool_improve,
            "pwd": tool_pwd,
        }
    except Exception:
        pass

    # Fallback: load craft.py directly from the expected location
    craft_path = HOME / "realai" / "cli" / "craft.py"
    if not craft_path.is_file():
        craft_path = HOME / "realai" / "craft.py"
    if craft_path.is_file():
        import importlib.util
        spec = importlib.util.spec_from_file_location("realai_craft", craft_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["realai_craft"] = mod
            try:
                spec.loader.exec_module(mod)
                return {
                    "doctor": getattr(mod, "tool_doctor", None),
                    "gaps": getattr(mod, "tool_gaps", None),
                    "heal": getattr(mod, "tool_heal", None),
                    "improve": getattr(mod, "tool_improve", None),
                    "pwd": getattr(mod, "tool_pwd", None),
                }
            except Exception as e:
                log(f"could not exec craft.py: {e}")
    return {}


def run_one(name: str, fn, **kwargs) -> dict[str, Any]:
    if fn is None:
        return {"tool": name, "ok": False, "error": "tool not available"}
    try:
        result = fn(**kwargs)
        return {"tool": name, "ok": True, "result": result}
    except Exception as e:
        return {
            "tool": name,
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc()[-500:],
        }


def is_healthy(doctor: dict, gaps: dict) -> bool:
    """Heuristic: doctor.ok and no high-severity gaps."""
    if not doctor.get("ok"):
        return False
    top = gaps.get("top_gaps") or []
    for g in top:
        if (g.get("severity") or "").lower() in ("fail", "critical", "error"):
            return False
    return True


def main(max_rounds: int = 4, force_heal: bool = True) -> int:
    log("=" * 60)
    log(f"RealAI Self-Heal Loop  HOME={HOME}")
    log(f"max_rounds={max_rounds}  force_heal={force_heal}")
    log("=" * 60)

    tools = try_import_craft_tools()
    if not tools:
        log("FATAL: could not import any Craft tools — is craft.py present?")
        return 1

    pwd = run_one("pwd", tools.get("pwd"))
    log(f"pwd → {json.dumps(pwd.get('result') or pwd.get('error'), default=str)[:300]}")

    final_status = {"healthy": False, "rounds": 0, "history": []}

    for round_no in range(1, max_rounds + 1):
        log(f"----- ROUND {round_no}/{max_rounds} -----")
        final_status["rounds"] = round_no

        doc = run_one("doctor", tools.get("doctor"))
        gap = run_one("gaps", tools.get("gaps"))
        heal = run_one("heal", tools.get("heal"), force=force_heal)
        imp = run_one("improve", tools.get("improve"))

        round_summary = {
            "round": round_no,
            "doctor_ok": (doc.get("result") or {}).get("ok"),
            "heal_summary": (heal.get("result") or {}).get("summary"),
            "improve_summary": (imp.get("result") or {}).get("summary"),
            "gaps_top": (gap.get("result") or {}).get("top_gaps"),
        }
        final_status["history"].append(round_summary)

        log(f"doctor  → ok={round_summary['doctor_ok']}")
        log(f"heal    → {round_summary['heal_summary']}")
        log(f"improve → {round_summary['improve_summary']}")

        if is_healthy(doc.get("result") or {}, gap.get("result") or {}):
            log("HEALTHY — stopping early")
            final_status["healthy"] = True
            break

        if round_no < max_rounds:
            time.sleep(1.5)  # brief pause so file locks / GPU settle

    # Final snapshot
    log("=" * 60)
    log(f"Self-Heal finished | healthy={final_status['healthy']} | rounds={final_status['rounds']}")
    log("=" * 60)

    # Write machine-readable status for the auto-update pipeline
    status_path = LOG_DIR / "last_self_heal.json"
    try:
        status_path.write_text(json.dumps(final_status, indent=2, default=str), encoding="utf-8")
        log(f"status written → {status_path}")
    except OSError as e:
        log(f"could not write status: {e}")

    return 0 if final_status["healthy"] else 2


if __name__ == "__main__":
    rounds = 4
    force = True
    for arg in sys.argv[1:]:
        if arg.startswith("--rounds="):
            rounds = int(arg.split("=", 1)[1])
        if arg in ("--no-force", "--soft"):
            force = False
    raise SystemExit(main(max_rounds=rounds, force_heal=force))
