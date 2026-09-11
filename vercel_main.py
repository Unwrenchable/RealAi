# vercel_main.py
def app(environ, start_response):
    """Minimal WSGI app for Vercel health checks."""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if method != "GET":
        body = b'{"error":"Method not allowed"}'
        start_response("405 Method Not Allowed", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body)))
        ])
        return [body]

    if path == "/health":
        body = b'{"status":"healthy","model":"realai-2.0"}'
        start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body)))
        ])
        return [body]

    body = b'{"message":"RealAI deployment is live. Use /health for status."}'
    start_response("200 OK", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body)))
    ])
    return [body]
