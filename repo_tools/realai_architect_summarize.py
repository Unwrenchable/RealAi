#!/usr/bin/env python3
from pathlib import Path

CHUNKS_PATH = Path(r"C:\RealAI-clean\results\architect_output_chunks.txt")
OUT_PATH = Path(r"C:\RealAI-clean\results\architect_summary.txt")

def main():
    raw = CHUNKS_PATH.read_text()
    sections = [
        sec.strip()
        for sec in raw.split("===== CHUNK")
        if sec.strip()
    ]

    summary_lines = [
        "RealAI Architect Mode — Unified Summary",
        "========================================",
        "",
        "This file merges all chunk analyses into one unified correction plan.",
        "",
        "Key Findings:",
        ""
    ]

    for idx, sec in enumerate(sections):
        summary_lines.append(f"--- Summary of Chunk {idx+1} ---")
        summary_lines.append(sec[:2000])
        summary_lines.append("")

    OUT_PATH.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"[summarizer] wrote {OUT_PATH}")

if __name__ == "__main__":
    main()
