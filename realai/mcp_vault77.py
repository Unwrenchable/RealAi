#!/usr/bin/env python3
"""Vault-77 game MCP (stdio JSON-RPC) — Atomic Fizz Caps live API adapter.

Companion to realai/mcp_server.py (Hive). Does NOT start Hive/Vulkan.
No wallet key files — optional VAULT77_API_KEY from env only.

Env:
  VAULT77_API_URL   default https://api.atomicfizzcaps.xyz
  VAULT77_API_KEY   optional x-admin-key header

Usage:
  python -u C:\\RealAI-clean\\realai\\mcp_vault77.py
  grok mcp add vault77 -- python -u C:\\RealAI-clean\\realai\\mcp_vault77.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

SERVER_NAME = "vault77-game"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

API_BASE = (os.environ.get("VAULT77_API_URL") or "https://api.atomicfizzcaps.xyz").rstrip("/")
API_KEY = (os.environ.get("VAULT77_API_KEY") or "").strip()


def _log(msg: str) -> None:
    sys.stderr.write(msg.rstrip() + "\n")
    sys.stderr.flush()


def _api(path: str, timeout: float = 30.0) -> tuple[int, Any]:
    url = API_BASE + path
    headers = {"Accept": "application/json", "User-Agent": "realai-vault77-mcp/1.0"}
    if API_KEY:
        headers["x-admin-key"] = API_KEY
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = getattr(resp, "status", None) or resp.getcode()
            try:
                return int(code), json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return int(code), {"raw": raw}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err) if err else {"error": str(e)}
        except json.JSONDecodeError:
            parsed = {"error": str(e), "raw": err}
        return int(e.code), parsed
    except Exception as e:
        return 0, {"error": str(e), "type": type(e).__name__}


def _tool_result(payload: Any, is_error: bool = False) -> Dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, default=str)
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


def _ok(code: int, data: Any) -> Dict[str, Any]:
    if code == 0 or code >= 400:
        return _tool_result({"http_status": code, "body": data}, is_error=True)
    return _tool_result({"http_status": code, "body": data})


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "vault77_health",
        "description": "Ping Atomic Fizz Caps backend /api/health",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "vault77_leaderboard",
        "description": "Wasteland leaderboard by caps/xp/claims",
        "inputSchema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "caps|xp|claims"},
                "limit": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "vault77_locations",
        "description": "List POI locations (optional type filter)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
                "type": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "vault77_items",
        "description": "List item definitions / mintables",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "search": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "vault77_config",
        "description": "Frontend game config (radii, cooldowns, XP)",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "vault77_quests",
        "description": "Quest definitions (optional id filter)",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "vault77_rotation",
        "description": "Daily/weekly event rotation",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "vault77_factions",
        "description": "Faction-oriented location metadata",
        "inputSchema": {
            "type": "object",
            "properties": {"faction": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "vault77_player",
        "description": "Player profile by wallet address (caller-supplied; no local key store)",
        "inputSchema": {
            "type": "object",
            "properties": {"wallet": {"type": "string"}},
            "required": ["wallet"],
            "additionalProperties": False,
        },
    },
]


def call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    args = arguments if isinstance(arguments, dict) else {}
    try:
        if name == "vault77_health":
            return _ok(*_api("/api/health"))
        if name == "vault77_leaderboard":
            metric = str(args.get("metric") or "caps")
            limit = int(args.get("limit") or 10)
            return _ok(*_api(f"/api/caps/leaderboard?metric={quote(metric)}&limit={limit}"))
        if name == "vault77_locations":
            qs: Dict[str, str] = {"limit": str(int(args.get("limit") or 50))}
            if args.get("type"):
                qs["type"] = str(args.get("type"))
            return _ok(*_api(f"/api/locations?{urlencode(qs)}"))
        if name == "vault77_items":
            qs = {}
            if args.get("category"):
                qs["category"] = str(args.get("category"))
            if args.get("search"):
                qs["q"] = str(args.get("search"))
            path = "/api/mintables" + (("?" + urlencode(qs)) if qs else "")
            return _ok(*_api(path))
        if name == "vault77_config":
            return _ok(*_api("/api/config/frontend"))
        if name == "vault77_quests":
            code, data = _api("/api/quests")
            qid = str(args.get("id") or "").strip()
            if qid and code < 400 and data is not None:
                quest = None
                if isinstance(data, list):
                    quest = next((q for q in data if isinstance(q, dict) and q.get("id") == qid), None)
                elif isinstance(data, dict):
                    quest = data.get(qid) or next(
                        (v for v in data.values() if isinstance(v, dict) and v.get("id") == qid),
                        None,
                    )
                if quest is None:
                    return _tool_result({"error": f'Quest "{qid}" not found'}, is_error=True)
                return _ok(code, quest)
            return _ok(code, data)
        if name == "vault77_rotation":
            return _ok(*_api("/api/rotation"))
        if name == "vault77_factions":
            qs = f"?faction={quote(str(args.get('faction')))}" if args.get("faction") else ""
            return _ok(*_api(f"/api/locations{qs}"))
        if name == "vault77_player":
            wallet = str(args.get("wallet") or "").strip()
            if not wallet:
                return _tool_result({"error": "wallet is required (caller-supplied; no local keys)"}, is_error=True)
            return _ok(*_api(f"/api/player/{quote(wallet, safe='')}"))
        return _tool_result({"error": "unknown tool", "name": name}, is_error=True)
    except Exception as e:
        _log("tool error: " + traceback.format_exc()[-600:])
        return _tool_result({"error": str(e)}, is_error=True)


def _rpc_result(req_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _rpc_error(req_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def handle_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(msg, dict):
        return _rpc_error(None, -32600, "Invalid Request")
    req_id = msg.get("id", None)
    method = msg.get("method")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}

    if method == "initialize":
        return _rpc_result(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _rpc_result(req_id, {})
    if method == "tools/list":
        return _rpc_result(req_id, {"tools": TOOLS})
    if method == "tools/call":
        name = str(params.get("name") or "")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        return _rpc_result(req_id, call_tool(name, arguments))
    if method == "resources/list":
        return _rpc_result(req_id, {"resources": []})
    if method == "prompts/list":
        return _rpc_result(req_id, {"prompts": []})
    return _rpc_error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    _log(f"{SERVER_NAME} mcp starting api={API_BASE} key_set={bool(API_KEY)}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            out = _rpc_error(None, -32700, "Parse error")
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()
            continue
        resp = handle_message(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
