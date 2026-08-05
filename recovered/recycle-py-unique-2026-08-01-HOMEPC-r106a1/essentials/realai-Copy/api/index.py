"""
Vercel entry point for RealAI.

Vercel's Python web-framework runtime requires an ``app`` WSGI callable in
one of several well-known files (``api/index.py`` is in that list).  We
provide that callable by wrapping :class:`~api_server.RealAIAPIHandler` in a
thin WSGI adapter that feeds each request through a fake socket so that the
full routing / UI logic in ``api_server.py`` is reused unchanged.

The ``handler`` alias is kept for compatibility with the legacy Vercel
serverless-function API (``BaseHTTPRequestHandler`` subclass).
"""

import os
import sys
from io import BytesIO

# Ensure the project root is importable.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from api_server import RealAIAPIHandler  # noqa: E402


# ---------------------------------------------------------------------------
# Fake socket – bridges WSGI environ ↔ BaseHTTPRequestHandler
# ---------------------------------------------------------------------------

class _FakeSocket:
    """Minimal socket shim so BaseHTTPRequestHandler can read/write BytesIO.

    Python ≥ 3.12's StreamRequestHandler uses ``_SocketWriter`` which calls
    ``socket.sendall()`` for writes; older versions use
    ``socket.makefile('wb')``.  We handle both.
    """

    def __init__(self, request_bytes: bytes, output: BytesIO) -> None:
        self._r = BytesIO(request_bytes)
        self._w = output

    def makefile(self, mode: str, bufsize=None) -> BytesIO:
        return self._w if "w" in mode else self._r

    def sendall(self, data: bytes) -> None:
        """Used by Python 3.12+ _SocketWriter in place of makefile('wb')."""
        self._w.write(data)

    def settimeout(self, t) -> None:
        pass

    def setsockopt(self, *args) -> None:
        pass

    def getpeername(self):
        return ("127.0.0.1", 0)


class _UnclosableBytesIO(BytesIO):
    """BytesIO that ignores close() so we can read the buffer after handler.finish()."""

    def close(self) -> None:
        pass  # intentionally a no-op

    def real_close(self) -> None:
        super().close()


# ---------------------------------------------------------------------------
# WSGI app (what Vercel's Python runtime actually requires)
# ---------------------------------------------------------------------------

def app(environ, start_response):
    """WSGI entry point consumed by Vercel's Python web-framework runtime."""
    method = environ["REQUEST_METHOD"]
    path = environ.get("PATH_INFO", "/")
    qs = environ.get("QUERY_STRING", "")
    if qs:
        path = f"{path}?{qs}"

    content_len = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(content_len) if content_len else b""

    # Build a raw HTTP/1.1 request that BaseHTTPRequestHandler can parse.
    host = environ.get("HTTP_HOST") or environ.get("SERVER_NAME", "localhost")
    header_lines = [f"{method} {path} HTTP/1.1", f"Host: {host}"]
    for key, val in environ.items():
        if key.startswith("HTTP_") and key != "HTTP_HOST":
            name = key[5:].replace("_", "-").title()
            header_lines.append(f"{name}: {val}")
    if body:
        ct = environ.get("CONTENT_TYPE", "application/octet-stream")
        if ct:
            header_lines.append(f"Content-Type: {ct}")
        header_lines.append(f"Content-Length: {len(body)}")

    raw_request = ("\r\n".join(header_lines) + "\r\n\r\n").encode("latin-1") + body

    output = _UnclosableBytesIO()
    fake_sock = _FakeSocket(raw_request, output)
    client_addr = (environ.get("REMOTE_ADDR", "127.0.0.1"), 0)

    class _FakeServer:
        server_name = host
        server_port = int(environ.get("SERVER_PORT") or 443)

    try:
        RealAIAPIHandler(fake_sock, client_addr, _FakeServer())
    except Exception:
        pass  # send_error() will have written an HTTP error response to output

    # Read back whatever the handler wrote.
    output.seek(0)
    raw_resp = output.read()
    output.real_close()

    # Split HTTP response into header / body.
    sep_idx = raw_resp.find(b"\r\n\r\n")
    sep_len = 4
    if sep_idx == -1:
        sep_idx = raw_resp.find(b"\n\n")
        sep_len = 2
    if sep_idx == -1:
        start_response("502 Bad Gateway", [("Content-Type", "text/plain")])
        return [b"No response from handler"]

    header_part = raw_resp[:sep_idx].decode("utf-8", errors="replace")
    body_part = raw_resp[sep_idx + sep_len:]

    lines = header_part.replace("\r\n", "\n").split("\n")
    status_line = lines[0]  # e.g. "HTTP/1.1 200 OK"
    parts = status_line.split(" ", 2)
    status = f"{parts[1]} {parts[2]}" if len(parts) > 2 else "200 OK"

    resp_headers = []
    for line in lines[1:]:
        if ": " in line:
            name, _, val = line.partition(": ")
            resp_headers.append((name.strip(), val.strip()))

    start_response(status, resp_headers)
    return [body_part]


# Keep the handler alias for the legacy Vercel serverless-function API.
handler = RealAIAPIHandler
