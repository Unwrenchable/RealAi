#!/usr/bin/env python3
import json
import shutil
from pathlib import Path

SUMMARY_PATH = Path(r"C:\RealAI-clean\results\architect_summary.txt")
ROOT = Path(r"C:\RealAI-clean")
LOG_PATH = Path(r"C:\RealAI-clean\results\autofix_log.json")

def main():
    summary = SUMMARY_PATH.read_text()
    lines = summary.split("\n")

    moves = []
    deletes = []

    for line in lines:
        if "MOVE →" in line:
            parts = line.split("MOVE →")[1].split("→")
            src = parts[0].strip()
            dest = parts[1].strip()
            moves.append((src, dest))

        if "DELETE →" in line:
            deletes.append(line.split("DELETE →")[1].strip())

    log = {"moves": [], "deletes": []}

    for src, dest in moves:
        abs_src = ROOT / src
        abs_dest = ROOT / dest

        try:
            abs_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(abs_src), str(abs_dest))
            log["moves"].append({"src": src, "dest": dest})
            print(f"[autofix] moved {src} → {dest}")
        except Exception as e:
            print(f"[autofix] failed to move {src}: {e}")

    for target in deletes:
        abs_target = ROOT / target
        try:
            if abs_target.is_file():
                abs_target.unlink()
            elif abs_target.is_dir():
                shutil.rmtree(abs_target)
            log["deletes"].append(target)
            print(f"[autofix] deleted {target}")
        except Exception as e:
            print(f"[autofix] failed to delete {target}: {e}")

    LOG_PATH.write_text(json.dumps(log, indent=2))
    print(f"[autofix] wrote log {LOG_PATH}")

if __name__ == "__main__":
    main()
