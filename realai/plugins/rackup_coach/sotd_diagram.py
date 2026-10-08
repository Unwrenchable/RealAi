"""Deterministic local SOTD diagram renderer: validated map -> SVG.

Pure Python string building. No dependencies, no network, no API keys.

The SVG is a render of the *validated* map and is not evidence: nobody should
read a cut angle back out of it. ``sotd_checker.validate_sotd`` calls this only
after ``ok`` is true (after any fixes).

Frame and transform
-------------------
This uses the same ``x_long`` frame as ``sotd_checker``. The 100 x 50 in
playing surface (cushion nose to cushion nose) has the head rail on the left
and y growing downward. ``_px`` is the single transform from playing-surface
inches to pixels, and balls, lines, pockets and diamonds all go through it.

Table style: dark walnut rails with a thin brass outer trim, a darker cushion
strip, dark green cloth with a radial vignette, a faint dashed head string at
x = 25, round pocket holes cut into the rail with straight, symmetric jaw cuts
through the cushion, and mother-of-pearl diamond inlays.

Diamond grid
------------
On a 9-ft table the diamonds are 12.5 in apart both ways (100 / 8 = 50 / 4),
so the diamond lines cut the cloth into an 8 x 4 grid of 32 identical squares.
``grid_lines()`` gives x = 12.5 ... 87.5 (including x = 50, which runs side
pocket to side pocket and has no diamond) and y = 12.5, 25, 37.5; the cloth
edges are the outer boundary. ``_px`` uses one ``SCALE`` for both axes, so the
squares stay square in pixels. ``show_grid=True`` draws it faintly in a normal
render; ``debug_grid=True`` draws it bold and extends it out to the diamonds.

Diamonds (real 9-ft layout)
---------------------------
Diamonds are measured from the pocket center points, so they split the
playing length into 8 equal parts and the width into 4:

* long rails: x = 12.5, 25, 37.5, 62.5, 75, 87.5. 50 is the side pocket, so no
  diamond there. That is 6 per long rail.
* short rails: y = 12.5, 25, 37.5, 3 per short rail.
* 18 total, none at corners. Each sits on the middle of the wood rail:
  ``CUSHION_IN + WOOD_IN / 2`` outside the cushion nose.

What is drawn from the map (and nothing else): the cue ball (white,
unlabeled); every object ball in standard colors with numbers (9-15 as a white
ball with a color band); a cream line from the cue to the ghost; the ghost as a
dashed outline; a line from the object ball to the called pocket in the object
ball's color; a dashed tangent labeled ``<tip> <speed>``; a follow (forward) or
draw (back) arrow; and an arrow pointing at the called pocket.
"""
from __future__ import annotations

import base64
import math
import os
import re
from pathlib import Path
from typing import Any, Optional
from xml.sax.saxutils import escape

SCALE = 10.0  # px per inch
TABLE_LONG = 100.0
TABLE_SHORT = 50.0
BALL_R = 1.125
CUSHION_IN = 1.75  # cushion rubber, nose to wood
WOOD_IN = 4.0  # visible wood rail
RAIL_IN = CUSHION_IN + WOOD_IN  # 5.75 in total rail (real 9-ft: ~5-6 in)
MARGIN_IN = 3.5  # transparent margin outside the table (holds the pocket arrow)
OUTER_RX_IN = 1.4  # rounded outer rail corners
DIAMOND_OFFSET_IN = CUSHION_IN + WOOD_IN / 2.0  # diamond centers: middle of the wood
DIAMOND_ALONG_IN = 0.7  # rhombus half-diagonal along the rail
DIAMOND_ACROSS_IN = 0.4  # rhombus half-diagonal across the rail
LONG_DIAMONDS_X = (12.5, 25.0, 37.5, 62.5, 75.0, 87.5)
SHORT_DIAMONDS_Y = (12.5, 25.0, 37.5)
GRID_STEP_IN = TABLE_LONG / 8.0  # 12.5 in, one diamond
assert GRID_STEP_IN == TABLE_SHORT / 4.0  # square cells
GRID_X = tuple(GRID_STEP_IN * i for i in range(1, 8))  # 12.5 ... 87.5, includes 50
GRID_Y = tuple(GRID_STEP_IN * i for i in range(1, 4))  # 12.5, 25, 37.5
HEAD_STRING_X = TABLE_LONG / 4.0
# Corner pocket (pocket-local inches, +x/+y into the table along each rail):
# cushion nose points at CORNER_MOUTH_IN from the cloth corner, straight jaw cuts
# back to CORNER_JAW_BACK_IN at the wood (about 142 deg to the nose, like a real
# corner jaw), and a round hole centered on the diagonal that the jaw backs land on.
CORNER_MOUTH_IN = 3.2
CORNER_JAW_BACK_IN = 1.8
CORNER_HOLE_OFFSET_IN = 0.45
CORNER_HOLE_R_IN = math.hypot(CORNER_JAW_BACK_IN + CORNER_HOLE_OFFSET_IN, CUSHION_IN - CORNER_HOLE_OFFSET_IN)
SIDE_MOUTH_HALF_IN = 2.6  # side mouth ~5.2 in at the noses
SIDE_JAW_BACK_HALF_IN = 2.3
SIDE_HOLE_OFFSET_IN = 0.3  # hole center behind the cushion back
SIDE_HOLE_R_IN = math.hypot(SIDE_JAW_BACK_HALF_IN, SIDE_HOLE_OFFSET_IN)
STOP_BAR_IN = 3.4  # stop marker width across the shot line
TANGENT_LEN_IN = 15.0
SPIN_ARROW_IN = 6.0
# Pocket arrows start in the margin and stop just short of the pocket mouth.
POCKET_ARROW_SIDE = (RAIL_IN + 2.2, CUSHION_IN + SIDE_HOLE_OFFSET_IN + SIDE_HOLE_R_IN + 0.7)  # (tail, tip) from pocket center
_CORNER_HOLE_REACH = CORNER_HOLE_OFFSET_IN * math.sqrt(2) + CORNER_HOLE_R_IN
POCKET_ARROW_CORNER = (_CORNER_HOLE_REACH + 5.6, _CORNER_HOLE_REACH + 0.9)  # along the diagonal
POCKET_ARROW_HALO_PX = 6.5

WOOD_DARK = "#33190a"
WOOD_MID = "#43230f"
WOOD_LIGHT = "#512d15"
BRASS = "#c9a24a"
CUSHION = "#0b4a28"
CUSHION_NOSE = "#06331b"
CLOTH_CENTER = "#1d7a45"
CLOTH_EDGE = "#0c5130"
POCKET = "#050505"
POCKET_LINER = "#1a1a1a"
POCKET_SHELF = "#06301b"  # slate shelf inside the jaws
PEARL = "#f2ead6"
PEARL_EDGE = "#b8a77f"
CUE_PATH = "#f5efd9"
TANGENT = "#8fd8ff"
SPIN = "#ffb347"
MARK = "#ff4d4d"

# Standard pool ball colors (1-8 solids; 9-15 stripes reuse 1-7).
BALL_HEX = {
    1: "#f2c200",
    2: "#1f4fbf",
    3: "#d0202a",
    4: "#5b2a86",
    5: "#f07f1a",
    6: "#0e7a3a",
    7: "#7a1f2b",
    8: "#111111",
}
for _n in range(9, 16):
    BALL_HEX[_n] = BALL_HEX[_n - 8]

POCKETS: dict[str, tuple[float, float]] = {
    "corner_head_left": (0.0, 0.0),
    "corner_head_right": (0.0, TABLE_SHORT),
    "side_left": (TABLE_LONG / 2.0, 0.0),
    "side_right": (TABLE_LONG / 2.0, TABLE_SHORT),
    "corner_foot_left": (TABLE_LONG, 0.0),
    "corner_foot_right": (TABLE_LONG, TABLE_SHORT),
}

CANVAS_W = (TABLE_LONG + 2 * (RAIL_IN + MARGIN_IN)) * SCALE
CANVAS_H = (TABLE_SHORT + 2 * (RAIL_IN + MARGIN_IN)) * SCALE


def _px(x: float, y: float) -> tuple[float, float]:
    """Playing-surface inches -> SVG pixels (the single transform)."""
    return ((x + RAIL_IN + MARGIN_IN) * SCALE, (y + RAIL_IN + MARGIN_IN) * SCALE)


def _f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def diamond_positions() -> list[dict[str, Any]]:
    """The 18 diamonds in playing-surface inches (rail centerline of the wood).

    ``at`` is the playing-surface coordinate the diamond marks; (x, y) is where
    it is drawn (outside the cushion nose)."""
    o = DIAMOND_OFFSET_IN
    out: list[dict[str, Any]] = []
    for x in LONG_DIAMONDS_X:
        out.append({"rail": "long_left", "at": x, "x": x, "y": -o})
        out.append({"rail": "long_right", "at": x, "x": x, "y": TABLE_SHORT + o})
    for y in SHORT_DIAMONDS_Y:
        out.append({"rail": "short_head", "at": y, "x": -o, "y": y})
        out.append({"rail": "short_foot", "at": y, "x": TABLE_LONG + o, "y": y})
    return out


def grid_lines() -> list[dict[str, Any]]:
    """The diamond grid on the cloth, in playing-surface inches.

    Seven x lines (including x = 50, side pocket to side pocket) and three y
    lines. With the cloth edges they bound 32 equal 12.5 in squares."""
    out: list[dict[str, Any]] = []
    for x in GRID_X:
        out.append({"axis": "x", "at": x, "a": (x, 0.0), "b": (x, TABLE_SHORT)})
    for y in GRID_Y:
        out.append({"axis": "y", "at": y, "a": (0.0, y), "b": (TABLE_LONG, y)})
    return out


def grid_cells_px() -> list[tuple[float, float, float, float]]:
    """The 32 grid squares as pixel boxes (x0, y0, x1, y1) via ``_px``."""
    xs = [0.0, *GRID_X, TABLE_LONG]
    ys = [0.0, *GRID_Y, TABLE_SHORT]
    cells = []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            x0, y0 = _px(xs[i], ys[j])
            x1, y1 = _px(xs[i + 1], ys[j + 1])
            cells.append((x0, y0, x1, y1))
    return cells


def _clip_ray(p: tuple[float, float], d: tuple[float, float], cap: float) -> float:
    """Longest step <= cap from p along unit d that stays on the cloth."""
    s = cap
    for i, hi in ((0, TABLE_LONG), (1, TABLE_SHORT)):
        if d[i] > 1e-9:
            s = min(s, (hi - BALL_R - p[i]) / d[i])
        elif d[i] < -1e-9:
            s = min(s, (BALL_R - p[i]) / d[i])
    return max(0.0, s)


def _line(a: tuple[float, float], b: tuple[float, float], color: str, width: float,
          *, dash: str = "", marker: str = "", cls: str = "", pfx: str = "", opacity: float = 1.0) -> str:
    ax, ay = _px(*a)
    bx, by = _px(*b)
    extra = ""
    if dash:
        extra += f' stroke-dasharray="{dash}"'
    if marker:
        extra += f' marker-end="url(#{pfx}{marker})"'
    if cls:
        extra += f' class="{cls}"'
    if opacity < 1.0:
        extra += f' stroke-opacity="{_f(opacity)}"'
    return (
        f'<line x1="{_f(ax)}" y1="{_f(ay)}" x2="{_f(bx)}" y2="{_f(by)}" '
        f'stroke="{color}" stroke-width="{_f(width)}" stroke-linecap="round"{extra}/>'
    )


def _corner_pocket(pid: str, X: float, Y: float) -> str:
    """Round hole in the rail corner with straight, symmetric jaw cuts.

    Local frame: +x along the end rail into the table, +y along the side rail,
    both pointing into the table, so the shape is mirror-symmetric about the
    diagonal by construction."""
    dx = 1 if X == 0 else -1
    dy = 1 if Y == 0 else -1

    def P(lx: float, ly: float) -> tuple[float, float]:
        return _px(X + dx * lx, Y + dy * ly)

    a, b, c, k = CORNER_MOUTH_IN, CORNER_JAW_BACK_IN, CUSHION_IN, CORNER_HOLE_OFFSET_IN
    n1, b1, n2, b2 = P(a, 0), P(b, -c), P(0, a), P(-c, b)
    shelf = [P(0, 0), n1, b1, P(-c, -c), b2, n2]
    hx, hy = P(-k, -k)
    r = CORNER_HOLE_R_IN * SCALE
    pts = " ".join(f"{_f(px)},{_f(py)}" for px, py in shelf)
    return (
        f'<g class="pocket corner-pocket" data-pocket="{pid}">'
        f'<polygon class="pocket-shelf" points="{pts}" fill="{POCKET_SHELF}"/>'
        f'<line class="jaw" x1="{_f(n1[0])}" y1="{_f(n1[1])}" x2="{_f(b1[0])}" y2="{_f(b1[1])}" '
        f'stroke="{CUSHION_NOSE}" stroke-width="1.5"/>'
        f'<line class="jaw" x1="{_f(n2[0])}" y1="{_f(n2[1])}" x2="{_f(b2[0])}" y2="{_f(b2[1])}" '
        f'stroke="{CUSHION_NOSE}" stroke-width="1.5"/>'
        f'<circle class="pocket-hole" cx="{_f(hx)}" cy="{_f(hy)}" r="{_f(r)}" fill="{POCKET}" '
        f'stroke="{POCKET_LINER}" stroke-width="1.2"/>'
        f"</g>"
    )


def _side_pocket(pid: str, X: float, Y: float) -> str:
    """Same style as the corners: straight jaw cuts through the cushion and a
    round hole in the long rail that the jaw backs land on. Symmetric about x = 50."""
    dy = 1 if Y == 0 else -1  # local +y points into the table

    def P(lx: float, ly: float) -> tuple[float, float]:
        return _px(X + lx, Y + dy * ly)

    a, b, c, k = SIDE_MOUTH_HALF_IN, SIDE_JAW_BACK_HALF_IN, CUSHION_IN, SIDE_HOLE_OFFSET_IN
    n1, b1, n2, b2 = P(-a, 0), P(-b, -c), P(a, 0), P(b, -c)
    pts = " ".join(f"{_f(px)},{_f(py)}" for px, py in (n1, b1, b2, n2))
    hx, hy = P(0, -(c + k))
    r = SIDE_HOLE_R_IN * SCALE
    return (
        f'<g class="pocket side-pocket" data-pocket="{pid}">'
        f'<polygon class="pocket-shelf" points="{pts}" fill="{POCKET_SHELF}"/>'
        f'<line class="jaw" x1="{_f(n1[0])}" y1="{_f(n1[1])}" x2="{_f(b1[0])}" y2="{_f(b1[1])}" '
        f'stroke="{CUSHION_NOSE}" stroke-width="1.5"/>'
        f'<line class="jaw" x1="{_f(n2[0])}" y1="{_f(n2[1])}" x2="{_f(b2[0])}" y2="{_f(b2[1])}" '
        f'stroke="{CUSHION_NOSE}" stroke-width="1.5"/>'
        f'<circle class="pocket-hole" cx="{_f(hx)}" cy="{_f(hy)}" r="{_f(r)}" fill="{POCKET}" '
        f'stroke="{POCKET_LINER}" stroke-width="1.2"/>'
        f"</g>"
    )


def _diamond(dm: dict[str, Any]) -> str:
    cx, cy = _px(dm["x"], dm["y"])
    along = DIAMOND_ALONG_IN * SCALE
    across = DIAMOND_ACROSS_IN * SCALE
    if dm["rail"].startswith("long"):
        ax, ay = along, across
    else:
        ax, ay = across, along
    pts = f"{_f(cx - ax)},{_f(cy)} {_f(cx)},{_f(cy - ay)} {_f(cx + ax)},{_f(cy)} {_f(cx)},{_f(cy + ay)}"
    return (
        f'<polygon class="diamond" data-rail="{dm["rail"]}" data-at="{_f(dm["at"])}" '
        f'data-cx="{_f(cx)}" data-cy="{_f(cy)}" points="{pts}" '
        f'fill="{PEARL}" stroke="{PEARL_EDGE}" stroke-width="0.6"/>'
    )


def _ball(n: Optional[int], x: float, y: float, pfx: str = "") -> str:
    cx, cy = _px(x, y)
    r = BALL_R * SCALE
    shade = f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="url(#{pfx}ball-shade)"/>'
    if n is None:  # cue ball: plain white, unlabeled
        return (
            f'<g class="ball cue" data-ball="cue">'
            f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="#fbfbf5"/>{shade}'
            f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="none" stroke="#1a1a1a" stroke-width="0.8"/>'
            f"</g>"
        )
    color = BALL_HEX.get(n, "#888888")
    parts = [f'<g class="ball object" data-ball="{n}">']
    if n >= 9:
        cid = f"{pfx}clip-ball-{n}"
        parts.append(
            f'<clipPath id="{cid}"><circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}"/></clipPath>'
            f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="#fbfbf5"/>'
            f'<rect x="{_f(cx - r)}" y="{_f(cy - r * 0.55)}" width="{_f(2 * r)}" height="{_f(r * 1.1)}" '
            f'fill="{color}" clip-path="url(#{cid})"/>'
        )
    else:
        parts.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="{color}"/>')
    parts.append(
        shade
        + f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="none" stroke="#1a1a1a" stroke-width="0.8"/>'
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r * 0.5)}" fill="#fbfbf5"/>'
        f'<text x="{_f(cx)}" y="{_f(cy)}" font-family="Arial, Helvetica, sans-serif" font-size="{_f(r * 0.78)}" '
        f'font-weight="bold" fill="#111" text-anchor="middle" dominant-baseline="central">{n}</text>'
        f"</g>"
    )
    return "".join(parts)


def _grid(*, debug: bool) -> list[str]:
    out: list[str] = []
    color, width, opacity = ("#ff66ff", 1.0, 0.75) if debug else ("#ffffff", 0.8, 0.13)
    cls = "grid-line debug-grid" if debug else "grid-line"
    for g in grid_lines():
        el = _line(g["a"], g["b"], color, width, cls=cls, opacity=opacity)
        out.append(el.replace("<line ", f'<line data-axis="{g["axis"]}" data-at="{_f(g["at"])}" ', 1))
    if debug:  # extend each diamond line out to its diamonds (not into the side pockets)
        o = DIAMOND_OFFSET_IN
        for x in LONG_DIAMONDS_X:
            out.append(_line((x, -o), (x, 0), color, width, cls="debug-tick", opacity=0.5))
            out.append(_line((x, TABLE_SHORT), (x, TABLE_SHORT + o), color, width, cls="debug-tick", opacity=0.5))
        for y in SHORT_DIAMONDS_Y:
            out.append(_line((-o, y), (0, y), color, width, cls="debug-tick", opacity=0.5))
            out.append(_line((TABLE_LONG, y), (TABLE_LONG + o, y), color, width, cls="debug-tick", opacity=0.5))
    return out


def _table(pfx: str, *, debug_grid: bool = False, show_grid: bool = False) -> list[str]:
    out: list[str] = []
    m = MARGIN_IN * SCALE
    tw = (TABLE_LONG + 2 * RAIL_IN) * SCALE
    th = (TABLE_SHORT + 2 * RAIL_IN) * SCALE
    rx = OUTER_RX_IN * SCALE
    sx, sy = _px(0, 0)
    out.append(
        f'<rect class="rail" x="{_f(m)}" y="{_f(m)}" width="{_f(tw)}" height="{_f(th)}" rx="{_f(rx)}" '
        f'fill="url(#{pfx}wood)"/>'
    )
    # brass trim: outer edge + a hairline just inside it
    out.append(
        f'<rect class="trim" x="{_f(m + 1)}" y="{_f(m + 1)}" width="{_f(tw - 2)}" height="{_f(th - 2)}" rx="{_f(rx)}" '
        f'fill="none" stroke="{BRASS}" stroke-width="2"/>'
    )
    out.append(
        f'<rect class="trim-inner" x="{_f(m + 5)}" y="{_f(m + 5)}" width="{_f(tw - 10)}" height="{_f(th - 10)}" '
        f'rx="{_f(max(rx - 4, 0))}" fill="none" stroke="{BRASS}" stroke-opacity="0.35" stroke-width="0.8"/>'
    )
    # cushion strip, then cloth with vignette
    cx0, cy0 = _px(-CUSHION_IN, -CUSHION_IN)
    out.append(
        f'<rect class="cushion" x="{_f(cx0)}" y="{_f(cy0)}" width="{_f((TABLE_LONG + 2 * CUSHION_IN) * SCALE)}" '
        f'height="{_f((TABLE_SHORT + 2 * CUSHION_IN) * SCALE)}" fill="{CUSHION}"/>'
    )
    out.append(
        f'<rect class="cloth" x="{_f(sx)}" y="{_f(sy)}" width="{_f(TABLE_LONG * SCALE)}" '
        f'height="{_f(TABLE_SHORT * SCALE)}" fill="url(#{pfx}cloth)" stroke="{CUSHION_NOSE}" stroke-width="1.5"/>'
    )
    # head string (faint, dashed) at the 1/4 line from the head rail
    out.append(_line((HEAD_STRING_X, 0), (HEAD_STRING_X, TABLE_SHORT), "#ffffff", 1.0,
                     dash="6 7", cls="head-string", opacity=0.22))
    if debug_grid or show_grid:
        out.extend(_grid(debug=debug_grid))
    for dm in diamond_positions():
        out.append(_diamond(dm))
    for pid, (X, Y) in POCKETS.items():
        out.append(_corner_pocket(pid, X, Y) if pid.startswith("corner") else _side_pocket(pid, X, Y))
    return out


def render_sotd_svg(m: dict[str, Any], a: dict[str, Any], *, debug_grid: bool = False,
                    show_grid: bool = False) -> str:
    """Render a validated map. ``a`` is ``sotd_checker.analyze(m)`` output.

    ``show_grid`` draws the 8 x 4 diamond grid faintly on the cloth (off by
    default). ``debug_grid`` draws it bold and out to the diamonds (alignment
    check)."""
    geo = a["geometry"]
    ghost = geo["_ghost"]
    t = geo["_t"]
    v = geo["_v"]
    called = m["called"]
    pocket = POCKETS[called["pocket"]]
    obj = next(b for b in m["balls"] if b["n"] == called["ball"])
    tip = m["stroke"]["tip"]
    speed = m["stroke"]["speed"]
    sx, sy = _px(0, 0)
    pfx = f"sotd-{safe_id(m.get('id'))}-"  # unique ids if several SVGs share a page

    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_f(CANVAS_W)} {_f(CANVAS_H)}" '
        f'width="{_f(CANVAS_W)}" height="{_f(CANVAS_H)}" data-axis="x_long" data-renderer="sotd_svg_v2" '
        f'data-scale="{_f(SCALE)}" data-origin-x="{_f(sx)}" data-origin-y="{_f(sy)}">'
    )
    out.append(f"<title>{escape(str(m.get('id') or 'sotd'))}</title>")
    out.append(
        "<defs>"
        f'<linearGradient id="{pfx}wood" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{WOOD_LIGHT}"/><stop offset="0.5" stop-color="{WOOD_MID}"/>'
        f'<stop offset="1" stop-color="{WOOD_DARK}"/></linearGradient>'
        f'<radialGradient id="{pfx}cloth" cx="0.5" cy="0.5" r="0.62">'
        f'<stop offset="0" stop-color="{CLOTH_CENTER}"/><stop offset="1" stop-color="{CLOTH_EDGE}"/></radialGradient>'
        f'<radialGradient id="{pfx}ball-shade" cx="0.35" cy="0.3" r="0.75">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.45"/><stop offset="0.45" stop-color="#ffffff" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity="0.28"/></radialGradient>'
        f'<marker id="{pfx}arrow-pocket" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{MARK}"/></marker>'
        f'<marker id="{pfx}arrow-spin" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{SPIN}"/></marker>'
        "</defs>"
    )
    out.extend(_table(pfx, debug_grid=debug_grid, show_grid=show_grid))

    # called-pocket arrow: from the margin, across the trim, toward the mouth
    ox = pocket[0] - TABLE_LONG / 2.0
    oy = pocket[1] - TABLE_SHORT / 2.0
    on = (1.0 if ox > 0 else -1.0 if ox < 0 else 0.0, 1.0 if oy > 0 else -1.0 if oy < 0 else 0.0)
    nrm = math.hypot(*on) or 1.0
    on = (on[0] / nrm, on[1] / nrm)
    tail, tipd = POCKET_ARROW_SIDE if (on[0] == 0 or on[1] == 0) else POCKET_ARROW_CORNER
    a_start = (pocket[0] + on[0] * tail, pocket[1] + on[1] * tail)
    a_end = (pocket[0] + on[0] * tipd, pocket[1] + on[1] * tipd)
    out.append(_line(a_start, a_end, "#000000", POCKET_ARROW_HALO_PX, cls="pocket-arrow-halo", opacity=0.45))
    out.append(_line(a_start, a_end, MARK, 4.0, marker="arrow-pocket", cls="pocket-arrow", pfx=pfx))

    # paths
    cue = (float(m["cue"]["x"]), float(m["cue"]["y"]))
    O = (float(obj["x"]), float(obj["y"]))
    obj_color = BALL_HEX.get(int(obj["n"]), "#ffe066")
    halo = "#f5efd9" if int(obj["n"]) == 8 else "#000000"
    out.append(_line(cue, ghost, "#000000", 4.0, cls="cue-path-halo", opacity=0.3))
    out.append(_line(cue, ghost, CUE_PATH, 2.2, cls="cue-path"))
    out.append(_line(O, pocket, halo, 4.2, cls="object-path-halo", opacity=0.45))
    out.append(_line(O, pocket, obj_color, 2.4, cls="object-path"))

    label = f"{tip} {speed}"
    label_w = 7.2 * len(label) + 10
    gx, gy = _px(*ghost)
    side = a.get("tangent_side")
    if geo.get("tangent_geo_side") in ("left", "right") and math.hypot(*t) > 1e-9:
        L = _clip_ray(ghost, t, TANGENT_LEN_IN)
        end = (ghost[0] + t[0] * L, ghost[1] + t[1] * L)
        out.append(_line(ghost, end, TANGENT, 2.0, dash="8 6", cls="tangent"))
        lx, ly = _px(ghost[0] + t[0] * L * 0.6, ghost[1] + t[1] * L * 0.6)
        # Offset the label perpendicular to the tangent, away from the object
        # path, by the label box's support distance so it never sits on the line.
        nx, ny = -t[1], t[0]
        if (nx * (O[0] - ghost[0]) + ny * (O[1] - ghost[1])) > 0:
            nx, ny = -nx, -ny
        shift = abs(nx) * label_w / 2 + abs(ny) * 10 + 6
        lx += nx * shift
        ly += ny * shift
    else:
        # Straight-in: no tangent. Put the label beside the ghost, off the shot line.
        nx, ny = -v[1], v[0]
        if ny > 0 or (ny == 0 and nx > 0):
            nx, ny = -nx, -ny
        shift = abs(nx) * label_w / 2 + abs(ny) * 10 + BALL_R * SCALE + 6
        lx, ly = gx + nx * shift, gy + ny * shift
    if side in ("forward", "back"):
        d = v if side == "forward" else (-v[0], -v[1])
        Ls = _clip_ray(ghost, d, SPIN_ARROW_IN)
        out.append(_line(ghost, (ghost[0] + d[0] * Ls, ghost[1] + d[1] * Ls), SPIN, 2.5, marker="arrow-spin", cls=f"spin-{side}", pfx=pfx))
    elif side == "straight":
        # Straight-in with no follow/draw: the cue ball stops on the ghost spot.
        # A bar across the shot line marks it so the label is not orphaned.
        hb = STOP_BAR_IN / 2.0
        p1 = (ghost[0] - v[1] * hb, ghost[1] + v[0] * hb)
        p2 = (ghost[0] + v[1] * hb, ghost[1] - v[0] * hb)
        out.append(_line(p1, p2, "#000000", 5.0, cls="spin-stop-halo", opacity=0.35))
        out.append(_line(p1, p2, SPIN, 3.0, cls="spin-stop"))
    W_lab = label_w
    lx = min(max(lx, sx + W_lab / 2 + 2), sx + TABLE_LONG * SCALE - W_lab / 2 - 2)
    ly = min(max(ly, sy + 12), sy + TABLE_SHORT * SCALE - 12)
    if geo.get("tangent_geo_side") == "straight":
        # No tangent line to sit on: tie the label to the ghost with a leader.
        dxl, dyl = gx - lx, gy - ly
        dl = math.hypot(dxl, dyl) or 1.0
        rb = BALL_R * SCALE + 2
        ex, ey = gx - dxl / dl * rb, gy - dyl / dl * rb
        out.append(
            f'<line class="label-leader" x1="{_f(lx)}" y1="{_f(ly)}" x2="{_f(ex)}" y2="{_f(ey)}" '
            f'stroke="{SPIN}" stroke-width="1.2" stroke-opacity="0.85" stroke-dasharray="2 3"/>'
        )
    out.append(
        f'<g class="tangent-label"><rect x="{_f(lx - W_lab / 2)}" y="{_f(ly - 10)}" width="{_f(W_lab)}" height="20" rx="4" '
        f'fill="#000" fill-opacity="0.55"/>'
        f'<text x="{_f(lx)}" y="{_f(ly)}" font-family="Arial, Helvetica, sans-serif" font-size="13" fill="#fff" '
        f'text-anchor="middle" dominant-baseline="central">{escape(label)}</text></g>'
    )

    # ghost ball (dashed outline), then the balls on top
    out.append(
        f'<circle class="ghost" cx="{_f(gx)}" cy="{_f(gy)}" r="{_f(BALL_R * SCALE)}" fill="none" '
        f'stroke="#ffffff" stroke-width="1.5" stroke-dasharray="3 3"/>'
    )
    for b in sorted(m["balls"], key=lambda x: x["n"]):
        out.append(_ball(int(b["n"]), float(b["x"]), float(b["y"]), pfx))
    out.append(_ball(None, *cue, pfx))
    out.append("</svg>")
    return "".join(out)


def svg_data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def safe_id(s: Any) -> str:
    out = re.sub(r"[^A-Za-z0-9._-]", "_", str(s or "sotd"))[:80].lstrip(".")
    return out or "sotd"


def diagram_dir() -> Path:
    """``$REALAI_DATA_DIR/rackup_coach/sotd`` (default ``~/.realai``), the same
    base the plugin's sotd_library uses."""
    base = os.environ.get("REALAI_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".realai")
    return Path(base) / "rackup_coach" / "sotd"


def save_svg(svg: str, sotd_id: Any) -> str:
    d = diagram_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{safe_id(sotd_id)}.svg"
    p.write_text(svg, encoding="utf-8")
    return str(p)


def svg_to_png(svg: str) -> Optional[bytes]:
    """Optional PNG, only when ``cairosvg`` is already installed locally.
    Returns None otherwise. Never installs or fetches anything."""
    try:
        import cairosvg  # type: ignore
    except Exception:
        return None
    try:
        return cairosvg.svg2png(bytestring=svg.encode("utf-8"))
    except Exception:
        return None


__all__ = [
    "diamond_positions",
    "grid_lines",
    "grid_cells_px",
    "render_sotd_svg",
    "svg_data_uri",
    "save_svg",
    "svg_to_png",
    "diagram_dir",
    "safe_id",
]
