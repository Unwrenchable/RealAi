"""
RealAI Craft Chat — portable streaming agent for *any* project folder.

  Canonical install : C:\\RealAI-clean\\realai\\cli\\craft.py
  realai                      # in any repo → workspace = cwd
  realai chat "fix the bug"
  realai heal
  /read /write /list /grep /git /heal /doctor /gpu
  /dispatch all               # run the automation pipeline (nested-aware)
  /walk /scripts /run-script  # whole-repo nested walk + run scripts any level

HOME (install): models, package, Vulkan, scripts, logs
WORKSPACE (project): file tools + git + project heal

Master cycle: paste the unified prompt or run:
  python scripts/auto_update_pipeline.py
  python scripts/self_heal_loop.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import traceback
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generator, Optional

from realai.workspace import (
    apply_workspace,
    default_gguf,
    is_realai_product_tree,
    product_root,
    realai_home,
    realai_workspace,
    safe_under_read,
    safe_under_write,
    workspace_banner,
)

VULKAN_DIR = Path(os.environ.get("REALAI_VULKAN_DIR") or r"C:\llama-vulkan")
GPU_HOST = os.environ.get("REALAI_GPU_HOST") or "127.0.0.1"
GPU_PORT = int(os.environ.get("REALAI_GPU_PORT") or "8080")

_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "recovered",
    "realai_og_mess",
    ".next",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}


def _home() -> Path:
    """Package/install dir (C:\\RealAI-clean\\realai)."""
    return realai_home()


def _ws() -> Path:
    """
    Canonical workspace root for craft / agents / multi / promote / file tools.

    Always C:\\RealAI-clean. Nested cwd such as C:\\RealAI-clean\\realai is
    clamped by realai.workspace.realai_workspace() — never becomes workspace.
    """
    apply_workspace()
    return realai_workspace()


def _product() -> Path:
    return product_root()


def _scripts() -> Path:
    """Automation scripts under the workspace root (not the package dir)."""
    from realai.workspace import workspace_scripts

    return workspace_scripts(_home())


# ---------------------------------------------------------------------------
# Tools (file ops → WORKSPACE; product ops → HOME)
# ---------------------------------------------------------------------------


def tool_doctor() -> dict[str, Any]:
    from realai.doctor import run_doctor

    doc = run_doctor(json_mode=True)
    doc["workspace"] = str(_ws())
    doc["home"] = str(_home())
    doc["mode"] = "product" if is_realai_product_tree() else "project"
    return doc


def tool_organs() -> dict[str, Any]:
    from modules.organs import hive_status

    return hive_status()


def tool_catalog(learn: bool = False) -> dict[str, Any]:
    apply_workspace()
    from realai.ability_catalog import coverage_summary, learn_keywords_from_scans, save_catalog

    path = str(save_catalog())
    cov = coverage_summary()
    learned = learn_keywords_from_scans() if learn else None
    return {
        "catalog_path": path,
        "coverage": cov,
        "learned": learned,
        "workspace": str(_ws()),
        "product_root": str(_product()),
    }


def tool_improve() -> dict[str, Any]:
    """Catalog self-improve on RealAI HOME (keywords + samples)."""
    out: dict[str, Any] = {"actions": [], "ok": False, "scope": "realai_home"}
    try:
        from realai.ability_catalog import (
            coverage_summary,
            emit_training_samples,
            learn_keywords_from_scans,
            save_catalog,
        )

        before = coverage_summary()
        bc = before.get("coverage") or {}
        out["before"] = {"weighted_pct": bc.get("weighted_pct"), "live_count": bc.get("live_count")}
        path = str(save_catalog())
        out["actions"].append(f"save_catalog -> {path}")
        learned = learn_keywords_from_scans(also_tools_cli=True)
        out["actions"].append(
            f"learn_keywords total={learned.get('total_count')} added={learned.get('added_count')}"
        )
        out["learned"] = learned
        try:
            samples = emit_training_samples()
            out["actions"].append(
                f"training_samples={samples.get('samples')} path={samples.get('path')}"
            )
        except Exception as e:
            out["actions"].append(f"training_samples skipped: {e}")
        after = coverage_summary()
        ac = after.get("coverage") or {}
        out["after"] = {
            "weighted_pct": ac.get("weighted_pct"),
            "live_count": ac.get("live_count"),
            "partial_count": ac.get("partial_count"),
        }
        out["ok"] = True
        out["summary"] = (
            f"Self-improve (HOME): coverage {out['before'].get('weighted_pct')}% → "
            f"{out['after'].get('weighted_pct')}%, LIVE "
            f"{out['before'].get('live_count')} → {out['after'].get('live_count')}"
        )
    except Exception as e:
        out["error"] = str(e)
        out["traceback"] = traceback.format_exc()[-600:]
    return out


def tool_deep_promote(
    mode: str = "full",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Actually run deep_promote_scan + deep_promote_wire and verify artifacts."""
    try:
        from abilities.deep_promote import run as deep_run

        return deep_run(context={"mode": mode, "dry_run": dry_run})
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc()[-800:],
            "summary": f"deep_promote failed: {e}",
        }


def tool_promote(mode: str = "deep", force: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """
    Real promote entrypoint (not a chat blurb).

    mode:
      deep     — curated allowlist + deep scan + thin wire (default)
      curated  — allowlist only
      scan     — deep map only
      wire     — thin wire only
      full     — curated + deep scan + wire (alias of deep)
    """
    apply_workspace()
    mode_l = (mode or "deep").lower().strip()
    out: dict[str, Any] = {
        "ok": False,
        "mode": mode_l,
        "actions": [],
        "steps": [],
        "home": str(_home()),
        "workspace": str(_ws()),
        "product_root": str(_product()),
    }
    try:
        if mode_l in {"curated", "allowlist", "deep", "full", "all"}:
            from realai.self_heal import run_curated_promote

            r = run_curated_promote(apply=not dry_run, force=force)
            out["steps"].append({"name": "curated_promote", "result": r})
            out["actions"].append(
                f"curated_promote ok={r.get('ok')} apply={not dry_run}"
            )
        if mode_l in {"deep", "full", "all", "scan", "wire", "map", "thin"}:
            deep_mode = "scan" if mode_l in {"scan", "map"} else (
                "wire" if mode_l in {"wire", "thin"} else "full"
            )
            d = tool_deep_promote(mode=deep_mode, dry_run=dry_run)
            out["steps"].append({"name": "deep_promote", "result": d})
            out["actions"].append(d.get("summary") or f"deep_promote ok={d.get('ok')}")
            out["artifacts"] = d.get("artifacts")
            out["wire_wrote"] = d.get("wire_wrote")
        def _step_ok(step: dict[str, Any]) -> bool:
            res = step.get("result") or {}
            if res.get("ok"):
                return True
            # curated may exit 1 on legacy missing_live; accept if deep artifacts exist
            if step.get("name") == "curated_promote":
                arts = out.get("artifacts") or {}
                if (arts.get("map_md") or {}).get("exists") and (
                    arts.get("queue") or {}
                ).get("exists"):
                    out["actions"].append(
                        "curated_promote soft-ok (deep artifacts present; check allowlist log)"
                    )
                    return True
            return False

        out["ok"] = all(_step_ok(s) for s in out["steps"]) if out["steps"] else False
        out["summary"] = (
            f"promote mode={mode_l} ok={out['ok']} steps={len(out['steps'])} "
            f"wire_wrote={out.get('wire_wrote')}"
        )
    except Exception as e:
        out["error"] = str(e)
        out["traceback"] = traceback.format_exc()[-800:]
        out["summary"] = f"promote failed: {e}"
    return out


def tool_heal(force: bool = False) -> dict[str, Any]:
    """
    Self-heal:
      - In RealAI product tree → curated promote + deep promote (real scripts)
      - In any other project → project diagnostics (git, structure, hints)
    """
    ws = _ws()
    out: dict[str, Any] = {
        "workspace": str(ws),
        "mode": "product" if is_realai_product_tree(ws) else "project",
        "ok": False,
        "actions": [],
    }

    if is_realai_product_tree(ws):
        try:
            # Ensure recovered JSON contract exists for older phases
            home = _home()
            rec = home / "recovered"
            scripts_rec = home / "scripts" / "recovered"
            try:
                rec.mkdir(parents=True, exist_ok=True)
                if scripts_rec.is_dir():
                    for name in (
                        "REALAI_REPO_SCAN.json",
                        "REALAI_SELF_IMPROVE_CANDIDATES.json",
                    ):
                        src = scripts_rec / name
                        dst = rec / name
                        if src.is_file() and (not dst.is_file() or src.stat().st_mtime > dst.stat().st_mtime):
                            dst.write_bytes(src.read_bytes())
                            out["actions"].append(f"synced recovered/{name}")
            except OSError as e:
                out["actions"].append(f"recovered sync skipped: {e}")

            promo = tool_promote(mode="deep", force=force, dry_run=False)
            out["promote"] = {
                "ok": promo.get("ok"),
                "summary": promo.get("summary"),
                "wire_wrote": promo.get("wire_wrote"),
                "artifacts": promo.get("artifacts"),
            }
            out["actions"].extend(promo.get("actions") or [])
            out["ok"] = bool(promo.get("ok"))
            out["summary"] = (
                f"Product heal+promote: {promo.get('summary')}"
                if out["ok"]
                else f"Product heal issues: {promo.get('summary') or promo.get('error')}"
            )
        except Exception as e:
            out["error"] = str(e)
            out["summary"] = f"Product heal failed: {e}"
        return out

    # Project mode — non-destructive diagnostics + light fixes
    out["actions"].append(f"project heal on {ws}")
    issues: list[str] = []

    # git
    git = tool_git_status()
    out["git"] = git
    if git.get("error"):
        issues.append(f"git: {git['error']}")
    else:
        out["actions"].append(f"branch={git.get('branch')}")

    # common project markers
    markers = {
        "package.json": (ws / "package.json").is_file(),
        "pyproject.toml": (ws / "pyproject.toml").is_file(),
        "requirements.txt": (ws / "requirements.txt").is_file(),
        "Cargo.toml": (ws / "Cargo.toml").is_file(),
        "go.mod": (ws / "go.mod").is_file(),
        "README": any((ws / n).is_file() for n in ("README.md", "README", "readme.md")),
        ".git": (ws / ".git").exists(),
    }
    out["markers"] = markers
    if not any(markers.values()):
        issues.append("no common project markers (package.json / pyproject / etc.)")

    # ensure .gitignore exists for node/python noise if missing
    gi = ws / ".gitignore"
    if not gi.is_file() and (markers.get("package.json") or markers.get("pyproject.toml")):
        defaults = [
            "node_modules/",
            "__pycache__/",
            ".venv/",
            "venv/",
            ".env",
            "dist/",
            "build/",
            "*.pyc",
            ".DS_Store",
        ]
        try:
            gi.write_text("\n".join(defaults) + "\n", encoding="utf-8")
            out["actions"].append("created .gitignore defaults")
        except OSError as e:
            issues.append(f"could not write .gitignore: {e}")

    # list top-level
    listing = tool_list(".")
    out["top_level"] = (listing.get("entries") or [])[:30]

    out["issues"] = issues
    out["ok"] = len(issues) == 0 or bool(markers.get(".git") or markers.get("README"))
    out["summary"] = (
        f"Project heal ({ws.name}): "
        f"{'looks ok' if out['ok'] else 'needs attention'}; "
        f"issues={len(issues)}. Ask craft to fix/write specific files."
    )
    out["hint"] = (
        "Chat: describe the bug or feature. Use /read PATH, then ask for a fix; "
        "use /write PATH to apply code. REALAI_HOME stays at install for GPU/models."
    )
    return out


def tool_gaps() -> dict[str, Any]:
    if not is_realai_product_tree():
        h = tool_heal()
        return {
            "mode": "project",
            "workspace": str(_ws()),
            "summary": h.get("summary"),
            "issues": h.get("issues"),
            "markers": h.get("markers"),
            "note": "Project mode — use /heal, /read, /write, /grep on this repo.",
        }
    doc = tool_doctor()
    cat = tool_catalog(learn=False)
    cov_wrap = cat.get("coverage") or {}
    cov = cov_wrap.get("coverage") if isinstance(cov_wrap.get("coverage"), dict) else cov_wrap
    fails = [c for c in (doc.get("checks") or []) if not c.get("ok")]
    gaps = []
    for f in fails[:5]:
        gaps.append({"area": f.get("name"), "detail": f.get("detail"), "severity": "fail"})
    wp, live = cov.get("weighted_pct"), cov.get("live_count")
    if wp is not None and float(wp) < 80:
        gaps.append(
            {
                "area": "ability_catalog_coverage",
                "detail": f"weighted={wp}% live={live} — use /improve",
                "severity": "improve",
            }
        )
    if not gaps:
        gaps.append(
            {
                "area": "ready",
                "detail": "Doctor green.",
                "severity": "info",
            }
        )
    return {
        "doctor_ok": doc.get("ok"),
        "coverage": {"weighted_pct": wp, "live_count": live},
        "top_gaps": gaps[:5],
        "workspace": str(_ws()),
    }


def tool_rackup(ability: str = "roc_info", payload: dict | None = None) -> dict[str, Any]:
    from plugins.rackup_coach import METADATA, invoke

    if not ability or ability in ("status", "meta", "info"):
        return {
            "version": METADATA.get("version"),
            "methods": METADATA.get("methods"),
            "roc": METADATA.get("roc"),
        }
    return invoke(
        {
            "ability": ability,
            "player": {"player_id": "craft-cli"},
            "payload": payload or {},
            "organs_enabled": True,
        }
    )


def tool_list(path: str = ".") -> dict[str, Any]:
    p, err = safe_under_read(_ws(), path)
    if err or p is None:
        return {"error": err or "bad path"}
    if not p.exists():
        return {"error": f"not found: {path}"}
    if p.is_file():
        return {"path": path, "type": "file", "size": p.stat().st_size}
    entries = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if child.name in _SKIP_DIRS or (child.name.startswith(".") and child.name not in (".env.example", ".gitignore")):
            continue
        entries.append({"name": child.name, "type": "dir" if child.is_dir() else "file"})
    return {"path": path, "workspace": str(_ws()), "entries": entries[:200]}


def tool_read(path: str, start: int = 1, limit: int = 80) -> dict[str, Any]:
    p, err = safe_under_read(_ws(), path)
    if err or p is None:
        return {"error": err or "bad path"}
    if not p.is_file():
        return {"error": f"not a file: {path}"}
    if p.stat().st_size > 2_000_000:
        return {"error": "file too large"}
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, int(start))
    limit = max(1, min(int(limit), 200))
    chunk = lines[start - 1 : start - 1 + limit]
    return {
        "path": path,
        "start": start,
        "end": start + len(chunk) - 1,
        "total_lines": len(lines),
        "content": "\n".join(f"{start + i}|{ln}" for i, ln in enumerate(chunk)),
    }


def tool_write(path: str, content: str = "", mode: str = "overwrite") -> dict[str, Any]:
    """Write file under WORKSPACE only (never EXTRA_READ roots). mode=overwrite|append."""
    p, err = safe_under_write(_ws(), path)
    if err or p is None:
        return {"error": err or "bad path"}
    # refuse obviously dangerous targets
    bad = {".git", "node_modules", "__pycache__"}
    if any(part in bad for part in p.parts):
        return {"error": "refusing to write under protected path"}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else str(content)
        # allow escaped newlines from slash-commands
        text = text.replace("\\n", "\n")
        if mode == "append" and p.is_file():
            with p.open("a", encoding="utf-8") as f:
                f.write(text)
        else:
            p.write_text(text, encoding="utf-8")
        return {
            "ok": True,
            "path": path,
            "bytes": len(text.encode("utf-8")),
            "mode": mode,
            "workspace": str(_ws()),
        }
    except OSError as e:
        return {"error": str(e)}


def tool_grep(pattern: str, path: str = ".", glob: str = "*", max_hits: int = 40) -> dict[str, Any]:
    import fnmatch

    root, err = safe_under_read(_ws(), path)
    if err or root is None:
        return {"error": err or "bad path"}
    try:
        rx = re.compile(pattern, re.I)
    except re.error as e:
        return {"error": f"bad pattern: {e}"}
    hits = []
    if root.is_file():
        walk_root = root.parent
        only = {root.name}
    else:
        walk_root = root
        only = None
    for dirpath, dirnames, filenames in os.walk(walk_root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if only is not None and fn not in only:
                continue
            if glob and glob != "*" and not fnmatch.fnmatch(fn, glob):
                continue
            fp = Path(dirpath) / fn
            try:
                if fp.stat().st_size > 1_000_000:
                    continue
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    try:
                        rel = str(fp.relative_to(_ws())).replace("\\", "/")
                    except ValueError:
                        rel = str(fp)
                    hits.append({"file": rel, "line": i, "text": line.strip()[:200]})
                    if len(hits) >= max_hits:
                        return {"pattern": pattern, "hits": hits, "truncated": True}
    return {"pattern": pattern, "hits": hits, "truncated": False, "workspace": str(_ws())}


def tool_model(name: str = "RealAI Hive") -> dict[str, Any]:
    """Select / brand the active craft chat model id (RealAI Hive by default)."""
    import os as _os

    raw = (name or "RealAI Hive").strip()
    try:
        from realai.model_catalog import build_catalog, resolve_model_for_backend

        # Ensure hive is registered
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(_scripts() / "register_realai_hive.py"),
                ],
                cwd=str(_home()),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception:
            pass

        backend, meta = resolve_model_for_backend(raw)
        resolved = meta.get("resolved_id") or "realai-hive"
        _os.environ["REALAI_DEFAULT_MODEL"] = str(resolved)
        # Persist for new terminals (best-effort)
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(
                key, "REALAI_DEFAULT_MODEL", 0, winreg.REG_EXPAND_SZ, str(resolved)
            )
            winreg.CloseKey(key)
        except Exception:
            pass

        cat = build_catalog()
        default = (cat.get("realai") or {}).get("default_model")
        return {
            "ok": True,
            "requested": raw,
            "resolved_id": resolved,
            "display_name": (meta.get("display_name") or resolved),
            "gguf_path": meta.get("gguf_path"),
            "gguf_filename": meta.get("gguf_filename"),
            "loaded_now": meta.get("loaded_now"),
            "backend_model_id": backend,
            "default_model": default,
            "switch_required": meta.get("switch_required"),
            "switch_cmd": meta.get("switch_cmd"),
            "note": meta.get("note"),
            "summary": (
                f"model={resolved} gguf={meta.get('gguf_filename')} "
                f"loaded_now={meta.get('loaded_now')} default={default}"
            ),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "summary": f"model select failed: {e}",
        }


def tool_walk_root(
    force: bool = False,
    deepen: bool = False,
    start: str = "",
) -> dict[str, Any]:
    """Recursive walk (deeper into every folder) → unify map + deepest nests."""
    home = _home()
    out_json = home / "scan_results" / "realai_root_walk.json"
    out_md = home / "scan_results" / "realai_root_walk.md"
    start = (start or "").strip().replace("\\", "/")

    # Cache only for plain /walk with no deepen/start
    if out_json.is_file() and not force and not deepen and not start:
        try:
            data = json.loads(out_json.read_text(encoding="utf-8"))
            deepest = data.get("deepest_nests") or []
            return {
                "ok": True,
                "cached": True,
                "path": str(out_json),
                "map_md": str(out_md) if out_md.is_file() else None,
                "scanned_dirs": data.get("scanned_dirs"),
                "max_depth_seen": data.get("max_depth_seen"),
                "module_count": data.get("module_count"),
                "nested_folder_count": data.get("nested_folder_count"),
                "runnable_script_count": data.get("runnable_script_count"),
                "js_file_count": data.get("js_file_count"),
                "json_file_count": data.get("json_file_count"),
                "deepest_nests": deepest[:12],
                "duplicate_basename_count": (data.get("unify") or {}).get(
                    "duplicate_basename_count"
                ),
                "summary": (
                    f"cached walk dirs={data.get('scanned_dirs')} "
                    f"max_depth={data.get('max_depth_seen')} "
                    f"scripts={data.get('runnable_script_count')} "
                    f"js={data.get('js_file_count')} json={data.get('json_file_count')} "
                    f"nests={data.get('nested_folder_count')} "
                    f"( /walk force | /walk deepen )"
                ),
            }
        except Exception:
            pass

    script = home / "tools" / "walk_root.py"
    if not script.is_file():
        script = home / "scripts" / "walk_root.py"

    cmd = [sys.executable, str(script), "--root", str(home), "--out", str(out_json)]
    if deepen:
        cmd.append("--deepen")
    if start:
        cmd.extend(["--start", start])

    try:
        if script.is_file():
            completed = subprocess.run(
                cmd,
                cwd=str(home),
                capture_output=True,
                text=True,
                timeout=3600,
                encoding="utf-8",
                errors="replace",
            )
            rc = completed.returncode
            stdout_tail = (completed.stdout or "")[-1500:]
            stderr_tail = (completed.stderr or "")[-800:]
        else:
            from core.realai_root_walker import RealAIRootWalker

            start_path = (home / start) if start else None
            RealAIRootWalker(
                home, out_json, deepen=deepen, start=start_path
            ).run()
            rc = 0
            stdout_tail = ""
            stderr_tail = ""

        data = {}
        if out_json.is_file():
            try:
                data = json.loads(out_json.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        ok = rc == 0 and bool(data)
        deepest = data.get("deepest_nests") or []
        return {
            "ok": ok,
            "cached": False,
            "deepen": deepen,
            "start": start or ".",
            "path": str(out_json),
            "map_md": str(out_md) if out_md.is_file() else data.get("map_md"),
            "returncode": rc,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "scanned_dirs": data.get("scanned_dirs"),
            "max_depth_seen": data.get("max_depth_seen"),
            "module_count": data.get("module_count"),
            "nested_folder_count": data.get("nested_folder_count"),
            "runnable_script_count": data.get("runnable_script_count"),
            "js_file_count": data.get("js_file_count"),
            "json_file_count": data.get("json_file_count"),
            "deepest_nests": deepest[:12],
            "leaf_nest_count": len(data.get("leaf_nests") or []),
            "duplicate_basename_count": (data.get("unify") or {}).get(
                "duplicate_basename_count"
            ),
            "summary": (
                f"walk ok={ok} deepen={deepen} start={start or '.'} "
                f"dirs={data.get('scanned_dirs')} max_depth={data.get('max_depth_seen')} "
                f"scripts={data.get('runnable_script_count')} "
                f"js={data.get('js_file_count')} json={data.get('json_file_count')} "
                f"nests={data.get('nested_folder_count')} "
                f"dupes={(data.get('unify') or {}).get('duplicate_basename_count')}"
            ),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "summary": f"walk failed: {e}"}


def tool_deep_unify(apply: bool = False, max_nests: int = 25) -> dict[str, Any]:
    """Deepen walk deepest nests → organize/patch/merge → auto-wire abilities."""
    home = _home()
    script = home / "scripts" / "deep_unify_walk.py"
    if not script.is_file():
        return {"ok": False, "error": f"missing {script}", "summary": "deep_unify_walk.py missing"}
    cmd = [
        sys.executable,
        str(script),
        "--root",
        str(home),
        "--max-nests",
        str(max(1, int(max_nests))),
    ]
    if apply:
        cmd.append("--apply")
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(home),
            capture_output=True,
            text=True,
            timeout=7200,
            encoding="utf-8",
            errors="replace",
        )
        report = home / "scan_results" / "DEEP_UNIFY_REPORT.json"
        data = {}
        if report.is_file():
            try:
                data = json.loads(report.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        return {
            "ok": completed.returncode == 0,
            "apply": apply,
            "returncode": completed.returncode,
            "stdout_tail": (completed.stdout or "")[-2000:],
            "stderr_tail": (completed.stderr or "")[-1000:],
            "report": str(report) if report.is_file() else None,
            "map_md": str(home / "scan_results" / "DEEP_UNIFY_REPORT.md"),
            "max_depth_seen": data.get("max_depth_seen"),
            "organize": data.get("organize"),
            "wire": data.get("wire"),
            "summary": (
                f"deep-unify apply={apply} exit={completed.returncode} "
                f"max_depth={data.get('max_depth_seen')} "
                f"organize={((data.get('organize') or {}).get('summary'))} "
                f"wire={data.get('wire')}"
            ),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "summary": f"deep-unify failed: {e}"}


def tool_list_scripts(query: str = "", limit: int = 40) -> dict[str, Any]:
    """List runnable scripts from nested walk index (any level)."""
    home = _home()
    walk_json = home / "scan_results" / "realai_root_walk.json"
    if not walk_json.is_file():
        w = tool_walk_root(force=False)
        if not w.get("ok") and not walk_json.is_file():
            return {
                "ok": False,
                "error": "no walk index — run /walk first",
                "walk": w,
                "summary": "missing realai_root_walk.json",
            }
    try:
        data = json.loads(walk_json.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

    q = (query or "").strip().lower()
    by_name = data.get("scripts_by_name") or {}
    rows = []
    for name, paths in sorted(by_name.items()):
        if q and q not in name.lower() and not any(q in p.lower() for p in paths):
            continue
        rows.append({"name": name, "paths": paths, "locations": len(paths)})
        if len(rows) >= max(1, limit):
            break
    return {
        "ok": True,
        "query": query,
        "count": len(rows),
        "total_names": len(by_name),
        "scripts": rows,
        "nested_folder_count": data.get("nested_folder_count"),
        "summary": f"{len(rows)} script name(s) (of {len(by_name)}) query={query!r}",
    }


def tool_run_script_any(
    name: str,
    timeout: int = 600,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Resolve and run a .py script from any nesting level under REALAI_HOME."""
    from core.realai_root_walker import resolve_script_from_walk

    home = _home()
    script_name = (name or "").strip()
    if not script_name:
        return {"ok": False, "error": "missing script name", "summary": "need a script name"}

    # Ensure index exists for better resolution
    walk_json = home / "scan_results" / "realai_root_walk.json"
    if not walk_json.is_file():
        tool_walk_root(force=False)

    path = resolve_script_from_walk(home, script_name)
    if path is None:
        return {
            "ok": False,
            "error": f"script not found: {script_name}",
            "summary": f"could not resolve {script_name} under {home}",
            "hint": "Try /walk then /scripts <name>",
        }
    try:
        rel = str(path.relative_to(home)).replace("\\", "/")
    except ValueError:
        rel = str(path)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "script": script_name,
            "path": str(path),
            "rel": rel,
            "summary": f"would run {rel}",
        }

    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(home),
            capture_output=True,
            text=True,
            timeout=max(30, int(timeout)),
            encoding="utf-8",
            errors="replace",
        )
        return {
            "ok": completed.returncode == 0,
            "script": script_name,
            "path": str(path),
            "rel": rel,
            "returncode": completed.returncode,
            "stdout_tail": (completed.stdout or "")[-2500:],
            "stderr_tail": (completed.stderr or "")[-1200:],
            "summary": f"ran {rel} exit={completed.returncode}",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "timeout",
            "path": str(path),
            "rel": rel,
            "summary": f"timeout running {rel}",
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(path), "summary": str(e)}


def tool_unify_nests(limit: int = 30) -> dict[str, Any]:
    """Show nested-folder + duplicate-basename unify view from the root walk."""
    home = _home()
    walk_json = home / "scan_results" / "realai_root_walk.json"
    if not walk_json.is_file():
        w = tool_walk_root(force=False)
        if not walk_json.is_file():
            return {"ok": False, "error": "no walk index", "walk": w}
    try:
        data = json.loads(walk_json.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

    nests = (data.get("nested_folders") or [])[: max(1, limit)]
    dupes = ((data.get("unify") or {}).get("duplicate_basenames") or [])[: max(1, limit)]
    multi = (data.get("unify") or {}).get("multi_location_scripts") or {}
    return {
        "ok": True,
        "path": str(walk_json),
        "map_md": str(home / "scan_results" / "realai_root_walk.md"),
        "nested_folders": nests,
        "duplicate_basenames": dupes,
        "multi_location_scripts": dict(list(multi.items())[:limit]),
        "js_file_count": data.get("js_file_count"),
        "json_file_count": data.get("json_file_count"),
        "summary": (
            f"nests={data.get('nested_folder_count')} "
            f"dupes={(data.get('unify') or {}).get('duplicate_basename_count')} "
            f"multi_scripts={len(multi)} "
            f"js={data.get('js_file_count')} json={data.get('json_file_count')}"
        ),
    }


def tool_organize_repo(apply: bool = False, refresh_walk: bool = False, limit: int = 500) -> dict[str, Any]:
    """Plan (or apply) moving/merging nested .py/.js/.json into proper locations."""
    home = _home()
    try:
        from core.repo_organizer import run_organize

        result = run_organize(
            root=home,
            apply=bool(apply),
            limit=int(limit),
            refresh_walk=bool(refresh_walk),
        )
        # compact preview for chat
        preview = []
        for r in result.get("results") or []:
            if str(r.get("action", "")).startswith("would") or r.get("action") in {
                "copied",
                "copied_enrich",
                "merged_json",
                "copied_json",
            }:
                preview.append(f"{r.get('action')}: {r.get('src')} → {r.get('dest')}")
            if len(preview) >= 20:
                break
        result["preview"] = preview
        return result
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc()[-800:],
            "summary": f"organize failed: {e}",
        }


def tool_architect_mode() -> dict[str, Any]:
    try:
        from realai.abilities.architect_mode import run_architect_mode
        return run_architect_mode()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_organs_task(goal: str) -> dict[str, Any]:
    try:
        from realai.agent_runtime import run_with_organs

        return run_with_organs(
            goal,
            context={
                "source": "craft-cli",
                "home": str(_home()),
                "workspace": str(_ws()),
            },
        )
    except Exception as e:
        return {"error": str(e)}


def tool_git_status() -> dict[str, Any]:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=_ws(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "-sb"],
            cwd=_ws(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return {"branch": branch, "status": status, "workspace": str(_ws())}
    except Exception as e:
        return {"error": str(e), "workspace": str(_ws())}


def tool_pwd() -> dict[str, Any]:
    return {
        "home": str(_home()),
        "workspace": str(_ws()),
        "mode": "product" if is_realai_product_tree() else "project",
        "banner": workspace_banner(),
        "gguf": str(default_gguf()),
    }


def tool_living_map() -> dict[str, Any]:
    if is_realai_product_tree():
        return {
            "mode": "product",
            "living": [
                "realai/",
                "core/",
                "modules/",
                "agent_tools/",
                "realai/agent_tools_gold/",
                "packages/sdk-ts/",
                "plugins/rackup_coach/",
                "scripts/",
            ],
            "snapshots": ["imports/external/*"],
            "archive_only": ["recovered/*"],
            "extra_read": "REALAI_EXTRA_READ_ROOTS for D:\\realai_archives, giant_hold, …",
            "workspace": str(_ws()),
        }
    return {
        "mode": "project",
        "workspace": str(_ws()),
        "note": "File tools are rooted here. Models/GPU come from REALAI_HOME.",
        "home": str(_home()),
    }


def _orch_base() -> str:
    return (os.environ.get("REALAI_API_BASE") or os.environ.get("REALAI_ORCH") or "http://127.0.0.1:8001").rstrip("/")


def tool_agents(query: str = "", limit: int = 30) -> dict[str, Any]:
    """Prefer live orchestrator registry GET /v1/agents (ONLINE)."""
    try:
        apply_workspace()
        q = (query or "").strip().lower()
        base = _orch_base()

        # /agents models → GET /v1/models
        if q in ("models", "model", "--models"):
            url = base + "/v1/models"
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    body = json.loads(resp.read().decode("utf-8", errors="replace"))
                return {
                    "ok": True,
                    "source": "orchestrator:/v1/models",
                    "url": url,
                    "models": body,
                    "workspace": str(_ws()),
                    "mode": "ONLINE",
                }
            except Exception as e:
                return {
                    "ok": False,
                    "error": f"GET {url} failed: {e}",
                    "workspace": str(_ws()),
                    "mode": "OFFLINE",
                }

        url = base + "/v1/agents"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
            data = body.get("data") if isinstance(body, dict) else body
            if not isinstance(data, list):
                data = []
            if q and q not in ("reload", "test", "test --all", "--all"):
                data = [
                    a
                    for a in data
                    if isinstance(a, dict) and q in json.dumps(a, default=str).lower()
                ]
            return {
                "ok": True,
                "source": "orchestrator:/v1/agents",
                "url": url,
                "count": len(data[: max(1, int(limit))]),
                "agents": data[: max(1, int(limit))],
                "total": body.get("count") if isinstance(body, dict) else len(data),
                "registry": body.get("source") if isinstance(body, dict) else None,
                "workspace": str(_ws()),
                "mode": "ONLINE",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"GET {url} failed: {e}",
                "hint": "Orchestrator must be up on :8001",
                "workspace": str(_ws()),
                "mode": "OFFLINE",
            }
    except Exception as e:
        return {"error": str(e), "workspace": str(_ws())}


def tool_tools() -> dict[str, Any]:
    try:
        from realai.v3_runtime_bridge import tools_catalog, list_agent_tools_tools, agent_tools_status

        cat = tools_catalog()
        names = [(t.get("function") or {}).get("name") for t in cat]
        gold = list_agent_tools_tools()
        return {
            "ok": True,
            "count": len(cat),
            "tools": names,
            "agent_tools": gold,
            "status": agent_tools_status().get("gold"),
        }
    except Exception as e:
        return {"error": str(e)}


def tool_agent_tools(
    action: str = "status",
    tool: str = "",
    payload: str | dict | None = None,
    profile: str = "balanced",
    dry_run: bool = True,
    query: str = "",
) -> dict[str, Any]:
    """Craft surface for living agent_tools gold package.

    Actions: status | tools | agents | profiles | assess | invoke
    """
    try:
        from realai.v3_runtime_bridge import (
            agent_tools_status,
            list_agent_tools_agents,
            list_access_profiles,
            list_agent_tools_tools,
            assess_agent_profile,
            invoke_agent_tool,
        )

        act = (action or "status").lower().strip()
        if act in ("status", "stat", "ok"):
            return agent_tools_status()
        if act in ("tools", "list_tools", "list-tools"):
            return list_agent_tools_tools()
        if act in ("agents", "list_agents", "list-agents"):
            return list_agent_tools_agents(limit=40, query=query)
        if act in ("profiles", "profile", "list_profiles"):
            return list_access_profiles()
        if act in ("assess",):
            # query = agent_id  profile= via profile arg
            return assess_agent_profile(query or tool, profile=profile)
        if act in ("invoke", "run", "call"):
            pl: dict[str, Any]
            if isinstance(payload, dict):
                pl = payload
            elif isinstance(payload, str) and payload.strip():
                try:
                    pl = json.loads(payload)
                except Exception:
                    # path-only shorthand for filesystem list
                    pl = {"operation": "list", "path": payload}
            else:
                pl = {"operation": "list", "path": "."}
            return invoke_agent_tool(
                tool or "filesystem",
                payload=pl,
                profile=profile,
                dry_run=bool(dry_run),
            )
        return {
            "ok": False,
            "error": f"unknown action:{act}",
            "usage": {
                "/at status": "gold package health",
                "/at tools": "wired tooling names",
                "/at agents [query]": "merged agent roster",
                "/at profiles": "access profiles",
                "/at assess <agent_id> [profile]": "assess agent vs profile",
                "/at invoke <tool> [json_payload]": "invoke gold tool (dry_run default)",
                "/at invoke-live <tool> [json]": "invoke with dry_run=false",
            },
        }
    except Exception as e:
        return {"error": str(e)}


def tool_multi(task: str, mode: str = "pipeline") -> dict[str, Any]:
    """ONLINE only: POST /v1/multi-agent/run on the live v3 orchestrator."""
    try:
        apply_workspace()
        base = _orch_base()
        url = base + "/v1/multi-agent/run"
        # Confirm health first — exact binding reason on failure.
        try:
            req_h = urllib.request.Request(base + "/health", method="GET")
            with urllib.request.urlopen(req_h, timeout=2) as resp:
                health = json.loads(resp.read().decode("utf-8", errors="replace"))
            print(f"[api] already_running → {base}/v1", flush=True)
        except Exception as e:
            return {
                "ok": False,
                "error": "orchestrator_offline",
                "binding": f"GET {base}/health failed: {e}",
                "workspace": str(_ws()),
                "mode": "OFFLINE",
            }

        payload = json.dumps(
            {
                "task": task,
                "mode": mode or "pipeline",
                "max_tokens": int(os.environ.get("REALAI_MULTI_MAX_TOKENS") or "384"),
                "temperature": float(os.environ.get("REALAI_MULTI_TEMPERATURE") or "0.3"),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + (os.environ.get("REALAI_API_KEY") or "local"),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8", errors="replace"))
        if not isinstance(result, dict):
            return {
                "ok": False,
                "error": "invalid_orch_response",
                "raw": str(result)[:500],
                "url": url,
            }
        result.setdefault("workspace", str(_ws()))
        result.setdefault("product_root", str(_product()))
        result.setdefault("url", url)
        result.setdefault("mode_flag", "ONLINE")
        result.setdefault("orch_health", health)
        # Reject silent fallback shapes if any older orch build returns them.
        if result.get("mode") == "pipeline_fallback":
            return {
                "ok": False,
                "error": "orch_returned_pipeline_fallback",
                "binding": "Live orchestrator returned offline fallback — restart v3_orchestrator after bridge patch",
                "result": result,
            }
        return result
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "binding": f"POST {_orch_base()}/v1/multi-agent/run failed: {e}",
            "workspace": str(_ws()),
            "mode": "OFFLINE",
        }


def tool_exec(name: str, **kwargs) -> dict[str, Any]:
    """Execute any orchestrator-native tool via v3_orchestrator._run_tool or bridge."""
    try:
        from realai.v3_orchestrator import _run_tool

        result = _run_tool(name, kwargs)
        # Fall through when orchestrator does not know the tool yet
        if isinstance(result, dict):
            err = str(result.get("error") or "")
            if err.startswith("unknown_tool:"):
                raise KeyError(err)
        return {"tool": name, "result": result}
    except Exception:
        pass
    try:
        from realai.v3_runtime_bridge import execute_registry_tool, workspace_tool

        if name.startswith("workspace_"):
            return workspace_tool(name, kwargs)
        return execute_registry_tool(name, kwargs)
    except Exception as e:
        return {"error": str(e)}


def tool_extend(goal: str = "") -> dict[str, Any]:
    from realai.server.tools.self_extend_tool import run as _r

    return _r({"goal": goal or "raise ability coverage"})


def tool_repair(issue: str = "") -> dict[str, Any]:
    from realai.server.tools.self_repair_tool import run as _r

    return _r({"issue": issue or "auto"})


def tool_scan(path: str = ".") -> dict[str, Any]:
    from realai.server.tools.system_scan_tool import run as _r

    return _r({"path": path})


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "doctor": lambda **kw: tool_doctor(),
    "organs": lambda **kw: tool_organs(),
    "catalog": lambda **kw: tool_catalog(learn=bool(kw.get("learn"))),
    "rackup": lambda **kw: tool_rackup(ability=str(kw.get("ability") or "roc_info")),
    "list": lambda **kw: tool_list(str(kw.get("path") or ".")),
    "read": lambda **kw: tool_read(
        str(kw.get("path") or "README.md"),
        start=int(kw.get("start") or 1),
        limit=int(kw.get("limit") or 80),
    ),
   "write": lambda **kw: tool_write(
    str(kw.get("path") or ""),
    content=str(kw.get("content") or ""),
    mode=str(kw.get("mode") or "overwrite"),
),

"architect_mode": lambda **kw: tool_architect_mode(),

"grep": lambda **kw: tool_grep(
    str(kw.get("pattern") or "."),
    path=str(kw.get("path") or "."),
    glob=str(kw.get("glob") or "*"),
),

    "task": lambda **kw: tool_organs_task(str(kw.get("goal") or "")),
    "git": lambda **kw: tool_git_status(),
    "map": lambda **kw: tool_living_map(),
    "improve": lambda **kw: tool_improve(),
    "heal": lambda **kw: tool_heal(force=bool(kw.get("force"))),
    "gaps": lambda **kw: tool_gaps(),
    "pwd": lambda **kw: tool_pwd(),
    "here": lambda **kw: tool_pwd(),
    "agents": lambda **kw: tool_agents(
        query=str(kw.get("query") or ""), limit=int(kw.get("limit") or 30)
    ),
    "tools": lambda **kw: tool_tools(),
    "at": lambda **kw: tool_agent_tools(
        action=str(kw.get("action") or "status"),
        tool=str(kw.get("tool") or ""),
        payload=kw.get("payload"),
        profile=str(kw.get("profile") or "balanced"),
        dry_run=bool(kw.get("dry_run") if kw.get("dry_run") is not None else True),
        query=str(kw.get("query") or ""),
    ),
    "agent-tools": lambda **kw: tool_agent_tools(
        action=str(kw.get("action") or "status"),
        tool=str(kw.get("tool") or ""),
        payload=kw.get("payload"),
        profile=str(kw.get("profile") or "balanced"),
        dry_run=bool(kw.get("dry_run") if kw.get("dry_run") is not None else True),
        query=str(kw.get("query") or ""),
    ),
    "multi": lambda **kw: tool_multi(
        str(kw.get("task") or kw.get("goal") or ""),
        mode=str(kw.get("mode") or "pipeline"),
    ),
    "exec": lambda **kw: tool_exec(
        str(kw.get("name") or ""),
        **{k: v for k, v in kw.items() if k != "name"},
    ),
    "extend": lambda **kw: tool_extend(str(kw.get("goal") or "")),
    "repair": lambda **kw: tool_repair(str(kw.get("issue") or "")),
    "scan": lambda **kw: tool_scan(str(kw.get("path") or ".")),
    "model": lambda **kw: tool_model(str(kw.get("name") or kw.get("model") or "RealAI Hive")),
    "walk": lambda **kw: tool_walk_root(
        force=bool(kw.get("force")),
        deepen=bool(kw.get("deepen")),
        start=str(kw.get("start") or kw.get("path") or ""),
    ),
    "unify": lambda **kw: tool_unify_nests(limit=int(kw.get("limit") or 30)),
    "deep-unify": lambda **kw: tool_deep_unify(
        apply=bool(kw.get("apply")),
        max_nests=int(kw.get("max_nests") or 25),
    ),
    "deep_unify": lambda **kw: tool_deep_unify(
        apply=bool(kw.get("apply")),
        max_nests=int(kw.get("max_nests") or 25),
    ),
    "organize": lambda **kw: tool_organize_repo(
        apply=bool(kw.get("apply")),
        refresh_walk=bool(kw.get("refresh_walk") or kw.get("force")),
        limit=int(kw.get("limit") or 500),
    ),
    "organise": lambda **kw: tool_organize_repo(
        apply=bool(kw.get("apply")),
        refresh_walk=bool(kw.get("refresh_walk") or kw.get("force")),
        limit=int(kw.get("limit") or 500),
    ),
    "scripts": lambda **kw: tool_list_scripts(
        query=str(kw.get("query") or ""),
        limit=int(kw.get("limit") or 40),
    ),
    "run-script": lambda **kw: tool_run_script_any(
        str(kw.get("name") or kw.get("script") or ""),
        timeout=int(kw.get("timeout") or 600),
        dry_run=bool(kw.get("dry_run")),
    ),
    "run_script": lambda **kw: tool_run_script_any(
        str(kw.get("name") or kw.get("script") or ""),
        timeout=int(kw.get("timeout") or 600),
        dry_run=bool(kw.get("dry_run")),
    ),
    "dispatch": lambda **kw: dispatch_prompt_actions(
        str(kw.get("prompt") or kw.get("goal") or ""),
        run_all=bool(kw.get("all") or kw.get("run_all") or kw.get("force_all")),
    ),
    "promote": lambda **kw: tool_promote(
        mode=str(kw.get("mode") or kw.get("goal") or "deep"),
        force=bool(kw.get("force")),
        dry_run=bool(kw.get("dry_run")),
    ),
    "deep-promote": lambda **kw: tool_deep_promote(
        mode=str(kw.get("mode") or "full"),
        dry_run=bool(kw.get("dry_run")),
    ),
    "deep_promote": lambda **kw: tool_deep_promote(
        mode=str(kw.get("mode") or "full"),
        dry_run=bool(kw.get("dry_run")),
    ),
}


# ---------------------------------------------------------------------------
# Intent
# ---------------------------------------------------------------------------

_MISSION_ECHO = re.compile(
    r"^(success|one branch|one interface|doctor ready|recovered preserved|"
    r"you continue unification|first action now|mission|non-negotiable|"
    r"startup checklist|work orders)",
    re.I,
)


def plan_tools(user_text: str) -> list[tuple[str, dict[str, Any]]]:
    t = user_text.strip()
    low = t.lower().strip()

    if t.startswith("/"):
        parts = t[1:].strip().split(maxsplit=1)
        cmd = (parts[0] or "").lower()
        rest = parts[1] if len(parts) > 1 else ""
        aliases = {
            "self-improve": "improve",
            "self_improve": "improve",
            "selfheal": "heal",
            "self-heal": "heal",
            "self_heal": "heal",
            "ws": "pwd",
            "workspace": "pwd",
            "agent": "agents",
            "multi-agent": "multi",
            "multi_agent": "multi",
            "tool": "tools",
            "self-extend": "extend",
            "self_extend": "extend",
            "self-repair": "repair",
            "self_repair": "repair",
            "agent_tools": "at",
            "agent-tools": "at",
            "atools": "at",
            "gold": "at",
            "deeppromote": "deep-promote",
            "deep_promote": "deep-promote",
            "nested-gold": "deep-promote",
            "nested_gold": "deep-promote",
            "root-walk": "walk",
            "walk-root": "walk",
            "walk_root": "walk",
            "nests": "unify",
            "nested": "unify",
            "runscript": "run-script",
            "run_script": "run-script",
            "organise": "organize",
            "rehome": "organize",
            "organize-repo": "organize",
            "deepunify": "deep-unify",
            "deep_unify": "deep-unify",
            "unify-deep": "deep-unify",
        }
        cmd = aliases.get(cmd, cmd)
        if cmd in TOOLS:
            if cmd == "read" and rest:
                return [("read", {"path": rest.split()[0]})]
            if cmd == "list" and rest:
                return [("list", {"path": rest.split()[0]})]
            if cmd == "grep" and rest:
                return [("grep", {"pattern": rest})]
            if cmd == "write" and rest:
                # /write path\ncontent...  or /write path|||content
                if "|||" in rest:
                    path, content = rest.split("|||", 1)
                    return [("write", {"path": path.strip(), "content": content})]
                bits = rest.split(maxsplit=1)
                path = bits[0]
                content = bits[1] if len(bits) > 1 else ""
                return [("write", {"path": path, "content": content})]
            if cmd == "rackup" and rest:
                return [("rackup", {"ability": rest.split()[0]})]
            if cmd == "catalog":
                return [("catalog", {"learn": "learn" in rest.lower()})]
            if cmd == "task" and rest:
                return [("task", {"goal": rest})]
            if cmd == "heal":
                return [("heal", {"force": "force" in rest.lower()})]
            if cmd == "agents" and rest:
                return [("agents", {"query": rest})]
            if cmd == "multi" and rest:
                return [("multi", {"task": rest})]
            if cmd == "exec" and rest:
                bits = rest.split(maxsplit=1)
                name = bits[0]
                # optional JSON args after name
                args: dict[str, Any] = {"name": name}
                if len(bits) > 1:
                    try:
                        args.update(json.loads(bits[1]))
                    except Exception:
                        args["input"] = bits[1]
                return [("exec", args)]
            if cmd == "extend" and rest:
                return [("extend", {"goal": rest})]
            if cmd == "repair" and rest:
                return [("repair", {"issue": rest})]
            if cmd == "scan" and rest:
                return [("scan", {"path": rest.split()[0]})]
            if cmd == "walk":
                rest_l = rest.lower().strip()
                deepen = any(x in rest_l for x in ("deepen", "deep", "deeper"))
                force = any(x in rest_l for x in ("force", "refresh")) or deepen
                # optional start path: /walk deepen imports/external
                bits = rest.split()
                start = ""
                for b in bits:
                    bl = b.lower()
                    if bl in {"force", "refresh", "deepen", "deep", "deeper", "--deepen", "--force"}:
                        continue
                    start = b
                    break
                return [("walk", {"force": force, "deepen": deepen, "start": start})]
            if cmd == "unify":
                return [("unify", {"limit": 30})]
            if cmd in ("deep-unify", "deep_unify"):
                rest_l = rest.lower()
                return [
                    (
                        "deep-unify",
                        {
                            "apply": any(x in rest_l for x in ("--apply", "apply", "write")),
                            "max_nests": 25,
                        },
                    )
                ]
            if cmd == "organize":
                rest_l = rest.lower()
                return [
                    (
                        "organize",
                        {
                            "apply": any(x in rest_l for x in ("--apply", "apply", "write", "merge")),
                            "refresh_walk": any(
                                x in rest_l for x in ("refresh", "force", "--refresh-walk")
                            ),
                        },
                    )
                ]
            if cmd == "scripts":
                return [("scripts", {"query": rest.strip(), "limit": 40})]
            if cmd in ("run-script", "run_script") and rest:
                bits = rest.split()
                name = bits[0]
                dry = any(x in rest.lower() for x in ("--dry", "dry-run", "dry_run"))
                return [("run-script", {"name": name, "dry_run": dry})]
            if cmd in ("train-walk", "trainwalk", "train_walk"):
                return [
                    (
                        "dispatch",
                        {"prompt": "train walk training sources", "run_all": False},
                    )
                ]
            if cmd in ("train-gguf", "traingguf", "train_gguf"):
                # Launch one-command train→gguf→swap (subprocess via run-script path)
                preset = (rest.split()[0] if rest.strip() else "qwen-coder-7b")
                return [
                    (
                        "run-script",
                        {
                            "name": "train_to_chat_gguf.py",
                            "dry_run": False,
                        },
                    )
                ]
            if cmd == "model":
                # /model RealAI Hive  |  /model realai-hive  |  /model
                name = rest.strip() or "RealAI Hive"
                return [("model", {"name": name})]
            if cmd == "train":
                rest_l = rest.lower().strip()
                if rest_l in {"walk", "sources"}:
                    return [("dispatch", {"prompt": "train walk", "run_all": False})]
                if rest_l.startswith("wire") or rest_l in {"ingest", "dataset"}:
                    return [("dispatch", {"prompt": "wire training", "run_all": False})]
                if rest_l.startswith("gguf") or "to-gguf" in rest_l or "to_gguf" in rest_l:
                    return [
                        (
                            "run-script",
                            {"name": "train_to_chat_gguf.py", "dry_run": False},
                        )
                    ]
                # /train  or /train 1.5b directml
                prompt = "dispatch training train " + (rest_l or "qwen-coder-1.5b directml")
                return [("dispatch", {"prompt": prompt, "run_all": False})]
            if cmd in ("dispatch", "automate", "pipeline", "auto"):
                # /dispatch  or  /dispatch all  or  /dispatch deep promote
                rest_l = rest.lower().strip()
                # Bare /dispatch with no args → deep promote recipe (real work, not empty chat)
                if not rest_l:
                    return [("promote", {"mode": "deep"})]
                # /dispatch training [train]
                if rest_l.startswith("training") or rest_l.startswith("train"):
                    return [
                        (
                            "dispatch",
                            {
                                "prompt": rest_l if rest_l else "dispatch training",
                                "run_all": False,
                            },
                        )
                    ]
                run_all = any(
                    x in rest_l for x in ("all", "full pipeline", "everything", "all phases")
                ) or rest_l in {"full", "pipeline", "7"}
                # Prefer dedicated promote tool for deep/nested recipes (faster + verified)
                if any(
                    k in rest_l
                    for k in (
                        "deep promote",
                        "promote deep",
                        "nested gold",
                        "deep gold",
                        "deep wire",
                        "thin wrap",
                    )
                ) and not run_all:
                    mode = "wire" if "wire" in rest_l and "scan" not in rest_l else "deep"
                    if "scan" in rest_l and "wire" not in rest_l:
                        mode = "scan"
                    return [("promote", {"mode": mode, "force": "force" in rest_l})]
                return [
                    (
                        "dispatch",
                        {
                            "prompt": rest or "full automation",
                            "run_all": run_all,
                        },
                    )
                ]
            if cmd == "promote":
                rest_l = rest.lower().strip() or "deep"
                mode = "deep"
                if rest_l in {"curated", "allowlist"}:
                    mode = "curated"
                elif rest_l in {"scan", "map"}:
                    mode = "scan"
                elif rest_l in {"wire", "thin"}:
                    mode = "wire"
                elif "curated" in rest_l:
                    mode = "curated"
                return [
                    (
                        "promote",
                        {
                            "mode": mode,
                            "force": "force" in rest_l,
                            "dry_run": "dry" in rest_l,
                        },
                    )
                ]
            if cmd == "deep-promote":
                rest_l = rest.lower().strip() or "full"
                mode = "full"
                if rest_l in {"scan", "map"}:
                    mode = "scan"
                elif rest_l in {"wire", "thin"}:
                    mode = "wire"
                return [
                    (
                        "deep-promote",
                        {"mode": mode, "dry_run": "dry" in rest_l},
                    )
                ]
            if cmd == "at":
                # /at [action] [args...]
                # /at invoke filesystem {"operation":"list","path":"."}
                # /at invoke-live filesystem path/to
                # /at assess agent-id balanced
                bits = rest.split(maxsplit=2) if rest else []
                action = (bits[0] if bits else "status").lower()
                dry = True
                if action in ("invoke-live", "invoke_live", "run-live"):
                    action = "invoke"
                    dry = False
                if action == "invoke" and len(bits) >= 2:
                    tool = bits[1]
                    payload: Any = bits[2] if len(bits) > 2 else None
                    return [
                        (
                            "at",
                            {
                                "action": "invoke",
                                "tool": tool,
                                "payload": payload,
                                "dry_run": dry,
                            },
                        )
                    ]
                if action == "assess" and len(bits) >= 2:
                    return [
                        (
                            "at",
                            {
                                "action": "assess",
                                "query": bits[1],
                                "profile": bits[2] if len(bits) > 2 else "balanced",
                            },
                        )
                    ]
                if action in ("agents", "list_agents") and len(bits) >= 2:
                    return [("at", {"action": "agents", "query": bits[1]})]
                return [("at", {"action": action or "status"})]
            return [(cmd, {})]
        return []

    if _MISSION_ECHO.search(low) or low.startswith("- one ") or low.startswith("- doctor"):
        return [("gaps", {}), ("improve", {})] if is_realai_product_tree() else [("heal", {})]

    if any(
        k in low
        for k in (
            "self-heal",
            "self heal",
            "selfheal",
            "run heal",
            "heal this",
            "heal the project",
            "heal the repo",
        )
    ):
        return [("heal", {})]

    if any(
        k in low
        for k in (
            "deep promote",
            "promote deep",
            "nested gold",
            "deep gold",
            "deep wire",
            "thin wrap promote",
            "run promote",
            "promote nested",
            "wire nested",
        )
    ) and is_realai_product_tree():
        mode = "wire" if ("wire" in low and "scan" not in low and "deep promote" not in low) else "deep"
        if "scan only" in low or low.strip() in {"deep scan promote", "promote scan"}:
            mode = "scan"
        return [("promote", {"mode": mode})]

    if low.strip() in {"promote", "/promote"} and is_realai_product_tree():
        return [("promote", {"mode": "deep"})]

    if any(
        k in low
        for k in (
            "deep unify",
            "deep-unify",
            "unify deepest",
            "deepen and organize",
            "walk deepen",
        )
    ) and is_realai_product_tree():
        return [
            (
                "deep-unify",
                {"apply": any(x in low for x in ("apply", "write", "merge now"))},
            )
        ]

    if any(
        k in low
        for k in (
            "walk root",
            "root walk",
            "walk the root",
            "nested walk",
            "see nested",
            "unify nests",
            "unify nested",
            "nested folders map",
            "go deeper",
            "deeper nests",
        )
    ) and is_realai_product_tree():
        deepen = any(x in low for x in ("deepen", "deeper", "deep walk"))
        if "unify" in low or "dupe" in low or "collision" in low:
            return [("walk", {"force": True, "deepen": deepen}), ("unify", {})]
        return [
            (
                "walk",
                {
                    "force": True if deepen or "force" in low or "refresh" in low else False,
                    "deepen": deepen,
                },
            )
        ]

    if any(
        k in low
        for k in (
            "self-improve",
            "self improve",
            "improve yourself",
            "fill the gap",
            "fill gaps",
            "raise coverage",
            "learn keywords",
        )
    ):
        return [("improve", {})] if is_realai_product_tree() else [("heal", {})]

    plans: list[tuple[str, dict[str, Any]]] = []
    if low in ("doctor",) or low.startswith("run doctor") or "self-check" in low:
        plans.append(("doctor", {}))
    elif re.search(r"\bare we ready\b", low):
        plans.append(("doctor", {}))
    if re.search(r"\bgaps?\b|\btop 3\b|\bwhat.?s missing\b", low):
        plans.append(("gaps", {}))
    if re.search(r"\borgans?\b|\bhive\b", low) and len(low) < 80:
        plans.append(("organs", {}))
    if "catalog" in low and is_realai_product_tree():
        plans.append(("catalog", {"learn": "learn" in low}))
    if re.search(r"\brackup\b|\bglicko\b|\broc\b", low) and len(low) < 120:
        ab = "rating_intel" if "rating" in low else "roc_info"
        if "audit" in low or "ledger" in low:
            ab = "ledger_audit"
        plans.append(("rackup", {"ability": ab}))
    if re.search(r"\bgit status\b|\buncommitted\b", low):
        plans.append(("git", {}))
    if re.search(r"\bwhere am i\b|\bwhat project\b|\bworkspace\b", low) and len(low) < 40:
        plans.append(("pwd", {}))
    if re.search(r"\blist agents\b|\bagents?\b", low) and len(low) < 40:
        plans.append(("agents", {}))
    if re.search(r"\bmulti[- ]?agent\b|\bplanner\b.*\bcritic\b", low):
        plans.append(("multi", {"task": t}))
    if re.search(r"\bwhat tools\b|\blist tools\b", low):
        plans.append(("tools", {}))
    if re.search(r"\bself[- ]?extend\b|\braise coverage\b", low):
        plans.append(("extend", {"goal": t}))
    if re.search(r"\bself[- ]?repair\b|\bfix the stack\b", low):
        plans.append(("repair", {"issue": t}))
    if low.startswith("read ") or low.startswith("open "):
        m = re.search(r"(?:read|open)\s+(\S+)", low)
        if m:
            plans.append(("read", {"path": m.group(1)}))
    if low.startswith("list "):
        m = re.search(r"list\s+(\S+)", low)
        plans.append(("list", {"path": m.group(1) if m else "."}))
    if low.startswith("grep ") or low.startswith("search for "):
        m = re.search(r"(?:grep|search for)\s+(.+)$", t, re.I)
        if m:
            plans.append(("grep", {"pattern": m.group(1).strip().strip("\"'")}))

    # RealAI automation dispatcher (phases 1–7) — only when clear intent
    auto_triggers = (
        "read first", "deep scan", "scan repos",
        "find lost", "self_improve", "self-improve",
        "promote unified", "unify realai", "unify",
        "world model", "merge world model",
        "plugin registry", "build plugins", "plugin_registry",
        "folder structure", "structure validate", "unified structure",
        "evolution plan", "monitor model",
        "full automation", "run all phases", "dispatch all",
        "automate all", "full pipeline", "run the 7",
    )
    if any(k in low for k in auto_triggers):
        run_all = any(
            x in low
            for x in (
                "full automation", "run all phases", "dispatch all",
                "automate all", "full pipeline", "run the 7", "all phases",
            )
        )
        # Avoid double-firing pure "map"/"validate" on every casual use;
        # those still match if other stronger keywords are present, or use /dispatch
        plans.append(("dispatch", {"prompt": t, "run_all": run_all}))

    return plans


def run_tools(plans: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []
    for name, kwargs in plans:
        fn = TOOLS.get(name)
        if not fn:
            out.append({"tool": name, "error": "unknown tool"})
            continue
        try:
            out.append({"tool": name, "args": kwargs, "result": fn(**kwargs)})
        except Exception as e:
            out.append({"tool": name, "args": kwargs, "error": str(e)})
    return out


# ---------------------------------------------------------------------------
# GPU / API streaming
# ---------------------------------------------------------------------------


def _api_bases() -> list[str]:
    """Prefer orchestrator if set/up, else raw Vulkan."""
    bases: list[str] = []
    for key in (
        "REALAI_API_BASE",
        "REALAI_GPU_API",
        "REALAI_VULKAN_BASE",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
    ):
        v = (os.environ.get(key) or "").strip().rstrip("/")
        if not v:
            continue
        if not v.endswith("/v1"):
            v = v + "/v1"
        if v not in bases:
            bases.append(v)
    # defaults: orchestrator then vulkan
    for d in (
        f"http://127.0.0.1:8001/v1",
        f"http://{GPU_HOST}:{GPU_PORT}/v1",
    ):
        if d not in bases:
            bases.append(d)
    return bases


def _probe(url: str, timeout: float = 1.2) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _active_base() -> Optional[str]:
    for b in _api_bases():
        root = b[: -len("/v1")] if b.endswith("/v1") else b
        if _probe(b + "/models", 1.2) or _probe(root + "/health", 1.2):
            return b
    return None


def ensure_gpu_server(wait_s: int = 90) -> dict[str, Any]:
    import time

    active = _active_base()
    if active:
        return {"ok": True, "status": "already_running", "url": active}

    # Prefer full stack script if present (Vulkan + orchestrator)
    home = _home()
    stack_ps1 = home / "scripts" / "run_local_chat.ps1"
    if stack_ps1.is_file() and os.environ.get("REALAI_CHAT_NO_STACK", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        print(
            "[api] nothing listening — starting full stack (Vulkan + orchestrator).\n"
            "      Model load often takes 1–3 minutes; please wait…",
            flush=True,
        )
        shell = "pwsh" if shutil_which("pwsh") else "powershell"
        try:
            rc = subprocess.call(
                [
                    shell,
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(stack_ps1),
                    "-SkipUI",
                    "-SkipPromote",
                ],
                cwd=str(home),
            )
            active = _active_base()
            if active:
                return {
                    "ok": True,
                    "status": "stack_started",
                    "url": active,
                    "exit_code": rc,
                }
            return {
                "ok": False,
                "status": "stack_failed",
                "exit_code": rc,
                "hint": f"Check {home}\\logs\\vulkan.err.log and v3-orchestrator.err.log",
            }
        except Exception as e:
            return {"ok": False, "status": "stack_exception", "error": str(e)}

    exe = VULKAN_DIR / "llama-server.exe"
    model = default_gguf()
    if not exe.is_file():
        return {"ok": False, "status": "missing_server", "path": str(exe)}
    if not model.is_file():
        return {"ok": False, "status": "missing_model", "path": str(model)}

    print(f"[api] starting Vulkan only… model={model.name} (1–3 min)", flush=True)
    args = [
        str(exe),
        "-m",
        str(model),
        "--host",
        GPU_HOST,
        "--port",
        str(GPU_PORT),
        "-c",
        os.environ.get("REALAI_CTX") or "8192",
        "-ngl",
        os.environ.get("REALAI_NGL") or "99",
        "--jinja",
    ]
    flags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        flags |= subprocess.DETACHED_PROCESS  # type: ignore
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        flags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore
    try:
        subprocess.Popen(
            args,
            cwd=str(VULKAN_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags or 0,
        )
    except Exception as e:
        return {"ok": False, "status": "start_failed", "error": str(e)}

    deadline = time.time() + max(15, int(wait_s))
    while time.time() < deadline:
        active = _active_base()
        if active:
            return {"ok": True, "status": "started", "url": active, "model": str(model)}
        time.sleep(1.5)
    return {
        "ok": False,
        "status": "timeout",
        "hint": r"Run: realai-stack   (or C:\RealAI-clean\run_chat.bat)",
    }


def shutil_which(name: str) -> Optional[str]:
    from shutil import which

    return which(name)


def _offline_api_message() -> str:
    return (
        "(Chat API offline — Vulkan :8080 / orch :8001 not answering.\n"
        "  LoRA train auto-pauses llama-server to free AMD VRAM.\n"
        "  Restart chat stack, then retry:\n"
        "    powershell -ExecutionPolicy Bypass -File C:\\RealAI-clean\\scripts\\run_local_chat.ps1\n"
        "  Tools still work without the model: /heal /dispatch /train-walk /train wire /gpu)"
    )


def stream_chat(
    messages: list[dict[str, str]],
    temperature: float = 0.5,
    max_tokens: int = 1200,
) -> Generator[str, None, str]:
    base = _active_base()
    if not base:
        # Do NOT auto-start the 7B Vulkan stack here — that blocks for minutes.
        # Use /gpu or run_local_chat.ps1 explicitly. Fail fast after train paused Vulkan.
        msg = _offline_api_message()
        yield msg
        return msg

    model = (
        os.environ.get("REALAI_DEFAULT_MODEL")
        or os.environ.get("REALAI_GPU_MODEL")
        or "realai-default-coder"
    )
    # raw vulkan often wants filename
    if ":8080" in base:
        model = os.environ.get("REALAI_GPU_MODEL") or default_gguf().name

    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
    ).encode("utf-8")
    url = base.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + (os.environ.get("REALAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or "local"),
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    full: list[str] = []
    # Connect/read timeout — do not block for minutes on a dead socket
    http_timeout = float(os.environ.get("REALAI_CHAT_HTTP_TIMEOUT") or "45")
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            while True:
                raw = resp.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        full.append(piece)
                        yield piece
    except Exception as e1:
        try:
            body2 = json.dumps(
                {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
            ).encode("utf-8")
            req2 = urllib.request.Request(
                url,
                data=body2,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer local",
                },
                method="POST",
            )
            with urllib.request.urlopen(req2, timeout=min(60.0, http_timeout)) as resp2:
                data = json.loads(resp2.read().decode("utf-8", errors="replace"))
            content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            if content:
                yield content
                full.append(content)
        except Exception as e2:
            msg = (
                _offline_api_message()
                + f"\n  stream_error: {type(e1).__name__}: {e1}"
                + f"\n  fallback_error: {type(e2).__name__}: {e2}"
            )
            yield msg
            full.append(msg)
    return "".join(full)


def _format_tools(tool_results: list[dict[str, Any]]) -> str:
    if not tool_results:
        return ""
    lines = ["### Tool results"]
    for tr in tool_results:
        name = tr.get("tool")
        if tr.get("error"):
            lines.append(f"- `{name}` error: {tr['error']}")
            continue
        r = tr.get("result") or {}
        if name in ("improve", "heal"):
            lines.append(f"- **{name}:** {r.get('summary') or r.get('error')}")
            for a in r.get("actions") or []:
                lines.append(f"  - {a}")
            for iss in r.get("issues") or []:
                lines.append(f"  - issue: {iss}")
        elif name == "gaps":
            lines.append(f"- **gaps** {r.get('summary') or r.get('coverage')}")
            for g in r.get("top_gaps") or []:
                lines.append(f"  - [{g.get('severity')}] {g.get('area')}: {g.get('detail')}")
            for iss in r.get("issues") or []:
                lines.append(f"  - issue: {iss}")
        elif name == "doctor":
            lines.append(
                f"- **doctor:** {'READY' if r.get('ok') else 'NOT READY'} "
                f"mode={r.get('mode')} ws={r.get('workspace')}"
            )
        elif name == "organs":
            lines.append(f"- **organs:** {r.get('organ_count')} complete={r.get('complete')}")
        elif name in ("pwd", "here"):
            lines.append(f"- **workspace:** {r.get('banner')}")
        elif name == "git":
            lines.append(f"- **git:** {r.get('branch')}\n```\n{r.get('status')}\n```")
        elif name == "read":
            lines.append(f"- **read** `{r.get('path')}`:\n```\n{(r.get('content') or '')[:2500]}\n```")
        elif name == "write":
            lines.append(f"- **write** `{r.get('path')}` ok={r.get('ok')} bytes={r.get('bytes')}")
        elif name == "grep":
            lines.append(f"- **grep** `{r.get('pattern')}` ({len(r.get('hits') or [])} hits)")
            for h in (r.get("hits") or [])[:12]:
                lines.append(f"  - {h.get('file')}:{h.get('line')}: {h.get('text')}")
        elif name == "list":
            names = [e.get("name") for e in (r.get("entries") or [])[:40]]
            lines.append(f"- **list** `{r.get('path')}`: {', '.join(names)}")
        elif name == "tools":
            lines.append(f"- **tools:** {r.get('count')} available")
            for n in (r.get("tools") or [])[:25]:
                lines.append(f"  - {n}")
        elif name == "agents":
            ag = (r.get("agents") or {}).get("agents") or []
            lines.append(f"- **agents:** {(r.get('agents') or {}).get('count')} shown")
            for a in ag[:12]:
                lines.append(f"  - {a.get('id')}: {a.get('role')}")
        elif name == "multi":
            lines.append(f"- **multi:** ok={r.get('ok')} mode={r.get('mode')}")
            fo = (r.get("final_output") or "")[:2000]
            if fo:
                lines.append(fo)
        elif name in (
            "extend",
            "repair",
            "scan",
            "exec",
            "model",
            "walk",
            "unify",
            "organize",
            "organise",
            "deep-unify",
            "deep_unify",
            "scripts",
            "run-script",
            "run_script",
        ):
            lines.append(f"- **{name}:** {r.get('summary') or r.get('error') or json.dumps(r, default=str)[:1200]}")
            if name == "model":
                if r.get("gguf_path"):
                    lines.append(f"  - gguf: `{r.get('gguf_path')}`")
                if r.get("switch_required"):
                    lines.append("  - Vulkan needs restart to hot-load this GGUF")
                    if r.get("switch_cmd"):
                        lines.append(f"  - `{r.get('switch_cmd')}`")
            if name == "scripts":
                for s in (r.get("scripts") or [])[:15]:
                    paths = s.get("paths") or []
                    lines.append(f"  - {s.get('name')} ×{s.get('locations')} → {paths[0] if paths else '?'}")
            if name == "walk":
                for n in (r.get("deepest_nests") or [])[:8]:
                    lines.append(
                        f"  - deepest depth={n.get('depth')} code={n.get('code_top')} `{n.get('rel')}`"
                    )
            if name == "unify":
                for d in (r.get("duplicate_basenames") or [])[:8]:
                    lines.append(f"  - dupe {d.get('basename')} ×{d.get('count')}")
                for n in (r.get("nested_folders") or [])[:8]:
                    if n.get("nest_hint"):
                        lines.append(f"  - nest `{n.get('rel')}` depth={n.get('depth')}")
            if name in ("organize", "organise"):
                lines.append(f"  - actions: {r.get('actions')}")
                for p in (r.get("preview") or [])[:12]:
                    lines.append(f"  - {p}")
                if r.get("map_md"):
                    lines.append(f"  - map: {r.get('map_md')}")
            if name in ("deep-unify", "deep_unify"):
                if r.get("map_md"):
                    lines.append(f"  - report: {r.get('map_md')}")
                for ln in ((r.get("stdout_tail") or "").strip().splitlines()[-6:]):
                    lines.append(f"  - out> {ln[:160]}")
            if name in ("run-script", "run_script") and r.get("rel"):
                lines.append(f"  - path: {r.get('rel')}")
                for ln in ((r.get("stdout_tail") or "").strip().splitlines()[-4:]):
                    lines.append(f"  - out> {ln[:160]}")
        elif name == "dispatch":
            lines.append(f"- **dispatch:** {r.get('summary') or r.get('error')}")
            for a in (r.get("actions") or [])[:18]:
                lines.append(f"  - {a}")
            for err in (r.get("errors") or [])[:6]:
                lines.append(f"  - ERR: {err}")
            if r.get("results"):
                ok_n = sum(1 for x in r["results"] if x.get("ok"))
                lines.append(f"  - results: {ok_n}/{len(r['results'])} succeeded")
                for res in r["results"]:
                    arts = res.get("artifacts") or []
                    if arts:
                        lines.append(f"  - evidence {res.get('script')}: {', '.join(arts)}")
        elif name in ("promote", "deep-promote", "deep_promote"):
            lines.append(f"- **{name}:** {r.get('summary') or r.get('error')}")
            for a in (r.get("actions") or [])[:12]:
                lines.append(f"  - {a}")
            arts = r.get("artifacts") or {}
            for k, v in arts.items():
                if isinstance(v, dict):
                    lines.append(
                        f"  - artifact {k}: exists={v.get('exists')} bytes={v.get('bytes')}"
                    )
            if r.get("wire_wrote") is not None:
                lines.append(f"  - wire_wrote={r.get('wire_wrote')}")
        elif name == "heal":
            lines.append(f"- **heal:** {r.get('summary') or r.get('error')}")
            for a in (r.get("actions") or [])[:12]:
                lines.append(f"  - {a}")
            promo = r.get("promote") or {}
            if promo:
                lines.append(f"  - promote: {promo.get('summary')}")
        else:
            blob = json.dumps(r, default=str)[:1500]
            lines.append(f"- **{name}:** {blob}")
    return "\n".join(lines)


def build_messages(
    user: str,
    history: list[dict[str, str]],
    tool_results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    ws = _ws()
    home = _home()
    mode = "product" if is_realai_product_tree(ws) else "project"
    system = (
        f"You are RealAI Craft — a coding assistant working inside a user project.\n"
        f"WORKSPACE (edit here): {ws}\n"
        f"REALAI_HOME (models/install): {home}\n"
        f"Mode: {mode}\n"
        "Rules:\n"
        "- Answer the user's LATEST message about THIS workspace.\n"
        "- Prefer concrete code: show full files or clear patches they can apply.\n"
        "- Use tool results when present. Paths are relative to WORKSPACE.\n"
        "- NEVER suggest git commit/push unless they explicitly ask.\n"
        "- Be concise. Stream naturally.\n"
        "- You can suggest /read /write /grep /heal for next steps.\n"
    )
    msgs: list[dict[str, str]] = [{"role": "system", "content": system}]
    for h in history[-8:]:
        msgs.append(h)
    if tool_results:
        tools_txt = _format_tools(tool_results)
        msgs.append(
            {
                "role": "user",
                "content": f"{user}\n\n{tools_txt}\n\nReply for this project workspace.",
            }
        )
    else:
        msgs.append({"role": "user", "content": user})
    return msgs


def stream_reply(
    user: str,
    history: list[dict[str, str]],
    tool_results: list[dict[str, Any]],
) -> str:
    # If tools already did real work and chat API is down, don't hang on LLM
    api_up = _active_base() is not None
    heavy_tools = {
        "dispatch",
        "promote",
        "deep-promote",
        "walk",
        "organize",
        "deep-unify",
        "heal",
        "train",
    }
    if tool_results and not api_up:
        only_heavy = all((tr.get("tool") in heavy_tools) for tr in tool_results)
        if only_heavy or any(tr.get("tool") in heavy_tools for tr in tool_results):
            print("realai> ", end="", flush=True)
            text = _format_tools(tool_results)
            text += (
                "\n\n(Chat model offline — Vulkan was likely paused for DirectML training. "
                "Restart: powershell -File scripts\\run_local_chat.ps1)"
            )
            print(text)
            return text

    msgs = build_messages(user, history, tool_results)
    print("realai> ", end="", flush=True)
    parts: list[str] = []
    try:
        for piece in stream_chat(msgs):
            print(piece, end="", flush=True)
            parts.append(piece)
    except KeyboardInterrupt:
        print("\n(interrupted)", flush=True)
        parts.append("\n(interrupted)")
    except Exception:
        pass
    text = "".join(parts).strip()
    if not text:
        if tool_results:
            text = _format_tools(tool_results)
            print(text)
        else:
            text = _offline_api_message()
            print(text)
    else:
        print()
    return text


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

HELP = """
RealAI Craft — full abilities inside RealAI-clean (any project workspace).

  cd C:\\YourProject
  realai                 # workspace = YourProject

Slash commands:
  /help /pwd /heal /doctor /gpu /improve /gaps /extend /repair
  /list /read /grep /write path|||content /scan
  /tools /agents [query] /multi <task> /exec <tool> {json}
  /agents                         # hive first: overseer coder architect analyst memory governor router
  /task /organs /rackup /catalog /git /map /quit
  /promote [deep|curated|scan|wire]   # REAL promote (scripts + artifact proof)
  /deep-promote [full|scan|wire]      # named-root / nest scan + thin wire
  /dispatch [deep promote|all]        # bare /dispatch → deep promote recipe
  /walk [force|deepen|<folder>]       # recurse every folder deeper+deeper (.py/.js/.json)
  /unify                              # nested folders + duplicate basename map
  /organize [apply|refresh]           # deepest-first patch/merge → proper locations
  /deep-unify [apply]                 # deepen walk deepest nests → organize → auto-wire
  /train-walk                         # walk learn/memory/finetune scripts for model needs
  /train wire                         # ingest extracts + rebuild LoRA-ready JSONL
  /train [preset]                     # dispatch training (+ optional LoRA on DirectML)
  /train-gguf [preset]                # ONE CMD: train→merge→Q5_K_M GGUF→swap Vulkan chat
  /model [RealAI Hive|id]             # set chat model id (default: realai-hive)
  /dispatch training [train]          # same as craft training pipeline
  /scripts [query]                    # runnable scripts at any nesting level
  /run-script <name>                  # resolve+run script from scripts|tools|nests

Automation (/dispatch or keywords) — scripts resolved at ANY level, evidence checked:
  Phase 0   catalog_good_code_roots  ← live trees + gold imports
  Phase 0b  walk_root                ← nested folders + scripts_by_name unify map
  Phase 1   scan_repos_for_realai
  Phase 2   find_self_improve_and_lost
  Phase 3   promote_unified (explicit 'promote unified' only)
  Phase 3b  diff + promote allowlist
  Phase 3c  curated_promote
  Phase 3d  deep_promote_scan   ← named roots + nests (function diff)
  Phase 3e  deep_promote_wire   ← thin wraps into abilities/
  Phase 4   world model merge
  Phase 5   plugin registry
  Phase 5b  wire_recovered
  Phase 6   structure validation
  Phase 6b  self_heal_loop
  Phase 7   monitor (one-shot)

  /dispatch all  or  "full automation" → every phase in order (starts with good-code + walk).
  "deep promote" / "nested gold" → curated + deep scan + wire (verified).
  Good code: abilities/, core/, modules/, agent_tools/, imports/external/*gold*
  Logs → REALAI_HOME/logs/dispatcher.log
  Maps → scan_results/realai_root_walk.md + DEEP_PROMOTE_MAP.md + GOOD_CODE_ROOTS.json

Abilities: multi-agent, organs, rackup (16), deep_promote, desktop lambdas,
tool registry, self-heal, catalog, nest_orchestrators index.
""".strip()

@dataclass
class CraftSession:
    history: list[dict[str, str]] = field(default_factory=list)

    def handle_stream(self, user: str) -> str:
        user = user.strip()
        if not user:
            return ""
        if user.lower() in ("/help", "help", "?"):
            print(HELP)
            return HELP
        if user.lower() in ("/quit", "/exit", "quit", "exit"):
            return "__QUIT__"
        if user.lower() in ("/gpu", "/server"):
            st = ensure_gpu_server(wait_s=90)
            msg = f"**GPU:** {json.dumps(st, indent=2)}"
            print(msg)
            return msg

        plans = plan_tools(user)
        results = run_tools(plans) if plans else []
        if results:
            names = ", ".join(tr.get("tool", "?") for tr in results)
            print(f"[tools: {names}]", flush=True)

        reply = stream_reply(user, self.history, results)
        self.history.append({"role": "user", "content": user})
        self.history.append({"role": "assistant", "content": reply})
        if len(self.history) > 20:
            self.history = self.history[-16:]
        return reply

def run_repl(one_shot: str | None = None) -> int:
    # Bind workspace to product root before any tool/agent discovery.
    apply_workspace()
    print(workspace_banner())
    session = CraftSession()
    wait = int(os.environ.get("REALAI_GPU_WAIT") or "90")
    autostart = os.environ.get("REALAI_CRAFT_AUTOSTART", "").lower() in {"1", "true", "yes"}

    def _announce_api() -> None:
        orch = _orch_base()
        # Prefer explicit orchestrator ONLINE announcement.
        try:
            req = urllib.request.Request(orch + "/health", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
            print(f"[api] already_running → {orch}/v1")
            print(f"[api] ONLINE mode  service={body.get('service')} vulkan_ok={(body.get('vulkan') or {}).get('ok')}")
            return
        except Exception as e:
            print(f"[api] orchestrator binding failed: GET {orch}/health → {e}")

        active = _active_base()
        if active:
            print(f"[api] already_running → {active}")
            return
        if autostart:
            st = ensure_gpu_server(wait_s=wait)
            if st.get("ok"):
                print(f"[api] {st.get('status')} → {st.get('url')}")
            else:
                print(f"[api] offline: {st}")
                print("      Prefer: powershell -File scripts\\run_local_chat.ps1")
            return
        print("[api] offline (Vulkan/orch not up)")
        print("      Start orch: python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001")
        print("      Or stack:  powershell -ExecutionPolicy Bypass -File scripts\\run_local_chat.ps1")
        print("      Tools work offline: /dispatch /train-walk /heal /read")

    if one_shot:
        # One-shot: only autostart if asked; otherwise tools-first / fail-fast chat
        if autostart and not _active_base():
            st = ensure_gpu_server(wait_s=wait)
            if not st.get("ok"):
                print(f"[gpu] {st} — tools only if offline")
        elif not _active_base():
            print("[api] offline — tools still run; restart chat stack for model replies")
        session.handle_stream(one_shot)
        return 0

    print("RealAI Craft — portable project assistant")
    print(workspace_banner())
    print(f"gguf: {default_gguf()}")
    _announce_api()
    print("/help · /heal · /read · /write · plain chat · /quit")
    print("-" * 50)
    session.handle_stream("/pwd")
    print("-" * 50)

    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not user:
            continue
        out = session.handle_stream(user)
        if out == "__QUIT__":
            print("bye")
            return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    apply_workspace()
    argv = list(argv or [])
    if argv and argv[0] in ("-h", "--help"):
        print(HELP)
        return 0
    one = " ".join(argv).strip() if argv else None
    return run_repl(one_shot=one or None)

# ============================================================
# REALAI FULL AUTOMATION DISPATCHER (robust, Windows-safe, never-crash)
# ============================================================
# Integrates with RealAI workspace (_home / _ws). Triggers on keywords
# in the user prompt or via /dispatch [all]. Logs to console + HOME/logs.
# Runs the 7 phase scripts under REALAI_HOME/scripts using sys.executable.
# ============================================================

def dispatch_prompt_actions(prompt: str = "", run_all: bool = False) -> dict[str, Any]:
    """
    Run RealAI recovery/automation phases.

    Keywords (case-insensitive partial match):
      Phase 1: deep scan | scan repos | nested | temp
      Phase 2: lost | self_improve | abilities | wire
      Phase 3: promote | unify
      Phase 3b/3c: allowlist | curated promote
      Phase 4: world model
      Phase 5: plugin registry
      Phase 5b: wire recovered
      Phase 6: structure / validate
      Phase 6b: self heal
      Phase 7: monitor

    Full pipeline: /dispatch all  or  "full automation"
    """
    from datetime import datetime

    apply_workspace()
    out: dict[str, Any] = {
        "ok": True,
        "actions": [],
        "results": [],
        "errors": [],
        "prompt": (prompt or "")[:300],
        "workspace": str(_ws()),
        "home": str(_home()),
        "product_root": str(_product()),
        "mode": "product" if is_realai_product_tree() else "project",
    }

    try:
        home = _home()
        ws = _ws()
        scripts_dir = _scripts()
        if not scripts_dir.is_dir():
            out["ok"] = False
            out["error"] = f"scripts dir not found under workspace {ws}"
            out["summary"] = out["error"]
            print(f"[dispatcher] {out['error']}", flush=True)
            return out

        # Logs belong on the workspace root, never nested package / cwd.
        log_dir = ws / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            log_dir = home / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "dispatcher.log"

        def log(msg: str) -> None:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] {msg}"
            print(f"[dispatcher] {msg}", flush=True)
            out["actions"].append(msg)
            try:
                with log_file.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except OSError:
                pass

        # Per-phase timeouts (seconds)
        PHASE_TIMEOUTS = {
            "catalog_good_code_roots.py": 120,
            "walk_root.py": 1800,
            "walk_training_sources.py": 600,
            "wire_training.py": 900,
            "dispatch_training.py": 7200,
            "train_lora_local.py": 7200,
            "amd_stack_status.py": 120,
            "deep_unify_walk.py": 7200,
            "organize_repo.py": 900,
            "scan_repos_for_realai.py": 1200,
            "find_self_improve_and_lost.py": 900,
            "promote_unified_realai.py": 1200,
            "diff_imports_promote_allowlist.py": 600,
            "curated_promote.py": 900,
            "deep_promote_scan.py": 1800,
            "deep_promote_wire.py": 600,
            "world_model_merger.py": 600,
            "plugin_registry_builder.py": 600,
            "wire_recovered.py": 900,
            "wire_hive_agents.py": 120,
            "unified_structure_validator.py": 300,
            "self_heal_loop.py": 600,
            "heal_cli.py": 300,
            "monitor_model.py": 60,
            "run_all_repo_scripts.py": 3600,
        }

        def resolve_phase_script(script_name: str) -> Path | None:
            """Find phase script under scripts/, tools/, or any nested level."""
            direct = scripts_dir / script_name
            if direct.is_file():
                return direct
            tools_hit = home / "tools" / script_name
            if tools_hit.is_file():
                return tools_hit
            try:
                from core.realai_root_walker import resolve_script_from_walk

                hit = resolve_script_from_walk(home, script_name)
                if hit is not None and hit.is_file():
                    return hit
            except Exception as e:
                log(f"resolve_script_from_walk failed: {e}")
            # last resort: shallow rglob under scripts + tools
            for base in (scripts_dir, home / "tools", home / "abilities", home / "scanners"):
                if not base.is_dir():
                    continue
                try:
                    for p in base.rglob(script_name):
                        if p.is_file():
                            return p
                except OSError:
                    continue
            return None

        def run_script(script_name: str) -> dict[str, Any]:
            script_path = resolve_phase_script(script_name)
            timeout = PHASE_TIMEOUTS.get(script_name, 600)
            res: dict[str, Any] = {
                "script": script_name,
                "path": str(script_path) if script_path else str(scripts_dir / script_name),
                "ok": False,
                "timeout_s": timeout,
            }
            if script_path is None or not script_path.is_file():
                msg = f"missing script (any level): {script_name}"
                log(msg)
                res["error"] = "missing"
                out["errors"].append(msg)
                return res

            try:
                rel = str(script_path.relative_to(home)).replace("\\", "/")
            except ValueError:
                rel = str(script_path)
            res["rel"] = rel

            log(f"START {script_name} ({rel}) (timeout={timeout}s)")
            try:
                cmd = [sys.executable, str(script_path)]
                # Deep recursive walk should deepen nests during full dispatch
                if script_name == "walk_root.py":
                    cmd.append("--deepen")
                # deep_unify applies only when user asked to apply/write
                if script_name == "deep_unify_walk.py" and any(
                    k in p for k in ("apply", "write", "merge now", "organize apply")
                ):
                    cmd.append("--apply")
                # Training dispatch: optionally kick LoRA after wire
                if script_name == "dispatch_training.py" and any(
                    k in p
                    for k in (
                        "train now",
                        "start training",
                        "finetune now",
                        "lora train",
                        "dispatch training train",
                        "--train",
                    )
                ):
                    cmd.append("--train")
                    if "directml" in p:
                        cmd.extend(["--device", "directml"])
                    if "1.5b" in p or "coder-1.5" in p:
                        cmd.extend(["--preset", "qwen-coder-1.5b"])
                    elif "7b" in p:
                        cmd.extend(["--preset", "qwen-coder-7b"])
                    elif "0.5" in p:
                        cmd.extend(["--preset", "qwen-0.5b"])
                    elif "llama" in p:
                        cmd.extend(["--preset", "llama-3.2-1b"])
                if script_name == "wire_training.py":
                    cmd.append("--refresh-walk")
                completed = subprocess.run(
                    cmd,
                    cwd=str(home),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                )
                res["returncode"] = completed.returncode
                stdout = (completed.stdout or "")[-4000:]
                stderr = (completed.stderr or "")[-2000:]
                res["stdout_tail"] = stdout
                res["stderr_tail"] = stderr
                res["ok"] = completed.returncode == 0

                if completed.returncode == 0:
                    log(f"OK    {script_name} (exit 0)")
                else:
                    log(f"FAIL  {script_name} exit={completed.returncode}")
                    out["errors"].append(f"{script_name} exit={completed.returncode}")
                    out["ok"] = False

                # Evidence check — refuse to claim success if expected artifacts missing
                checks = ARTIFACT_CHECKS.get(script_name) or []
                if checks and completed.returncode == 0:
                    found_any = False
                    art_info = []
                    for rel in checks:
                        ap = home / rel
                        if ap.is_file() and ap.stat().st_size > 0:
                            found_any = True
                            art_info.append(f"{rel} ({ap.stat().st_size}B)")
                    res["artifacts"] = art_info
                    if not found_any:
                        res["ok"] = False
                        msg = f"NO ARTIFACTS after {script_name} (expected one of {checks})"
                        log(msg)
                        res["error"] = "missing_artifacts"
                        out["errors"].append(msg)
                        out["ok"] = False
                    else:
                        log(f"  evidence> {', '.join(art_info)}")

                if stdout.strip():
                    for ln in stdout.strip().splitlines()[-6:]:
                        log(f"  out> {ln[:180]}")
                if stderr.strip():
                    for ln in stderr.strip().splitlines()[-4:]:
                        log(f"  err> {ln[:180]}")

            except subprocess.TimeoutExpired:
                msg = f"TIMEOUT {script_name} (>{timeout}s)"
                log(msg)
                res["error"] = "timeout"
                out["errors"].append(msg)
                out["ok"] = False
            except Exception as e:
                msg = f"EXCEPTION {script_name}: {type(e).__name__}: {e}"
                log(msg)
                res["error"] = str(e)
                out["errors"].append(msg)
                out["ok"] = False
            return res

        p = (prompt or "").lower().strip()
        log(f"dispatch begin | run_all={run_all} | prompt={p[:120]!r}")
        log(f"scripts_dir={scripts_dir}")

        # Keep recovered/ JSON contract in sync (phases 1–2 used to break after archive move)
        try:
            rec = home / "recovered"
            scripts_rec = home / "scripts" / "recovered"
            rec.mkdir(parents=True, exist_ok=True)
            if scripts_rec.is_dir():
                for name in (
                    "REALAI_REPO_SCAN.json",
                    "REALAI_SELF_IMPROVE_CANDIDATES.json",
                    "GOOD_CODE_ROOTS.json",
                ):
                    src, dst = scripts_rec / name, rec / name
                    if src.is_file() and (
                        not dst.is_file() or src.stat().st_mtime >= dst.stat().st_mtime
                    ):
                        dst.write_bytes(src.read_bytes())
                        log(f"synced recovered/{name} from scripts/recovered")
        except OSError as e:
            log(f"recovered sync skipped: {e}")

        ARTIFACT_CHECKS = {
            "catalog_good_code_roots.py": [
                "scan_results/GOOD_CODE_ROOTS.json",
                "recovered/GOOD_CODE_ROOTS.json",
            ],
            "walk_root.py": [
                "scan_results/realai_root_walk.json",
                "scan_results/realai_root_walk.md",
            ],
            "organize_repo.py": [
                "scan_results/ORGANIZE_PLAN.json",
                "scan_results/ORGANIZE_PLAN.md",
            ],
            "deep_unify_walk.py": [
                "scan_results/DEEP_UNIFY_REPORT.json",
                "scan_results/DEEP_UNIFY_REPORT.md",
                "scan_results/realai_root_walk.json",
            ],
            "walk_training_sources.py": [
                "scan_results/TRAINING_SOURCES_WALK.json",
                "scan_results/TRAINING_SOURCES_WALK.md",
            ],
            "wire_training.py": [
                "scan_results/TRAINING_WIRE.json",
                "scan_results/TRAINING_WIRE.md",
            ],
            "dispatch_training.py": [
                "scan_results/TRAINING_DISPATCH.json",
                "scan_results/TRAINING_DISPATCH.md",
                "scan_results/TRAINING_WIRE.json",
            ],
            "deep_promote_scan.py": [
                "scan_results/DEEP_PROMOTE_MAP.md",
                "scan_results/deep_promote_queue.json",
            ],
            "deep_promote_wire.py": ["scan_results/DEEP_PROMOTE_WIRE_LOG.json"],
            "wire_hive_agents.py": ["scan_results/HIVE_AGENTS.json"],
            "curated_promote.py": [
                "scan_results/CURATED_PROMOTE.md",
                "scan_results/CURATED_PROMOTE_LOG.json",
                "recovered/CURATED_PROMOTE_LOG.json",
            ],
            "scan_repos_for_realai.py": [
                "scripts/recovered/REALAI_REPO_SCAN.json",
                "recovered/REALAI_REPO_SCAN.json",
            ],
            "find_self_improve_and_lost.py": [
                "scripts/recovered/REALAI_SELF_IMPROVE_CANDIDATES.json",
                "recovered/REALAI_SELF_IMPROVE_CANDIDATES.json",
                "scan_results/REALAI_SELF_IMPROVE_CANDIDATES.json",
            ],
        }

        phases = [
            {
                "name": "PHASE 0 — CATALOG GOOD CODE ROOTS",
                "script": "catalog_good_code_roots.py",
                "keywords": [
                    "good code", "code roots", "catalog roots", "where is code",
                    "gold roots", "live trees",
                ],
            },
            {
                "name": "PHASE 0b — NESTED ROOT WALK (py/js/json + scripts any level)",
                "script": "walk_root.py",
                "keywords": [
                    "walk root", "root walk", "nested folders", "unify nests",
                    "walk_root", "see nested", "scripts any level", "unify map",
                    "json", "javascript",
                ],
            },
            {
                "name": "PHASE 0c — ORGANIZE PLAN (nests → proper locations)",
                "script": "organize_repo.py",
                "keywords": [
                    "organize", "organise", "rehome", "proper locations",
                    "patch merge", "merge nests", "organize repo",
                ],
            },
            {
                "name": "PHASE 0d — DEEP UNIFY (deepest nests → organize → wire)",
                "script": "deep_unify_walk.py",
                "keywords": [
                    "deep unify", "deepen walk", "unify deepest", "deep-unify",
                    "wire abilities", "deepest nests",
                ],
            },
            {
                "name": "PHASE T1 — TRAINING SOURCES WALK (learn/memory/finetune)",
                "script": "walk_training_sources.py",
                "keywords": [
                    "train walk", "training walk", "walk training", "train-walk",
                    "memory train", "learning scripts", "finetune sources",
                    "what should i train", "training data walk",
                ],
            },
            {
                "name": "PHASE T2 — WIRE TRAINING (ingest + LoRA-ready JSONL)",
                "script": "wire_training.py",
                "keywords": [
                    "wire training", "train wire", "ingest training",
                    "build lora dataset", "training sources",
                ],
            },
            {
                "name": "PHASE T3 — DISPATCH TRAINING (walk→wire→optional train)",
                "script": "dispatch_training.py",
                "keywords": [
                    "dispatch training", "training dispatch", "train pipeline",
                    "full training", "train all phases", "training automation",
                    "lora train", "start training", "finetune now",
                ],
            },
            {
                "name": "PHASE T4 — AMD STACK STATUS (Vulkan chat + DirectML)",
                "script": "amd_stack_status.py",
                "keywords": [
                    "amd stack", "vulkan train status", "directml status",
                    "chat and train", "stack status",
                ],
            },
            {
                "name": "PHASE 1 — DEEP SCAN (repos + nested + good-code roots)",
                "script": "scan_repos_for_realai.py",
                "keywords": [
                    "read first", "deep scan", "scan repos", "scan for realai",
                    "nested", "temp", "temp_repos", "nested repo",
                ],
            },
            {
                "name": "PHASE 2 — FIND LOST / SELF-IMPROVE / ABILITIES",
                "script": "find_self_improve_and_lost.py",
                "keywords": [
                    "learn", "lost", "self_improve", "self-improve",
                    "find lost", "abilities", "ability", "wire", "wiring",
                    "servers", "missing code", "good code",
                ],
            },
            {
                "name": "PHASE 3 — PROMOTE / UNIFY",
                "script": "promote_unified_realai.py",
                "keywords": ["promote unified", "unify realai", "unify map"],
            },
            {
                "name": "PHASE 3b — DIFF + ALLOWLIST (safe promote)",
                "script": "diff_imports_promote_allowlist.py",
                "keywords": ["allowlist", "diff imports", "promote allowlist"],
            },
            {
                "name": "PHASE 3c — CURATED PROMOTE",
                "script": "curated_promote.py",
                "keywords": ["curated", "curated promote", "allowlist promote", "safe promote"],
            },
            {
                "name": "PHASE 3d — DEEP PROMOTE SCAN (named roots + nests)",
                "script": "deep_promote_scan.py",
                "keywords": [
                    "deep promote", "promote deep", "nested gold", "deep gold",
                    "named folders", "function diff", "richer nest", "deep scan promote",
                    "promote",  # bare promote → deep path (bundled with 3e below)
                ],
            },
            {
                "name": "PHASE 3e — DEEP PROMOTE WIRE (thin wraps)",
                "script": "deep_promote_wire.py",
                "keywords": [
                    "deep wire", "wire deep", "thin wrap", "wire nested",
                    "promote wire", "integrate nested", "deep promote", "promote deep",
                    "nested gold", "promote",
                ],
            },
            {
                "name": "PHASE 4 — WORLD MODEL MERGE",
                "script": "world_model_merger.py",
                "keywords": ["world model", "merge world model", "world_model"],
            },
            {
                "name": "PHASE 5 — PLUGIN REGISTRY",
                "script": "plugin_registry_builder.py",
                "keywords": [
                    "plugin registry", "plugins registry", "plugin_registry",
                    "build plugins", "registry builder", "plugins",
                ],
            },
            {
                "name": "PHASE 5b — WIRE RECOVERED (abilities / servers)",
                "script": "wire_recovered.py",
                "keywords": [
                    "wire", "wiring", "wire recovered", "wire abilities",
                    "wire servers", "connect recovered",
                ],
            },
            {
                "name": "PHASE 5c — WIRE HIVE AGENTS (.github/agents)",
                "script": "wire_hive_agents.py",
                "keywords": [
                    "hive agents", "wire hive", "activate hive", "hive mode",
                    "overseer", "github agents", "nextgen hive",
                ],
            },
            {
                "name": "PHASE 6 — STRUCTURE VALIDATION",
                "script": "unified_structure_validator.py",
                "keywords": [
                    "validate", "structure", "folder structure",
                    "structure validate", "unified structure",
                ],
            },
            {
                "name": "PHASE 6b — SELF HEAL LOOP",
                "script": "self_heal_loop.py",
                "keywords": ["self heal", "self_heal", "heal loop", "heal"],
            },
            {
                "name": "PHASE 7 — MONITOR (one-shot)",
                "script": "monitor_model.py",
                "keywords": [
                    "evolution plan", "long-term", "monitor", "monitor model",
                    "evolution",
                ],
            },
        ]

        full_kws = (
            "full automation", "run all phases", "dispatch all", "automate all",
            "run the 7", "full pipeline", "auto execute all", "run all scripts",
            "all phases", "run everything",
        )
        force_all = bool(run_all) or any(k in p for k in full_kws)

        recovery_intent = any(
            k in p for k in ("abilities", "ability", "wire", "wiring", "servers", "nested", "lost")
        )

        to_run: list[str] = []
        if force_all:
            to_run = [ph["script"] for ph in phases]
            log(f"FULL pipeline — will run all {len(phases)} phases in order")
        else:
            for ph in phases:
                if any(kw in p for kw in ph["keywords"]):
                    to_run.append(ph["script"])
                    log(f"matched {ph['name']}")

            if recovery_intent and not to_run:
                to_run = [
                    "catalog_good_code_roots.py",
                    "walk_root.py",
                    "organize_repo.py",
                    "scan_repos_for_realai.py",
                    "find_self_improve_and_lost.py",
                    "promote_unified_realai.py",
                    "diff_imports_promote_allowlist.py",
                    "curated_promote.py",
                    "deep_promote_scan.py",
                    "deep_promote_wire.py",
                    "world_model_merger.py",
                    "plugin_registry_builder.py",
                    "wire_recovered.py",
                ]
                log("recovery intent detected → forced good-code + walk + organize + discovery + promote + wire phases")

        # De-dupe while preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for s in to_run:
            if s not in seen:
                seen.add(s)
                ordered.append(s)

        if not ordered:
            log("no matching phases — nothing to run")
            out["summary"] = (
                "No automation phases matched. "
                "Try: /dispatch all   or mention 'abilities', 'wire', 'world model', etc."
            )
            return out

        log(f"executing {len(ordered)} script(s): {', '.join(ordered)}")
        for script in ordered:
            res = run_script(script)
            out["results"].append(res)

        n_ok = sum(1 for r in out["results"] if r.get("ok"))
        n_fail = len(out["results"]) - n_ok
        out["summary"] = (
            f"Dispatched {len(ordered)} phase(s) → {n_ok} ok, {n_fail} failed. "
            f"Scripts: {', '.join(ordered)}"
        )
        if out["errors"]:
            out["ok"] = False

        hints = []
        if any(r["script"] == "world_model_merger.py" and r.get("ok") for r in out["results"]):
            hints.append("Check realai/world_model/world_model.json for key count")
        if any(r["script"] == "plugin_registry_builder.py" and r.get("ok") for r in out["results"]):
            hints.append("Check realai/plugins/registry.json for discovered plugins")
        if any(r["script"] == "find_self_improve_and_lost.py" and r.get("ok") for r in out["results"]):
            hints.append("Inspect recovered/REALAI_SELF_IMPROVE_CANDIDATES.json for abilities")
        if any(r["script"] == "wire_recovered.py" and r.get("ok") for r in out["results"]):
            hints.append("wire_recovered.py finished — check how abilities/servers were connected")
        if hints:
            out["next"] = hints
            for h in hints:
                log(f"hint> {h}")

        log(out["summary"])
        log("dispatch complete")

    except Exception as e:
        out["ok"] = False
        out["error"] = str(e)
        out["traceback"] = traceback.format_exc()[-800:]
        out["summary"] = f"Dispatcher fatal: {e}"
        try:
            print(f"[dispatcher] FATAL: {e}", flush=True)
        except Exception:
            pass

    return out

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

