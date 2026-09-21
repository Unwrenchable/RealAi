"""RealAI live hive exec — real processes only, never invent stdout.

Runs commands/scripts under ``{REALAI_HOME}/.hive`` with captured output.
Used by the orchestrator so the bot quotes live traces instead of hallucinating.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MAX_OUT = 48_000
CMD_TIMEOUT = 45
SCRIPT_TIMEOUT = 60

# Loose keyword match — intentionally narrow. Bare "type"/"run"/"command" in
# operator policy prose must NOT steal the Console turn (shell-help hijack).
_WANTS_RE = re.compile(
    r"(?is)("
    r"^\s*\$"
    r"|^\s*/(?:run|exec|py|python|script)\b"
    r"|\brun\s+`"
    r"|\bexec(?:ute)?\s+`"
    r"|\b(?:whoami|hostname)\b"
    r"|```(?:python|py|js|javascript|bash|sh|powershell|ps1)"
    r"|\b(?:powershell|pwsh|cmd\.exe)\b"
    r")"
)

# Craft file ops belong to operator dispatch / cli.craft — never live_exec.
_CRAFT_FILE_SLASH_RE = re.compile(
    r"^/(?:write|read|list|ls|grep|git|pwd|here|cat|ws|workspace)\b",
    re.I,
)

# Operator / coding-agent policy pastes — never live_exec, even under 280 chars.
_POLICY_PROSE_RE = re.compile(
    r"(?is)("
    r"work like a desktop coding agent"
    r"|loop\s*[—\-–:]?\s*every request"
    r"|never invent (?:file )?contents"
    r"|prefer tools over essays"
    r"|inspect\s*[—\-–].*act\s*[—\-–].*verify"
    r"|writes stay in workspace"
    r"|no fake success"
    r")"
)


def hive_root() -> Path:
    home = (
        os.environ.get("REALAI_HIVE_DIR")
        or os.environ.get("REALAI_HOME")
        or os.environ.get("REALAI_ROOT")
        or str(Path(__file__).resolve().parents[2])
    )
    root = Path(home).resolve() / ".hive"
    root.mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scratch").mkdir(exist_ok=True)
    return root


def _explicit_exec_prefix(text: str) -> bool:
    """True for $ /run /py /script /exec or run `cmd` — real shell asks."""
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    if t.startswith("$") or low.startswith(("/run", "/py", "/python", "/script", "/exec")):
        return True
    if re.search(r"(?is)^\s*run\s+`", t) or re.search(r"(?is)\brun\s+`[^`]+`", t):
        return True
    if re.search(r"(?is)\bexec(?:ute)?\s+`[^`]+`", t):
        return True
    if "```" in t and re.search(r"(?is)\b(run|exec(?:ute)?)\b.{0,40}```", t):
        return True
    # "run whoami" / "run dir" / "please run hostname" — single safe shell asks
    m_run = re.match(
        r"(?i)^(?:please\s+)?(?:can you\s+)?run\s+([a-zA-Z0-9_./\\:-]+(?:\s+\S+){0,8})\s*$",
        t,
    )
    if m_run:
        head = m_run.group(1).split()[0].lower()
        if head not in ("craft", "hive", "ability", "heal", "doctor", "multi", "agents"):
            return True
    return False


def wants_live_exec(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    # /write /read /list /grep /git /pwd are Craft TOOLS, not hive shell.
    if _CRAFT_FILE_SLASH_RE.match(t):
        return False
    low = t.lower()
    if low.startswith("/craft"):
        return False
    # Operator / coding-agent policy pastes — never shell-help.
    if _POLICY_PROSE_RE.search(t):
        return False
    # Natural Mode / Craft file asks win over shell-help (avoid "I type", "run exactly").
    try:
        from realai.bot.natural_mode import (
            looks_like_learn_ask,
            looks_like_repo_ask,
            looks_like_write_ask,
            should_natural_act,
        )

        if (
            should_natural_act(t)
            or looks_like_repo_ask(t)
            or looks_like_write_ask(t)
            or looks_like_learn_ask(t)
        ):
            return False
    except Exception:
        pass
    try:
        from realai.bot.workspace_intent import looks_like_workspace_switch

        if looks_like_workspace_switch(t):
            return False
    except Exception:
        pass
    # Explicit shell forms always win (even when long).
    if _explicit_exec_prefix(t):
        return True
    # Long pastes are never live_exec via loose keyword match.
    if len(t) > 280:
        return False
    return bool(_WANTS_RE.search(t))


def _clip(s: str, n: int = MAX_OUT) -> str:
    s = s or ""
    if len(s) <= n:
        return s
    return s[:n] + "\n…(truncated)"


def _resolve_in_hive(rel: str) -> Path:
    root = hive_root()
    cleaned = (rel or ".").replace("\\", "/").lstrip("/")
    resolved = (root / cleaned).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("path escapes hive") from exc
    return resolved


def _spawn(cmd: List[str], cwd: Path, timeout: int) -> Dict[str, Any]:
    started = time.time()
    timed_out = False
    error = None
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            timeout=timeout,
            env=_sanitized_env(),
            check=False,
        )
        stdout = proc.stdout or b""
        stderr = proc.stderr or b""
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        code = -1
        error = f"timeout after {timeout}s"
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "duration_ms": int((time.time() - started) * 1000),
            "timed_out": False,
            "error": str(exc),
        }

    def dec(buf: bytes) -> str:
        if not buf:
            return ""
        if b"\x00" in buf[:64]:
            return f"<binary {len(buf)} bytes>"
        return _clip(buf.decode("utf-8", errors="replace"))

    return {
        "stdout": dec(stdout if isinstance(stdout, (bytes, bytearray)) else b""),
        "stderr": dec(stderr if isinstance(stderr, (bytes, bytearray)) else b""),
        "exit_code": code,
        "duration_ms": int((time.time() - started) * 1000),
        "timed_out": timed_out,
        "error": error,
    }


def _sanitized_env() -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if isinstance(v, str)}
    for k in (
        "XAI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROK_API_KEY",
        "DATABASE_URL",
        "BETTER_AUTH_SECRET",
    ):
        env.pop(k, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["REALAI_BOT_LOCAL_ONLY"] = env.get("REALAI_BOT_LOCAL_ONLY") or "1"
    return env


def run_command(command: str) -> Dict[str, Any]:
    cwd = hive_root()
    trimmed = (command or "").strip()
    trace: Dict[str, Any] = {
        "id": f"exec-{uuid.uuid4().hex[:10]}",
        "kind": "command",
        "command": trimmed,
        "cwd": str(cwd),
        "live": True,
        "ok": False,
    }
    if not trimmed:
        trace.update(stdout="", stderr="empty command", exit_code=-1, duration_ms=0, error="empty command")
        return trace
    if os.name == "nt":
        out = _spawn(["cmd.exe", "/d", "/s", "/c", trimmed], cwd, CMD_TIMEOUT)
    else:
        out = _spawn(["bash", "-lc", trimmed], cwd, CMD_TIMEOUT)
    trace.update(out)
    trace["ok"] = out.get("exit_code") == 0 and not out.get("timed_out")
    return trace


def run_script(*, language: str, code: str, filename: Optional[str] = None, argv: Optional[List[str]] = None) -> Dict[str, Any]:
    cwd = hive_root()
    lang = (language or "python").lower().strip()
    if lang in ("py", "python3"):
        lang = "python"
    if lang in ("js", "javascript"):
        lang = "node"
    if lang in ("ps1", "pwsh", "powershell"):
        lang = "powershell"
    if lang in ("sh", "bash", "shell"):
        lang = "bash" if os.name != "nt" else "powershell"

    ext = {"python": "py", "node": "js", "bash": "sh", "powershell": "ps1"}.get(lang, "txt")
    rel = (filename or "").strip() or f"scratch/run-{int(time.time())}.{ext}"
    trace: Dict[str, Any] = {
        "id": f"exec-{uuid.uuid4().hex[:10]}",
        "kind": "script",
        "language": lang,
        "path": rel,
        "cwd": str(cwd),
        "live": True,
        "ok": False,
    }
    try:
        abs_path = _resolve_in_hive(rel)
    except Exception as exc:
        trace.update(stdout="", stderr=str(exc), exit_code=-1, duration_ms=0, error=str(exc))
        return trace

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(code or "", encoding="utf-8")
    args = list(argv or [])

    if lang == "python":
        bin_name = "python" if os.name == "nt" else "python3"
        cmd = [bin_name, str(abs_path), *args]
    elif lang == "node":
        cmd = ["node", str(abs_path), *args]
    elif lang == "powershell":
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(abs_path),
            *args,
        ]
    else:
        cmd = ["bash", str(abs_path), *args]

    trace["command"] = " ".join(cmd)
    out = _spawn(cmd, cwd, SCRIPT_TIMEOUT)
    trace.update(out)
    trace["ok"] = out.get("exit_code") == 0 and not out.get("timed_out")
    return trace


def format_trace(trace: Dict[str, Any]) -> str:
    """Human + model-facing dump of a LIVE process result."""
    kind = trace.get("kind") or "command"
    hdr = f"$ {trace.get('command')}" if kind == "command" else f"# {trace.get('language')} {trace.get('path')}"
    lines = [
        "[RealAI live_exec — REAL process output, not invented]",
        hdr,
        f"cwd: {trace.get('cwd')}",
        f"exit={trace.get('exit_code')}  {trace.get('duration_ms')}ms"
        + ("  TIMEOUT" if trace.get("timed_out") else ""),
        "",
        "stdout:",
        (trace.get("stdout") or "(empty)"),
    ]
    err = (trace.get("stderr") or "").strip()
    if err:
        lines.extend(["", "stderr:", err])
    if trace.get("error"):
        lines.extend(["", f"error: {trace.get('error')}"])
    lines.append("")
    lines.append("Rule: quote this output. Do not invent different stdout/stderr.")
    return "\n".join(lines)


def parse_live_request(text: str) -> Optional[Dict[str, Any]]:
    """Extract an executable request from user text. None = not parseable."""
    raw = (text or "").strip()
    if not raw:
        return None

    # $ command
    m = re.match(r"^\$\s*(.+)$", raw, flags=re.S)
    if m:
        return {"kind": "command", "command": m.group(1).strip()}

    # /run … /exec …
    m = re.match(r"^/(?:run|exec)\s+(.+)$", raw, flags=re.I | re.S)
    if m:
        return {"kind": "command", "command": m.group(1).strip()}

    # /py … /python …
    m = re.match(r"^/(?:py|python)\s+([\s\S]+)$", raw, flags=re.I)
    if m:
        return {"kind": "script", "language": "python", "code": m.group(1).strip()}

    # /script lang code
    m = re.match(r"^/script\s+(python|py|node|js|bash|sh|powershell|ps1)\s+([\s\S]+)$", raw, flags=re.I)
    if m:
        return {"kind": "script", "language": m.group(1).lower(), "code": m.group(2).strip()}

    # Fenced code block
    m = re.search(
        r"```(?:(python|py|javascript|js|node|bash|sh|powershell|ps1))?\s*\n([\s\S]*?)```",
        raw,
        flags=re.I,
    )
    if m and wants_live_exec(raw):
        lang = (m.group(1) or "python").lower()
        code = (m.group(2) or "").strip()
        if code:
            # If user also said "run this command" with only a one-liner that's a shell cmd
            if lang in ("bash", "sh") or (
                lang in ("",) and re.match(r"^(whoami|dir|ls|pwd|echo|hostname)\b", code, re.I)
            ):
                if "\n" not in code and lang in ("bash", "sh", ""):
                    return {"kind": "command", "command": code}
            return {"kind": "script", "language": lang or "python", "code": code}

    # run `cmd` or execute `cmd`
    m = re.search(r"(?i)\b(?:run|exec(?:ute)?)\s+`([^`]+)`", raw)
    if m:
        return {"kind": "command", "command": m.group(1).strip()}

    # run command: … / execute: …
    m = re.search(r"(?i)\b(?:run\s+command|exec(?:ute)?(?:\s+command)?)\s*[:\-]\s*(.+)$", raw)
    if m:
        cmd = m.group(1).strip().strip("`")
        if cmd and len(cmd) < 500 and "\n" not in cmd:
            return {"kind": "command", "command": cmd}

    # run whoami / run dir / run hostname (single safe token commands)
    m = re.match(
        r"(?i)^(?:please\s+)?(?:can you\s+)?run\s+([a-zA-Z0-9_./\\:-]+(?:\s+[^\n]{0,120})?)\s*$",
        raw,
    )
    if m:
        cmd = m.group(1).strip()
        # Avoid "run craft" / "run hive" — those are operator surfaces
        head = cmd.split()[0].lower()
        if head not in ("craft", "hive", "ability", "heal", "doctor", "multi", "agents"):
            return {"kind": "command", "command": cmd}

    # python: code one-liner
    m = re.search(r"(?i)\b(?:run\s+)?(?:this\s+)?python(?:\s+code)?\s*[:\-]\s*([\s\S]+)$", raw)
    if m:
        code = m.group(1).strip().strip("`")
        if code and not code.lower().startswith("script"):
            return {"kind": "script", "language": "python", "code": code}

    return None


def try_live_exec(text: str) -> Optional[Dict[str, Any]]:
    """Parse + execute. Returns operator-style dispatch dict or None if not an exec ask."""
    if not wants_live_exec(text):
        return None
    req = parse_live_request(text)
    if req is None:
        # Only show shell-help when the user clearly tried to run something
        # incomplete. Prose that merely mentions run/type must not steal the turn.
        if not _explicit_exec_prefix(text):
            return None
        return {
            "surface": "live_exec",
            "result": {
                "ok": False,
                "live": True,
                "error": "need_explicit_command",
                "hint": (
                    "I only report REAL process output. Give me one of:\n"
                    "  $ whoami\n"
                    "  /run dir\n"
                    "  /py print(2+2)\n"
                    "  /script python print('hi')\n"
                    "  run `hostname`\n"
                    "  a ```python``` block and ask me to run it\n"
                    "I will not invent stdout."
                ),
            },
        }

    if req["kind"] == "command":
        trace = run_command(str(req.get("command") or ""))
    else:
        trace = run_script(
            language=str(req.get("language") or "python"),
            code=str(req.get("code") or ""),
            filename=req.get("filename"),
            argv=req.get("argv"),
        )
    return {"surface": "live_exec", "result": trace}


def format_live_reply(dispatch: Dict[str, Any]) -> str:
    result = dispatch.get("result") or {}
    if result.get("error") == "need_explicit_command":
        return str(result.get("hint") or "Need an explicit command. I will not invent stdout.")
    if result.get("live") and ("exit_code" in result or "stdout" in result):
        return format_trace(result)
    try:
        import json

        return "[RealAI live_exec]\n" + json.dumps(result, indent=2, default=str)[:6000]
    except Exception:
        return f"[RealAI live_exec]\n{result}"
