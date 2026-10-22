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
import subprocess
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


def default_sandbox(_change: dict[str, Any]) -> dict[str, Any]:
    """Run REALAI_SANDBOX_CMD (e.g. the agent-tools sandbox_runner) if configured; else fail closed."""
    cmd = os.environ.get("REALAI_SANDBOX_CMD", "").strip()
    if not cmd:
        return {"ok": False, "reason": "sandbox not configured (set REALAI_SANDBOX_CMD)"}
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=900)
    return {"ok": proc.returncode == 0, "reason": f"sandbox exit {proc.returncode}",
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
