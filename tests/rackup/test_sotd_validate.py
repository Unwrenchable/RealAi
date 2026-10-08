"""shot_of_the_day / mode=sotd_validate — deterministic map checker tests."""
from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT, _ROOT / "realai"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from plugins.rackup_coach import invoke  # noqa: E402
from plugins.rackup_coach import sotd_checker as sc  # noqa: E402

EXAMPLE = {
    "id": "sotd-2026-10-08",
    "game": "nine_ball",
    "cue": {"x": 28, "y": 18},
    "balls": [{"n": 1, "x": 62, "y": 14}, {"n": 2, "x": 78, "y": 36}],
    "called": {"ball": 1, "pocket": "corner_foot_right"},
    "stroke": {"tip": "center", "speed": "medium"},
    "claim": "Cut the 1 in the foot-right corner and stop for the 2.",
}


def _map(**over):
    m = copy.deepcopy(EXAMPLE)
    m["claim"] = ""
    for k, v in over.items():
        m[k] = v
    return m


def _analyze(raw):
    m, errs = sc.normalize_map(raw)
    assert errs == []
    return m, sc.analyze(m)


def _checks(a):
    return [f["check"] for f in a["fails"]]


@pytest.fixture(autouse=True)
def _default_backend_no_keys(monkeypatch, tmp_path):
    for k in ("REALAI_SOTD_IMAGE_BACKEND", "REALAI_SOTD_LOCAL_SD_URL", "XAI_API_KEY", "GROK_API_KEY",
              "OPENAI_API_KEY", "REALAI_OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "realai-data"))


# ---------------------------------------------------------------- axis
def test_axis_and_pocket_mapping():
    assert sc.AXIS == "x_long"
    assert sc.POCKETS == {
        "corner_head_left": (0.0, 0.0),
        "corner_head_right": (0.0, 50.0),
        "side_left": (50.0, 0.0),
        "side_right": (50.0, 50.0),
        "corner_foot_left": (100.0, 0.0),
        "corner_foot_right": (100.0, 50.0),
    }


def test_prompt_file_saved():
    txt = sc.load_checker_prompt()
    assert "RackUp Shot of the Day checker" in txt
    assert "Image generation runs only after ok is true" in txt


# ---------------------------------------------------------------- example map
def test_travis_example_full_result():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert r["ok"] is True
    assert r["axis"] == "x_long"
    assert r["cut_deg"] == pytest.approx(53.2, abs=0.05)
    assert r["blocked_by"] is None
    assert r["tangent_side"] == "left"
    fails = [f["detail"] for f in r["fails"]]
    assert all(f["check"] == "claim" for f in r["fails"])
    assert any("stop" in d for d in fails)
    assert any("the 2" in d for d in fails)  # 2 is not on the exit side
    assert r["fixes"][-1]["fix"] == "claim_rerender"
    assert r["fixes"][-1]["from"] == EXAMPLE["claim"]
    assert r["sentence"] == (
        "Cut the 1 in the foot-right corner with center ball at medium speed and come off the tangent."
    )
    assert r["map"]["claim"] == r["sentence"]
    assert r["map"]["balls"] == [{"n": 1, "x": 62.0, "y": 14.0}, {"n": 2, "x": 78.0, "y": 36.0}]
    assert r["geometry"]["ghost"] == {"x": pytest.approx(60.367, abs=1e-3), "y": pytest.approx(12.453, abs=1e-3)}
    assert r["diagram_backend"] == "svg"
    assert r["diagram"].startswith("data:image/svg+xml;base64,")
    assert r["diagram_svg"].startswith("<svg")
    assert "diagram_error" not in r
    assert "dashed tangent" in r["diagram_prompt"] and "shooter's left" in r["diagram_prompt"]


def test_example_axis_sensitivity_foot_left_pocket():
    # If foot-right meant (100, 0) instead, the shot is a 14.5 deg cut to the right
    # and the 2 sits on the exit side.
    _, a = _analyze(_map(called={"ball": 1, "pocket": "corner_foot_left"}))
    assert a["cut_deg"] == pytest.approx(14.5, abs=0.05)
    assert a["tangent_side"] == "right"
    assert a["next_on_exit"] is True


# ---------------------------------------------------------------- 1 place
def test_place_off_cloth_and_overlap():
    _, a = _analyze(_map(cue={"x": 0.5, "y": 18}))
    assert "place" in _checks(a)
    _, a = _analyze(_map(balls=[{"n": 1, "x": 62, "y": 14}, {"n": 2, "x": 63.5, "y": 14}]))
    assert any(f["check"] == "place" and "overlap" in f["detail"] for f in a["fails"])
    _, a = _analyze(_map(balls=[{"n": 1, "x": 62, "y": 14}, {"n": 2, "x": 64.25, "y": 14}]))
    assert "place" not in _checks(a)  # exactly touching is legal
    _, a = _analyze(_map(cue={"x": 1.125, "y": 48.875}))
    assert not any(f["check"] == "place" and "off the cloth" in f["detail"] for f in a["fails"])


# ---------------------------------------------------------------- 2 called
def test_called_missing_ball_and_bad_pocket():
    _, a = _analyze(_map(called={"ball": 5, "pocket": "corner_foot_right"}))
    assert "called" in _checks(a) and "ghost" in a["skipped"]
    _, a = _analyze(_map(called={"ball": 1, "pocket": "middle_top"}))
    assert "called" in _checks(a)


def test_called_lowest_rule_rotation_only():
    _, a = _analyze(_map(called={"ball": 2, "pocket": "corner_foot_right"}))
    assert any("not the lowest" in f["detail"] for f in a["fails"])
    _, a = _analyze(_map(game="ten_ball", called={"ball": 2, "pocket": "corner_foot_right"}))
    assert any("not the lowest" in f["detail"] for f in a["fails"])
    _, a = _analyze(_map(game="eight_ball", called={"ball": 2, "pocket": "corner_foot_right"}))
    assert not any("not the lowest" in f["detail"] for f in a["fails"])


# ---------------------------------------------------------------- 3 ghost
def test_ghost_is_one_diameter_behind_object_on_pocket_line():
    _, a = _analyze(_map())
    g = a["geometry"]["_ghost"]
    O, P = (62.0, 14.0), (100.0, 50.0)
    assert math.dist(g, O) == pytest.approx(2.25)
    # collinear and on the far side from the pocket
    assert (P[0] - O[0]) * (g[1] - O[1]) - (P[1] - O[1]) * (g[0] - O[0]) == pytest.approx(0, abs=1e-9)
    assert math.dist(g, P) == pytest.approx(math.dist(O, P) + 2.25)


def test_ghost_off_cloth_fails():
    # Object ball near the foot-left corner, called into the head-right corner:
    # the ghost lands behind the foot rail.
    raw = _map(game="eight_ball", cue={"x": 50, "y": 25},
               balls=[{"n": 1, "x": 98.0, "y": 1.5}],
               called={"ball": 1, "pocket": "corner_head_right"})
    _, a = _analyze(raw)
    assert "ghost" in _checks(a)


# ---------------------------------------------------------------- 4 path
def test_path_blocked_on_cue_leg():
    raw = _map(balls=EXAMPLE["balls"] + [{"n": 3, "x": 45, "y": 15.5}])
    _, a = _analyze(raw)
    assert a["blocked_by"] == 3
    assert a["blockers"][0]["leg"] == "cue_to_ghost"


def test_path_clearance_boundary():
    # Straight-down shot: cue (50,10) -> 1 at (50,40) -> right side pocket (50,50).
    # The 2 sits beside the cue leg; 2.25 + 0.15 = 2.40 clears, 2.39 does not.
    raw = _map(game="eight_ball", cue={"x": 50, "y": 10},
               balls=[{"n": 1, "x": 50, "y": 40}, {"n": 2, "x": 52.40, "y": 25}],
               called={"ball": 1, "pocket": "side_right"})
    _, a = _analyze(raw)
    assert "path" not in _checks(a)
    raw["balls"][1]["x"] = 52.39
    _, a = _analyze(raw)
    assert "path" in _checks(a)


def test_path_blocked_on_pocket_leg():
    raw = _map(balls=EXAMPLE["balls"] + [{"n": 3, "x": 81, "y": 32}])
    _, a = _analyze(raw)
    assert any(b["leg"] == "object_to_pocket" and b["ball"] == 3 for b in a["blockers"])


# ---------------------------------------------------------------- 5 cut
def test_cut_pro_only_warning_and_illegal():
    # object at (70,30) into the foot-right corner; move the cue to change the cut
    raw = _map(game="eight_ball", balls=[{"n": 1, "x": 70, "y": 30}],
               called={"ball": 1, "pocket": "corner_foot_right"})
    for cue, lo, hi, want_warn, want_fail in [
        ({"x": 40, "y": 10}, 0, 1, False, False),
        ({"x": 46, "y": 48}, 70, 80, True, False),
        ({"x": 53, "y": 48}, 80, 90, False, True),
    ]:
        raw["cue"] = cue
        _, a = _analyze(raw)
        assert lo <= a["cut_deg"] <= hi, (cue, a["cut_deg"])
        assert bool(a["warnings"]) is want_warn, (cue, a["cut_deg"])
        assert ("cut" in _checks(a)) is want_fail, (cue, a["cut_deg"])


# ---------------------------------------------------------------- 6 tangent
def test_tangent_sides():
    _, a = _analyze(_map())
    assert a["tangent_side"] == "left"
    _, a = _analyze(_map(called={"ball": 1, "pocket": "corner_foot_left"}))
    assert a["tangent_side"] == "right"
    _, a = _analyze(_map(stroke={"tip": "follow", "speed": "medium"}))
    assert a["tangent_side"] == "forward"
    _, a = _analyze(_map(stroke={"tip": "draw", "speed": "soft"}))
    assert a["tangent_side"] == "back"
    _, a = _analyze(_map(stroke={"tip": "left", "speed": "medium"}))
    assert a["tangent_side"] == "left"  # English does not move the tangent itself
    _, a = _analyze(_map(stroke={"tip": "masse", "speed": "medium"}))
    assert "tangent" in _checks(a)


def test_tangent_perpendicular_to_pocket_line():
    _, a = _analyze(_map())
    g = a["geometry"]
    assert g["_t"][0] * g["_u"][0] + g["_t"][1] * g["_u"][1] == pytest.approx(0, abs=1e-9)


def test_straight_in_has_no_tangent():
    raw = _map(game="eight_ball", cue={"x": 60, "y": 30}, balls=[{"n": 3, "x": 80, "y": 40}],
               called={"ball": 3, "pocket": "corner_foot_right"})
    _, a = _analyze(raw)
    assert a["cut_deg"] == pytest.approx(0, abs=0.05)
    assert a["tangent_side"] == "straight"
    assert a["stop_legal"] is True


# ---------------------------------------------------------------- 7 claim
STRAIGHT = dict(game="eight_ball", cue={"x": 60, "y": 30}, balls=[{"n": 3, "x": 80, "y": 40}],
                called={"ball": 3, "pocket": "corner_foot_right"})


def _claim_fails(raw, claim):
    raw = copy.deepcopy(raw)
    raw["claim"] = claim
    _, a = _analyze(raw)
    return [f["detail"] for f in a["fails"] if f["check"] == "claim"]


def test_claim_stop_rules():
    s = _map(**STRAIGHT)
    assert _claim_fails(s, "Shoot the 3 into the foot-right corner and stop.") == []
    s_firm = copy.deepcopy(s)
    s_firm["stroke"] = {"tip": "center", "speed": "firm"}
    assert any("stop" in d for d in _claim_fails(s_firm, "Shoot the 3 and stop."))
    assert any("stop" in d for d in _claim_fails(_map(), "Cut the 1 and stop."))


def test_claim_stun_center_only():
    assert _claim_fails(_map(), "Stun the 1 into the foot-right corner.") == []
    raw = _map(stroke={"tip": "follow", "speed": "medium"})
    assert any("stun" in d for d in _claim_fails(raw, "Stun the 1."))


def test_claim_names_wrong_pocket_ball_spin_speed():
    assert any("pocket" in d for d in _claim_fails(_map(), "Cut the 1 in the foot-left corner."))
    assert any("pocket" in d for d in _claim_fails(_map(), "Cut the 1 in the side pocket."))
    assert any("not on the table" in d for d in _claim_fails(_map(), "Cut the 1 and come off for the 7."))
    assert any("English" in d for d in _claim_fails(_map(), "Cut the 1 with right english."))
    assert any("draw" in d for d in _claim_fails(_map(), "Draw the 1 into the foot-right corner."))
    assert any("speed" in d for d in _claim_fails(_map(), "Cut the 1 firmly."))
    raw = _map(stroke={"tip": "right", "speed": "medium"})
    assert _claim_fails(raw, "Cut the 1 in the foot-right corner with right english.") == []


def test_claim_next_ball_exit_side():
    raw = _map(called={"ball": 1, "pocket": "corner_foot_left"})
    assert _claim_fails(raw, "Cut the 1 in the foot-left corner and come off the tangent for the 2.") == []
    assert any("exit side" in d for d in _claim_fails(_map(), "Cut the 1 and come off the tangent for the 2."))


def test_claim_parse_ignores_table_size():
    p = sc.parse_claim("On a 9-foot table cut the 4-ball in the head-left corner, soft.")
    assert p["balls"] == [4]
    assert p["pockets"] == [{"kind": "corner", "end": "head", "side": "left"}]
    assert p["speeds"] == ["soft"]


# ---------------------------------------------------------------- fixes
def _ball_numbers(m):
    return {b["n"] for b in m["balls"]}


def test_fix_nudge_cue_open_side():
    raw = _map(balls=EXAMPLE["balls"] + [{"n": 3, "x": 45, "y": 15.5}])
    r = sc.validate_sotd(raw)
    assert r["ok"] is True
    assert r["fixes"][0]["fix"] == "nudge_cue" and r["fixes"][0]["side"] == "open"
    assert r["blocked_by"] is None
    assert _ball_numbers(r["map"]) == {1, 2, 3}


def test_fix_drop_blocking_ball_on_pocket_lane():
    raw = _map(balls=EXAMPLE["balls"] + [{"n": 3, "x": 81, "y": 32}])
    r = sc.validate_sotd(raw)
    assert r["ok"] is True
    assert r["fixes"][0] == {"fix": "drop_ball", "dropped": [3]}
    assert _ball_numbers(r["map"]) == {1, 2}


def test_fix_swap_pocket_smaller_cut():
    r = sc.validate_sotd(_map(cue={"x": 90, "y": 5}))
    assert r["ok"] is True
    fx = r["fixes"][0]
    assert fx["fix"] == "swap_pocket" and fx["from"] == "corner_foot_right"
    assert r["cut_deg"] <= sc.MAX_CUT_DEG
    assert r["map"]["called"]["pocket"] == fx["to"]


def test_fix_catalog_replacement_never_invents_balls():
    r = sc.validate_sotd(_map(called={"ball": 2, "pocket": "corner_foot_right"}))
    assert r["ok"] is True
    assert r["fixes"][0]["fix"] == "catalog_map"
    assert r["map"]["id"] == "sotd-2026-10-08"


def test_catalog_maps_all_pass():
    for entry in sc.SOTD_MAP_CATALOG:
        r = sc.validate_sotd(entry, allow_fixes=False)
        assert r["ok"] is True, entry["catalog_id"]
        assert [f for f in r["fails"]] == []


def test_unfixable_map_stays_failed_and_draws_nothing():
    calls = []
    import plugins.rackup_coach.sotd_diagram as sd

    orig = sd.render_sotd_svg
    try:
        sd.render_sotd_svg = lambda *a, **k: calls.append(1) or orig(*a, **k)
        r = sc.validate_sotd(
            _map(called={"ball": 2, "pocket": "corner_foot_right"}),
            render_diagram=True,
            save_diagram=True,
            catalog=[],
        )
    finally:
        sd.render_sotd_svg = orig
    assert r["ok"] is False
    assert r["sentence"] is None and r["diagram_prompt"] is None and r["diagram"] is None
    assert "diagram_svg" not in r and "diagram_path" not in r
    assert calls == []


def test_fixed_sentences_pass_their_own_claim_check():
    for raw in (EXAMPLE, _map(cue={"x": 90, "y": 5}), _map(**STRAIGHT)):
        r = sc.validate_sotd(raw)
        assert r["ok"] is True
        m, _ = sc.normalize_map(r["map"])
        assert [f for f in sc.analyze(m)["fails"] if f["check"] == "claim"] == []


# ---------------------------------------------------------------- diagram (local SVG)
import base64  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402

import plugins.rackup_coach.sotd_diagram as sd  # noqa: E402

SVG_NS = "{http://www.w3.org/2000/svg}"


def _svg_root(r):
    return ET.fromstring(r["diagram_svg"])


def _by_class(root, tag, cls):
    return [e for e in root.iter(SVG_NS + tag) if cls in (e.get("class") or "").split()]


def test_svg_well_formed_with_exact_balls_ghost_tangent():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    root = _svg_root(r)
    assert root.tag == SVG_NS + "svg"
    objs = [g for g in root.iter(SVG_NS + "g") if (g.get("class") or "") == "ball object"]
    cues = [g for g in root.iter(SVG_NS + "g") if (g.get("class") or "") == "ball cue"]
    assert sorted(int(g.get("data-ball")) for g in objs) == [1, 2]
    assert len(cues) == 1
    assert len(_by_class(root, "circle", "ghost")) == 1
    assert len(_by_class(root, "line", "tangent")) == 1
    assert len(_by_class(root, "line", "cue-path")) == 1
    assert len(_by_class(root, "line", "object-path")) == 1
    assert len(_by_class(root, "line", "pocket-arrow")) == 1
    pockets = [e for e in root.iter() if "pocket" in (e.get("class") or "").split()]
    assert sorted(e.get("data-pocket") for e in pockets) == sorted(sc.POCKETS)
    # cue ball unlabeled; true-scale position through the shared transform
    cue_c = cues[0].find(SVG_NS + "circle")
    assert (float(cue_c.get("cx")), float(cue_c.get("cy"))) == pytest.approx(sd._px(28, 18), abs=0.01)
    assert float(cue_c.get("r")) == pytest.approx(sd.BALL_R * sd.SCALE)
    assert cues[0].find(SVG_NS + "text") is None
    label = "".join(_by_class(root, "g", "tangent-label")[0].itertext())
    assert label == "center medium"
    # data URI decodes to the same SVG
    assert base64.b64decode(r["diagram"].split(",", 1)[1]).decode() == r["diagram_svg"]


def test_svg_called_pocket_arrow_points_at_called_pocket():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    arrow = _by_class(_svg_root(r), "line", "pocket-arrow")[0]
    x1, y1, x2, y2 = (float(arrow.get(k)) for k in ("x1", "y1", "x2", "y2"))
    px, py = sd._px(100, 50)  # corner_foot_right
    assert math.dist((x2, y2), (px, py)) < math.dist((x1, y1), (px, py))
    assert 0 <= x1 <= sd.CANVAS_W and 0 <= y1 <= sd.CANVAS_H  # inside the canvas


def _poly_center(el):
    pts = [tuple(map(float, p.split(","))) for p in el.get("points").split()]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def test_svg_diamonds_real_nine_foot_layout():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    root = _svg_root(r)
    diamonds = _by_class(root, "polygon", "diamond")
    assert len(diamonds) == 18
    by_rail = {}
    for d in diamonds:
        by_rail.setdefault(d.get("data-rail"), []).append(d)
    assert {k: len(v) for k, v in by_rail.items()} == {
        "long_left": 6, "long_right": 6, "short_head": 3, "short_foot": 3,
    }
    off = sd.DIAMOND_OFFSET_IN
    assert sd.CUSHION_IN < off < sd.RAIL_IN  # on the wood, not the cushion
    for rail, els in by_rail.items():
        for d in els:
            at = float(d.get("data-at"))
            want = {
                "long_left": (at, -off), "long_right": (at, 50 + off),
                "short_head": (-off, at), "short_foot": (100 + off, at),
            }[rail]
            got = _poly_center(d)
            assert got == pytest.approx(sd._px(*want), abs=0.5), (rail, at)
            assert (float(d.get("data-cx")), float(d.get("data-cy"))) == pytest.approx(sd._px(*want), abs=0.5)
        ats = sorted(float(d.get("data-at")) for d in els)
        if rail.startswith("long"):
            assert ats == [12.5, 25, 37.5, 62.5, 75, 87.5]
            assert 50 not in ats  # side pocket, no diamond
            # equal spacing (12.5 in = 125 px) on each side of the side pocket, 25 in across it
            xs = sorted(_poly_center(d)[0] for d in els)
            gaps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
            assert gaps == pytest.approx([125, 125, 250, 125, 125], abs=0.5)
        else:
            assert ats == [12.5, 25, 37.5]
            ys = sorted(_poly_center(d)[1] for d in els)
            assert [b - a for a, b in zip(ys, ys[1:])] == pytest.approx([125, 125], abs=0.5)
    # a ball at x=25 lines up with the x=25 diamonds
    assert sd._px(25, 10)[0] == pytest.approx(_poly_center(by_rail["long_left"][1])[0], abs=0.5)
    # no diamond at a corner
    for d in diamonds:
        assert float(d.get("data-at")) not in (0.0, 50.0, 100.0)


def test_svg_head_string_and_debug_grid():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    root = _svg_root(r)
    hs = _by_class(root, "line", "head-string")
    assert len(hs) == 1 and float(hs[0].get("x1")) == pytest.approx(sd._px(25, 0)[0])
    assert _by_class(root, "line", "debug-grid") == []
    assert _by_class(root, "line", "grid-line") == []  # show_grid is off by default
    m, _ = sc.normalize_map(r["map"])
    dbg = ET.fromstring(sd.render_sotd_svg(m, sc.analyze(m), debug_grid=True))
    assert len(_by_class(dbg, "line", "debug-grid")) == 10  # 7 x lines (incl. 50) + 3 y lines
    assert len(_by_class(dbg, "line", "debug-tick")) == 18  # one out to each diamond


def _cells_from_svg(root):
    cloth = _by_class(root, "rect", "cloth")[0]
    x0, y0 = float(cloth.get("x")), float(cloth.get("y"))
    w, h = float(cloth.get("width")), float(cloth.get("height"))
    lines = _by_class(root, "line", "grid-line")
    xs = sorted(float(e.get("x1")) for e in lines if e.get("data-axis") == "x")
    ys = sorted(float(e.get("y1")) for e in lines if e.get("data-axis") == "y")
    for e in lines:  # x lines are vertical and span the cloth; y lines horizontal
        if e.get("data-axis") == "x":
            assert float(e.get("x1")) == float(e.get("x2"))
            assert (float(e.get("y1")), float(e.get("y2"))) == pytest.approx((y0, y0 + h), abs=0.01)
        else:
            assert float(e.get("y1")) == float(e.get("y2"))
            assert (float(e.get("x1")), float(e.get("x2"))) == pytest.approx((x0, x0 + w), abs=0.01)
    bx = [x0, *xs, x0 + w]
    by = [y0, *ys, y0 + h]
    cells = [(bx[i + 1] - bx[i], by[j + 1] - by[j]) for j in range(len(by) - 1) for i in range(len(bx) - 1)]
    return (w, h, xs, ys, cells)


def test_grid_is_32_equal_squares():
    assert sd.SCALE > 0 and sd._px(1, 0)[0] - sd._px(0, 0)[0] == sd._px(0, 1)[1] - sd._px(0, 0)[1]  # one scale
    r = sc.validate_sotd(EXAMPLE, render_diagram=True, show_grid=True)
    root = _svg_root(r)
    w, h, xs, ys, cells = _cells_from_svg(root)
    assert w == pytest.approx(2 * h, abs=1e-9)  # cloth exactly 2:1 in pixels
    assert len(xs) == 7 and len(ys) == 3
    assert sd._px(50, 0)[0] in [pytest.approx(x, abs=0.01) for x in xs]  # side-pocket line is there
    assert len(cells) == 32
    cw = [c[0] for c in cells]
    ch = [c[1] for c in cells]
    assert max(cw) - min(cw) <= 0.5 and max(ch) - min(ch) <= 0.5
    for cwi, chi in cells:
        assert cwi == pytest.approx(chi, abs=0.5)  # square
        assert cwi == pytest.approx(12.5 * sd.SCALE, abs=0.5)
    # the helper agrees with the drawn grid
    helper = sd.grid_cells_px()
    assert len(helper) == 32
    assert all((c[2] - c[0]) == pytest.approx(c[3] - c[1], abs=0.5) for c in helper)
    # grid lines pass through the diamonds they belong to
    dm = {(d.get("data-rail"), float(d.get("data-at"))): d for d in _by_class(root, "polygon", "diamond")}
    for x in sd.LONG_DIAMONDS_X:
        assert _poly_center(dm[("long_left", x)])[0] == pytest.approx(sd._px(x, 0)[0], abs=0.5)
        assert sd._px(x, 0)[0] in [pytest.approx(v, abs=0.5) for v in xs]
    for y in sd.SHORT_DIAMONDS_Y:
        assert _poly_center(dm[("short_head", y)])[1] == pytest.approx(sd._px(0, y)[1], abs=0.5)
        assert sd._px(0, y)[1] in [pytest.approx(v, abs=0.5) for v in ys]
    # no diamond on the x = 50 line
    assert ("long_left", 50.0) not in dm and ("long_right", 50.0) not in dm


def test_show_grid_through_payload():
    res = sc.run_validate(None, {"map": copy.deepcopy(EXAMPLE), "render_diagram": True, "show_grid": True})
    root = ET.fromstring(res["diagram_svg"])
    assert len(_by_class(root, "line", "grid-line")) == 10
    assert _by_class(root, "line", "debug-grid") == []
    res = sc.run_validate(None, {"map": copy.deepcopy(EXAMPLE), "render_diagram": True})
    assert _by_class(ET.fromstring(res["diagram_svg"]), "line", "grid-line") == []


def test_pocket_arrow_inside_image_for_every_pocket():
    marker_px = 4 * 4.0  # markerWidth x stroke-width
    for pid, (X, Y) in sc.POCKETS.items():
        ball_n = 1
        m, _ = sc.normalize_map(EXAMPLE)
        a = sc.analyze(m, check_claim=False)
        m = copy.deepcopy(m)
        m["called"] = {"ball": ball_n, "pocket": pid}
        a = sc.analyze(m, check_claim=False)
        root = ET.fromstring(sd.render_sotd_svg(m, a))
        arrow = _by_class(root, "line", "pocket-arrow")[0]
        x1, y1, x2, y2 = (float(arrow.get(k)) for k in ("x1", "y1", "x2", "y2"))
        pad = sd.POCKET_ARROW_HALO_PX / 2 + 2
        for x, y in ((x1, y1), (x2, y2)):
            assert pad <= x <= sd.CANVAS_W - pad and pad <= y <= sd.CANVAS_H - pad, pid
        # tail sits outside the cushion (rail / margin), tip stops short of the cloth
        cx0, cy0 = sd._px(-sd.CUSHION_IN, -sd.CUSHION_IN)
        cx1, cy1 = sd._px(100 + sd.CUSHION_IN, 50 + sd.CUSHION_IN)
        assert not (cx0 < x1 < cx1 and cy0 < y1 < cy1), pid
        sx0, sy0 = sd._px(0, 0)
        sx1, sy1 = sd._px(100, 50)
        assert not (sx0 < x2 < sx1 and sy0 < y2 < sy1), pid
        # tip points at the pocket and does not run into the hole
        px, py = sd._px(X, Y)
        assert math.dist((x2, y2), (px, py)) < math.dist((x1, y1), (px, py))
        assert math.dist((x1, y1), (x2, y2)) > marker_px  # a visible shaft behind the head


def test_pockets_round_and_symmetric():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    root = _svg_root(r)
    groups = {g.get("data-pocket"): g for g in root.iter(SVG_NS + "g") if "pocket" in (g.get("class") or "").split()}
    assert sorted(groups) == sorted(sc.POCKETS)
    for pid, g in groups.items():
        X, Y = sc.POCKETS[pid]
        px, py = sd._px(X, Y)
        hole = [e for e in g.iter(SVG_NS + "circle") if e.get("class") == "pocket-hole"]
        assert len(hole) == 1  # one round hole, no teardrop path
        hx, hy, hr = (float(hole[0].get(k)) for k in ("cx", "cy", "r"))
        jaws = [e for e in g.iter(SVG_NS + "line") if e.get("class") == "jaw"]
        assert len(jaws) == 2
        if pid.startswith("corner"):
            assert abs(hx - px) == pytest.approx(abs(hy - py), abs=0.01)  # on the diagonal
            assert (hx, hy) == pytest.approx((px, py), abs=0.01)  # centered on the grid corner
        else:
            assert (hx, hy) == pytest.approx((px, py), abs=0.01)  # centered on the nose midpoint
        # jaw backs land on the hole; jaws mirror each other about the pocket axis
        for j in jaws:
            bx, by = float(j.get("x2")), float(j.get("y2"))
            assert math.dist((bx, by), (hx, hy)) == pytest.approx(hr, abs=0.05)
        (a1, b1), (a2, b2) = [((float(j.get("x1")), float(j.get("y1"))), (float(j.get("x2")), float(j.get("y2")))) for j in jaws]
        assert math.dist(a1, b1) == pytest.approx(math.dist(a2, b2), abs=0.01)
        assert math.dist(a1, (hx, hy)) == pytest.approx(math.dist(a2, (hx, hy)), abs=0.01)


def test_object_path_uses_object_ball_color():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    line = _by_class(_svg_root(r), "line", "object-path")[0]
    assert line.get("stroke") == sd.BALL_HEX[1]


def test_svg_follow_draw_and_straight():
    r = sc.validate_sotd(_map(stroke={"tip": "follow", "speed": "soft"}), render_diagram=True)
    root = _svg_root(r)
    assert len(_by_class(root, "line", "spin-forward")) == 1
    r = sc.validate_sotd(_map(stroke={"tip": "draw", "speed": "firm"}), render_diagram=True)
    assert len(_by_class(_svg_root(r), "line", "spin-back")) == 1
    r = sc.validate_sotd(_map(**STRAIGHT), render_diagram=True)
    root = _svg_root(r)
    assert _by_class(root, "line", "tangent") == []
    assert len(_by_class(root, "circle", "ghost")) == 1
    # straight-in center hit: a stop bar at the ghost and a leader to the label
    stop = _by_class(root, "line", "spin-stop")
    assert len(stop) == 1
    x1, y1, x2, y2 = (float(stop[0].get(k)) for k in ("x1", "y1", "x2", "y2"))
    g = r["geometry"]["ghost"]
    gx, gy = sd._px(g["x"], g["y"])
    assert ((x1 + x2) / 2, (y1 + y2) / 2) == pytest.approx((gx, gy), abs=0.6)
    assert math.dist((x1, y1), (x2, y2)) > 2 * sd.BALL_R * sd.SCALE  # wider than the ball
    assert len(_by_class(root, "line", "label-leader")) == 1
    # straight-in with follow still gets its arrow (and the leader), no stop bar
    r = sc.validate_sotd(_map(**STRAIGHT, stroke={"tip": "follow", "speed": "soft"}), render_diagram=True)
    root = _svg_root(r)
    assert len(_by_class(root, "line", "spin-forward")) == 1 and _by_class(root, "line", "spin-stop") == []
    assert len(_by_class(root, "line", "label-leader")) == 1
    # a cut shot has a tangent and no leader
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert _by_class(_svg_root(r), "line", "label-leader") == []


def test_svg_stripes_and_ids_unique_and_escaped():
    raw = _map(game="eight_ball", id='x"<b>&', balls=[{"n": 3, "x": 62, "y": 14}, {"n": 11, "x": 78, "y": 36}],
               called={"ball": 3, "pocket": "corner_foot_right"})
    r = sc.validate_sotd(raw, render_diagram=True)
    root = _svg_root(r)  # parses despite the hostile id
    assert root.find(SVG_NS + "title").text == 'x"<b>&'
    clips = list(root.iter(SVG_NS + "clipPath"))
    assert len(clips) == 1 and clips[0].get("id").endswith("clip-ball-11")


def test_no_diagram_when_render_flag_off():
    r = sc.validate_sotd(EXAMPLE)
    assert r["ok"] is True and r["diagram"] is None and "diagram_svg" not in r
    assert r["diagram_prompt"]  # kept for a future local image model


def test_backend_default_svg_and_others(monkeypatch):
    assert sc.resolve_diagram_backend() == "svg"
    monkeypatch.setenv("REALAI_SOTD_IMAGE_BACKEND", "xai")  # not supported -> local svg
    assert sc.resolve_diagram_backend() == "svg"
    monkeypatch.setenv("REALAI_SOTD_IMAGE_BACKEND", "none")
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert r["ok"] is True and r["diagram"] is None and "none" in r["diagram_error"]
    monkeypatch.setenv("REALAI_SOTD_IMAGE_BACKEND", "local_sd")
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert r["diagram_svg"] and "not set" in r["diagram_error"]
    monkeypatch.setenv("REALAI_SOTD_LOCAL_SD_URL", "https://api.example.com/sd")
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert "loopback" in r["diagram_error"] and r["diagram_svg"]
    monkeypatch.setenv("REALAI_SOTD_LOCAL_SD_URL", "http://127.0.0.1:7860")
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert "stub" in r["diagram_error"] and r["diagram_svg"]


def test_render_failure_never_fails_passed_map(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("renderer down")

    monkeypatch.setattr(sd, "render_sotd_svg", boom)
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert r["ok"] is True and r["diagram"] is None
    assert "renderer down" in r["diagram_error"]


def test_save_diagram_to_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path))
    raw = copy.deepcopy(EXAMPLE)
    raw["id"] = "../../etc/sotd 2026"
    r = sc.validate_sotd(raw, render_diagram=True, save_diagram=True)
    p = Path(r["diagram_path"])
    assert p.parent == tmp_path / "rackup_coach" / "sotd"
    assert p.name == "_.._etc_sotd_2026.svg"
    assert p.read_text(encoding="utf-8") == r["diagram_svg"]


def test_sotd_code_has_no_cloud_image_path():
    root = Path(sc.__file__).resolve().parent
    for name in ("sotd_checker.py", "sotd_diagram.py", "abilities/shot_of_the_day.py"):
        src = (root / name).read_text(encoding="utf-8").lower()
        for needle in ("xai_media", "xai_api_key", "grok_api_key", "api.x.ai", "openai"):
            assert needle not in src, (name, needle)


# ---------------------------------------------------------------- envelope
ENVELOPE = {
    "ability": "shot_of_the_day",
    "goal": "validate sotd map, then render copy and diagram",
    "organs_enabled": False,
    "player": {"discipline": "nine_ball"},
    "payload": {"mode": "sotd_validate", "render_diagram": True, "map": EXAMPLE},
}


def test_envelope_through_plugin_invoke():
    out = invoke(copy.deepcopy(ENVELOPE))
    assert out["ok"] is True and out["error"] is None
    res = out["result"]
    assert res["mode"] == "sotd_validate"
    assert res["ok"] is True
    assert res["cut_deg"] == pytest.approx(53.2, abs=0.05)
    assert res["diagram_backend"] == "svg" and res["diagram_svg"].startswith("<svg")


def test_failed_map_is_http_style_not_crash():
    env = copy.deepcopy(ENVELOPE)
    env["payload"]["map"] = {"id": "x", "game": "nine_ball", "cue": {"x": "nope"}}
    out = invoke(env)
    assert out["ok"] is True  # plugin ran fine
    # input fail is listed; with a known game the only allowed repair is a catalog map
    assert any(f["check"] == "input" for f in out["result"]["fails"])
    assert [f["fix"] for f in out["result"]["fixes"]][0] == "catalog_map"
    env["payload"]["map"] = {"id": "x", "cue": {"x": "nope"}}
    env["player"] = {"discipline": "one_pocket"}
    out = invoke(env)
    assert out["ok"] is True and out["result"]["ok"] is False
    assert out["result"]["sentence"] is None and out["result"]["diagram"] is None
    env["payload"]["map"] = None
    out = invoke(env)
    assert out["result"]["ok"] is False


def test_other_sotd_modes_unchanged():
    out = invoke({"ability": "shot_of_the_day", "organs_enabled": False,
                  "player": {"player_id": "p1", "discipline": "nine_ball"}, "payload": {}})
    assert out["ok"] is True
    assert "primary" in out["result"] and "cut_deg" not in out["result"]


def test_hive_tools_execute_rackup_invoke_passes_mode():
    """Local hive (:8001) path RackUp falls back to: tools/execute rackup_invoke."""
    from realai.orchestration.v3_orchestrator import _run_tool

    env = copy.deepcopy(ENVELOPE)
    env["payload"] = {"prefer_local": False, "allow_cloud_llm": True, **env["payload"]}
    out = _run_tool("rackup_invoke", env)
    assert out["ok"] is True
    assert out["result"]["mode"] == "sotd_validate"
    assert out["result"]["tangent_side"] == "left"


def test_cloth_rect_is_the_grid_rect_and_pockets_on_grid_points():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True, show_grid=True)
    root = _svg_root(r)
    x0, y0 = sd._px(0, 0)
    x1, y1 = sd._px(100, 50)
    cloth = _by_class(root, "rect", "cloth")
    assert len(cloth) == 1
    c = cloth[0]
    got = tuple(float(c.get(k)) for k in ("x", "y", "width", "height"))
    assert got == pytest.approx((x0, y0, 1000.0, 500.0), abs=1e-9)
    assert (x1 - x0, y1 - y0) == pytest.approx((1000.0, 500.0))
    assert c.get("stroke") in (None, "none")  # nothing spills past the playing edge
    # the grid boundary (cushion nose) is drawn exactly on the cloth rect
    gb = _by_class(root, "rect", "grid-boundary")
    assert len(gb) == 1
    assert tuple(float(gb[0].get(k)) for k in ("x", "y", "width", "height")) == pytest.approx(got, abs=1e-9)
    # the grid's outer cells end exactly at the cloth edges
    cells = sd.grid_cells_px()
    assert min(cl[0] for cl in cells) == pytest.approx(x0) and max(cl[2] for cl in cells) == pytest.approx(x1)
    assert min(cl[1] for cl in cells) == pytest.approx(y0) and max(cl[3] for cl in cells) == pytest.approx(y1)
    # pocket centers are the grid corners and long-edge midpoints
    want = {
        "corner_head_left": (x0, y0), "corner_head_right": (x0, y1),
        "side_left": ((x0 + x1) / 2, y0), "side_right": ((x0 + x1) / 2, y1),
        "corner_foot_left": (x1, y0), "corner_foot_right": (x1, y1),
    }
    groups = {g.get("data-pocket"): g for g in root.iter(SVG_NS + "g") if "pocket" in (g.get("class") or "").split()}
    corners = {(cl[i], cl[j]) for cl in cells for i in (0, 2) for j in (1, 3)}
    for pid, (wx, wy) in want.items():
        g = groups[pid]
        assert (float(g.get("data-cx")), float(g.get("data-cy"))) == pytest.approx((wx, wy), abs=1e-9)
        assert any(math.dist((wx, wy), q) < 1e-6 for q in corners)  # a grid corner
        # jaw noses sit on the playing edge, symmetric about the pocket point
        jaws = [e for e in g.iter(SVG_NS + "line") if e.get("class") == "jaw"]
        noses = [(float(j.get("x1")), float(j.get("y1"))) for j in jaws]
        for nx, ny in noses:
            on_edge = abs(nx - x0) < 1e-6 or abs(nx - x1) < 1e-6 or abs(ny - y0) < 1e-6 or abs(ny - y1) < 1e-6
            assert on_edge, pid
        assert math.dist(noses[0], (wx, wy)) == pytest.approx(math.dist(noses[1], (wx, wy)), abs=1e-6)
    # cushions AND pockets under the cloth, so no hole intrudes on the playing surface
    order = list(root.iter())
    ci = order.index(c)
    assert all(order.index(g) < ci for g in groups.values())
    assert all(order.index(e) < ci for e in _by_class(root, "polygon", "cushion"))


def test_cushions_sit_outside_the_playing_rect():
    root = _svg_root(sc.validate_sotd(EXAMPLE, render_diagram=True))
    x0, y0 = sd._px(0, 0)
    x1, y1 = sd._px(100, 50)
    cushions = _by_class(root, "polygon", "cushion")
    assert len(cushions) == 6
    for cu in cushions:
        assert cu.get("fill", "").startswith("url(#") and "cush-" in cu.get("fill")  # its own bevel, not cloth
        pts = [tuple(map(float, q.split(","))) for q in cu.get("points").split()]
        for x, y in pts:  # every vertex on or outside the playing rect
            inside = (x0 + 1e-6 < x < x1 - 1e-6) and (y0 + 1e-6 < y < y1 - 1e-6)
            assert not inside
        on_edge = [q for q in pts if abs(q[0] - x0) < 1e-6 or abs(q[0] - x1) < 1e-6
                   or abs(q[1] - y0) < 1e-6 or abs(q[1] - y1) < 1e-6]
        assert len(on_edge) >= 2  # the nose edge is the playing edge
        depth = max(max(x0 - x, x - x1, y0 - y, y - y1, 0.0) for x, y in pts)  # how far out it reaches
        assert depth == pytest.approx(sd.CUSHION_IN * sd.SCALE, abs=1e-6)
    assert len(_by_class(root, "line", "cushion-nose")) == 6  # nose highlight on each cushion


def test_diamonds_line_up_with_grid_lines_through_the_cushion():
    m, _ = sc.normalize_map(EXAMPLE)
    root = ET.fromstring(sd.render_sotd_svg(m, sc.analyze(m), debug_grid=True))
    ticks = _by_class(root, "line", "debug-tick")
    grid = _by_class(root, "line", "grid-line")
    for d in _by_class(root, "polygon", "diamond"):
        cx, cy = _poly_center(d)
        rail = d.get("data-rail")
        if rail.startswith("long"):
            gl = [e for e in grid if e.get("data-axis") == "x" and abs(float(e.get("x1")) - cx) < 0.5]
            tk = [e for e in ticks if abs(float(e.get("x1")) - cx) < 0.5 and float(e.get("x1")) == float(e.get("x2"))
                  and min(float(e.get("y1")), float(e.get("y2"))) - 0.5 <= cy <= max(float(e.get("y1")), float(e.get("y2"))) + 0.5]
        else:
            gl = [e for e in grid if e.get("data-axis") == "y" and abs(float(e.get("y1")) - cy) < 0.5]
            tk = [e for e in ticks if abs(float(e.get("y1")) - cy) < 0.5 and float(e.get("y1")) == float(e.get("y2"))
                  and min(float(e.get("x1")), float(e.get("x2"))) - 0.5 <= cx <= max(float(e.get("x1")), float(e.get("x2"))) + 0.5]
        assert len(gl) == 1, (rail, d.get("data-at"))  # its grid line on the cloth
        assert len(tk) == 1, (rail, d.get("data-at"))  # extended through the cushion to the diamond
    # diamonds every 12.5 in along each rail, on the wood centerline, none at a pocket
    for dm in sd.diamond_positions():
        assert dm["at"] % 12.5 == 0 and dm["at"] not in (0.0, 50.0, 100.0)
        off = dm["y"] if dm["rail"] == "long_left" else dm["x"] if dm["rail"] == "short_head" else None
        if off is not None:
            assert off == pytest.approx(-(sd.CUSHION_IN + sd.WOOD_IN / 2))


def test_diamond_to_pocket_spacing_equals_diamond_spacing_on_every_rail():
    """Along each rail centerline, end diamond -> pocket center (corner or side)
    must equal diamond -> diamond (125 px) within 1 px, so no box looks bigger."""
    root = _svg_root(sc.validate_sotd(EXAMPLE, render_diagram=True))
    holes = {}
    for g in root.iter(SVG_NS + "g"):
        if "pocket" in (g.get("class") or "").split():
            c = [e for e in g.iter(SVG_NS + "circle") if e.get("class") == "pocket-hole"][0]
            holes[g.get("data-pocket")] = (float(c.get("cx")), float(c.get("cy")), float(c.get("r")))
    # one hole size everywhere, so corner and side mouths bite the cloth equally
    assert len({round(h[2], 6) for h in holes.values()}) == 1
    step = 12.5 * sd.SCALE
    rails = {
        "long_left": (0, ["corner_head_left", "side_left", "corner_foot_left"]),
        "long_right": (0, ["corner_head_right", "side_right", "corner_foot_right"]),
        "short_head": (1, ["corner_head_left", "corner_head_right"]),
        "short_foot": (1, ["corner_foot_left", "corner_foot_right"]),
    }
    diamonds = _by_class(root, "polygon", "diamond")
    for rail, (ax, pids) in rails.items():
        seq = sorted([("D", _poly_center(d)[ax]) for d in diamonds if d.get("data-rail") == rail]
                     + [("P", holes[p][ax]) for p in pids], key=lambda t: t[1])
        assert seq[0][0] == "P" and seq[-1][0] == "P"  # a pocket at each end of every rail
        gaps = [b[1] - a[1] for a, b in zip(seq, seq[1:])]
        assert len(gaps) == (8 if ax == 0 else 4)
        for gp in gaps:
            assert gp == pytest.approx(step, abs=1.0), (rail, gaps)
    # pocket centers stay on the table-coordinate pocket points (cloth corners / edge midpoints)
    for pid, (X, Y) in sc.POCKETS.items():
        assert holes[pid][:2] == pytest.approx(sd._px(X, Y), abs=1e-6)


def test_pockets_set_in_the_rail_and_cloth_intact():
    """Pocket holes, throats and jaws are all drawn before the (opaque) cloth,
    so every one of the 32 grid cells is a full, unbroken 125 x 125 px square;
    the object-ball line ends at the pocket point on the cloth edge."""
    r = sc.validate_sotd(EXAMPLE, render_diagram=True, show_grid=True)
    root = _svg_root(r)
    order = list(root.iter())
    cloth = _by_class(root, "rect", "cloth")[0]
    ci = order.index(cloth)
    assert cloth.get("fill-opacity") in (None, "1") and cloth.get("opacity") in (None, "1")
    pocket_parts = [e for e in root.iter() if (e.get("class") or "").split()
                    and {"pocket", "pocket-hole", "pocket-shelf", "jaw"} & set((e.get("class") or "").split())]
    assert len(pocket_parts) == 6 * 5  # group + shelf + hole + 2 jaws, per pocket
    assert all(order.index(e) < ci for e in pocket_parts)
    w, h, xs, ys, cells = _cells_from_svg(root)
    assert len(cells) == 32
    for cw, ch in cells:
        assert cw == pytest.approx(125.0, abs=0.01) and ch == pytest.approx(125.0, abs=0.01)
    # nothing black drawn after the cloth except balls/lines: no pocket fill sits on a cell
    for e in order[ci + 1:]:
        assert e.get("fill") != sd.POCKET
    # hole centers are the cloth corners / long-edge midpoints, equal radii
    holes = [e for e in root.iter(SVG_NS + "circle") if e.get("class") == "pocket-hole"]
    assert len({e.get("r") for e in holes}) == 1
    centers = sorted((float(e.get("cx")), float(e.get("cy"))) for e in holes)
    want = sorted(sd._px(*p) for p in sc.POCKETS.values())
    assert centers == pytest.approx(want, abs=1e-6)
    assert sorted(sc.POCKETS.values()) == sorted([(0.0, 0.0), (50.0, 0.0), (100.0, 0.0), (0.0, 50.0), (50.0, 50.0), (100.0, 50.0)])
    assert sc.POCKET_MOUTHS is sc.POCKETS
    # the object-ball line ends at the pocket point on the cloth edge
    line = _by_class(root, "line", "object-path")[0]
    assert (float(line.get("x2")), float(line.get("y2"))) == pytest.approx(sd._px(100, 50), abs=0.01)
    # prompt file is the verbatim standing instruction again
    assert "grid rule" not in sc.PROMPT_PATH.read_text(encoding="utf-8")
