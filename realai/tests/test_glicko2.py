"""ROC Glicko-2 singles ladder tests."""
from __future__ import annotations

from plugins.rackup_coach import invoke
from plugins.rackup_coach.glicko2 import (
    DEFAULT_RD,
    DEFAULT_RATING,
    DEFAULT_VOL,
    MIN_RD,
    PlayerRating,
    apply_match,
    band_for,
    seed_from_external,
    update_glicko2,
)


def test_defaults_and_bands():
    p = PlayerRating()
    assert p.rating == DEFAULT_RATING
    assert p.rd == DEFAULT_RD
    assert abs(p.volatility - DEFAULT_VOL) < 1e-9
    assert band_for(312) == "Novice"
    assert band_for(450) == "Intermediate"
    assert band_for(547) == "Advanced"
    assert band_for(640) == "Expert"
    assert band_for(700) == "Elite"
    assert p.display == "Advanced • 500"


def test_update_increases_on_upset_win():
    low = PlayerRating(rating=500, rd=175, volatility=0.06)
    high = PlayerRating(rating=600, rd=100, volatility=0.06)
    after = update_glicko2(low, opp_rating=high.rating, opp_rd=high.rd, score=1.0)
    assert after.rating > low.rating
    assert after.rd >= MIN_RD


def test_apply_match_both_sides():
    w = PlayerRating(rating=547, rd=80, volatility=0.06, player_id="w")
    l = PlayerRating(rating=560, rd=90, volatility=0.06, player_id="l")
    res = apply_match(w, l)
    assert res["algorithm"] == "glicko2_v1"
    assert res["winner_after"]["rating"] > w.rating or res["deltas"]["winner_rating"] != 0
    assert res["loser_after"]["rating"] < l.rating or res["deltas"]["loser_rating"] != 0
    assert "display" in res


def test_seed_from_external_high_rd_low_conf():
    high = seed_from_external(520, confidence=0.9, from_system="fargo")
    low = seed_from_external(520, confidence=0.4, from_system="apa")
    assert low["rd"] > high["rd"]
    assert low["rd"] >= DEFAULT_RD or low["rd"] >= 150
    assert low["seed"]["band"] == "Advanced"


def test_rating_update_ability():
    r = invoke(
        {
            "ability": "rating_update",
            "player": {
                "player_id": "u1",
                "rating": 547,
                "rd": 80,
                "volatility": 0.06,
                "discipline": "nine_ball",
            },
            "payload": {
                "opponent_rating": 560,
                "opponent_rd": 90,
                "won": True,
                "format": "SINGLES",
                "game_style": "nine_ball",
                "session_id": "ses1",
            },
            "organs_enabled": False,
        }
    )
    assert r["ok"]
    res = r["result"]
    assert res["algorithm"] == "glicko2_v1"
    assert res["ladder"] == "roc_glicko2"
    assert "winner_after" in res and "loser_after" in res
    assert res["rating_after"] > 547
    assert res["rd_after"] >= MIN_RD
    assert res["persist_hint"]["fields_to_write"] == [
        "rating",
        "rd",
        "volatility",
        "rating_updated_at",
        "last_match_delta",
    ]


def test_rating_convert_seed():
    r = invoke(
        {
            "ability": "rating_convert",
            "player": {"player_id": "p", "matches_played_rackup": 0},
            "payload": {"from_system": "apa", "from_value": 4, "from_scale": "skill_1_9"},
            "organs_enabled": False,
        }
    )
    assert r["ok"]
    res = r["result"]
    assert res["rackup_rating_estimate"] == 520
    assert res["glicko2_seed"]["rd"] >= 120
    assert res["seed_hint"]["write_once"]["rd"] == res["glicko2_seed"]["rd"]
    assert res["ladder"] == "roc_glicko2"


def test_matchmaking_uses_rd():
    r = invoke(
        {
            "ability": "matchmaking",
            "player": {"player_id": "p", "rating": 547, "rd": 160},
            "payload": {
                "candidates": [
                    {"player_id": "a", "rating": 580, "rd": 50},
                    {"player_id": "b", "league_ratings": {"apa": 4}, "primary_rating_system": "apa"},
                ]
            },
            "organs_enabled": False,
        }
    )
    assert r["ok"]
    assert r["result"]["ladder"] == "roc_glicko2"
    assert r["result"]["player_rd"] == 160
    assert r["result"]["policy"]["uses_rd_uncertainty"] is True
    for c in r["result"]["ranked_candidates"]:
        assert "rd" in c


def test_rating_intel_glicko():
    r = invoke(
        {
            "ability": "rating_intel",
            "player": {"player_id": "p", "rating": 547, "rd": 175, "volatility": 0.06},
            "payload": {
                "rating_history": [
                    {"rating": 520, "rd": 175},
                    {"rating": 535, "rd": 120},
                    {"rating": 547, "rd": 90},
                ]
            },
            "organs_enabled": False,
        }
    )
    assert r["ok"]
    assert r["result"]["algorithm"] == "glicko2_v1"
    assert r["result"]["band_label"] == "Advanced"
    assert "uncertainty" in r["result"]


def test_pyramid_still_validates():
    r = invoke(
        {
            "ability": "league_validate",
            "player": {
                "player_id": "p",
                "rating": 640,
                "discipline": "pyramid",
                "table_size": "7ft",
                "skill_level": "intermediate",
            },
            "payload": {
                "game": "pyramid",
                "my_score": 35,
                "opp_score": 20,
                "table_size": "7ft",
                "skill_level": "intermediate",
            },
            "organs_enabled": False,
        }
    )
    assert r["ok"]
    assert r["result"]["valid"] is True
