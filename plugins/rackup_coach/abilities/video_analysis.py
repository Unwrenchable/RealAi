"""Video analysis — structured feedback from host-supplied annotations/transcript."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.pyramid import classical_mindset_tips, resolve_pyramid
from plugins.rackup_coach.types import PlayerProfile, RatingBand


def analyze_video(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host may send:
      - video_meta: {clip_type, duration_s, fps, url_ref}
      - observations: free text or checklist flags from client CV / coach notes
      - checklist: {stance_stable, chin_drop, elbow_tuck, grip_tension, follow_through, ...}
      - pyramid / table_size / skill_level for Pyramid-scaled feedback
    Pure AI structure — no binary video decode here.
    """
    payload = payload or {}
    meta = dict(payload.get("video_meta") or {})
    clip_type = str(meta.get("clip_type") or payload.get("clip_type") or "stroke").lower()
    checklist = dict(payload.get("checklist") or {})
    observations = str(payload.get("observations") or payload.get("notes") or "")
    cfg = resolve_pyramid(player=player, payload=payload)
    is_pyramid = (player.discipline or "").lower() == "pyramid" or bool(
        payload.get("pyramid") or payload.get("game") == "pyramid"
    )

    issues: list[dict[str, str]] = []
    drills: list[str] = []

    def flag(key: str, default_ok: bool = True) -> bool:
        if key in checklist:
            return bool(checklist[key])
        return default_ok

    if clip_type in ("stroke", "stance", "general"):
        if not flag("stance_stable", True) or "sway" in observations.lower():
            issues.append(
                {
                    "area": "stance",
                    "finding": "Lower-body stability looks inconsistent during the stroke.",
                    "fix": "Lock back foot; quiet head; film side-on.",
                }
            )
            drills.append("15 setup freezes (no shot) checking hip/shoulder alignment in mirror.")
        if not flag("follow_through", True) or "jab" in observations.lower():
            issues.append(
                {
                    "area": "stroke",
                    "finding": "Stroke may be decelerating or jabbing at contact.",
                    "fix": "Accelerate through; freeze finish for 1s.",
                }
            )
            drills.append("Pendulum feathers ×20 + finish-hold on straight stops.")
        if not flag("elbow_tuck", True):
            issues.append(
                {
                    "area": "elbow",
                    "finding": "Elbow wander can spray tip contact (unwanted english).",
                    "fix": "Drop elbow on a vertical plane; tip stays center.",
                }
            )
            drills.append("Wall-elbow drill: light contact with wall to feel plane.")
        if not flag("grip_tension", True) or "grip" in observations.lower():
            issues.append(
                {
                    "area": "grip",
                    "finding": "Grip tension likely high — kills feel and draw length control.",
                    "fix": "Hold like a bird; pressure only in last 20% of stroke.",
                }
            )

    if clip_type == "break":
        issues.append(
            {
                "area": "break",
                "finding": "Evaluate CB box more than raw power.",
                "fix": "Mark a CB landing box; legal break + box > max speed.",
            }
        )
        drills.append("10 controlled breaks scoring CB-in-box without scratch.")
        if player.band in (RatingBand.BEGINNER, RatingBand.INTERMEDIATE):
            drills.append("Reduce power 15%; prioritize center-ball contact on head ball.")

    if clip_type in ("stance",) and player.band == RatingBand.BEGINNER:
        drills.append("Chin-over-cue check photo every 5 balls.")

    if is_pyramid:
        if cfg.rack_size == 10:
            issues.append(
                {
                    "area": "pyramid_10ball",
                    "finding": "7ft/10-ball Pyramid: CB errors cost more race share per miss.",
                    "fix": f"Prioritize stop/soft-follow; target first-to-{cfg.points_to_win}.",
                }
            )
            drills.append(
                f"Point-count set: play short races to {cfg.points_to_win} with verbal scores."
            )
        else:
            issues.append(
                {
                    "area": "pyramid_15ball",
                    "finding": "9ft/15-ball Pyramid: pattern depth + 1-ball (11) decisions matter.",
                    "fix": "Film a full value-route; call high-value balls before shooting.",
                }
            )
            drills.append("15-ball ladder: open traffic then isolate 1-ball (11 pts).")
        if cfg.call_shot == "yes":
            drills.append("Call-shot only set: ball+pocket every stroke (pro rule).")
        elif cfg.call_shot == "optional":
            drills.append("Optional call-shot practice: call outs on pressure balls.")

    if not issues:
        issues.append(
            {
                "area": "general",
                "finding": "No critical flags in checklist — refine tempo and PSR.",
                "fix": "Keep pre-shot routine fixed; add one measurable target per set.",
            }
        )
        drills.append("20-ball PSR set: every shot 8–12 seconds, unbroken routine.")

    expectation = {
        RatingBand.BEGINNER: "Prioritize stillness and center-ball contact over shape.",
        RatingBand.INTERMEDIATE: "Connect stroke quality to a planned CB landing zone.",
        RatingBand.ADVANCED: "Demand repeatable tip precision under slight time pressure.",
        RatingBand.PRO: "Micro-adjust for cloth speed; track variance across 3 sessions.",
    }[player.band]
    if is_pyramid:
        expectation = (
            f"Pyramid {cfg.table_size}/{cfg.rack_size}-ball · skill={cfg.skill_level} · "
            f"first to {cfg.points_to_win}. " + expectation
        )

    return {
        "player_id": player.player_id,
        "band": player.band.value,
        "clip_type": clip_type,
        "video_meta": meta,
        "expectation": expectation,
        "findings": issues,
        "recommended_drills": drills,
        "pyramid": cfg.to_dict() if is_pyramid else None,
        "classical_mindset": classical_mindset_tips(cfg) if is_pyramid else [],
        "scorecard": {
            "checklist_provided": bool(checklist),
            "issue_count": len(issues),
            "ready_for_match_sim": player.band.value in ("advanced", "pro") and len(issues) <= 2,
            "points_to_win": cfg.points_to_win if is_pyramid else None,
            "rack_size": cfg.rack_size if is_pyramid else None,
        },
        "next_upload_prompt": (
            "Upload side-angle value-route (include 1-ball decision) for Pyramid CB kill check."
            if is_pyramid
            else "Upload a side-angle stop-shot set (10 balls) for cue-ball kill check."
        ),
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return analyze_video(player, payload)
