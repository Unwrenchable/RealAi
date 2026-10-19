"""Read-only shallow mirror of Travis's approved repos for repo_search / the repo_corpus adapter.

  python -m tools.repo_mirror --dry-run                     # plan only: no network, no writes
  python -m tools.repo_mirror [--out D:\\ARCHIVE\\repo-mirror] [--repos Rack_em_up overseer-bot-ai ...]

* Output must be under D:\\ARCHIVE (Travis's storage rule); anything else is refused.
* Repos: realai.hive_tools.repo_search.REPOS (searchable ones). Excluded/skipped repos (LustLink, reverse-phone-search,
  Productivitybot, Domain-bot, duplicates) and refusal-only Token-scalper are never cloned.
* Shallow, partial, sparse: ``git clone --depth 1 --filter=blob:none --no-checkout --sparse`` then a non-cone
  sparse-checkout that never fetches or writes secret-bearing files (.env*, .npmrc, keys, credential/wallet files),
  vendored/build dirs or binaries. Symlinks are checked out as plain files (core.symlinks=false). Public HTTPS only,
  no credentials (GIT_TERMINAL_PROMPT=0).
* Never overwrites: a repo dir that already exists is skipped (mirror into a new --out to refresh); an existing
  manifest is backed up before it is rewritten. Nothing is deleted.
* Writes ``repo_mirror_manifest.json`` (commit, SHA256 per file, sizes, blocked paths), ``secrets-report-<stamp>.json``
  (secret TYPES and paths only, never values; flagged files are added to ``blocked`` so repo_search refuses them) and
  appends to ``ACTIONS.log``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import ntpath
import os
import shutil
import subprocess
import sys
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from realai.hive_tools.repo_search import (BINARY_EXT, BLOCKED_DIRS, EXCLUDED_REPOS, OWNER, REPOS,  # noqa: E402
                                           blocked_name, find_secret_types, searchable)

ARCHIVE_ROOT = r"D:\ARCHIVE"
DEFAULT_OUT = r"D:\ARCHIVE\repo-mirror"
URL_TEMPLATE = "https://github.com/{owner}/{repo}.git"
MAX_MIRROR_FILE = 1024 * 1024  # larger files stay on disk but are blocked for repo_search / the corpus

SPARSE_PATTERNS: List[str] = (
    ["/*"]
    + [f"!**/{d}/" for d in sorted(BLOCKED_DIRS) if d != ".git"]
    + ["!**/.env", "!**/.env.*", "**/.env.example", "**/.env.sample", "**/.env.template",
       "!**/.npmrc", "!**/.pypirc", "!**/.netrc", "!**/.git-credentials", "!**/id_rsa*", "!**/id_dsa*", "!**/id_ecdsa*",
       "!**/id_ed25519*", "!**/*.pem", "!**/*.key", "!**/*.p12", "!**/*.pfx", "!**/*.keystore", "!**/*.jks", "!**/*.kdbx",
       "!**/*credential*", "!**/*Credential*", "!**/*CREDENTIAL*", "!**/*secret*.json", "!**/*secret*.env", "!**/*secret*.yml",
       "!**/*secret*.yaml", "!**/*secret*.txt", "!**/*wallet*.json", "!**/*wallet*.txt", "!**/*keypair*", "!**/*mnemonic*",
       "!**/*seed*phrase*", "!**/*seed_phrase*"]
    + [f"!**/*{e}" for e in sorted(BINARY_EXT)]
)


def default_repos() -> List[str]:
    return [r for r in REPOS if searchable(r)]


def under_archive(out: str, archive_root: str = ARCHIVE_ROOT) -> bool:
    """True if `out` is archive_root or below it (Windows paths compared case-insensitively; '..' resolved)."""
    if _win(archive_root):
        o = PureWindowsPath(ntpath.normpath(str(out)))
        a = PureWindowsPath(ntpath.normpath(archive_root))
        op, ap = [p.lower() for p in o.parts], [p.lower() for p in a.parts]
        return o.is_absolute() and op[: len(ap)] == ap
    o, a = Path(out).resolve(), Path(archive_root).resolve()
    return o == a or a in o.parents


def _win(p: str) -> bool:
    return os.name == "nt" or (len(str(p)) > 1 and str(p)[1] == ":")


def _join(out: str, repo: str) -> str:
    return str(PureWindowsPath(out) / repo) if _win(out) else str(Path(out) / repo)


def plan(repos: List[str], out: str, owner: str = OWNER, url_template: str = URL_TEMPLATE) -> Dict[str, Any]:
    steps = []
    for r in repos:
        dst = _join(out, r)
        url = url_template.format(owner=owner, repo=r)
        steps.append({"repo": r, "tier": REPOS[r]["tier"], "url": url, "dest": dst, "commands": [
            ["git", "-c", "core.symlinks=false", "clone", "--depth", "1", "--single-branch", "--filter=blob:none", "--no-checkout",
             "--sparse", url, dst],
            ["git", "-C", dst, "sparse-checkout", "set", "--no-cone", "--stdin"],
            ["git", "-C", dst, "-c", "core.symlinks=false", "checkout"]]})
    return {"out": out, "repos": repos, "sparse_patterns": SPARSE_PATTERNS, "steps": steps,
            "excluded": list(EXCLUDED_REPOS) + [r for r in REPOS if not searchable(r)]}


def _git(args: List[str], stdin: Optional[str] = None, timeout: int = 900) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "GCM_INTERACTIVE": "never"}
    return subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=timeout, env=env)


def scan_repo(dst: Path) -> Dict[str, Any]:
    """SHA256 manifest + secret types per file (values never stored). Blocks large / flagged / blocked-name files."""
    files: Dict[str, Dict[str, Any]] = {}
    blocked: List[str] = []
    findings: List[Dict[str, Any]] = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(dst):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            rel = p.relative_to(dst).as_posix()
            data = p.read_bytes()
            total += len(data)
            files[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            if any(blocked_name(part) for part in rel.split("/")):
                blocked.append(rel)
                findings.append({"path": rel, "types": ["blocked_filename"]})
                continue
            if len(data) > MAX_MIRROR_FILE:
                blocked.append(rel)
                continue
            if b"\0" in data[:4096]:
                continue
            types = find_secret_types(data.decode("utf-8", errors="replace"))
            if types:
                blocked.append(rel)
                findings.append({"path": rel, "types": types})
    return {"files": files, "file_count": len(files), "bytes": total, "blocked": sorted(set(blocked)), "secret_findings": findings}


def _log(out: Path, msg: str) -> None:
    with (out / "ACTIONS.log").open("a", encoding="utf-8") as f:
        f.write(f"{_dt.datetime.now().isoformat(timespec='seconds')} {msg}\n")


def mirror(repos: List[str], out: str, owner: str = OWNER, url_template: str = URL_TEMPLATE,
           archive_root: str = ARCHIVE_ROOT, log=print) -> Dict[str, Any]:
    if not under_archive(out, archive_root):
        raise SystemExit(f"refused: --out {out} is not under {archive_root}")
    bad = [r for r in repos if r in EXCLUDED_REPOS or not searchable(r)]
    if bad:
        raise SystemExit(f"refused: not in the approved searchable allowlist: {', '.join(bad)}")
    outp = Path(out)
    outp.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    man_p = outp / "repo_mirror_manifest.json"
    man: Dict[str, Any] = json.loads(man_p.read_text(encoding="utf-8")) if man_p.is_file() else {}
    man.setdefault("repos", {})
    report: Dict[str, Any] = {"stamp": stamp, "note": "secret TYPES and paths only; values are never read out or stored",
                              "repos": {}}
    _log(outp, f"start mirror {stamp}: {', '.join(repos)}")
    for step in plan(repos, out, owner, url_template)["steps"]:
        r, dst = step["repo"], Path(step["dest"])
        if dst.exists():
            log(f"skip {r}: {dst} exists (mirror into a new --out to refresh)")
            _log(outp, f"skip {r}: exists")
            continue
        c1, c2, c3 = step["commands"]
        p = _git(c1)
        if p.returncode != 0:
            log(f"FAIL clone {r}: {p.stderr.strip()[-300:]}")
            _log(outp, f"fail clone {r}")
            continue
        p = _git(c2, stdin="\n".join(SPARSE_PATTERNS) + "\n")
        if p.returncode == 0:
            p = _git(c3)
        if p.returncode != 0:
            log(f"FAIL checkout {r}: {p.stderr.strip()[-300:]}")
            _log(outp, f"fail checkout {r}")
            continue
        commit = _git(["git", "-C", str(dst), "rev-parse", "HEAD"]).stdout.strip()
        info = scan_repo(dst)
        man["repos"][r] = {"commit": commit, "tier": REPOS[r]["tier"], "url": step["url"], "mirrored": stamp,
                           **{k: info[k] for k in ("file_count", "bytes", "blocked", "files")}}
        report["repos"][r] = info["secret_findings"]
        log(f"ok {r}: {info['file_count']} files, {info['bytes'] / 1e6:.1f} MB, commit {commit[:12]}, "
            f"blocked {len(info['blocked'])}, secret-type findings {len(info['secret_findings'])}")
        _log(outp, f"ok {r} {commit[:12]} files={info['file_count']} blocked={len(info['blocked'])}")
    if man_p.is_file():
        shutil.copy2(man_p, outp / f"repo_mirror_manifest.json.bak-{stamp}")
    man.update(updated=stamp, owner=owner, sparse_patterns=SPARSE_PATTERNS)
    man_p.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    rep_p = outp / f"secrets-report-{stamp}.json"
    rep_p.write_text(json.dumps(report, indent=1), encoding="utf-8")
    _log(outp, f"done {stamp}: manifest + {rep_p.name}")
    return {"manifest": str(man_p), "secrets_report": str(rep_p), "repos": sorted(man["repos"]),
            "secret_findings": {r: len(v) for r, v in report["repos"].items()}}


def main(argv=None, archive_root: str = ARCHIVE_ROOT) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.repo_mirror")
    ap.add_argument("--out", default=DEFAULT_OUT, help=f"mirror root (must be under {ARCHIVE_ROOT})")
    ap.add_argument("--repos", nargs="*", help="subset of the approved allowlist (default: all searchable)")
    ap.add_argument("--owner", default=OWNER)
    ap.add_argument("--dry-run", action="store_true", help="print the plan only (no network, no writes)")
    ap.add_argument("--url-template", default=URL_TEMPLATE, help=argparse.SUPPRESS)  # tests: file:// sources
    a = ap.parse_args(argv)
    repos = a.repos or default_repos()
    unknown = [r for r in repos if r not in REPOS or r in EXCLUDED_REPOS or not searchable(r)]
    if unknown:
        print(f"refused: not in the approved searchable allowlist: {', '.join(unknown)}")
        return 2
    if not under_archive(a.out, archive_root):
        print(f"refused: --out {a.out} is not under {archive_root}")
        return 2
    if a.dry_run:
        print(json.dumps(plan(repos, a.out, a.owner, a.url_template), indent=1))
        return 0
    try:
        res = mirror(repos, a.out, a.owner, a.url_template, archive_root)
    except SystemExit as exc:
        print(exc)
        return 2
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
