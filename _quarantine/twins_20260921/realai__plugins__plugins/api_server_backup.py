# api_server.py — root-level backward-compat shim
# The real implementation now lives in realai/api_server.py.
# This file allows `python api_server.py` to keep working.
from realai.api_server import main, run_server, RealAIAPIHandler  # noqa: F401

if __name__ == "__main__":
    main()
