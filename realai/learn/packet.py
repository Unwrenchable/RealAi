"""Learning packet JSON shape + writers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKET_SCHEMA = "realai.learn.packet/v1"

PACKET_REQUIRED_KEYS = (
    "schema",
    "slug",
    "source",
    "summary",
    "fingerprints",
    "proposed_abilities",
    "plugin_proposal",
    "learned_at",
    "heal",
)

SUMMARY_REQUIRED_KEYS = (
    "title",
    "description",
    "file_count",
    "languages",
    "frameworks",
    "domain_keywords",
    "readme",
    "api_routes",
    "plugin_like_folders",
)


def build_packet(
    *,
    slug: str,
    source: dict[str, Any],
    scan: dict[str, Any],
    signals: dict[str, Any],
    plugin_proposal: dict[str, Any],
) -> dict[str, Any]:
    fps = list(scan.get("fingerprints") or [])
    packet = {
        "schema": PACKET_SCHEMA,
        "slug": slug,
        "source": {
            "input": source.get("input"),
            "kind": source.get("kind"),
            "resolved_path": str(source.get("path") or ""),
            "url": source.get("url"),
            "cloned": bool(source.get("cloned")),
            "reused_cache": bool(source.get("reused_cache")),
            "git": source.get("git") or {},
        },
        "summary": {
            "title": signals.get("title") or slug,
            "description": signals.get("description") or "",
            "file_count": int(scan.get("file_count") or len(fps)),
            "truncated": bool(scan.get("truncated")),
            "languages": signals.get("languages") or {},
            "frameworks": list(signals.get("frameworks") or []),
            "domain_keywords": list(signals.get("domain_keywords") or []),
            "readme": signals.get("readme") or "",
            "api_routes": list(signals.get("api_routes") or []),
            "plugin_like_folders": list(signals.get("plugin_like_folders") or []),
        },
        "fingerprints": fps,
        "proposed_abilities": list(signals.get("proposed_abilities") or []),
        "plugin_proposal": plugin_proposal,
        "learned_at": datetime.now(timezone.utc).isoformat(),
        "heal": False,
    }
    return packet


def validate_packet(packet: dict[str, Any]) -> list[str]:
    """Return a list of missing/invalid field names (empty = ok)."""
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["packet"]
    for key in PACKET_REQUIRED_KEYS:
        if key not in packet:
            errors.append(key)
    summary = packet.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary")
    else:
        for key in SUMMARY_REQUIRED_KEYS:
            if key not in summary:
                errors.append(f"summary.{key}")
    if packet.get("schema") != PACKET_SCHEMA:
        errors.append("schema")
    if packet.get("heal") is not False:
        errors.append("heal")
    fps = packet.get("fingerprints")
    if not isinstance(fps, list):
        errors.append("fingerprints")
    abilities = packet.get("proposed_abilities")
    if not isinstance(abilities, list) or not abilities:
        errors.append("proposed_abilities")
    elif not any(
        isinstance(a, dict) and a.get("id") == "health" for a in abilities
    ):
        errors.append("proposed_abilities.health")
    return errors


def write_packet(packet: dict[str, Any], *, catalog_path: Path, docs_path: Path | None) -> dict[str, str]:
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(packet, indent=2, default=str) + "\n"
    catalog_path.write_text(text, encoding="utf-8")
    written = {"catalog": str(catalog_path)}
    if docs_path is not None:
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(text, encoding="utf-8")
        written["docs"] = str(docs_path)
    return written
