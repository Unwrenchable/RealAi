"""RealAI Hive CLI — orchestrator-centric, agent-aware, GPU-honest."""

__all__ = ["main"]


def main(argv=None):
    from realai.cli.hive.app import main as _main

    return _main(argv)
