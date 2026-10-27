"""Opt-in bridge: serve the merged legacy API routes (realai.server.legacy_api) from the structured :8000 server.

Off by default, so live :8000 (``realai-server`` / ``realai.server.app``) behaves exactly as before. With
REALAI_SERVER_MERGED_ROUTES=1, ``router.dispatch_request`` forwards any path that no structured route (and no
REALAI_UNIFIED_ROUTES route) handled to the legacy handler in-process. Examples: /v1/organs, /v1/hive, /v1/plugins,
/v1/personas, /v1/world/*, /v1/knowledge/*, /v1/reasoning/chain, /v1/memory/recall, /v1/rackup/coach, /fusion-ui/.
Structured routes always win. No socket is opened: the request is fed to ``RealAIAPIHandler`` through an in-memory
connection object.
"""
from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, Optional, Tuple


def enabled() -> bool:
    return os.environ.get("REALAI_SERVER_MERGED_ROUTES", "").strip().lower() in {"1", "true", "yes", "on"}


class _Conn:
    def __init__(self, raw: bytes) -> None:
        self._r = io.BytesIO(raw)
        self.out = io.BytesIO()

    def makefile(self, mode: str, *a: Any, **k: Any):
        return self._r if "r" in mode else self.out

    def sendall(self, data: bytes) -> None:
        self.out.write(data)

    def settimeout(self, *_a: Any) -> None:
        pass

    def setsockopt(self, *_a: Any) -> None:
        pass


class _Server:
    server_name = "realai-merged"
    server_port = 0


def call(method: str, path: str, payload: Any = None, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Any, str]:
    from realai.server.legacy_api import RealAIAPIHandler

    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    hdrs = {"Host": "127.0.0.1", "Connection": "close", "Content-Length": str(len(body)),
            "Content-Type": "application/json", **(headers or {})}
    raw = (f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in hdrs.items()) + "\r\n").encode() + body
    conn = _Conn(raw)

    class _H(RealAIAPIHandler):
        def log_message(self, *a: Any) -> None:
            pass

    _H(conn, ("127.0.0.1", 0), _Server())
    resp = conn.out.getvalue()
    head, _, data = resp.partition(b"\r\n\r\n")
    lines = head.decode("iso-8859-1").split("\r\n")
    try:
        status = int(lines[0].split()[1])
    except (IndexError, ValueError):
        return 502, {"error": {"message": "legacy handler produced no response"}}, "application/json"
    ctype = next((ln.split(":", 1)[1].strip() for ln in lines[1:] if ln.lower().startswith("content-type:")), "application/json")
    if ctype.startswith("application/json"):
        try:
            return status, json.loads(data.decode("utf-8") or "null"), ctype
        except ValueError:
            pass
    return status, data.decode("utf-8", "replace"), ctype


def dispatch(method: str, path: str, payload: Any = None) -> Optional[Tuple[int, Any, str]]:
    """Router hook: None when disabled or the legacy API does not know the path either (keeps the 404)."""
    if not enabled():
        return None
    status, data, ctype = call(method, path, payload)
    if status == 404:
        return None
    return status, data, ctype
