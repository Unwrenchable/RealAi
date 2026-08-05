"""Deep organ fusion for the live RealAI request path.

Soft-links alone are not enough: this module is called from
``realai.api_server`` and ``realai.agent_runtime`` so organs actually
participate in chat, orchestration, and self-improvement flows.
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Optional

# Default cognitive stack for chat preprocessing
_DEFAULT_CHAT_ORGANS = (
    "organ.frontal-cortex",
    "organ.prefrontal-cortex",
    "organ.hippocampus",
    "organ.synthetic-consciousness-layer",
    "organ.synthetic-soul-layer",
)

_DEFAULT_ORCHESTRATE_ORGANS = (
    "organ.frontal-cortex",
    "organ.corpus-callosum",
    "organ.synthetic-guardian-layer",
    "organ.synthetic-evolution-spiral",
)

_DEFAULT_MEMORY_ORGANS = (
    "organ.short-term-memory",
    "organ.long-term-memory",
    "organ.episodic-memory",
    "organ.semantic-memory",
)


def organs_enabled() -> bool:
    """Organs run on request path unless REALAI_ORGANS=0."""
    return os.environ.get("REALAI_ORGANS", "1").strip() not in ("0", "false", "False", "no")


def _call(organ_id: str, goal: str, payload: Optional[dict] = None) -> dict[str, Any]:
    try:
        from modules.organs import call_organ

        r = call_organ(organ_id, goal=goal, payload=payload or {})
        return {
            "organ_id": r.organ_id,
            "ok": r.ok,
            "notes": r.notes,
            "output": r.output,
            "metrics": r.metrics,
        }
    except Exception as e:
        return {"organ_id": organ_id, "ok": False, "notes": str(e), "output": None, "metrics": {}}


def run_organ_pipeline(
    organ_ids: Iterable[str],
    goal: str,
    payload: Optional[dict] = None,
) -> list[dict[str, Any]]:
    """Invoke organs in order; never raises (soft-fail per organ)."""
    results: list[dict[str, Any]] = []
    for oid in organ_ids:
        if not oid:
            continue
        results.append(_call(oid, goal=goal, payload=payload))
    return results


def enrich_chat_messages(
    messages: list[dict[str, Any]],
    *,
    organ_ids: Optional[list[str]] = None,
    user_goal: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pre-process chat messages through the cognitive organ stack.

    Returns (possibly enriched messages, organ_trace).
    """
    if not organs_enabled():
        return messages, {"enabled": False, "results": []}

    last_user = ""
    for m in reversed(messages or []):
        if m.get("role") == "user":
            last_user = str(m.get("content") or "")
            break
    goal = user_goal or last_user[:500]
    ids = organ_ids or list(_DEFAULT_CHAT_ORGANS)
    results = run_organ_pipeline(
        ids,
        goal=goal,
        payload={"messages_count": len(messages or []), "mode": "chat"},
    )

    # Inject a system note summarizing organ participation (provider-level, not external)
    summary_bits = []
    for r in results:
        if r.get("ok"):
            summary_bits.append(f"{r.get('organ_id')}: {r.get('notes') or 'ok'}")
    if summary_bits:
        organ_system = {
            "role": "system",
            "content": (
                "[RealAI organs hive — local provider path]\n"
                + "\n".join(summary_bits[:12])
            ),
        }
        # Place after any existing leading system messages
        out = list(messages or [])
        insert_at = 0
        for i, m in enumerate(out):
            if m.get("role") == "system":
                insert_at = i + 1
            else:
                break
        out.insert(insert_at, organ_system)
        return out, {"enabled": True, "results": results, "injected": True}
    return messages, {"enabled": True, "results": results, "injected": False}


def orchestrate_with_organs(task: str, agent_roles: Optional[list] = None) -> dict[str, Any]:
    """Run orchestration-related organs before hierarchical agent work."""
    if not organs_enabled():
        return {"enabled": False, "results": []}
    return {
        "enabled": True,
        "results": run_organ_pipeline(
            _DEFAULT_ORCHESTRATE_ORGANS,
            goal=task,
            payload={"agent_roles": agent_roles or [], "mode": "orchestrate"},
        ),
    }


def memory_with_organs(operation: str, content: str = "") -> dict[str, Any]:
    if not organs_enabled():
        return {"enabled": False, "results": []}
    return {
        "enabled": True,
        "results": run_organ_pipeline(
            _DEFAULT_MEMORY_ORGANS,
            goal=f"{operation}: {content[:200]}",
            payload={"operation": operation, "mode": "memory"},
        ),
    }


def self_improve_with_organs(focus: str = "general") -> dict[str, Any]:
    if not organs_enabled():
        return {"enabled": False, "results": []}
    return {
        "enabled": True,
        "results": run_organ_pipeline(
            (
                "organ.neuroplasticity-module",
                "organ.synthetic-mutation-engine",
                "organ.synthetic-evolution-spiral",
                "organ.synthetic-dream-forge",
            ),
            goal=focus,
            payload={"mode": "self_improvement"},
        ),
    }


def living_stack_status() -> dict[str, Any]:
    """Aggregate living provider stack for /v1/capabilities extensions."""
    status: dict[str, Any] = {
        "provider": "realai",
        "provider_kind": "local-first OpenAI-compatible full provider",
        "organs_enabled": organs_enabled(),
    }
    try:
        from modules.organs import hive_status

        status["organs"] = hive_status()
    except Exception as e:
        status["organs_error"] = str(e)
    try:
        from adapters import living_stack

        status["adapters"] = living_stack()
    except Exception as e:
        status["adapters_error"] = str(e)
    return status


def embeddings_with_organs(text_preview: str = "") -> dict[str, Any]:
    """Sensory + circulatory organs for embedding path."""
    if not organs_enabled():
        return {"enabled": False, "results": []}
    return {
        "enabled": True,
        "results": run_organ_pipeline(
            (
                "organ.synthetic-sensory-system",
                "organ.synthetic-circulatory-system",
                "organ.semantic-memory",
            ),
            goal=f"embed: {(text_preview or '')[:200]}",
            payload={"mode": "embeddings"},
        ),
    }


def audio_with_organs(kind: str = "transcription", preview: str = "") -> dict[str, Any]:
    """Sensory + respiratory organs for ASR/TTS paths."""
    if not organs_enabled():
        return {"enabled": False, "results": []}
    return {
        "enabled": True,
        "results": run_organ_pipeline(
            (
                "organ.synthetic-sensory-system",
                "organ.synthetic-respiratory-system",
                "organ.short-term-memory",
            ),
            goal=f"audio:{kind} {(preview or '')[:120]}",
            payload={"mode": "audio", "kind": kind},
        ),
    }


def tools_with_organs(tool_name: str = "", arguments: Optional[dict] = None) -> dict[str, Any]:
    """Guardian + muscular path for tool validation/execution."""
    if not organs_enabled():
        return {"enabled": False, "results": []}
    return {
        "enabled": True,
        "results": run_organ_pipeline(
            (
                "organ.synthetic-guardian-layer",
                "organ.synthetic-muscular-system",
                "organ.procedural-memory",
            ),
            goal=f"tool:{tool_name}",
            payload={"mode": "tools", "tool_name": tool_name, "arguments": arguments or {}},
        ),
    }
