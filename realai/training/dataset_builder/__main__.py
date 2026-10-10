from __future__ import annotations

import argparse
import json
import sys

from .pipeline import build, load_config


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m realai.training.dataset_builder")
    ap.add_argument("--config", required=True, help="JSON or YAML build config")
    ap.add_argument("--dry-run", action="store_true", help="compute everything, write nothing")
    ap.add_argument("--name", default=None, help="override dataset name")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.name:
        cfg["name"] = args.name
    res = build(cfg, dry_run=args.dry_run)
    json.dump(res.manifest, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
