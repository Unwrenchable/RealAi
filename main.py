"""Unified WSGI entrypoint for local development and serverless deployment."""

from realai.unified_server import create_unified_app


def app(environ, start_response):
    """WSGI entrypoint for health checks and unified API routing."""
    return create_unified_app()(environ, start_response)


if __name__ == "__main__":
    from realai.unified_server import run_server

    run_server()
