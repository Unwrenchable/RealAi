"""Deterministic local SOTD diagram renderer: validated map -> SVG.

Pure Python string building. No dependencies, no network, no API keys.

The SVG is a render of the *validated* map and is not evidence: nobody should
read a cut angle back out of it. ``sotd_checker.validate_sotd`` calls this only
after ``ok`` is true (after any fixes).

Frame
-----
This uses the same ``x_long`` frame as ``sotd_checker``. The 100 x 50 in
playing surface is drawn at ``SCALE`` px per inch, with the head rail on the
left and y growing downward. Balls are true scale (radius 1.125 in).

What is drawn (and nothing else):

* the green cloth, wooden rails, and the six pockets at the documented centers
* the cue ball (white, unlabeled) and every object ball in the map, in
  standard colors with numbers; 9-15 are drawn as a white ball with a color
  band
* a solid line from the cue center to the ghost center, and the ghost ball as
  a dashed outline
* a solid line from the object ball to the called pocket
* a dashed tangent from the ghost on the cue-ball exit side, labeled
  ``<tip> <speed>``. follow adds a short forward arrow and draw a short back
  arrow along the shot line. A straight-in center hit has no tangent; only
  the label is drawn.
* a small arrow in the rail pointing at the called pocket
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
RAIL_IN = 6.0  # rail + frame width drawn around the playing surface (in)
TABLE_LONG = 100.0
TABLE_SHORT = 50.0
BALL_R = 1.125
CORNER_POCKET_R = 2.4
SIDE_POCKET_R = 2.2
TANGENT_LEN_IN = 15.0
SPIN_ARROW_IN = 6.0
POCKET_ARROW_OUT_IN = 5.6  # side pockets: arrow tail distance from the pocket center (in)
POCKET_ARROW_OUT_CORNER_IN = 7.0  # corners: along the diagonal, still inside the rounded frame
POCKET_ARROW_TIP_IN = 2.9  # arrow tip stops just outside the pocket circle

CLOTH = "#0f6b3a"
CLOTH_EDGE = "#0b5a30"
RAIL = "#5a3a1e"
RAIL_EDGE = "#3d2712"
POCKET = "#0a0a0a"
CUE_PATH = "#ffffff"
OBJ_PATH = "#ffe066"
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


def _px(x: float, y: float) -> tuple[float, float]:
    return ((x + RAIL_IN) * SCALE, (y + RAIL_IN) * SCALE)


def _f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


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
          *, dash: str = "", marker: str = "", cls: str = "", pfx: str = "") -> str:
    ax, ay = _px(*a)
    bx, by = _px(*b)
    extra = ""
    if dash:
        extra += f' stroke-dasharray="{dash}"'
    if marker:
        extra += f' marker-end="url(#{pfx}{marker})"'
    if cls:
        extra += f' class="{cls}"'
    return (
        f'<line x1="{_f(ax)}" y1="{_f(ay)}" x2="{_f(bx)}" y2="{_f(by)}" '
        f'stroke="{color}" stroke-width="{_f(width)}" stroke-linecap="round"{extra}/>'
    )


def _ball(n: Optional[int], x: float, y: float, pfx: str = "") -> str:
    cx, cy = _px(x, y)
    r = BALL_R * SCALE
    if n is None:  # cue ball: plain white, unlabeled
        return (
            f'<g class="ball cue" data-ball="cue">'
            f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="#fbfbf5" stroke="#222" stroke-width="0.8"/>'
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
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="none" stroke="#222" stroke-width="0.8"/>'
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r * 0.5)}" fill="#fbfbf5"/>'
        f'<text x="{_f(cx)}" y="{_f(cy)}" font-family="Arial, Helvetica, sans-serif" font-size="{_f(r * 0.78)}" '
        f'font-weight="bold" fill="#111" text-anchor="middle" dominant-baseline="central">{n}</text>'
        f"</g>"
    )
    return "".join(parts)


def render_sotd_svg(m: dict[str, Any], a: dict[str, Any]) -> str:
    """Render a validated map. ``a`` is ``sotd_checker.analyze(m)`` output."""
    geo = a["geometry"]
    ghost = geo["_ghost"]
    t = geo["_t"]
    v = geo["_v"]
    called = m["called"]
    pocket = POCKETS[called["pocket"]]
    obj = next(b for b in m["balls"] if b["n"] == called["ball"])
    tip = m["stroke"]["tip"]
    speed = m["stroke"]["speed"]
    W = (TABLE_LONG + 2 * RAIL_IN) * SCALE
    H = (TABLE_SHORT + 2 * RAIL_IN) * SCALE
    sx, sy = _px(0, 0)
    pfx = f"sotd-{safe_id(m.get('id'))}-"  # unique ids if several SVGs share a page

    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_f(W)} {_f(H)}" '
        f'width="{_f(W)}" height="{_f(H)}" data-axis="x_long" data-renderer="sotd_svg_v1">'
    )
    out.append(f"<title>{escape(str(m.get('id') or 'sotd'))}</title>")
    out.append(
        "<defs>"
        f'<marker id="{pfx}arrow-pocket" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{MARK}"/></marker>'
        f'<marker id="{pfx}arrow-spin" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{SPIN}"/></marker>'
        "</defs>"
    )
    # table
    out.append(f'<rect class="rail" x="0" y="0" width="{_f(W)}" height="{_f(H)}" rx="{_f(2.5 * SCALE)}" fill="{RAIL}" stroke="{RAIL_EDGE}" stroke-width="3"/>')
    out.append(
        f'<rect class="cloth" x="{_f(sx)}" y="{_f(sy)}" width="{_f(TABLE_LONG * SCALE)}" '
        f'height="{_f(TABLE_SHORT * SCALE)}" fill="{CLOTH}" stroke="{CLOTH_EDGE}" stroke-width="2"/>'
    )
    for pid, (px_, py_) in POCKETS.items():
        cx, cy = _px(px_, py_)
        r = (CORNER_POCKET_R if pid.startswith("corner") else SIDE_POCKET_R) * SCALE
        out.append(f'<circle class="pocket" data-pocket="{pid}" cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="{POCKET}"/>')

    # called-pocket arrow, in the rail, pointing at the pocket
    ox = pocket[0] - TABLE_LONG / 2.0
    oy = pocket[1] - TABLE_SHORT / 2.0
    on = (1.0 if ox > 0 else -1.0 if ox < 0 else 0.0, 1.0 if oy > 0 else -1.0 if oy < 0 else 0.0)
    nrm = math.hypot(*on) or 1.0
    on = (on[0] / nrm, on[1] / nrm)
    # Keep the whole arrow inside the drawn frame (corners run on the diagonal).
    tail = POCKET_ARROW_OUT_IN if (on[0] == 0 or on[1] == 0) else POCKET_ARROW_OUT_CORNER_IN
    a_start = (pocket[0] + on[0] * tail, pocket[1] + on[1] * tail)
    a_end = (pocket[0] + on[0] * POCKET_ARROW_TIP_IN, pocket[1] + on[1] * POCKET_ARROW_TIP_IN)
    out.append(_line(a_start, a_end, MARK, 4.0, marker="arrow-pocket", cls="pocket-arrow", pfx=pfx))

    # paths
    cue = (float(m["cue"]["x"]), float(m["cue"]["y"]))
    O = (float(obj["x"]), float(obj["y"]))
    out.append(_line(cue, ghost, CUE_PATH, 2.0, cls="cue-path"))
    out.append(_line(O, pocket, OBJ_PATH, 2.0, cls="object-path"))

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
    W_lab = label_w
    lx = min(max(lx, sx + W_lab / 2 + 2), sx + TABLE_LONG * SCALE - W_lab / 2 - 2)
    ly = min(max(ly, sy + 12), sy + TABLE_SHORT * SCALE - 12)
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
    out.append(_ball(None, *cue))
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
    "render_sotd_svg",
    "svg_data_uri",
    "save_svg",
    "svg_to_png",
    "diagram_dir",
    "safe_id",
]
