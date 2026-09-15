"""Unified Player Card — envelope shape (pytest-visible twin of realai/tests)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Plugin package lives under realai/plugins via the root plugins shim.
_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT, _ROOT / "realai"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

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
    card = result["card"]
    for key in CARD_KEYS:
        assert key in card
    for k, v in POLICY.items():
        assert result["policy"][k] == v


def test_never_invent_fargo_or_overwrite_roc():
    r = _invoke({"apa_sl": 4, "leagues_v2_rating": 1200})
    card = r["result"]["card"]
    assert card["fargo"]["rating"] is None
    assert card["fargo"]["invented"] is False
    assert card["roc_glicko"]["rating"] == 547
    assert card["leagues_v2"]["value"] == 1200
    assert card["leagues_v2"]["overwrites_roc"] is False
    assert card["roc_glicko"]["rating"] != card["leagues_v2"]["value"]
