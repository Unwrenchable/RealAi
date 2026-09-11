from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
LOG = HOME / "structure.log"

REQUIRED = [
    HOME / "realai/agent_runtime",
    HOME / "realai/world_model",
    HOME / "realai/plugins",
    HOME / "apps/vscode",
    HOME / "apps/dashboard",
    HOME / "recovered"
]

def main():
    LOG.write_text("=== RealAI Unified Structure Validator ===\n")

    for path in REQUIRED:
        if not path.exists():
            LOG.write_text(f"Missing: {path}\n")
            path.mkdir(parents=True, exist_ok=True)
            LOG.write_text(f"Created: {path}\n")
        else:
            LOG.write_text(f"OK: {path}\n")

if __name__ == "__main__":
    main()
