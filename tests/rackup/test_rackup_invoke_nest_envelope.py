"""Nest tools/execute rackup_invoke must pass player + payload into rackup-coach.

Local re-smoke (orchestrator :8001), after this mapping:

  curl -s http://127.0.0.1:8001/v1/tools/execute -H 'content-type: application/json' -d '{
    "name": "rackup_invoke",
    "tool": "rackup_invoke",
    "arguments": {
      "ability": "coach",
      "player": {"display_name": "AtomicFizz", "discipline": "nine_ball"},
      "payload": {"question": "How should I break from the kitchen?"}
    }
  }'

  curl -s http://127.0.0.1:8001/v1/tools/execute -H 'content-type: application/json' -d '{
    "name": "rackup_invoke",
    "tool": "rackup_invoke",
    "arguments": {
      "ability": "shot_of_the_day",
      "player": {"display_name": "AtomicFizz", "discipline": "nine_ball"},
      "payload": {"game": "nine_ball"}
    }
  }'

  curl -s http://127.0.0.1:8001/v1/tools/execute -H 'content-type: application/json' -d '{
    "name": "rackup_invoke",
    "tool": "rackup_invoke",
    "arguments": {
      "ability": "rating_update",
      "player": {"display_name": "AtomicFizz", "discipline": "nine_ball", "rating": 540, "rd": 80, "volatility": 0.06},
      "payload": {
        "won": true,
        "opponent": {"display_name": "CueKing", "rating": 560, "rd": 90},
        "scores": {"my_score": 7, "opp_score": 4},
        "match_id": "nest-smoke-1"
      }
    }
  }'

Pass: coach / shot_of_the_day text mentions AtomicFizz or nine-ball, never craft-cli as the player.
rating_update is ok, or a real rating error — never missing_outcome when won, outcome, or scores were sent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT, _ROOT / "realai"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from realai.cli.craft import tool_rackup
from realai.orchestration.v3_orchestrator import _run_tool

PLAYER = {
    "display_name": "AtomicFizz",
    "discipline": "nine_ball",
    "rating": 540,
    "rd": 80,
    "volatility": 0.06,
}


def _text(resp: dict) -> str:
    return json.dumps(resp)


def _failure(resp: dict) -> str:
    err = str(resp.get("error") or "")
    result = resp.get("result")
    if isinstance(result, dict) and result.get("error"):
        err = err or str(result.get("error"))
    return err


def _invoke(ability: str, payload: dict | None = None, **extra: object) -> dict:
    arguments = {
        "ability": ability,
        "player": dict(PLAYER),
        "payload": dict(payload or {}),
        "organs_enabled": False,
    }
    arguments.update(extra)
    resp = _run_tool("rackup_invoke", arguments)
    assert isinstance(resp, dict)
    return resp


def test_cli_without_player_stays_craft_demo():
    resp = tool_rackup(ability="roc_info", organs_enabled=False)
    assert resp["ok"] is True
    assert "craft-cli" in resp.get("notes", "")


def test_coach_nest_player_and_discipline():
    resp = _invoke("coach", {"question": "How should I break from the kitchen?"})
    assert resp["ok"] is True
    assert resp["ability"] == "coach"
    result = resp["result"]
    assert result["display_name"] == "AtomicFizz"
    assert result["discipline"] == "nine_ball"
    notes = resp.get("notes") or ""
    assert "AtomicFizz" in notes
    assert "nine-ball" in notes
    blob = _text(resp)
    assert "craft-cli" not in blob
    assert result["player_id"] != "craft-cli"


def test_shot_of_the_day_nest_player_and_discipline():
    resp = _invoke("shot_of_the_day", {"game": "nine_ball"})
    assert resp["ok"] is True
    assert resp["ability"] == "shot_of_the_day"
    result = resp["result"]
    assert result["discipline"] == "nine_ball"
    assert result["player_id"] != "craft-cli"
    notes = resp.get("notes") or ""
    assert "AtomicFizz" in notes
    assert "nine-ball" in notes
    assert "craft-cli" not in _text(resp)


def test_rating_update_won_opponent_scores_not_missing_outcome():
    resp = _invoke(
        "rating_update",
        {
            "won": True,
            "opponent": {"display_name": "CueKing", "rating": 560, "rd": 90},
            "scores": {"my_score": 7, "opp_score": 4},
            "match_id": "nest-smoke-1",
            "game": "nine_ball",
        },
    )
    assert _failure(resp) != "missing_outcome"
    assert resp["ok"] is True
    assert resp["result"]["discipline"] == "nine_ball"
    assert resp["result"]["input"]["outcome"] == 1.0
    assert "AtomicFizz" in (resp.get("notes") or "")
    assert "craft-cli" not in _text(resp)


def test_rating_update_outcome_string_without_won():
    resp = _invoke(
        "rating_update",
        {
            "outcome": "win",
            "opponent_rating": 520,
            "match_id": "nest-outcome",
        },
    )
    assert _failure(resp) != "missing_outcome"
    assert resp["ok"] is True
    assert resp["result"]["input"]["outcome"] == 1.0


def test_rating_update_scores_only_without_won():
    resp = _invoke(
        "rating_update",
        {
            "scores": {"my_score": 5, "opp_score": 9},
            "opponent": {"rating": 500, "rd": 120},
            "match_id": "nest-scores",
        },
    )
    assert _failure(resp) != "missing_outcome"
    assert resp["ok"] is True
    assert resp["result"]["input"]["outcome"] == 0.0


def test_rating_update_sibling_won_flattened_onto_payload():
    """won beside payload, not inside it, still counts as an outcome."""
    resp = _run_tool(
        "rackup_invoke",
        {
            "ability": "rating_update",
            "player": dict(PLAYER),
            "opponent_rating": 510,
            "won": True,
            "organs_enabled": False,
        },
    )
    assert _failure(resp) != "missing_outcome"
    assert resp["ok"] is True
    assert resp["result"]["input"]["outcome"] == 1.0


def test_rating_update_named_scores_follow_display_name():
    resp = _invoke(
        "rating_update",
        {
            "scores": {"AtomicFizz": 9, "CueKing": 6},
            "opponent_rating": 530,
            "match_id": "nest-named",
        },
    )
    assert _failure(resp) != "missing_outcome"
    assert resp["ok"] is True
    assert resp["result"]["input"]["outcome"] == 1.0
