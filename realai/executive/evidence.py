"""Evidence rules — environment proof, not vibes."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_check(cmd: List[str], cwd: Optional[Path] = None, timeout: float = 120.0) -> Dict[str, Any]:
    """Run a command and capture exit code + truncated log as evidence.

    Static executive helpers may call this; the Voice Engine reconstruction
    agent does not invoke it during reconstruction turns.
    """
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        out = (p.stdout or "")[-4000:]
        err = (p.stderr or "")[-2000:]
        return {
            "ok": p.returncode == 0,
            "exit_code": p.returncode,
            "cmd": cmd,
            "stdout_tail": out,
            "stderr_tail": err,
        }
    except Exception as e:
        return {"ok": False, "exit_code": None, "cmd": cmd, "error": str(e)}


def file_exists(path: Path) -> Dict[str, Any]:
    return {"ok": path.is_file(), "path": str(path), "size": path.stat().st_size if path.is_file() else 0}


def parse_log_snippet(text: str, keywords: List[str]) -> Dict[str, Any]:
    hits = [k for k in keywords if k.lower() in (text or "").lower()]
    return {"ok": bool(hits), "hits": hits, "snippet": (text or "")[-800:]}