"""Game-world ability — thin wrap over Atomic Fizz plugin gold.

Authority: ``realai/plugins/atomic_fizz_realai/`` (JS engines already extracted).
No second copy of plugin modules. No vault secrets — metadata + entrypoint map only.
Empty ``C:\\tools\\realai\\plugins\\overseer.js`` is NOT a source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ABILITY = {
    "id": "game_world",
    "name": "game_world",
    "type": "ability",
    "status": "CODE",
    "source": "realai/plugins/atomic_fizz_realai",
    "dest": "abilities/game_world.py",
    "capabilities": [
        "npc_generation",
        "quest_generation",
        "dungeon_generation",
        "overseer",
        "dialogue",
        "world_events",
        "survival_rewards",
    ],
    "secrets_policy": "none — plugin metadata/entrypoints only; never promote vault wallets/keys",
}

_ROOT = Path(__file__).resolve().parents[1]
_PLUGIN = _ROOT / "realai" / "plugins" / "atomic_fizz_realai"


def plugin_dir() -> Path:
    return _PLUGIN


def load_manifest() -> dict[str, Any]:
    p = _PLUGIN / "plugin_manifest.json"
    if not p.is_file():
        return {"ok": False, "error": "manifest_missing", "path": str(p)}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(p)}
    data["ok"] = True
    data["plugin_dir"] = str(_PLUGIN)
    return data


def list_entrypoints() -> dict[str, Any]:
    """List on-disk JS entrypoints (no Node execution required)."""
    man = load_manifest()
    entries = (man.get("entrypoints") if isinstance(man, dict) else None) or {}
    files = []
    engines_gold = []
    media = []
    if _PLUGIN.is_dir():
        for f in sorted(_PLUGIN.glob("*.js")):
            try:
                size = f.stat().st_size
            except OSError:
                size = -1
            files.append({"name": f.name, "bytes": size, "likely_husk": size < 400})
        gold_dir = _PLUGIN / "engines_gold"
        if gold_dir.is_dir():
            for f in sorted(gold_dir.glob("*.js")):
                try:
                    size = f.stat().st_size
                except OSError:
                    size = -1
                engines_gold.append({"name": f.name, "bytes": size})
        media_dir = _PLUGIN / "media"
        if media_dir.is_dir():
            for f in sorted(media_dir.iterdir()):
                if f.is_file():
                    try:
                        size = f.stat().st_size
                    except OSError:
                        size = -1
                    media.append({"name": f.name, "bytes": size})
    return {
        "ok": _PLUGIN.is_dir(),
        "plugin_dir": str(_PLUGIN),
        "entrypoints": dict(entries),
        "files": files,
        "engines_gold": engines_gold,
        "media": media,
        "manifest_ok": bool(man.get("ok")),
        "vault_source": r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS",
        "note": (
            "Root realai-client.js is LIVE CJS hive client; engines_src/ (+ engines_gold/) hold fuller scripts/realai "
            "implementations. media/grok_xai.js = xAI image/video client. "
            "Python Hive path: ability.image_generation / ability.video_generation via xai_media."
        ),
    }


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Catalog/bridge entry — returns manifest + entrypoint inventory."""
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "list").strip().lower()
    if action in ("manifest", "info"):
        return {"ok": True, "ability": "game_world", "source": ABILITY["source"], "result": load_manifest()}
    return {
        "ok": True,
        "ability": "game_world",
        "source": ABILITY["source"],
        "result": list_entrypoints(),
    }
