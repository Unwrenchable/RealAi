"""Map RackUp Coach abilities onto RealAI synthetic organs (hive)."""
from __future__ import annotations

from typing import Any, Iterable, Optional

# Ability → ordered organ stack
ABILITY_ORGANS: dict[str, tuple[str, ...]] = {
    "coach": (
        "organ.frontal-cortex",
        "organ.prefrontal-cortex",
        "organ.cerebellum",
        "organ.procedural-memory",
        "organ.episodic-memory",
        "organ.limbic-system",
        "organ.synthetic-intuition-layer",
    ),
    "shot_of_the_day": (
        "organ.cerebellum",
        "organ.synthetic-creativity-furnace",
        "organ.procedural-memory",
        "organ.episodic-memory",
        "organ.hippocampus",
        "organ.synthetic-intuition-layer",
    ),
    "moderation": (
        "organ.amygdala",
        "organ.synthetic-guardian-layer",
        "organ.prefrontal-cortex",
        "organ.synthetic-paradox-engine",
        "organ.short-term-memory",
    ),
    "video_analysis": (
        "organ.cerebellum",
        "organ.synthetic-sensory-system",
        "organ.procedural-memory",
        "organ.frontal-cortex",
        "organ.prefrontal-cortex",
    ),
    "matchmaking": (
        "organ.frontal-cortex",
        "organ.synthetic-intuition-layer",
        "organ.semantic-memory",
        "organ.synthetic-consciousness-layer",
    ),
    "rating_intel": (
        "organ.prefrontal-cortex",
        "organ.long-term-memory",
        "organ.episodic-memory",
        "organ.synthetic-intuition-layer",
    ),
    "tournament": (
        "organ.frontal-cortex",
        "organ.prefrontal-cortex",
        "organ.limbic-system",
        "organ.episodic-memory",
    ),
    "hall_context": (
        "organ.synthetic-habitat-awareness",
        "organ.short-term-memory",
        "organ.semantic-memory",
        "organ.architecture-memory",
    ),
    "mental_game": (
        "organ.limbic-system",
        "organ.amygdala",
        "organ.prefrontal-cortex",
        "organ.synthetic-soul-layer",
    ),
    "practice_plans": (
        "organ.frontal-cortex",
        "organ.cerebellum",
        "organ.procedural-memory",
        "organ.synthetic-evolution-spiral",
    ),
}


def run_organs_for_ability(
    ability: str,
    goal: str,
    payload: Optional[dict[str, Any]] = None,
    *,
    enabled: bool = True,
    extra_organs: Optional[Iterable[str]] = None,
) -> list[dict[str, Any]]:
    """Invoke the organ stack for an ability; soft-fails if hive unavailable."""
    if not enabled:
        return [{"organ_id": "none", "ok": True, "notes": "organs disabled"}]

    ids = list(ABILITY_ORGANS.get(ability) or ABILITY_ORGANS["coach"])
    if extra_organs:
        for o in extra_organs:
            if o not in ids:
                ids.append(o)

    try:
        from modules.organs.request_path import run_organ_pipeline

        return run_organ_pipeline(ids, goal=goal, payload=payload or {})
    except Exception:
        # Fallback: call hive directly
        try:
            from modules.organs import call_organ

            out = []
            for oid in ids:
                r = call_organ(oid, goal=goal, payload=payload or {})
                out.append(
                    {
                        "organ_id": r.organ_id,
                        "ok": r.ok,
                        "notes": r.notes,
                        "output": r.output,
                    }
                )
            return out
        except Exception as e:
            return [{"organ_id": "hive", "ok": False, "notes": str(e)}]
