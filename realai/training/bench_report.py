"""Compare train_sft --bench results: python -m realai.training.bench_report <bench dir or bench.json> ...

Prints one line per run (s/step, tok/s, peak VRAM, padding efficiency, OOMs, projected full run) and the speedup
of each run against the first one (the baseline). Read-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load(p: str) -> Dict[str, Any]:
    f = Path(p)
    f = f / "bench.json" if f.is_dir() else f
    b = json.loads(f.read_text(encoding="utf-8"))
    b["_name"] = f.parent.name
    return b


def sps(b: Dict[str, Any]) -> float:
    return float(b.get("sec_per_step_after_first") or b.get("sec_per_step") or 0)


def table(benches: List[Dict[str, Any]]) -> str:
    base = sps(benches[0]) if benches else 0
    head = f"{'run':34} {'s/step':>7} {'tok/s':>7} {'VRAM GB':>8} {'pad eff':>8} {'OOMs':>5} {'full run':>9} {'speedup':>8}"
    lines = [head, "-" * len(head)]
    for b in benches:
        s = sps(b)
        sp = b.get("speed") or {}
        lines.append(f"{b['_name'][:34]:34} {s:7.1f} {float(b.get('tokens_per_s') or 0):7.0f} "
                     f"{str(b.get('peak_vram_gb') or '-'):>8} {float(b.get('padding_efficiency') or 0):8.3f} "
                     f"{int(sp.get('ooms') or 0):5d} {float(b.get('projected_full_run_min') or 0) / 60:8.1f}h "
                     f"{(base / s if s and base else 0):7.2f}x")
    lines.append("speedup = baseline s/step / run s/step (same rows per optimizer step); full run = projected "
                 "total training time. OOMs > 0 or skipped rows mean the profile is too big for this GPU.")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    found = []
    for a in argv:
        try:
            found.append(load(a))
        except (OSError, ValueError) as exc:
            print(f"skip {a}: {exc}")
    if not found:
        print("no bench.json found")
        return 1
    print(table(found))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
