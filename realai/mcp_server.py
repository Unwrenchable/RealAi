#!/usr/bin/env python3
"""RealAI Hive MCP server (stdio JSON-RPC) — adapter to http://127.0.0.1:8001.

- Speaks MCP over stdin/stdout (newline-delimited JSON).
- Logs ONLY to stderr (stdout is the protocol).
- Does NOT start/stop/restart the orchestrator.
- Does NOT talk to Vulkan :8080 as if it were the hive.
- stdlib only (urllib, json, os, sys).

Env:
  REALAI_HIVE_URL   default http://127.0.0.1:8001
  REALAI_API_KEY    optional Bearer token
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

SERVER_NAME = "realai-hive"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

HIVE_URL = (os.environ.get("REALAI_HIVE_URL") or "http://127.0.0.1:8001").rstrip("/")
API_KEY = (os.environ.get("REALAI_API_KEY") or "").strip()


def _configure_stdio() -> None:
    """Windows-safe stdio: binary protocol on stdout, logs on stderr only."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass
    # Avoid accidental prints breaking JSON-RPC on stdout.
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _log(msg: str) -> None:
    try:
        sys.stderr.write(msg.rstrip() + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def _hive_request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 120.0,
) -> Tuple[int, Any]:
    url = HIVE_URL + path
    data = None
    headers = {"Accept": "application/json", "User-Agent": "realai-hive-mcp/1.0"}
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    if API_KEY:
        headers["Authorization"] = "Bearer " + API_KEY
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read().decode("utf-8", errors="replace")
            code = getattr(resp, "status", None) or resp.getcode()
            if not raw_body:
                return int(code), None
            try:
                return int(code), json.loads(raw_body)
            except json.JSONDecodeError:
                return int(code), {"raw": raw_body}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_body) if err_body else {"error": str(e)}
        except json.JSONDecodeError:
            parsed = {"error": str(e), "raw": err_body}
        return int(e.code), parsed
    except Exception as e:
        return 0, {"error": str(e), "type": type(e).__name__}


def _tool_result(payload: Any, is_error: bool = False) -> Dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, default=str)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": bool(is_error),
    }


def _ok_json(code: int, data: Any) -> Dict[str, Any]:
    if code == 0:
        return _tool_result(data, is_error=True)
    if code >= 400:
        return _tool_result({"http_status": code, "body": data}, is_error=True)
    return _tool_result({"http_status": code, "body": data})


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "realai_health",
        "description": "GET Hive /health (orchestrator :8001, not Vulkan :8080)",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "realai_recovery",
        "description": "GET /v1/recovery — LoRA/recovery inventory",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "realai_capabilities",
        "description": "GET /v1/capabilities — ability honesty catalog",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "realai_tools",
        "description": "GET /v1/tools — hive tool list",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "realai_lora",
        "description": "GET /v1/lora — recovered PEFT adapters",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "realai_tasks_list",
        "description": "GET /v1/tasks — list tasks",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "realai_task_get",
        "description": "GET /v1/tasks/{id}",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Task id"}},
            "required": ["id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "realai_task_create",
        "description": "POST /v1/tasks with {task, context}",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "context": {"type": "string", "description": "Optional context string"},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "realai_chat",
        "description": "POST /v1/chat/completions (OpenAI-style messages)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Chat messages",
                },
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "max_tokens": {"type": "integer"},
                "realai_multi_agent": {"type": "boolean"},
            },
            "required": ["messages"],
            "additionalProperties": True,
        },
    },
    {
        "name": "realai_multi_agent",
        "description": "POST /v1/multi-agent/run — Vulkan-backed pipeline",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "mode": {"type": "string", "description": "pipeline or parallel"},
                "max_tokens": {"type": "integer"},
                "temperature": {"type": "number"},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "realai_tool_execute",
        "description": "POST /v1/tools/execute {name, arguments}",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "realai_self_heal_status",
        "description": "GET /v1/self-heal/status",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    args = arguments if isinstance(arguments, dict) else {}
    try:
        if name == "realai_health":
            return _ok_json(*_hive_request("GET", "/health"))
        if name == "realai_recovery":
            return _ok_json(*_hive_request("GET", "/v1/recovery"))
        if name == "realai_capabilities":
            return _ok_json(*_hive_request("GET", "/v1/capabilities"))
        if name == "realai_tools":
            return _ok_json(*_hive_request("GET", "/v1/tools"))
        if name == "realai_lora":
            return _ok_json(*_hive_request("GET", "/v1/lora"))
        if name == "realai_tasks_list":
            return _ok_json(*_hive_request("GET", "/v1/tasks"))
        if name == "realai_task_get":
            tid = str(args.get("id") or "").strip()
            if not tid:
                return _tool_result({"error": "id is required"}, is_error=True)
            return _ok_json(*_hive_request("GET", "/v1/tasks/" + quote(tid, safe="")))
        if name == "realai_task_create":
            task = str(args.get("task") or "").strip()
            if not task:
                return _tool_result({"error": "task is required"}, is_error=True)
            body = {"task": task, "context": str(args.get("context") or "")}
            return _ok_json(*_hive_request("POST", "/v1/tasks", body))
        if name == "realai_chat":
            messages = args.get("messages")
            if not isinstance(messages, list) or not messages:
                return _tool_result({"error": "messages array is required"}, is_error=True)
            body = dict(args)
            body["messages"] = messages
            return _ok_json(*_hive_request("POST", "/v1/chat/completions", body, timeout=300.0))
        if name == "realai_multi_agent":
            task = str(args.get("task") or "").strip()
            if not task:
                return _tool_result({"error": "task is required"}, is_error=True)
            body = {
                "task": task,
                "mode": str(args.get("mode") or "pipeline"),
                "max_tokens": int(args.get("max_tokens") or 384),
                "temperature": float(args.get("temperature") or 0.3),
            }
            return _ok_json(*_hive_request("POST", "/v1/multi-agent/run", body, timeout=300.0))
        if name == "realai_tool_execute":
            tname = str(args.get("name") or "").strip()
            if not tname:
                return _tool_result({"error": "name is required"}, is_error=True)
            body = {"name": tname, "arguments": args.get("arguments") or {}}
            return _ok_json(*_hive_request("POST", "/v1/tools/execute", body, timeout=180.0))
        if name == "realai_self_heal_status":
            return _ok_json(*_hive_request("GET", "/v1/self-heal/status", timeout=60.0))
        return _tool_result({"error": "unknown tool", "name": name}, is_error=True)
    except Exception as e:
        _log("tool error: " + traceback.format_exc()[-800:])
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
    is_notification = "id" not in msg

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
        result = call_tool(name, arguments)
        return _rpc_result(req_id, result)

    if is_notification:
        _log("ignored notification: " + str(method))
        return None

    return _rpc_error(req_id, -32601, "Method not found: " + str(method))


def _write(msg: Dict[str, Any]) -> None:
    raw = (json.dumps(msg, default=str, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        buf = getattr(sys.stdout, "buffer", None)
        if buf is not None:
            buf.write(raw)
            buf.flush()
        else:
            sys.stdout.write(raw.decode("utf-8"))
            sys.stdout.flush()
    except Exception:
        # Last resort — still attempt text write.
        sys.stdout.write(raw.decode("utf-8", errors="replace"))
        sys.stdout.flush()


def main() -> int:
    _configure_stdio()
    _log(
        "realai-hive MCP stdio starting; hive=%s key=%s"
        % (HIVE_URL, "set" if API_KEY else "unset")
    )
    # Read binary-safe lines so Windows pipe clients don't stall on decode.
    stdin = getattr(sys.stdin, "buffer", None)
    if stdin is not None:
        def _iter_lines():
            while True:
                line = stdin.readline()
                if not line:
                    break
                yield line.decode("utf-8", errors="replace")
        line_iter = _iter_lines()
    else:
        line_iter = sys.stdin

    for line in line_iter:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            _write(_rpc_error(None, -32700, "Parse error: " + str(e)))
            continue
        try:
            resp = handle_message(msg)
            if resp is not None:
                _write(resp)
        except Exception:
            _log("handler crash: " + traceback.format_exc()[-800:])
            rid = msg.get("id") if isinstance(msg, dict) else None
            _write(_rpc_error(rid, -32603, "Internal error"))
    _log("stdin closed; exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
