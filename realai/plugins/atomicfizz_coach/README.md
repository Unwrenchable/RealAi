# Atomic Fizz Coach (`atomicfizz-coach`)

Stub **living** RealAI plugin for Atomic Fizz / Caps — the same provider
boundary as [`rackup-coach`](../rackup_coach/README.md).

| | |
|--|--|
| Plugin id | `atomicfizz-coach` |
| Package | `plugins.atomicfizz_coach` |
| Folder | `realai/plugins/atomicfizz_coach` (one canonical directory; no hyphenated twin) |
| Manifest | `manifest.yaml` |
| Version | `0.1.0` (stub) |

This is **not** `atomic_fizz_realai` (recovered JS world/NPC engines). That
package stays untouched. This plugin is the product-shell contract so Caps can
call RealAI the way RackUp calls `rackup-coach`.

## Abilities (placeholders)

| Ability | Description |
|---------|-------------|
| `health` | Liveness + contract discovery. **Not** a runtime heal. |
| `caps_context` | Structured Caps validation hints. No GPS / vault implementation. |
| `wrist_ui_hint` | Structured Wrist UI hint payload. Product owns chrome. |

Caps, Wrist UI, and vault GPS stay **product-owned**. RealAI returns hints and
validation only. **No money movement / no `authorize_payout`.**

## Example

```python
from plugins.atomicfizz_coach import invoke

invoke("health", {"player_id": "p1"}, {})
invoke("caps_context", {"player_id": "p1"}, {"tenant": "caps-dev"})
invoke({"ability": "wrist_ui_hint", "player": {"player_id": "p1"}, "payload": {}})
```

Canonical HTTP: `POST {REALAI_BASE_URL}/v1/plugins/atomicfizz-coach`

See `docs/external_contracts/REALAI_ATOMICFIZZ_WIRING_CONTRACT.md`.
