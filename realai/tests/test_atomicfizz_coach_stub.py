"""atomicfizz-coach stub — envelope + placeholder abilities (no Caps GPS)."""
from __future__ import annotations

from plugins.atomicfizz_coach import METADATA, invoke, register
from plugins.rackup_coach import invoke as rackup_invoke


def test_metadata_stub_contract():
    assert METADATA["name"] == "atomicfizz-coach"
    assert METADATA["version"] == "0.1.0"
    assert METADATA["stub"] is True
    assert METADATA["money"]["authorize_payout"] is False
    assert "caps" in METADATA["product_owned"]
    assert "wrist_ui" in METADATA["product_owned"]
    assert "vault_gps" in METADATA["product_owned"]


def test_invoke_ability_player_payload():
    resp = invoke("health", {"player_id": "caps-1"}, {})
    assert resp["ok"] is True
    assert resp["plugin"] == "atomicfizz-coach"
    assert resp["ability"] == "health"
    assert resp["error"] is None
    assert resp["result"]["stub"] is True
    assert resp["result"]["heal"] is False
    assert resp["result"]["status"] == "ok"
    assert "caps_context" in resp["result"]["abilities"]


def test_caps_context_placeholder_not_gps():
    resp = invoke("caps_context", {"player_id": "caps-1"}, {"tenant": "caps-dev"})
    assert resp["ok"] is True
    result = resp["result"]
    assert result["stub"] is True
    assert result["caps"]["gps"] is None
    assert result["caps"]["vault"] is None
    assert result["validation"]["implemented"] is False
    assert "product" in result["caps"]["owned_by"].lower()


def test_wrist_ui_hint_placeholder():
    resp = invoke(
        {
            "ability": "wrist_ui_hint",
            "player": {"player_id": "caps-1"},
            "payload": {"surface": "wrist"},
        }
    )
    assert resp["ok"] is True
    assert resp["ability"] == "wrist_ui_hint"
    hint = resp["result"]["hint"]
    assert hint["actions"] == []
    assert hint["surface"] == "wrist"
    assert "Wrist UI" in resp["result"]["owned_by"]


def test_unknown_ability_does_not_crash():
    resp = invoke("authorize_payout", {"player_id": "caps-1"}, {})
    assert resp["ok"] is False
    assert resp["error"]
    assert "unknown ability" in resp["error"]
    assert "health" in resp["result"]["available"]


def test_register_attaches_methods():
    class Model:
        pass

    model = Model()
    meta = register(model, {"env": "test"})
    assert meta["ok"] is True
    assert meta["name"] == "atomicfizz-coach"
    assert callable(model.atomicfizz_coach)
    health = model.atomicfizz_health({})
    assert health["ok"] is True
    assert health["ability"] == "health"


def test_default_ability_is_health():
    resp = invoke()
    assert resp["ok"] is True
    assert resp["ability"] == "health"
    assert resp["result"]["status"] == "ok"


def test_rackup_coach_still_invokes():
    """Stub must not break rackup-coach."""
    resp = rackup_invoke(
        {
            "ability": "pyramid_rules",
            "player": {
                "player_id": "rackup-smoke",
                "rating": 700,
                "discipline": "pyramid",
                "table_size": "9ft",
                "skill_level": "advanced",
            },
            "organs_enabled": False,
        }
    )
    assert resp["ok"] is True
    assert resp["plugin"] == "rackup-coach"
    assert resp["result"]["config"]["points_to_win"] == 71
