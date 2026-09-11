#!/usr/bin/env python3
"""
Curated promote — APPLY by default.

Unlike dump scanners, this only touches a short allowlist of paths.
No bulk copy. No mangled C_Users_* basenames.

  python scripts/curated_promote.py           # apply
  python scripts/curated_promote.py --dry-run
  python scripts/curated_promote.py --force   # overwrite different content
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "scan_results" / "curated_promote_allowlist.json"
LOG = ROOT / "recovered" / "CURATED_PROMOTE_LOG.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(p: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def resolve(p: str) -> Path:
    """Resolve relative-to-ROOT paths; map C:/... to /mnt/c/... under WSL."""
    import sys
    s = (p or "").strip().replace("\\", "/")
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():
        drive, rest = s[0].lower(), s[2:].lstrip("/")
        if sys.platform.startswith("win"):
            return Path(f"{drive.upper()}:/{rest}" if rest else f"{drive.upper()}:/")
        return Path(f"/mnt/{drive}") / rest if rest else Path(f"/mnt/{drive}")
    path = Path(s)
    if path.is_absolute():
        return path
    return ROOT / s


def first_existing(cands: List[str]) -> Optional[Path]:
    for c in cands:
        p = resolve(c)
        if p.is_file():
            return p
    return None


def ensure_parent(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)


def apply_item(item: Dict[str, Any], dry_run: bool, force: bool) -> Dict[str, Any]:
    iid = item.get("id") or "?"
    mode = item.get("mode") or "if_missing_or_smaller"
    dest = resolve(str(item["dest"]))
    rec: Dict[str, Any] = {"id": iid, "dest": str(dest), "mode": mode}

    if mode == "keep_live":
        # Packages (e.g. realai/agent_runtime/) are dirs — still "live"
        # Also accept dest.py stub vs dest/ package (common after nest pin)
        candidates = [dest]
        if dest.suffix == ".py":
            candidates.append(dest.with_suffix(""))
        alive = any(c.is_file() or c.is_dir() for c in candidates)
        live_path = next((c for c in candidates if c.is_file() or c.is_dir()), dest)
        rec["action"] = "keep_live" if alive else "missing_live"
        rec["ok"] = alive
        rec["dest"] = str(live_path)
        if alive and live_path.is_dir():
            rec["note"] = "package_dir"
        return rec

    if mode == "write_if_missing":
        content = item.get("content") or ""
        if dest.is_file():
            rec["action"] = "skip_exists"
            rec["ok"] = True
            return rec
        if dry_run:
            rec["action"] = "would_write"
            rec["ok"] = True
            return rec
        ensure_parent(dest)
        dest.write_text(content, encoding="utf-8")
        rec["action"] = "wrote"
        rec["bytes"] = len(content.encode("utf-8"))
        rec["ok"] = True
        return rec

    src: Optional[Path] = None
    if item.get("src"):
        src = resolve(str(item["src"]))
        if not src.is_file():
            src = None
    if src is None and item.get("src_candidates"):
        src = first_existing(list(item["src_candidates"]))

    if src is None:
        rec["action"] = "skip_no_src"
        rec["ok"] = mode in ("first_existing_if_dest_missing", "if_missing_or_smaller")
        # ok=True only if dest already exists for optional items
        if dest.is_file():
            rec["action"] = "dest_ok_no_src"
            rec["ok"] = True
        return rec

    rec["src"] = str(src)

    if mode == "first_existing_if_dest_missing":
        if dest.is_file() and not force:
            rec["action"] = "skip_dest_exists"
            rec["ok"] = True
            return rec
    elif mode == "if_missing_or_smaller":
        if dest.is_file() and not force:
            if dest.stat().st_size >= src.stat().st_size:
                # same or larger
                sh_s, sh_d = sha256_file(src), sha256_file(dest)
                if sh_s and sh_d and sh_s == sh_d:
                    rec["action"] = "skip_same_hash"
                    rec["ok"] = True
                    return rec
                if dest.stat().st_size > src.stat().st_size:
                    rec["action"] = "skip_live_larger"
                    rec["ok"] = True
                    return rec
    elif mode == "always" or force:
        pass
    else:
        # default: if missing
        if dest.is_file() and not force:
            rec["action"] = "skip_exists"
            rec["ok"] = True
            return rec

    if dry_run:
        rec["action"] = "would_copy"
        rec["src_bytes"] = src.stat().st_size
        rec["ok"] = True
        return rec

    ensure_parent(dest)
    shutil.copy2(src, dest)
    rec["action"] = "copied"
    rec["bytes"] = dest.stat().st_size
    rec["ok"] = True
    return rec


def run(dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
    if not ALLOWLIST.is_file():
        return {"ok": False, "error": f"missing allowlist {ALLOWLIST}"}
    data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    items = data.get("items") or []
    results = []
    for item in items:
        results.append(apply_item(item, dry_run=dry_run, force=force))

    # ensure critical package inits for imports
    for rel, content in (
        ("realai/server/tools/__init__.py", '"""Server tools."""\n'),
        ("realai/memory/__init__.py", '"""Memory package."""\nfrom .engine import *  # noqa\n'),
        ("agents/agentx/.gitkeep", ""),
        ("training/data/.gitkeep", ""),
    ):
        p = ROOT / rel
        if not p.is_file() and not dry_run:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            results.append({"id": f"ensure:{rel}", "action": "wrote", "ok": True})

    # verify imports
    verify = {}
    if not dry_run:
        import sys
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        checks = [
            ("realai.aura_memory", "AuraMemory"),
            ("realai.memory.engine", "MEMORY_ENGINE"),
            ("realai.world_model", None),
            ("realai.agent_runtime", None),
            ("realai.v3_orchestrator", None),
            ("realai.self_heal", "run_curated_promote"),
        ]
        for mod, attr in checks:
            try:
                m = __import__(mod, fromlist=["*"])
                if attr and not hasattr(m, attr):
                    # self_heal may not have run_curated_promote yet
                    verify[mod] = "ok_import" if attr != "run_curated_promote" else "import_ok_attr_pending"
                else:
                    verify[mod] = "ok"
            except Exception as e:
                verify[mod] = f"fail:{e}"

    summary = {
        "ok": all(r.get("ok") for r in results if r.get("action") not in ("skip_no_src",)),
        "dry_run": dry_run,
        "force": force,
        "applied_at": utc(),
        "copied": sum(1 for r in results if r.get("action") == "copied"),
        "wrote": sum(1 for r in results if r.get("action") == "wrote"),
        "skipped": sum(1 for r in results if str(r.get("action", "")).startswith("skip")),
        "results": results,
        "verify": verify,
    }

    if not dry_run:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        md = ROOT / "scan_results" / "CURATED_PROMOTE.md"
        lines = [
            "# Curated promote log",
            "",
            f"Applied: {summary['applied_at']}",
            f"Copied: {summary['copied']}  Wrote: {summary['wrote']}  Skipped: {summary['skipped']}",
            "",
            "## Results",
            "",
        ]
        for r in results:
            lines.append(f"- **{r.get('id')}**: `{r.get('action')}` → `{r.get('dest','')}`")
        lines += ["", "## Import verify", ""]
        for k, v in (verify or {}).items():
            lines.append(f"- `{k}`: {v}")
        md.write_text("\n".join(lines), encoding="utf-8")

    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Curated promote — apply by default")
    ap.add_argument("--dry-run", action="store_true", help="Do not write files")
    ap.add_argument("--force", action="store_true", help="Overwrite existing dest")
    args = ap.parse_args()
    # APPLY BY DEFAULT (opposite of old promote_gold)
    dry = bool(args.dry_run)
    summary = run(dry_run=dry, force=bool(args.force))
    print(json.dumps({
        "ok": summary.get("ok"),
        "dry_run": dry,
        "copied": summary.get("copied"),
        "wrote": summary.get("wrote"),
        "skipped": summary.get("skipped"),
        "verify": summary.get("verify"),
        "log": str(LOG) if not dry else None,
    }, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
