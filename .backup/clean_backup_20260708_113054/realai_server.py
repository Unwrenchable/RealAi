"""
RealAI Authoritative Launcher

This is the default and authoritative launcher for Fusion UI + unified API.
"""

import os

# Force Fusion UI + auth/dev defaults
os.environ.setdefault("REALAI_DEFAULT_UI", "fusion")
os.environ.setdefault("REALAI_UI_PATH", "fusion-ui")
os.environ.setdefault("REALAI_SKIP_AUTH", "true")
os.environ.setdefault("REALAI_CLEAN_STUB", "true")

def _is_enabled(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def main():
    host = os.environ.get("REALAI_HOST", "127.0.0.1")
    port_str = os.environ.get("REALAI_PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        port = 8000

    use_structured = _is_enabled(os.environ.get("REALAI_USE_STRUCTURED", "0"))

    print("=== RealAI Authoritative Fusion Server ===")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"REALAI_DEFAULT_UI={os.environ.get('REALAI_DEFAULT_UI')}")
    print(f"REALAI_UI_PATH={os.environ.get('REALAI_UI_PATH')}")
    print(f"REALAI_CLEAN_STUB={os.environ.get('REALAI_CLEAN_STUB')}")
    print(f"REALAI_USE_STRUCTURED={os.environ.get('REALAI_USE_STRUCTURED', '0')}")

    if use_structured:
        print("⚙️  Structured mode enabled via REALAI_USE_STRUCTURED=1")
        from realai.server.app import main as structured_main
        structured_main(host=host, port=port)
        return

    from realai.api_server import run_server
    run_server(host=host, port=port)


if __name__ == "__main__":
    main()
