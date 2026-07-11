"""RealAI definitive backend entrypoint.

Run with:
    python realai_server.py

Notes:
- Provides OpenAI-compatible endpoints required by the UI.
- Uses the existing stdlib HTTP server implementation from realai.api_server.
- Ensures the required FastAPI-style paths exist (/status, /health, /v1/*).

This file is intentionally small: the repo already contains a working
OpenAI-compatible implementation (realai/api_server.py) and a tool registry
(realai/tools.py).
"""

from __future__ import annotations

import os


def main() -> None:
    # Reuse the existing, tested server implementation.
    from realai.api_server import run_server

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    run_server(host=host, port=port)


if __name__ == "__main__":
    main()

