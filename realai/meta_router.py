"""RealAI Orchestrator 2.0 — meta-router (classify → route → memory hooks).

Emits a routing decision before any model call:
  { target, reason, backend, estimated_cost_or_vram, fallback }

This is the first vertical slice of Hive Orchestrator 2.0:
one task → local GGUF OR cloud OR named hive agent, with memory read before
and memory write after (hooks only — no silent cloud secret exfil).

Not a Grok wrapper. xAI/Grok is one optional remote backend if configured.
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


SECRET_PATTERNS = (
    re.compile(r"\b(sk-[a-zA-Z0-9]{16,})\b"),
    re.compile(r"\b(private[_ ]?key|seed phrase|mnemonic)\b", re.I),
    re.compile(r"\b(0x[a-fA-F0-9]{64})\b"),
    re.compile(r"\b(BEGIN (RSA |OPENSSH )?PRIVATE KEY)\b"),
)


@dataclass
class RoutingDecision:
    target: str  # agent id or "raw-model"
    reason: str
    backend: str  # local-gguf | groq | openai | anthropic | ollama | vulkan
    estimated_cost_or_vram: str
    fallback: str
    privacy: str = "local-ok"  # local-ok | cloud-blocked | cloud-allowed
    memory_read: bool = True
    memory_write: bool = True
    task_class: str = "general"
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _cloud_allowed() -> bool:
    return (os.environ.get("REALAI_ALLOW_CLOUD") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _has_secrets(text: str) -> bool:
    return any(p.search(text or "") for p in SECRET_PATTERNS)


def _looks_like_work_loop(text: str) -> bool:
    """True for Craft `/work <goal>`."""
    t = (text or "").strip().lower()
    return t.startswith("/work")


# Free-text that Craft auto-inspects in a foreign repo (keep in sync with craft._should_auto_inspect).
_FOREIGN_INSPECT_HINTS = (
    "inspect", "check", "look", "review", "audit", "report", "findings",
    "fix", "improve", "recommend", "better", "broken", "bug", "issue",
    "hall", "shot", "sotd", "map", "rack", "site", "repo", "project",
    "where", "how", "what", "why", "implement", "wire", "update",
    "diagram", "location", "grep", "patch", "refactor",
)


def _foreign_inspect_ask(text: str) -> bool:
    low = (text or "").lower()
    return any(k in low for k in _FOREIGN_INSPECT_HINTS)


def classify_task(text: str) -> str:
    t = (text or "").lower()
    # `/work` is a coding work loop — must beat "plan"/"architect" in the goal text.
    if _looks_like_work_loop(text):
        return "code"
    if any(k in t for k in ("deploy", "git push", "rm -rf", "drop table", "transfer sol", "sign tx")):
        return "side-effect"
    if any(k in t for k in ("plan", "architect", "decompose", "roadmap", "design system")):
        return "deep-reasoning"
    if any(k in t for k in ("npc", "quest", "in-world", "game")):
        return "game-npc"
    if any(k in t for k in ("remember", "recall", "what did we", "memory")):
        return "memory"
    if any(k in t for k in ("code", "refactor", "implement", "patch", "bug", "test", "inspect")):
        return "code"
    if any(k in t for k in ("fast", "quick", "stream", "cheap")):
        return "speed"
    if any(k in t for k in ("private", "offline", "local only", "airgap")):
        return "private"
    return "general"


def route_task(
    text: str,
    *,
    prefer_local: bool = True,
    allow_cloud: Optional[bool] = None,
    mode: Optional[str] = None,
    **_ignored: Any,
) -> RoutingDecision:
    """Classify and route. Does not call models — returns the decision only.

    ``mode`` is Craft's workspace mode (``product`` vs ``project``). Foreign
    project inspect / ``/work`` asks prefer hive ``coder`` instead of the
    default overseer.
    """
    task_class = classify_task(text)
    foreign = str(mode or "").strip().lower() in {"project", "foreign"}
    if task_class == "general" and foreign and _foreign_inspect_ask(text):
        task_class = "code"
    cloud_ok = _cloud_allowed() if allow_cloud is None else allow_cloud
    secrets = _has_secrets(text)

    # Privacy gate: secrets never go cloud unless explicitly allowed AND no secret patterns
    if secrets and not cloud_ok:
        privacy = "cloud-blocked"
    elif secrets and cloud_ok:
        privacy = "cloud-blocked"  # still block raw secrets
    else:
        privacy = "cloud-allowed" if cloud_ok else "local-ok"

    # Defaults: local Vulkan GGUF
    target = "overseer"
    backend = "local-gguf"
    reason = "default local hive overseer"
    cost = "vram:7B-q5 ~local"
    fallback = "local-gguf:1.5B"

    if task_class == "speed" and privacy == "cloud-allowed":
        target = "raw-model"
        backend = "groq"
        reason = "speed/cheap streaming"
        cost = "cloud:tokens-cheap"
        fallback = "local-gguf"
    elif task_class == "deep-reasoning":
        target = "architect"
        if privacy == "cloud-allowed" and not prefer_local:
            backend = "openai"
            reason = "deep reasoning — strongest available"
            cost = "cloud:tokens-high"
            fallback = "local-gguf:7B"
        else:
            backend = "local-gguf"
            reason = "deep reasoning on local GGUF (privacy/cost)"
            cost = "vram:7B-q5"
            fallback = "anthropic" if privacy == "cloud-allowed" else "local-gguf:1.5B"
    elif task_class == "private":
        target = "overseer"
        backend = "local-gguf"
        reason = "private/offline — local only"
        cost = "vram:local"
        fallback = "ollama"
        privacy = "local-ok"
    elif task_class == "code":
        target = "coder"
        backend = "local-gguf"
        if foreign or _looks_like_work_loop(text):
            reason = "foreign project /work → hive coder on local GGUF"
        else:
            reason = "code slice → hive coder on local GGUF"
        cost = "vram:7B-q5"
        fallback = "openai" if privacy == "cloud-allowed" else "local-gguf"
    elif task_class == "memory":
        target = "memory"
        backend = "local-gguf"
        reason = "memory agent — retrieve/compress/write"
        cost = "vram:embed+chat"
        fallback = "local-gguf"
    elif task_class == "game-npc":
        target = "hive-orchestrator"
        backend = "local-gguf"
        reason = "game/NPC → hive orchestrator"
        cost = "vram:local"
        fallback = "local-gguf"
    elif task_class == "side-effect":
        target = "governor"
        backend = "local-gguf"
        reason = "side effects require safety/governor then tool agent"
        cost = "tools+confirm"
        fallback = "overseer"

    if secrets:
        backend = "local-gguf"
        reason = f"{reason}; secrets detected — forced local"
        privacy = "cloud-blocked"
        fallback = "local-gguf"

    return RoutingDecision(
        target=target,
        reason=reason,
        backend=backend,
        estimated_cost_or_vram=cost,
        fallback=fallback,
        privacy=privacy,
        memory_read=True,
        memory_write=task_class not in {"speed"},
        task_class=task_class,
        extras={
            "prefer_local": prefer_local,
            "secrets_detected": secrets,
            "mode": str(mode or ""),
            "foreign": foreign,
        },
    )


def memory_read_hook(decision: RoutingDecision, query: str) -> Dict[str, Any]:
    """Pre-call memory read via Memory Fabric (+ universe status)."""
    try:
        from realai.universe.memory_bridge import memory_status

        st = memory_status(__import__("pathlib").Path(os.environ.get("REALAI_WORKSPACE") or r"C:\RealAI-clean"))
    except Exception as e:
        st = {"active": False, "error": str(e)}
    hits: List[Dict[str, Any]] = []
    fabric_err = None
    try:
        from realai.memory.fabric import read_memory

        redact = str(getattr(decision, "privacy", "") or "") == "cloud-blocked"
        raw = read_memory(
            query or "",
            owner=None,
            limit=8,
            include_expired=False,
            redact_high=redact,
        )
        if isinstance(raw, list):
            hits = raw
        elif isinstance(raw, dict):
            hits = list(raw.get("hits") or raw.get("records") or [])
    except Exception as e:
        fabric_err = str(e)
    return {
        "ok": True,
        "hook": "memory_read",
        "query": (query or "")[:200],
        "decision_target": decision.target,
        "memory": st,
        "fabric_hits": hits,
        "fabric_error": fabric_err,
        "note": "fabric JSONL read; high/secret redacted when privacy=cloud-blocked",
    }


def memory_write_hook(decision: RoutingDecision, outcome: Dict[str, Any]) -> Dict[str, Any]:
    """Post-call durable write into Memory Fabric (facts/decisions only)."""
    tags = {
        "scope": "episodic",
        "owner": decision.target,
        "ttl": "30d",
        "sensitivity": "high" if decision.privacy == "cloud-blocked" else "normal",
    }
    outcome = outcome or {}
    keys = list(outcome.keys())[:12]
    if any(k in outcome for k in ("messages", "raw_chat", "transcript")) and not any(
        k in outcome for k in ("decision", "result", "reply", "summary", "fact")
    ):
        return {
            "ok": True,
            "hook": "memory_write",
            "skipped": True,
            "tags": tags,
            "outcome_keys": keys,
            "note": "skipped raw chat dump",
        }
    parts = []
    for k in ("summary", "fact", "decision", "result", "reply"):
        v = outcome.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            parts.append(s[:500])
    text = " | ".join(parts).strip()
    if not text:
        return {
            "ok": True,
            "hook": "memory_write",
            "skipped": True,
            "tags": tags,
            "outcome_keys": keys,
            "note": "no durable fact/decision text",
        }
    try:
        from realai.memory.fabric import write_memory

        rec = write_memory(
            text,
            scope=str(tags["scope"]),
            owner=str(tags["owner"] or "overseer"),
            ttl=str(tags["ttl"]),
            sensitivity=str(tags["sensitivity"]),
            tags=["meta_router", str(getattr(decision, "task_class", "") or "")],
            meta={"outcome_keys": keys},
        )
        rid = None
        if isinstance(rec, dict):
            rid = rec.get("id")
        else:
            rid = getattr(rec, "id", None)
        return {
            "ok": True,
            "hook": "memory_write",
            "tags": tags,
            "record_id": rid,
            "outcome_keys": keys,
            "note": "persisted to fabric JSONL",
        }
    except Exception as e:
        return {
            "ok": False,
            "hook": "memory_write",
            "tags": tags,
            "outcome_keys": keys,
            "error": str(e),
        }


def plan_call(text: str, **kwargs: Any) -> Dict[str, Any]:
    """Full preflight: route + memory read. Does not invoke backends."""
    decision = route_task(text, **kwargs)
    mem = memory_read_hook(decision, text) if decision.memory_read else {"ok": True, "skipped": True}
    return {
        "routing": decision.to_dict(),
        "memory_read": mem,
        "next": "invoke target on backend, then memory_write_hook",
    }
