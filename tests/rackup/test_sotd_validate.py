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
def _no_image_backend(monkeypatch):
    monkeypatch.delenv("REALAI_SOTD_IMAGE_BACKEND", raising=False)


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
    assert r["diagram"] is None
    assert "no image backend" in r["diagram_error"]
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
    r = sc.validate_sotd(
        _map(called={"ball": 2, "pocket": "corner_foot_right"}),
        render_diagram=True,
        image_fn=lambda p: calls.append(p) or "http://img",
        catalog=[],
    )
    assert r["ok"] is False
    assert r["sentence"] is None and r["diagram_prompt"] is None and r["diagram"] is None
    assert calls == []


def test_fixed_sentences_pass_their_own_claim_check():
    for raw in (EXAMPLE, _map(cue={"x": 90, "y": 5}), _map(**STRAIGHT)):
        r = sc.validate_sotd(raw)
        assert r["ok"] is True
        m, _ = sc.normalize_map(r["map"])
        assert [f for f in sc.analyze(m)["fails"] if f["check"] == "claim"] == []


# ---------------------------------------------------------------- diagram
def test_image_fn_called_only_after_pass_and_failure_is_soft():
    r = sc.validate_sotd(EXAMPLE, render_diagram=True, image_fn=lambda p: "https://img.example/sotd.png")
    assert r["ok"] is True and r["diagram"] == "https://img.example/sotd.png"
    assert "diagram_error" not in r

    def boom(_p):
        raise RuntimeError("backend down")

    r = sc.validate_sotd(EXAMPLE, render_diagram=True, image_fn=boom)
    assert r["ok"] is True and r["diagram"] is None
    assert "backend down" in r["diagram_error"]


def test_diagram_prompt_only_uses_map_balls():
    r = sc.validate_sotd(EXAMPLE)
    dp = r["diagram_prompt"]
    assert "1 ball: solid yellow" in dp and "2 ball: solid blue" in dp
    assert "3 ball" not in dp
    assert "62.0% across, 28.0% down" in dp  # (62,14) -> x/100, y/50
    assert "cue ball: plain white, unlabeled, at 28.0% across, 36.0% down" in dp
    assert "no people, no cue stick, no room" in dp


def test_unknown_backend_reports_error(monkeypatch):
    monkeypatch.setenv("REALAI_SOTD_IMAGE_BACKEND", "dalle9000")
    r = sc.validate_sotd(EXAMPLE, render_diagram=True)
    assert r["ok"] is True and r["diagram"] is None
    assert "unknown" in r["diagram_error"]


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
