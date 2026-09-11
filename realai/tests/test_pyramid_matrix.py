"""Integration tests: full RackUp Pyramid matrix (4 skills × 2 tables)."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from plugins.rackup_coach import invoke
from plugins.rackup_coach.pyramid import POINTS_TO_WIN, RACK_SIZE, CALL_SHOT, RATING_WEIGHT


SKILLS = ("beginner", "intermediate", "advanced", "pro")
TABLES = ("7ft", "9ft")


def _player(skill: str, table: str, rating: float = 500.0) -> dict:
    return {
        "player_id": f"test-{skill}-{table}",
        "rating": rating,
        "discipline": "pyramid",
        "table_size": table,
        "skill_level": skill,
        "weaknesses": ["pattern_play", "cue_ball_control"],
        "strengths": ["long_potting"],
    }


@pytest.mark.parametrize("skill", SKILLS)
@pytest.mark.parametrize("table", TABLES)
def test_pyramid_rules_matrix(skill: str, table: str):
    r = invoke({
        "ability": "pyramid_rules",
        "player": _player(skill, table),
        "payload": {"game": "pyramid"},
        "organs_enabled": False,
    })
    assert r["ok"] is True, r
    cfg = r["result"]["config"]
    assert cfg["rack_size"] == RACK_SIZE[table]
    assert cfg["points_to_win"] == POINTS_TO_WIN[skill][table]
    assert cfg["call_shot"] == CALL_SHOT[skill]
    assert cfg["rating_weight"] == RATING_WEIGHT[skill]
    assert cfg["one_ball_value"] == 11
    assert cfg["cue_ball"] == "designated_only"


@pytest.mark.parametrize("skill", SKILLS)
@pytest.mark.parametrize("table", TABLES)
def test_shot_of_the_day_pyramid(skill: str, table: str):
    r = invoke({
        "ability": "shot_of_the_day",
        "player": _player(skill, table, rating=550),
        "payload": {"game": "pyramid", "shown_shot_ids": []},
        "organs_enabled": False,
    })
    assert r["ok"] is True, r
    res = r["result"]
    assert res["primary"]["id"]
    assert res["primary"].get("why_helps_regular_play") or res["primary"].get("why_this_shot")
    assert res["primary"].get("not_a_trick_shot") is True
    assert res.get("pyramid")
    assert res["pyramid"]["rack_size"] == RACK_SIZE[table]
    assert res["pyramid"]["points_to_win"] == POINTS_TO_WIN[skill][table]


@pytest.mark.parametrize("skill", SKILLS)
@pytest.mark.parametrize("table", TABLES)
def test_coach_pyramid(skill: str, table: str):
    r = invoke({
        "ability": "pyramid",
        "player": _player(skill, table, rating=800 if skill != "beginner" else 300),
        "payload": {"mode": "pyramid", "game": "pyramid"},
        "organs_enabled": False,
    })
    assert r["ok"] is True, r
    res = r["result"]
    assert res["pyramid"]["points_to_win"] == POINTS_TO_WIN[skill][table]
    assert res["pyramid"]["call_shot"] == CALL_SHOT[skill]
    assert res["practice_plan"]["blocks"]
    assert res.get("classical_mindset")


@pytest.mark.parametrize("skill", SKILLS)
@pytest.mark.parametrize("table", TABLES)
def test_matchmaking_pyramid_weights(skill: str, table: str):
    r = invoke({
        "ability": "matchmaking",
        "player": _player(skill, table, rating=700),
        "payload": {
            "game": "pyramid",
            "candidates": [
                {
                    "player_id": "same",
                    "rating": 705,
                    "table_size": table,
                    "skill_level": skill,
                },
                {
                    "player_id": "other",
                    "rating": 705,
                    "table_size": "7ft" if table == "9ft" else "9ft",
                    "skill_level": "beginner",
                },
            ],
        },
        "organs_enabled": False,
    })
    assert r["ok"] is True, r
    res = r["result"]
    assert res["policy"]["rating_weight"] == RATING_WEIGHT[skill]
    assert res["policy"]["points_to_win"] == POINTS_TO_WIN[skill][table]
    assert res["best"]["player_id"] == "same"


@pytest.mark.parametrize("skill", SKILLS)
@pytest.mark.parametrize("table", TABLES)
def test_rating_intel_pyramid(skill: str, table: str):
    r = invoke({
        "ability": "rating_intel",
        "player": _player(skill, table, rating=720),
        "payload": {
            "game": "pyramid",
            "rating_history": [{"rating": 700}, {"rating": 710}, {"rating": 720}],
        },
        "organs_enabled": False,
    })
    assert r["ok"] is True, r
    assert r["result"]["rating_weight"] == RATING_WEIGHT[skill]
    assert r["result"]["pyramid"]["rack_size"] == RACK_SIZE[table]


def test_moderation_smoke():
    r = invoke({
        "ability": "moderation",
        "player": {"player_id": "m1", "rating": 500},
        "payload": {"text": "you sandbagging hustler"},
        "organs_enabled": False,
    })
    assert r["ok"] is True
    assert r["result"]["severity"] >= 2
    assert r["result"]["action"]


def test_coach_basic_smoke():
    r = invoke({
        "ability": "coach",
        "player": {
            "player_id": "c1",
            "rating": 320,
            "weaknesses": ["stance"],
            "discipline": "eight_ball",
        },
        "payload": {"mode": "full"},
        "organs_enabled": False,
    })
    assert r["ok"] is True
    assert r["result"]["band"] == "beginner"
    assert r["result"]["practice_plan"]["blocks"]


def test_league_validate_and_rating_update():
    v = invoke({
        "ability": "league_validate",
        "player": _player("pro", "9ft", 900),
        "payload": {"game": "pyramid", "my_score": 71, "opp_score": 40},
        "organs_enabled": False,
    })
    assert v["result"]["valid"] is True
    assert v["result"]["normalized"]["points_to_win"] == 71

    ru = invoke({
        "ability": "rating_update",
        "player": _player("intermediate", "7ft", 640),
        "payload": {
            "game": "pyramid",
            "opponent_rating": 650,
            "won": True,
            "skill_level": "intermediate",
            "table_size": "7ft",
        },
        "organs_enabled": False,
    })
    assert ru["ok"] is True
    assert ru["result"]["rating_after"] > 640
    assert ru["result"]["input"]["rating_weight"] == 0.85
