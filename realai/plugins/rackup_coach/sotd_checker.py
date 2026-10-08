"""Shot of the Day map checker + diagram-prompt renderer (pure Python, no LLM).

Used by ``shot_of_the_day`` when ``payload.mode == "sotd_validate"``.

The map is the source of truth. Geometry here fills ``cut_deg``,
``blocked_by`` and ``tangent_side`` *before* the player sentence or the
diagram prompt is written. A model never supplies degrees. The sentence and the
diagram prompt are deterministic renders of the validated (possibly fixed) map.

Coordinate frame (``axis = "x_long"``)
--------------------------------------
9-foot playing surface, 100 x 50 inches. **x is the long axis** (0..100),
**y is the short axis** (0..50). Image frame: x/100 across, y/50 down, so the
head rail is the left edge of the diagram and the foot rail the right edge.

"Left" and "right" are named from the head end looking toward the foot rail
(+x), with y growing downward in the image: left = the y=0 rail, right = the
y=50 rail.

Pocket targets follow Travis's grid rule. The 100 x 50 cloth is an 8 x 4 grid
of equal 12.5 in boxes, and a pocket sits *inside* its box: each corner hole
(radius ``POCKET_HOLE_R_IN`` = 2.3) is tangent to both cushion noses at its
corner, and each side hole is tangent to its long rail, straddling x = 50. The
checker aims at those hole centers, which are exactly where the diagram draws
the holes, so the object-ball line ends at the drawn hole center:

=====================  ==============  =====================
pocket id              target (x,y)    mouth on the cloth edge
=====================  ==============  =====================
corner_head_left       (2.3, 2.3)      (0, 0)
corner_head_right      (2.3, 47.7)     (0, 50)
side_left              (50, 2.3)       (50, 0)
side_right             (50, 47.7)      (50, 50)
corner_foot_left       (97.7, 2.3)     (100, 0)
corner_foot_right      (97.7, 47.7)    (100, 50)
=====================  ==============  =====================

The mouth points (``POCKET_MOUTHS``) are the standing instruction's corner /
midpoint list with the axes swapped (x up to 100, y up to 50); the targets
(``POCKETS``) are those points moved ``POCKET_HOLE_R_IN`` into the table on
each axis that meets a rail.

Checks, in order: place, called, ghost, path, cut, tangent, claim. Every visible
fail is listed. A hard fail in checks 1-6 stops the map from shipping until a
fix makes it pass. A claim fail is fixed by rendering the sentence from the
validated geometry. The old claim is never kept next to a disagreeing tangent.

Interpretations (named constants below):

* ``path`` checks both legs: cue -> ghost (the instruction's rule) and
  object -> pocket. A ball sitting in the object ball's lane also means the
  map cannot finish the shot. A ball blocks a leg when its center is closer
  than ``BALL_D + PATH_CLEARANCE`` to that segment.
* ``stop``: physically a stop shot only happens when the cue ball arrives
  nearly straight. "Thin cut" in the standing instruction is read as
  *near-straight*. ``stop`` is legal only with tip center, speed medium, and
  ``cut_deg <= STOP_MAX_CUT_DEG``. ``stun`` is legal with tip center (a stun
  shot leaves on the tangent line).
* ``tangent_side`` is named from the shooter's view along cue -> ghost. A
  center (or left/right English) hit gives ``left``/``right``, the side
  opposite the object ball's direction. ``follow`` gives ``forward`` and
  ``draw`` gives ``back``. A center hit within ``STRAIGHT_EPS_DEG`` of
  straight-in gives ``straight``, because there is no tangent; that value is
  an extension of the instruction's enum.
* The exit side for a named next ball depends on the tip. center/left/right:
  the half-plane of the object->pocket line that the tangent points into.
  follow: the sector between the shot line and the tangent. draw: the sector
  between the tangent and the reversed shot line. A legal stop may name the
  next ball, since the cue ball stays at the ghost spot.

Diagram: when ``render_diagram`` is set and ``ok`` is true (after fixes),
``sotd_diagram.render_sotd_svg`` draws the validated map as a deterministic
local SVG (``diagram_svg``, plus ``diagram`` as a base64 data URI). It uses no
API keys and makes no network calls. ``show_grid`` adds the faint 8 x 4
diamond grid. ``diagram_prompt`` is kept for a future
local image model only.
"""
from __future__ import annotations

import copy
import math
import os
import re
from pathlib import Path
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Table law
# ---------------------------------------------------------------------------
AXIS = "x_long"
TABLE_LONG = 100.0  # x
TABLE_SHORT = 50.0  # y
BALL_D = 2.25
BALL_R = BALL_D / 2.0
PATH_CLEARANCE = 0.15
PRO_CUT_DEG = 70.0  # over this: pro-only (warning)
MAX_CUT_DEG = 80.0  # over this: illegal for SOTD (hard fail)
STOP_MAX_CUT_DEG = 10.0  # "stop" claim legal only at or below this cut
STRAIGHT_EPS_DEG = 1.0  # center hit within this of straight-in = no tangent
STRAIGHT_VERB_MAX_DEG = 5.0  # sentence says "straight in" at or below this
EXIT_MARGIN_DEG = 10.0  # tolerance on follow/draw sectors
STRAIGHT_CONE_DEG = 20.0  # follow/draw cone when straight-in
NUDGE_STEP = 0.5
NUDGE_MAX = 12.0
EPS = 1e-9

POCKET_HOLE_R_IN = 2.3  # one hole radius for all six pockets
# Where each pocket opens on the cloth edge (cushion-nose corner / midpoint).
POCKET_MOUTHS: dict[str, tuple[float, float]] = {
    "corner_head_left": (0.0, 0.0),
    "corner_head_right": (0.0, TABLE_SHORT),
    "side_left": (TABLE_LONG / 2.0, 0.0),
    "side_right": (TABLE_LONG / 2.0, TABLE_SHORT),
    "corner_foot_left": (TABLE_LONG, 0.0),
    "corner_foot_right": (TABLE_LONG, TABLE_SHORT),
}
_R = POCKET_HOLE_R_IN
# Pocket targets = drawn hole centers, inside the corner box / straddling x = 50.
POCKETS: dict[str, tuple[float, float]] = {
    "corner_head_left": (_R, _R),
    "corner_head_right": (_R, TABLE_SHORT - _R),
    "side_left": (TABLE_LONG / 2.0, _R),
    "side_right": (TABLE_LONG / 2.0, TABLE_SHORT - _R),
    "corner_foot_left": (TABLE_LONG - _R, _R),
    "corner_foot_right": (TABLE_LONG - _R, TABLE_SHORT - _R),
}

POCKET_PHRASE = {
    "corner_head_left": "head-left corner",
    "corner_head_right": "head-right corner",
    "side_left": "left side pocket",
    "side_right": "right side pocket",
    "corner_foot_left": "foot-left corner",
    "corner_foot_right": "foot-right corner",
}

GAME_MAX_BALL = {"nine_ball": 9, "ten_ball": 10, "eight_ball": 15}
ROTATION_GAMES = ("nine_ball", "ten_ball")
TIPS = ("center", "follow", "draw", "left", "right")
SPEEDS = ("soft", "medium", "firm")

BALL_COLORS = {
    1: "solid yellow",
    2: "solid blue",
    3: "solid red",
    4: "solid purple",
    5: "solid orange",
    6: "solid green",
    7: "solid maroon",
    8: "solid black",
    9: "yellow stripe",
    10: "blue stripe",
    11: "red stripe",
    12: "purple stripe",
    13: "orange stripe",
    14: "green stripe",
    15: "maroon stripe",
}

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "sotd_checker.txt"


def load_checker_prompt() -> str:
    """Travis's standing instruction. Only used as a system prompt if an LLM
    step is ever added; the checker itself never calls a model."""
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Catalog of maps that already pass (fix option 4). Tests assert each passes.
# ---------------------------------------------------------------------------
SOTD_MAP_CATALOG: list[dict[str, Any]] = [
    {
        "catalog_id": "cat-nine-foot-right-tangent",
        "game": "nine_ball",
        "cue": {"x": 34.0, "y": 40.0},
        "balls": [{"n": 1, "x": 75.0, "y": 38.0}, {"n": 2, "x": 85.0, "y": 20.0}],
        "called": {"ball": 1, "pocket": "corner_foot_right"},
        "stroke": {"tip": "center", "speed": "medium"},
        "claim": "",
    },
    {
        "catalog_id": "cat-ten-foot-right-tangent",
        "game": "ten_ball",
        "cue": {"x": 34.0, "y": 40.0},
        "balls": [{"n": 1, "x": 75.0, "y": 38.0}, {"n": 2, "x": 85.0, "y": 20.0}],
        "called": {"ball": 1, "pocket": "corner_foot_right"},
        "stroke": {"tip": "center", "speed": "medium"},
        "claim": "",
    },
    {
        "catalog_id": "cat-eight-straight-stop",
        "game": "eight_ball",
        "cue": {"x": 60.0, "y": 30.0},
        "balls": [{"n": 3, "x": 80.0, "y": 40.0}, {"n": 11, "x": 30.0, "y": 12.0}],
        "called": {"ball": 3, "pocket": "corner_foot_right"},
        "stroke": {"tip": "center", "speed": "medium"},
        "claim": "",
    },
]


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------
Vec = tuple[float, float]


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1])


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1])


def _mul(a: Vec, k: float) -> Vec:
    return (a[0] * k, a[1] * k)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _cross(a: Vec, b: Vec) -> float:
    # In the image frame (y down) a positive value means b is clockwise from a,
    # i.e. to the right of a shooter facing along a.
    return a[0] * b[1] - a[1] * b[0]


def _len(a: Vec) -> float:
    return math.hypot(a[0], a[1])


def _unit(a: Vec) -> Vec:
    n = _len(a)
    return (a[0] / n, a[1] / n) if n > EPS else (0.0, 0.0)


def _angle_deg(a: Vec, b: Vec) -> float:
    na, nb = _len(a), _len(b)
    if na < EPS or nb < EPS:
        return 0.0
    c = max(-1.0, min(1.0, _dot(a, b) / (na * nb)))
    return math.degrees(math.acos(c))


def _seg_dist(p: Vec, a: Vec, b: Vec) -> float:
    ab = _sub(b, a)
    L2 = _dot(ab, ab)
    if L2 < EPS:
        return _len(_sub(p, a))
    t = max(0.0, min(1.0, _dot(_sub(p, a), ab) / L2))
    return _len(_sub(p, _add(a, _mul(ab, t))))


def _r(x: float, nd: int = 3) -> float:
    return round(float(x), nd)


def _pt(v: Vec, nd: int = 3) -> dict[str, float]:
    return {"x": _r(v[0], nd), "y": _r(v[1], nd)}


# ---------------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------------
def _num(v: Any) -> float:
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        raise ValueError("not finite")
    return f


def normalize_map(raw: Any, *, default_game: str = "") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (map, input_fails). Never raises."""
    fails: list[dict[str, Any]] = []

    def bad(detail: str) -> None:
        fails.append({"check": "input", "hard": True, "detail": detail})

    if not isinstance(raw, dict):
        bad("map must be an object")
        return {}, fails
    m: dict[str, Any] = {"id": str(raw.get("id") or "sotd-unknown")}
    game = str(raw.get("game") or default_game or "").strip().lower().replace("-", "_")
    if game in ("9ball", "9_ball", "nine"):
        game = "nine_ball"
    elif game in ("10ball", "10_ball", "ten"):
        game = "ten_ball"
    elif game in ("8ball", "8_ball", "eight"):
        game = "eight_ball"
    if game not in GAME_MAX_BALL:
        bad(f"game must be one of {sorted(GAME_MAX_BALL)}; got {raw.get('game')!r}")
    m["game"] = game
    try:
        cue = raw.get("cue") or {}
        m["cue"] = {"x": _num(cue["x"]), "y": _num(cue["y"])}
    except Exception:
        bad("cue must be {x:number, y:number}")
        m["cue"] = None
    balls: list[dict[str, Any]] = []
    seen: set[int] = set()
    for i, b in enumerate(raw.get("balls") or []):
        try:
            n = int(b["n"])
            if float(b["n"]) != n:
                raise ValueError
            ball = {"n": n, "x": _num(b["x"]), "y": _num(b["y"])}
        except Exception:
            bad(f"balls[{i}] must be {{n:int, x:number, y:number}}")
            continue
        maxn = GAME_MAX_BALL.get(game, 15)
        if not 1 <= n <= maxn:
            bad(f"ball {n} is not a legal number for {game or 'this game'} (1..{maxn})")
        if n in seen:
            bad(f"ball {n} appears twice")
        seen.add(n)
        balls.append(ball)
    if not balls:
        bad("balls must list at least one object ball")
    m["balls"] = balls
    called = raw.get("called") or {}
    try:
        m["called"] = {"ball": int(called["ball"]), "pocket": str(called["pocket"]).strip().lower()}
    except Exception:
        bad("called must be {ball:int, pocket:pocket_id}")
        m["called"] = None
    stroke = raw.get("stroke") or {}
    m["stroke"] = {
        "tip": str(stroke.get("tip") or "center").strip().lower(),
        "speed": str(stroke.get("speed") or "medium").strip().lower(),
    }
    m["claim"] = str(raw.get("claim") or "")
    return m, fails


# ---------------------------------------------------------------------------
# Geometry analysis (checks 1-6) + claim (7)
# ---------------------------------------------------------------------------
def _on_cloth(p: Vec) -> bool:
    return (
        p[0] >= BALL_R - EPS
        and p[0] <= TABLE_LONG - BALL_R + EPS
        and p[1] >= BALL_R - EPS
        and p[1] <= TABLE_SHORT - BALL_R + EPS
    )


def _ball_xy(b: dict[str, Any]) -> Vec:
    return (float(b["x"]), float(b["y"]))


def _next_ball(m: dict[str, Any]) -> Optional[int]:
    """Rotation games: lowest ball left after the called ball. 8-ball: none
    (the map carries no group info, so the checker will not guess)."""
    if m.get("game") not in ROTATION_GAMES:
        return None
    called = (m.get("called") or {}).get("ball")
    rest = sorted(b["n"] for b in m.get("balls") or [] if b["n"] != called)
    return rest[0] if rest else None


def _exit_ok(geo: dict[str, Any], tip: str, target: Vec) -> bool:
    ghost = geo["_ghost"]
    u = geo["_u"]
    v = geo["_v"]
    t = geo["_t"]
    w = _sub(target, ghost)
    if _len(w) < EPS:
        return False
    straight = geo["cut_deg"] <= STRAIGHT_EPS_DEG
    if tip in ("center", "left", "right"):
        if straight:
            return False
        return _cross(u, w) * _cross(u, t) > 0
    if tip == "follow":
        if straight:
            return _angle_deg(w, v) <= STRAIGHT_CONE_DEG
        return _dot(w, v) > 0 and _cross(u, w) * _cross(u, t) > 0 and (
            _angle_deg(w, v) <= _angle_deg(t, v) + EXIT_MARGIN_DEG
        )
    if tip == "draw":
        back = _mul(v, -1.0)
        if straight:
            return _angle_deg(w, back) <= STRAIGHT_CONE_DEG
        return _angle_deg(w, back) <= _angle_deg(t, back) + EXIT_MARGIN_DEG and (
            _cross(back, w) * _cross(back, t) >= 0
        )
    return False


def analyze(m: dict[str, Any], *, check_claim: bool = True) -> dict[str, Any]:
    """Run checks 1-7 on a normalized map. Pure; never raises on a sane map."""
    fails: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    out: dict[str, Any] = {
        "fails": fails,
        "warnings": warnings,
        "cut_deg": None,
        "blocked_by": None,
        "tangent_side": None,
        "geometry": None,
        "skipped": [],
    }

    def fail(check: str, detail: str, **extra: Any) -> None:
        fails.append({"check": check, "hard": check != "claim", "detail": detail, **extra})

    cue = m.get("cue")
    balls = m.get("balls") or []
    called = m.get("called")
    stroke = m.get("stroke") or {}
    tip, speed = stroke.get("tip"), stroke.get("speed")
    if cue is None or called is None or not balls:
        out["skipped"] = ["place", "called", "ghost", "path", "cut", "tangent", "claim"]
        return out
    cue_p: Vec = (cue["x"], cue["y"])

    # 1 place
    pts: list[tuple[str, Vec]] = [("cue", cue_p)] + [(str(b["n"]), _ball_xy(b)) for b in balls]
    for name, p in pts:
        if not _on_cloth(p):
            fail("place", f"{'cue ball' if name == 'cue' else 'ball ' + name} at ({_r(p[0], 2)}, {_r(p[1], 2)}) is off the cloth (center must be >= {BALL_R} from every rail)", ball=name)
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = _len(_sub(pts[i][1], pts[j][1]))
            if d < BALL_D - EPS:
                fail("place", f"{pts[i][0]} and {pts[j][0]} overlap (center distance {_r(d, 3)} < {BALL_D})", pair=[pts[i][0], pts[j][0]])

    # 2 called
    obj = next((b for b in balls if b["n"] == called["ball"]), None)
    pocket = POCKETS.get(called["pocket"])
    if obj is None:
        fail("called", f"called ball {called['ball']} is not on the table")
    if pocket is None:
        fail("called", f"called pocket {called['pocket']!r} is not one of {list(POCKETS)}")
    if obj is not None and m.get("game") in ROTATION_GAMES:
        low = min(b["n"] for b in balls)
        if called["ball"] != low:
            fail("called", f"{m['game']}: called ball {called['ball']} is not the lowest on the table ({low})")
    if obj is None or pocket is None:
        out["skipped"] = ["ghost", "path", "cut", "tangent", "claim"]
        return out

    # 3 ghost
    O = _ball_xy(obj)
    to_pocket = _sub(pocket, O)
    if _len(to_pocket) < EPS:
        fail("ghost", "object ball center sits on the pocket center")
        out["skipped"] = ["path", "cut", "tangent", "claim"]
        return out
    u = _unit(to_pocket)
    ghost = _sub(O, _mul(u, BALL_D))
    if not _on_cloth(ghost):
        fail("ghost", f"ghost ball at ({_r(ghost[0], 2)}, {_r(ghost[1], 2)}) is off the cloth; the cue ball cannot reach the contact point")

    # 4 path (both legs)
    blockers: list[dict[str, Any]] = []
    need = BALL_D + PATH_CLEARANCE
    for b in balls:
        if b["n"] == obj["n"]:
            continue
        d = _seg_dist(_ball_xy(b), cue_p, ghost)
        if d < need - EPS:
            blockers.append({"ball": b["n"], "leg": "cue_to_ghost", "clearance": _r(d - BALL_D, 3),
                             "_along": _len(_sub(_ball_xy(b), cue_p))})
    for b in balls:
        if b["n"] == obj["n"]:
            continue
        d = _seg_dist(_ball_xy(b), O, pocket)
        if d < need - EPS:
            blockers.append({"ball": b["n"], "leg": "object_to_pocket", "clearance": _r(d - BALL_D, 3),
                             "_along": 1e6 + _len(_sub(_ball_xy(b), O))})
    blockers.sort(key=lambda x: x["_along"])
    for bl in blockers:
        bl.pop("_along", None)
        fail("path", f"ball {bl['ball']} blocks the {bl['leg'].replace('_', ' ')} leg (clearance {bl['clearance']} < {PATH_CLEARANCE})", ball=bl["ball"], leg=bl["leg"])
    out["blocked_by"] = blockers[0]["ball"] if blockers else None
    out["blockers"] = blockers

    # 5 cut
    v = _sub(ghost, cue_p)
    if _len(v) < EPS:
        fail("cut", "cue ball sits on the ghost spot")
        out["skipped"] = ["tangent", "claim"]
        return out
    cut = _angle_deg(v, u)
    out["cut_deg"] = _r(cut, 1)
    if cut > MAX_CUT_DEG:
        fail("cut", f"cut {_r(cut, 1)} deg is over {MAX_CUT_DEG} — illegal for SOTD")
    elif cut > PRO_CUT_DEG:
        warnings.append({"check": "cut", "detail": f"cut {_r(cut, 1)} deg is over {PRO_CUT_DEG} — pro-only"})

    # 6 tangent
    c = _cross(v, u)  # > 0: object ball goes to shooter's right -> cue to the left
    perp = _sub(v, _mul(u, _dot(v, u)))
    t = _unit(perp) if _len(perp) > EPS else (0.0, 0.0)
    if cut <= STRAIGHT_EPS_DEG:
        geo_side = "straight"
    else:
        geo_side = "left" if c > 0 else "right"
    if tip not in TIPS:
        fail("tangent", f"stroke.tip {tip!r} is not one of {list(TIPS)}")
    if speed not in SPEEDS:
        fail("tangent", f"stroke.speed {speed!r} is not one of {list(SPEEDS)}")
    if tip == "follow":
        side = "forward"
    elif tip == "draw":
        side = "back"
    else:
        side = geo_side
    out["tangent_side"] = side
    geo = {
        "pocket_center": _pt(pocket, 2),
        "object": _pt(O, 3),
        "ghost": _pt(ghost, 3),
        "cue": _pt(cue_p, 3),
        "tangent_geo_side": geo_side,
        "tangent_dir": _pt(t, 4),
        "cut_dir": "object_to_shooter_right" if c > 0 else ("object_to_shooter_left" if c < 0 else "straight"),
        "_ghost": ghost,
        "_u": u,
        "_v": _unit(v),
        "_t": t,
        "cut_deg": cut,
    }
    out["geometry"] = geo

    nxt = _next_ball(m)
    out["next_ball"] = nxt
    if nxt is not None and tip in TIPS:
        nb = next(b for b in balls if b["n"] == nxt)
        out["next_on_exit"] = _exit_ok(geo, tip, _ball_xy(nb))
    else:
        out["next_on_exit"] = False

    out["stop_legal"] = tip == "center" and speed == "medium" and cut <= STOP_MAX_CUT_DEG

    # 7 claim
    if check_claim and m.get("claim", "").strip():
        for f in check_claim_text(m, geo, out):
            fails.append(f)
    return out


# ---------------------------------------------------------------------------
# Claim parsing (deterministic regex — no LLM)
# ---------------------------------------------------------------------------
_BALL_RE = re.compile(
    r"\b(?:the|on|for|off|to)\s+(\d{1,2})\b(?![\s-]?(?:foot|ft|feet|inch|inches|diamonds?|rails?|degrees?|deg)\b)"
    r"|\b(\d{1,2})[\s-]?ball\b",
    re.I,
)
_POCKET_FULL = [
    re.compile(r"\b(head|foot)[\s_-]*(left|right)[\s_-]*corner\b", re.I),
    re.compile(r"\bcorner[\s_-]*(head|foot)[\s_-]*(left|right)\b", re.I),
    re.compile(r"\b(head|foot)[\s_-]+(left|right)\b(?![\s_-]*(?:english|spin|side))", re.I),
]
_POCKET_SIDE = [
    re.compile(r"\b(left|right)[\s_-]*side\b(?![\s_-]*spin)", re.I),
    re.compile(r"\bside[\s_-]*(left|right)\b", re.I),
]
_POCKET_LR_CORNER = re.compile(r"(?<![a-z_-])(left|right)[\s_-]*corner\b", re.I)
_POCKET_HF_CORNER = re.compile(r"\b(head|foot)[\s_-]*corner\b", re.I)
_GENERIC_CORNER = re.compile(r"\bcorner\b", re.I)
_GENERIC_SIDE = re.compile(r"\bside(?:[\s_-]*pocket)?\b(?![\s_-]*spin)", re.I)

_SPIN_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bleft[\s-]*(?:english|spin|side[\s-]*spin)\b", re.I), "left"),
    (re.compile(r"\bright[\s-]*(?:english|spin|side[\s-]*spin)\b", re.I), "right"),
    (re.compile(r"\b(?:english|side[\s-]*spin|sidespin)\b", re.I), "english"),
    (re.compile(r"\b(?:follow|top[\s-]*spin|topspin|top|high[\s-]*ball|roll)\b", re.I), "follow"),
    (re.compile(r"\b(?:draw|screw|back[\s-]*spin|backspin|low[\s-]*ball|pull[\s-]*back)\b", re.I), "draw"),
    (re.compile(r"\bcent(?:er|re)(?:[\s-]*ball)?\b", re.I), "center"),
    (re.compile(r"\bstun\b", re.I), "stun"),
    (re.compile(r"\bstop(?:s|ped|[\s-]*shot)?\b", re.I), "stop"),
]
_SPEED_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:soft|softly|slow|gentle|gently|lag)\b", re.I), "soft"),
    (re.compile(r"\b(?:medium|moderate|normal)\b", re.I), "medium"),
    (re.compile(r"\b(?:firm|firmly|hard|power|fast)\b", re.I), "firm"),
]


def parse_claim(text: str) -> dict[str, Any]:
    s = str(text or "")
    balls: list[int] = []
    for mt in _BALL_RE.finditer(s):
        n = int(mt.group(1) or mt.group(2))
        if n not in balls:
            balls.append(n)
    pockets: list[dict[str, Optional[str]]] = []
    spans: list[tuple[int, int]] = []

    def taken(a: int, b: int) -> bool:
        return any(not (b <= x or a >= y) for x, y in spans)

    for rx in _POCKET_FULL:
        for mt in rx.finditer(s):
            if taken(*mt.span()):
                continue
            spans.append(mt.span())
            pockets.append({"kind": "corner", "end": mt.group(1).lower(), "side": mt.group(2).lower()})
    for rx in _POCKET_SIDE:
        for mt in rx.finditer(s):
            if taken(*mt.span()):
                continue
            spans.append(mt.span())
            pockets.append({"kind": "side", "end": None, "side": mt.group(1).lower()})
    for mt in _POCKET_LR_CORNER.finditer(s):
        if not taken(*mt.span()):
            spans.append(mt.span())
            pockets.append({"kind": "corner", "end": None, "side": mt.group(1).lower()})
    for mt in _POCKET_HF_CORNER.finditer(s):
        if not taken(*mt.span()):
            spans.append(mt.span())
            pockets.append({"kind": "corner", "end": mt.group(1).lower(), "side": None})
    for mt in _GENERIC_CORNER.finditer(s):
        if not taken(*mt.span()):
            spans.append(mt.span())
            pockets.append({"kind": "corner", "end": None, "side": None})
    for mt in _GENERIC_SIDE.finditer(s):
        if not taken(*mt.span()):
            spans.append(mt.span())
            pockets.append({"kind": "side", "end": None, "side": None})
    # pocket ids written verbatim
    for pid in POCKETS:
        if re.search(rf"\b{pid}\b", s, re.I):
            kind, *rest = pid.split("_")
            if kind == "corner":
                pockets.append({"kind": "corner", "end": rest[0], "side": rest[1]})
            else:
                pockets.append({"kind": "side", "end": None, "side": rest[0]})

    spins: list[str] = []
    spin_spans: list[tuple[int, int]] = []
    for rx, name in _SPIN_WORDS:
        for mt in rx.finditer(s):
            if any(not (mt.end() <= x or mt.start() >= y) for x, y in spin_spans):
                continue
            spin_spans.append(mt.span())
            if name not in spins:
                spins.append(name)
    speeds = [name for rx, name in _SPEED_WORDS if rx.search(s)]
    return {"balls": balls, "pockets": pockets, "spins": spins, "speeds": speeds}


def _pocket_matches(p: dict[str, Optional[str]], pid: str) -> bool:
    kind, *rest = pid.split("_")
    if p["kind"] != kind:
        return False
    if kind == "corner":
        end, side = rest
        return (p["end"] in (None, end)) and (p["side"] in (None, side))
    return p["side"] in (None, rest[0])


def check_claim_text(m: dict[str, Any], geo: dict[str, Any], a: dict[str, Any]) -> list[dict[str, Any]]:
    claim = m.get("claim", "")
    parsed = parse_claim(claim)
    called = m["called"]
    tip = m["stroke"]["tip"]
    speed = m["stroke"]["speed"]
    on_table = {b["n"]: b for b in m["balls"]}
    fails: list[dict[str, Any]] = []

    def fail(detail: str, **extra: Any) -> None:
        fails.append({"check": "claim", "hard": False, "detail": detail, **extra})

    for n in parsed["balls"]:
        if n == called["ball"]:
            continue
        if n not in on_table:
            fail(f"claim names the {n}, which is not on the table", ball=n)
            continue
        if a.get("stop_legal") and "stop" in parsed["spins"]:
            continue
        if not _exit_ok(geo, tip, _ball_xy(on_table[n])):
            fail(f"claim names the {n} as next, but it is not on the exit side of the {a.get('tangent_side')} tangent", ball=n)
    for p in parsed["pockets"]:
        if not _pocket_matches(p, called["pocket"]):
            label = " ".join(x for x in (p.get("end"), p.get("side"), p.get("kind")) if x)
            fail(f"claim names a {label} pocket; the called pocket is {called['pocket']}", pocket=label)
    for sp in parsed["spins"]:
        if sp in ("left", "right"):
            if tip != sp:
                fail(f"claim names {sp} English but stroke.tip is {tip}", spin=sp)
        elif sp == "english":
            if tip not in ("left", "right"):
                fail(f"claim names English but stroke.tip is {tip}", spin=sp)
        elif sp in ("follow", "draw", "center"):
            if tip != sp:
                fail(f"claim names {sp} but stroke.tip is {tip}", spin=sp)
        elif sp == "stun":
            if tip != "center":
                fail(f"claim names stun but stroke.tip is {tip}", spin=sp)
        elif sp == "stop":
            if not a.get("stop_legal"):
                why = []
                if tip != "center":
                    why.append(f"tip is {tip}, not center")
                if speed != "medium":
                    why.append(f"speed is {speed}, not medium")
                if (a.get("cut_deg") or 0) > STOP_MAX_CUT_DEG:
                    why.append(f"cut is {a.get('cut_deg')} deg (> {STOP_MAX_CUT_DEG}); a center ball leaves on the tangent, it does not stop")
                fail("claim says stop, which is illegal here: " + "; ".join(why), spin="stop")
    for spd in parsed["speeds"]:
        if spd != speed:
            fail(f"claim says {spd} speed but stroke.speed is {speed}", speed=spd)
    return fails


# ---------------------------------------------------------------------------
# Renders (only from a validated map)
# ---------------------------------------------------------------------------
_TIP_PHRASE = {
    "center": "center ball",
    "follow": "follow",
    "draw": "draw",
    "left": "left English",
    "right": "right English",
}


def render_sentence(m: dict[str, Any], a: dict[str, Any]) -> str:
    called = m["called"]
    tip = m["stroke"]["tip"]
    speed = m["stroke"]["speed"]
    cut = a["cut_deg"] or 0.0
    pocket = POCKET_PHRASE[called["pocket"]]
    if cut <= STRAIGHT_VERB_MAX_DEG:
        head = f"Shoot the {called['ball']} straight into the {pocket}"
    else:
        head = f"Cut the {called['ball']} in the {pocket}"
    nxt = a.get("next_ball")
    for_next = f" for the {nxt}" if nxt is not None and a.get("next_on_exit") else ""
    if tip == "center" and a.get("stop_legal"):
        tail = "and stop" + (f" for the {nxt}" if nxt is not None else "")
    elif tip == "follow":
        tail = "and follow forward" + for_next
    elif tip == "draw":
        tail = "and draw back" + for_next
    elif a.get("tangent_side") == "straight":
        tail = "and let the cue ball roll through"
    else:
        tail = "and come off the tangent" + for_next
    return f"{head} with {_TIP_PHRASE[tip]} at {speed} speed {tail}."


def _frac(p: Vec) -> str:
    return f"{p[0] / TABLE_LONG * 100:.1f}% across, {p[1] / TABLE_SHORT * 100:.1f}% down"


def _ray_to_cloth_edge(p: Vec, d: Vec, cap: float) -> float:
    """Longest step <= cap from p along unit d that keeps a ball center on the cloth."""
    s = cap
    for i, hi in ((0, TABLE_LONG), (1, TABLE_SHORT)):
        if d[i] > EPS:
            s = min(s, (hi - BALL_R - p[i]) / d[i])
        elif d[i] < -EPS:
            s = min(s, (BALL_R - p[i]) / d[i])
    return max(0.0, s)


def render_diagram_prompt(m: dict[str, Any], a: dict[str, Any]) -> str:
    geo = a["geometry"]
    ghost = geo["_ghost"]
    t = geo["_t"]
    called = m["called"]
    pocket = POCKETS[called["pocket"]]
    tip, speed = m["stroke"]["tip"], m["stroke"]["speed"]
    parts = [
        "top-down orthographic view of a 9-foot pool table playing surface, 2:1 aspect ratio, "
        "green cloth, six pockets, no people, no cue stick, no room, plain flat background",
        "positions are fractions of the playing surface from its top-left corner (x across, y down); "
        "head rail is the left edge, foot rail the right edge",
        f"cue ball: plain white, unlabeled, at {_frac((m['cue']['x'], m['cue']['y']))}",
    ]
    for b in sorted(m["balls"], key=lambda x: x["n"]):
        parts.append(f"{b['n']} ball: {BALL_COLORS.get(b['n'], 'numbered')} with the number {b['n']} visible, at {_frac(_ball_xy(b))}")
    parts.append(f"faint ghost-ball outline at {_frac(ghost)}")
    parts.append("solid line from the cue ball center to the ghost-ball center")
    parts.append(f"solid line from the {called['ball']} ball into the {POCKET_PHRASE[called['pocket']]} at {_frac(pocket)}")
    if a["tangent_side"] == "straight":
        parts.append(f"no tangent line; small label '{tip}, {speed}' next to the ghost ball")
    else:
        end = _add(ghost, _mul(t, _ray_to_cloth_edge(ghost, t, 15.0)))
        parts.append(
            f"dashed tangent line from the ghost ball toward {_frac(end)} "
            f"(shooter's {geo['tangent_geo_side']}), labeled '{tip}, {speed}'"
        )
    parts.append(f"small arrow marking the {POCKET_PHRASE[called['pocket']]}")
    parts.append("do not draw any other balls, pockets, spin arrows, cue-ball paths, or text beyond the ball numbers and the tip/speed label")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Diagram backend (local only, only after ok is true). No API keys anywhere.
# ---------------------------------------------------------------------------
DIAGRAM_BACKENDS = ("svg", "local_sd", "none")


def resolve_diagram_backend() -> str:
    """``REALAI_SOTD_IMAGE_BACKEND``: ``svg`` (default), ``local_sd`` or ``none``.

    * ``svg``: deterministic local SVG from ``sotd_diagram``. No deps, no network.
    * ``local_sd``: a hook for a future local Stable Diffusion server
      (``REALAI_SOTD_LOCAL_SD_URL``, loopback only). It is a stub: no call is
      made yet, and the SVG is still returned as the diagram.
    * ``none``: no diagram.
    Unknown values fall back to ``svg``.
    """
    b = (os.environ.get("REALAI_SOTD_IMAGE_BACKEND") or "svg").strip().lower()
    if b in ("", "default"):
        return "svg"
    if b in ("off", "0", "false"):
        return "none"
    return b if b in DIAGRAM_BACKENDS else "svg"


def _local_sd_stub_note() -> str:
    url = (os.environ.get("REALAI_SOTD_LOCAL_SD_URL") or "").strip()
    if not url:
        return "local_sd hook is off: REALAI_SOTD_LOCAL_SD_URL is not set; returned the SVG render"
    if not re.match(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)", url, re.I):
        return "local_sd hook refused: REALAI_SOTD_LOCAL_SD_URL must be a loopback URL; returned the SVG render"
    return "local_sd hook is a stub (no call made yet); returned the SVG render"


def _render_diagram_into(result: dict[str, Any], m: dict[str, Any], a: dict[str, Any], *, save: bool,
                         show_grid: bool = False) -> None:
    from plugins.rackup_coach import sotd_diagram as sd

    backend = resolve_diagram_backend()
    result["diagram_backend"] = backend
    if backend == "none":
        result["diagram"] = None
        result["diagram_error"] = "diagram backend is none (REALAI_SOTD_IMAGE_BACKEND=none)"
        return
    try:
        svg = sd.render_sotd_svg(m, a, show_grid=show_grid)
    except Exception as e:  # a failed render never fails a passed map
        result["diagram"] = None
        result["diagram_error"] = f"svg render failed: {e}"[:300]
        return
    result["diagram_svg"] = svg
    result["diagram"] = sd.svg_data_uri(svg)
    result["diagram_mime"] = "image/svg+xml"
    if backend == "local_sd":
        result["diagram_error"] = _local_sd_stub_note()
    if save:
        try:
            result["diagram_path"] = sd.save_svg(svg, m.get("id"))
        except Exception as e:
            result["diagram_save_error"] = f"could not save svg: {e}"[:300]


# ---------------------------------------------------------------------------
# Fixes
# ---------------------------------------------------------------------------
_GEOMETRY_CHECKS = ("input", "place", "called", "ghost", "path", "cut", "tangent")


def _geometry_ok(a: dict[str, Any]) -> bool:
    return not a["skipped"] and not any(f["check"] in _GEOMETRY_CHECKS for f in a["fails"])


def _try_nudge(m: dict[str, Any], a: dict[str, Any]) -> Optional[tuple[dict[str, Any], dict[str, Any]]]:
    cue = (m["cue"]["x"], m["cue"]["y"])
    geo = a.get("geometry")
    candidates: list[tuple[float, int, Vec]] = []
    if not _on_cloth(cue):
        clamped = (min(max(cue[0], BALL_R), TABLE_LONG - BALL_R), min(max(cue[1], BALL_R), TABLE_SHORT - BALL_R))
        candidates.append((0.0, 0, clamped))
    if geo is not None:
        v = geo["_v"]
        n_left = (v[1], -v[0])  # shooter's left in the y-down frame
        open_sign = 1
        bl = next((b for b in (a.get("blockers") or []) if b["leg"] == "cue_to_ghost"), None)
        if bl is not None:
            bp = next(_ball_xy(b) for b in m["balls"] if b["n"] == bl["ball"])
            # blocker on shooter's left -> open side is the right
            open_sign = -1 if _dot(_sub(bp, cue), n_left) > 0 else 1
        k = NUDGE_STEP
        while k <= NUDGE_MAX + EPS:
            for pref, sgn in ((0, open_sign), (1, -open_sign)):
                candidates.append((k, pref, _add(cue, _mul(n_left, sgn * k))))
            k += NUDGE_STEP
    candidates.sort(key=lambda c: (c[0], c[1]))
    for dist, pref, p in candidates:
        cand = copy.deepcopy(m)
        cand["cue"] = {"x": _r(p[0], 2), "y": _r(p[1], 2)}
        ca = analyze(cand, check_claim=False)
        if _geometry_ok(ca):
            return cand, {
                "fix": "nudge_cue",
                "from": dict(m["cue"]),
                "to": dict(cand["cue"]),
                "distance": _r(dist, 2),
                "side": "open" if pref == 0 else "other",
            }
    return None


def _try_drop(m: dict[str, Any], a: dict[str, Any]) -> Optional[tuple[dict[str, Any], dict[str, Any]]]:
    called = m["called"]["ball"]
    blockers = [b["ball"] for b in (a.get("blockers") or []) if b["ball"] != called]
    # place-overlap offenders that are not the called ball also count as blocking
    for f in a["fails"]:
        if f["check"] == "place" and f.get("pair"):
            for nm in f["pair"]:
                if nm != "cue" and int(nm) != called and int(nm) not in blockers:
                    blockers.append(int(nm))
    seen: list[int] = []
    for b in blockers:
        if b not in seen:
            seen.append(b)
    options: list[list[int]] = [[b] for b in seen]
    if len(seen) > 1:
        options.append(list(seen))
    for drop in options:
        cand = copy.deepcopy(m)
        cand["balls"] = [b for b in cand["balls"] if b["n"] not in drop]
        if not cand["balls"]:
            continue
        ca = analyze(cand, check_claim=False)
        if _geometry_ok(ca):
            return cand, {"fix": "drop_ball", "dropped": drop}
    return None


def _try_swap_pocket(m: dict[str, Any], a: dict[str, Any]) -> Optional[tuple[dict[str, Any], dict[str, Any]]]:
    best: Optional[tuple[float, dict[str, Any]]] = None
    for pid in POCKETS:
        if pid == m["called"]["pocket"]:
            continue
        cand = copy.deepcopy(m)
        cand["called"]["pocket"] = pid
        ca = analyze(cand, check_claim=False)
        if _geometry_ok(ca) and (best is None or ca["cut_deg"] < best[0]):
            best = (ca["cut_deg"], cand)
    if best is None:
        return None
    return best[1], {"fix": "swap_pocket", "from": m["called"]["pocket"], "to": best[1]["called"]["pocket"], "cut_deg": best[0]}


def _try_catalog(m: dict[str, Any], catalog: list[dict[str, Any]]) -> Optional[tuple[dict[str, Any], dict[str, Any]]]:
    game = m.get("game") or "nine_ball"
    for entry in catalog:
        if entry.get("game") != game:
            continue
        cand, errs = normalize_map({**entry, "id": m.get("id") or "sotd-unknown"})
        if errs:
            continue
        ca = analyze(cand, check_claim=False)
        if _geometry_ok(ca):
            return cand, {"fix": "catalog_map", "catalog_id": entry.get("catalog_id")}
    return None


def _public_fail(f: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in f.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def validate_sotd(
    raw_map: Any,
    *,
    render_diagram: bool = False,
    save_diagram: bool = False,
    show_grid: bool = False,
    catalog: Optional[list[dict[str, Any]]] = None,
    default_game: str = "",
    allow_fixes: bool = True,
) -> dict[str, Any]:
    """Validate a SOTD map; fix if needed; render sentence + diagram prompt.

    Never raises: a failed check is ``ok: False`` (HTTP 200 style).
    """
    catalog = SOTD_MAP_CATALOG if catalog is None else catalog
    m, input_fails = normalize_map(raw_map, default_game=default_game)
    result: dict[str, Any] = {
        "ok": False,
        "id": (m or {}).get("id") or (raw_map.get("id") if isinstance(raw_map, dict) else None) or "sotd-unknown",
        "axis": AXIS,
        "cut_deg": None,
        "blocked_by": None,
        "tangent_side": None,
        "fails": [],
        "warnings": [],
        "fixes": [],
        "map": None,
        "sentence": None,
        "diagram_prompt": None,
        "diagram": None,
        "pockets": {k: {"x": v[0], "y": v[1]} for k, v in POCKETS.items()},
        "checker": "deterministic_geometry_v1",
    }
    if input_fails:
        result["fails"] = input_fails
        a0 = None
    else:
        a0 = analyze(m)
        result["fails"] = [_public_fail(f) for f in a0["fails"]]
        result["warnings"] = a0["warnings"]
        result["original"] = {
            "cut_deg": a0["cut_deg"],
            "blocked_by": a0["blocked_by"],
            "tangent_side": a0["tangent_side"],
        }

    current: Optional[dict[str, Any]] = None
    fixes: list[dict[str, Any]] = []
    if a0 is not None and _geometry_ok(a0):
        current = m
    elif allow_fixes:
        attempts: list[Callable[[], Optional[tuple[dict[str, Any], dict[str, Any]]]]] = []
        if a0 is not None and not a0["skipped"]:
            attempts += [
                lambda: _try_nudge(m, a0),
                lambda: _try_drop(m, a0),
                lambda: _try_swap_pocket(m, a0),
            ]
        # Catalog replacement needs a known game; garbage input stays ok:false.
        if m and m.get("game") in GAME_MAX_BALL:
            attempts.append(lambda: _try_catalog(m, catalog))
        for attempt in attempts:
            try:
                got = attempt()
            except Exception:
                got = None
            if got:
                current, fx = got
                fixes.append(fx)
                break

    if current is None:
        result["fixes"] = fixes
        if a0 is not None:
            result.update(cut_deg=a0["cut_deg"], blocked_by=a0["blocked_by"], tangent_side=a0["tangent_side"])
        result["map"] = m or None
        result["diagram_error"] = "map failed checks; no diagram is rendered for a bad map"
        return result

    # Re-check the (possibly fixed) map, claim included. A claim that does not
    # match the validated geometry is replaced by the render — never both.
    a = analyze(current)
    claim_fails = [f for f in a["fails"] if f["check"] == "claim"]
    if not _geometry_ok(a):  # defensive: should not happen
        result["fixes"] = fixes
        result["map"] = current
        result["diagram_error"] = "map failed checks after fix"
        return result
    sentence = render_sentence(current, a)
    if claim_fails or fixes:
        if current.get("claim", "") != sentence:
            fixes.append({
                "fix": "claim_rerender",
                "from": current.get("claim", ""),
                "to": sentence,
                "reason": "; ".join(f["detail"] for f in claim_fails) or "map changed by an earlier fix",
            })
        current = {**current, "claim": sentence}
        a = analyze(current)
    # The rendered sentence must itself pass the claim check.
    if any(f["check"] == "claim" for f in a["fails"]):
        result["fixes"] = fixes
        result["map"] = current
        result["diagram_error"] = "rendered sentence failed the claim check (bug)"
        return result

    result.update(
        ok=True,
        cut_deg=a["cut_deg"],
        blocked_by=a["blocked_by"],
        tangent_side=a["tangent_side"],
        fixes=fixes,
        map=current,
        sentence=sentence,
        warnings=a["warnings"] or result["warnings"],
        next_ball=a.get("next_ball"),
        next_on_exit=bool(a.get("next_on_exit")),
        geometry={k: v for k, v in a["geometry"].items() if not k.startswith("_") and k != "cut_deg"},
    )
    result["diagram_prompt"] = render_diagram_prompt(current, a)

    if render_diagram:
        _render_diagram_into(result, current, a, save=save_diagram, show_grid=show_grid)
    return result


def run_validate(player: Any, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Ability-mode entry: ``shot_of_the_day`` with ``payload.mode == 'sotd_validate'``."""
    payload = payload or {}
    default_game = str(
        payload.get("game")
        or getattr(player, "game_style", "")
        or getattr(player, "discipline", "")
        or ""
    )
    out = validate_sotd(
        payload.get("map"),
        render_diagram=bool(payload.get("render_diagram")),
        save_diagram=bool(payload.get("save_diagram")),
        show_grid=bool(payload.get("show_grid")),
        default_game=default_game,
    )
    out["mode"] = "sotd_validate"
    out["date_role"] = "shot_of_the_day"
    return out


__all__ = [
    "AXIS",
    "POCKETS",
    "POCKET_MOUTHS",
    "POCKET_HOLE_R_IN",
    "SOTD_MAP_CATALOG",
    "analyze",
    "load_checker_prompt",
    "normalize_map",
    "parse_claim",
    "render_diagram_prompt",
    "render_sentence",
    "run_validate",
    "validate_sotd",
]
