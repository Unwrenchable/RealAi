import io

from realai.unified_server import create_unified_app


def _call_wsgi(app, path="/health", method="GET"):
    response = {}
    body_buffer = io.BytesIO()

    def start_response(status, headers, exc_info=None):
        response["status"] = status
        response["headers"] = dict(headers)

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8000",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    body = app(environ, start_response)
    if isinstance(body, (bytes, bytearray)):
        body_buffer.write(body)
    else:
        for chunk in body:
            body_buffer.write(chunk)

    response["body"] = body_buffer.getvalue()
    return response


def test_unified_app_serves_health_endpoint():
    app = create_unified_app()
    response = _call_wsgi(app, "/health")

    assert response["status"] == "200 OK"
    assert response["headers"]["Content-Type"].startswith("application/json")
    assert b"status" in response["body"]


def test_unified_app_serves_root_info():
    app = create_unified_app()
    response = _call_wsgi(app, "/")

    assert response["status"] == "200 OK"
    assert b"RealAI" in response["body"]
