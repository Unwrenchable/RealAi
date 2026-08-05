# api_server.py — root-level backward-compat shim
# The real implementation now lives in realai/api_server.py.
# This file allows `python api_server.py` to keep working.
import warnings

from realai.api_server import main, run_server, RealAIAPIHandler  # noqa: F401


def _warn_legacy_entrypoint() -> None:
    warnings.warn(
        "Deprecated entrypoint: use 'python -m realai.api_server' instead of 'python api_server.py'.",
        FutureWarning,
        stacklevel=2,
    )


if __name__ == "__main__":
    _warn_legacy_entrypoint()
    main()
