"""
Vercel-compatible Python entrypoint.

This file exists so platforms like Vercel can detect a standard Python
entrypoint (`main.py`) and import a callable named `app`.
"""

def app(environ, start_response):
    """Minimal WSGI app for serverless health and default status routes."""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if method != "GET":
        body = b'{"error":"Method not allowed"}'
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body)))]
        start_response("405 Method Not Allowed", headers)
        return [body]

    if path == "/health":
        body = b'{"status":"healthy","model":"realai-2.0"}'
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body)))]
        start_response("200 OK", headers)
        return [body]

    body = b'{"message":"RealAI deployment is live. Use /health for status."}'
    headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body)))]
    start_response("200 OK", headers)
    return [body]


if __name__ == "__main__":
    from api_server import run_server

    run_server()
