"""Unified Player Card — envelope shape + two-continua policy."""
from __future__ import annotations

import os
from unittest.mock import patch

from plugins.rackup_coach import invoke, METADATA
from plugins.rackup_coach.abilities.player_card_sync import CARD_KEYS, POLICY, SCHEMA

_CLEAR_APA = {"APA_MEMBER_TOKEN": "", "RACKUP_APA_TOKEN": "", "APA_TOKEN": ""}


def _invoke(payload, player=None, **extra):
    env = {**os.environ, **_CLEAR_APA}
    env.update(extra.pop("env", {}))
    body = {
        "ability": extra.pop("ability", "player_card_sync"),
        "organs_enabled": False,
        "player": player
        or {
            "player_id": "u1",
            "display_name": "Alex Rivera",
            "rating": 547,
            "rd": 80,
            "volatility": 0.06,
            "matches_played_rackup": 12,
        },
        "payload": payload,
    }
    with patch.dict(os.environ, env, clear=False):
        return invoke(body)


def test_metadata_registers_player_card_sync():
    assert "player_card_sync" in METADATA["methods"]
    assert "player_card_sync" in METADATA["capabilities"]
    assert METADATA["version"].startswith("1.")


def test_envelope_shape():
    r = _invoke(
        {
            "name": "Alex Rivera",
            "fargo": {"playerId": "12345", "rating": 552, "robustness": 410},
            "apa_sl": 5,
            "bca": {"value": 4, "scale": "skill_1_9"},
            "tap": {"value": 5, "scale": "skill_1_9"},
            "leagues_v2_rating": 1500,
        }
    )
    assert r["ok"] is True
    assert r["plugin"] == "rackup-coach"
    assert r["ability"] == "player_card_sync"
    assert r["error"] is None
    result = r["result"]
    assert result["schema"] == SCHEMA
    assert set(CARD_KEYS) <= set(result["card"])
    card = result["card"]
    for key in CARD_KEYS:
        assert key in card
    policy = result["policy"]
    for k, v in POLICY.items():
        assert policy[k] == v
    assert policy["lms_submit"] is False
    assert policy["heal"] is False
    assert policy["invent_fargo"] is False
    assert policy["leagues_v2_overwrites_roc"] is False
    assert policy["canonical_competitive"] == "roc_glicko"


def test_parallel_fields_and_two_continua():
    r = _invoke(
        {
            "fargo": {"playerId": "12345", "rating": 552, "robustness": 410},
            "apa_sl": 5,
            "leagues_v2_rating": 1500,
        }
    )
    card = r["result"]["card"]
    roc = card["roc_glicko"]
    assert roc["canonical"] is True
    assert roc["storage"] == "users.rating"
    assert roc["rating"] == 547
    assert roc["math_owner"] == "realai.rating_update"
    assert roc["scale"] == "roc_500_band"
    assert roc["rating"] != card["leagues_v2"]["value"]

    fargo = card["fargo"]
    assert fargo["read_only"] is True
    assert fargo["invented"] is False
    assert fargo["status"] == "present"
    assert fargo["rating"] == 552

    shadow = card["rackup_rate_shadow"]
    assert shadow is not None
    assert shadow["alongside"] == "fargo"
    assert shadow["does_not_overwrite_fargo"] is True
    assert shadow["does_not_overwrite_roc_glicko"] is True
    assert shadow["value"] == 552

    assert card["apa_sl"] == 5
    assert card["bca"] is None or card["bca"].get("entry") == "manual"
    v2 = card["leagues_v2"]
    assert v2["scale"] == "0_3000"
    assert v2["value"] == 1500
    assert v2["overwrites_roc"] is False
    assert v2["do_not_write_to_users_rating"] is True
    assert "roc_glicko" == card["matchmaking"]["competitive_input"]
    assert "leagues_v2" in card["matchmaking"]["ignore_for_roc_ladder"]


def test_never_invent_fargo():
    r = _invoke({"name": "Unknown Player", "apa_sl": 4})
    fargo = r["result"]["card"]["fargo"]
    assert fargo["status"] == "missing"
    assert fargo["rating"] is None
    assert fargo["invented"] is False
    assert fargo["read_only"] is True
    # Shadow may exist from APA convert — still must not fill fargo.rating
    shadow = r["result"]["card"]["rackup_rate_shadow"]
    if shadow:
        assert shadow["does_not_overwrite_fargo"] is True
        assert r["result"]["card"]["fargo"]["rating"] is None


def test_apa_lms_requires_token():
    r = _invoke({"apa_sl": 5, "apa": {"skill_level": 5}})
    src = r["result"]["card"]["sources"]["apa"]
    assert src["sync"] == "skipped_no_token"
    assert src["requires_token"] is True
    assert src["entry"] != "apa_lms"
    assert r["result"]["card"]["apa_sl"] == 5

    r2 = _invoke(
        {"apa_sl": 5, "apa": {"skill_level": 5}, "apa_token": "secret-not-for-output"},
    )
    src2 = r2["result"]["card"]["sources"]["apa"]
    assert src2["sync"] == "token_ok"
    assert src2["entry"] == "apa_lms"
    blob = str(r2)
    assert "secret-not-for-output" not in blob


def test_alias_unified_player_card():
    r = _invoke({"fargo_id": "9"}, ability="unified_player_card")
    assert r["ok"] is True
    assert r["ability"] == "unified_player_card"
    assert r["result"]["schema"] == SCHEMA
