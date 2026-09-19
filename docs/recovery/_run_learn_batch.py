"""Batch learn RealAI-related local trees. No heal/GPU/orchestrator."""
from __future__ import annotations

import json
import time
from pathlib import Path

from realai.cli.craft import tool_learn
from realai.learn_git import compact_learn_result

SOURCES = [
    r"C:\RealAI-gold",
    r"C:\RealAi",
    r"C:\RealAI-clean",
    r"C:\RealAI-clean-backup",
    r"C:\realai-cold",
]

OUT = Path(r"C:\RealAI-clean\docs\recovery\_learn_batch_results.json")


def summarize(source: str, result: dict, elapsed: float) -> dict:
    src = result.get("source") if isinstance(result.get("source"), dict) else {}
    scan = result.get("scan") if isinstance(result.get("scan"), dict) else {}
    packet = result.get("packet") if isinstance(result.get("packet"), dict) else {}
    return {
        "source": source,
        "exists": Path(source).exists(),
        "ok": bool(result.get("ok")),
        "error": result.get("error"),
        "heal": bool(result.get("heal")),
        "slug": result.get("slug"),
        "kind": src.get("kind"),
        "path": src.get("path") or source,
        "cloned": bool(src.get("cloned")),
        "packet_path": result.get("packet_path"),
        "docs_path": result.get("docs_path"),
        "fingerprint_count": packet.get("fingerprint_count")
        if packet.get("fingerprint_count") is not None
        else len(packet.get("fingerprints") or []),
        "files_scanned": scan.get("files") or scan.get("file_count") or scan.get("n_files"),
        "branches": scan.get("branches") or scan.get("branch_count"),
        "shape_errors": result.get("shape_errors") or [],
        "wrote_plugin": bool(result.get("wrote_plugin")),
        "elapsed_sec": round(elapsed, 2),
    }


def main() -> int:
    rows = []
    for source in SOURCES:
        started = time.time()
        print(f"LEARN {source} ...", flush=True)
        if not Path(source).exists():
            row = {
                "source": source,
                "exists": False,
                "ok": False,
                "error": "path_not_found",
                "heal": False,
                "elapsed_sec": 0.0,
            }
            rows.append(row)
            print(json.dumps(row), flush=True)
            continue
        try:
            # Caps keep huge trees (clean / backup) bounded but still prove learn works.
            raw = tool_learn(
                source=source,
                write=False,
                max_files=400,
                max_branches=12,
            )
            result = compact_learn_result(raw)
        except Exception as exc:
            result = {"ok": False, "error": str(exc), "heal": False}
        row = summarize(source, result, time.time() - started)
        rows.append(row)
        print(json.dumps(row, default=str), flush=True)

    payload = {
        "ok": all(r.get("ok") for r in rows if r.get("exists")),
        "count": len(rows),
        "results": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"WROTE {OUT}", flush=True)
    print(json.dumps({"ok": payload["ok"], "count": payload["count"]}, indent=2), flush=True)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
