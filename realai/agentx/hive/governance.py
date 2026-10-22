"""Capability guardian + approval/sandbox gate.

Profiles come from data/access_profiles.json (safe, balanced, power). The default is
``safe`` (read-only). Nothing is written to disk unless:
  1. the agent's profile allows writes,
  2. a human approved the request in realai.core.approval_gate, and
  3. the sandbox check passed.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .registry import DATA

DEFAULT_PROFILE = "safe"


def load_profiles() -> dict[str, dict[str, Any]]:
    data = json.loads((DATA / "access_profiles.json").read_text(encoding="utf-8"))
    return {p["name"]: p for p in data}


@dataclass
class AccessDecision:
    ok: bool
    profile: str
    missing: list[str]
    can_write: bool
    reason: str


class CapabilityGuardian:
    """Least-privilege check: required tools vs. the tools a profile grants."""

    def __init__(self, profiles: dict[str, dict[str, Any]] | None = None, default: str = DEFAULT_PROFILE):
        self.profiles = profiles or load_profiles()
        self.default = default

    def profile_for(self, agent_raw: dict[str, Any] | None) -> str:
        name = (agent_raw or {}).get("profile") or self.default
        return name if name in self.profiles else self.default

    def check(self, agent_raw: dict[str, Any], required: list[str] | None = None,
              profile: str | None = None) -> AccessDecision:
        name = profile or self.profile_for(agent_raw)
        prof = self.profiles.get(name) or self.profiles[self.default]
        granted = set(prof.get("tools") or [])
        need = list(required if required is not None else agent_raw.get("tools_allowed") or [])
        # Only gate tools the profile system knows about; free-form Copilot tool names are advisory.
        known = set().union(*(set(p.get("tools") or []) for p in self.profiles.values()))
        missing = [t for t in need if t in known and t not in granted]
        return AccessDecision(ok=not missing, profile=name, missing=missing,
                              can_write=bool(prof.get("write")),
                              reason="ok" if not missing else f"profile {name!r} lacks {missing}")

    def recommend(self, required: list[str]) -> str:
        for name in ("safe", "balanced", "power"):
            if name in self.profiles and set(required) <= set(self.profiles[name].get("tools") or []):
                return name
        return "power"


SandboxRunner = Callable[[dict[str, Any]], dict[str, Any]]


# Review-branch default: run the patch's own tests with pytest, in a throwaway copy of the
# workspace that has the patch applied. Override with REALAI_SANDBOX_CMD ({tests} = test files).
DEFAULT_SANDBOX_CMD = "{python} -m pytest -q -x -p no:cacheprovider {tests}"
DEFAULT_SANDBOX_TIMEOUT = 300
_COPY_IGNORE = shutil.ignore_patterns(
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "logs", "memory",
    "models", "checkpoints*", "_quarantine", "recovered*", "archive", "*.gguf", "*.safetensors", "*.bin",
)


def _change_args(change: dict[str, Any]) -> dict[str, Any]:
    for key in ("args", "params", "payload", "arguments"):
        v = change.get(key)
        if isinstance(v, dict) and "file_path" in v:
            return v
    return change


def _workspace() -> Path:
    return Path(os.environ.get("REALAI_WORKSPACE") or os.environ.get("REALAI_HOME") or Path.cwd()).resolve()


def tests_for(file_path: str, root: Path) -> list[str]:
    """Scope: tests named after the patched module (tests/**/test_<stem>*.py), or the file itself if it is a test."""
    override = os.environ.get("REALAI_SANDBOX_TESTS", "").strip()
    if override:
        return shlex.split(override)
    p = Path(file_path)
    try:
        rel = (p if p.is_absolute() else root / p).resolve().relative_to(root)
    except ValueError:
        return []
    if rel.name.startswith("test_") and rel.suffix == ".py":
        return [rel.as_posix()]
    tdir = root / "tests"
    if not tdir.is_dir():
        return []
    stem = rel.stem
    hits = sorted({q.relative_to(root).as_posix() for q in tdir.rglob(f"test_{stem}*.py")})
    if not hits and rel.parent.name not in ("", "."):
        hits = sorted({q.relative_to(root).as_posix() for q in tdir.rglob(f"test_{rel.parent.name}*.py")})
    return hits


def default_sandbox(change: dict[str, Any]) -> dict[str, Any]:
    """Apply the change to a temp copy of the workspace and run its scoped tests there (timeout)."""
    args = _change_args(change)
    file_path = str(args.get("file_path") or "")
    old, new = args.get("old_string"), args.get("new_string")
    if not file_path or old is None or new is None:
        return {"ok": False, "reason": "sandbox: change has no file_path/old_string/new_string"}
    root = _workspace()
    tests = tests_for(file_path, root)
    if not tests:
        return {"ok": False, "reason": f"sandbox: no tests found for {file_path} (set REALAI_SANDBOX_TESTS)"}
    template = os.environ.get("REALAI_SANDBOX_CMD", "").strip() or DEFAULT_SANDBOX_CMD
    timeout = int(os.environ.get("REALAI_SANDBOX_TIMEOUT") or DEFAULT_SANDBOX_TIMEOUT)
    with tempfile.TemporaryDirectory(prefix="realai-sandbox-") as tmp:
        box = Path(tmp) / "ws"
        shutil.copytree(root, box, ignore=_COPY_IGNORE)
        tgt = box / (Path(file_path).resolve().relative_to(root) if Path(file_path).is_absolute() else Path(file_path))
        if not tgt.is_file():
            return {"ok": False, "reason": f"sandbox: {file_path} not in workspace"}
        text = tgt.read_text(encoding="utf-8")
        if text.count(str(old)) != 1:
            return {"ok": False, "reason": "sandbox: old_string must match exactly once"}
        tgt.write_text(text.replace(str(old), str(new), 1), encoding="utf-8")
        cmd = [part.replace("{python}", sys.executable) for part in shlex.split(template.replace("{tests}", "\x00T"))]
        argv: list[str] = []
        for part in cmd:
            argv.extend(tests if part == "\x00T" else [part])
        env = dict(os.environ, REALAI_HOME=str(box), REALAI_WORKSPACE=str(box), PYTHONPATH=str(box))
        try:
            proc = subprocess.run(argv, cwd=box, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return {"ok": False, "reason": f"sandbox timeout after {timeout}s", "tests": tests}
    return {"ok": proc.returncode == 0, "reason": f"sandbox exit {proc.returncode}", "tests": tests,
            "tail": (proc.stdout + proc.stderr)[-2000:]}


class PatchGate:
    """Approval store + sandbox in front of every file change an agent proposes."""

    def __init__(self, guardian: CapabilityGuardian | None = None, sandbox: SandboxRunner | None = None):
        from realai.core import approval_gate

        self.gate = approval_gate
        self.guardian = guardian or CapabilityGuardian()
        self.sandbox = sandbox or default_sandbox

    def propose(self, agent_raw: dict[str, Any], file_path: str, old: str, new: str) -> dict[str, Any]:
        decision = self.guardian.check(agent_raw, required=["apply_patch"])
        if not decision.can_write or not decision.ok:
            return {"status": "denied", "executed": False,
                    "reason": f"profile {decision.profile!r} cannot write", "agent": agent_raw.get("id")}
        req = self.gate.request("search_replace", {"file_path": file_path, "old_string": old, "new_string": new})
        req["agent"] = agent_raw.get("id")
        return req

    def apply(self, approval_id: str) -> dict[str, Any]:
        item = self._item(approval_id)
        if not item or item.get("status") != "approved":
            return {"ok": False, "reason": "not approved"}
        box = self.sandbox(item)
        if not box.get("ok"):
            return {"ok": False, "reason": f"sandbox blocked: {box.get('reason')}"}
        return self.gate.execute(approval_id)

    def _item(self, approval_id: str) -> dict[str, Any] | None:
        for fn in ("get", "get_request", "status"):
            f = getattr(self.gate, fn, None)
            if callable(f):
                try:
                    out = f(approval_id)
                    if isinstance(out, dict):
                        return out.get("item", out)
                except Exception:
                    continue
        store = Path(os.environ.get("REALAI_APPROVALS_STORE") or "")
        if store.is_file():
            for it in json.loads(store.read_text(encoding="utf-8")).get("items", []):
                if it.get("approval_id") == approval_id or it.get("id") == approval_id:
                    return it
        return None
