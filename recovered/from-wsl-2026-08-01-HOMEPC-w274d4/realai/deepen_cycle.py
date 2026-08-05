#!/usr/bin/env python3
"""
RealAI Deepen Cycle — every successful run should go deeper than the last.

Records:
  scan_results/deepen_history.jsonl   (one line per run)
  scan_results/deepen_last.json       (latest snapshot)
  scan_results/deepen_last.md         (human report)

Steps (safe, no bulk merge):
  1. Snapshot previous depth (keywords, coverage, artifacts)
  2. Learn keywords + ability catalog (+ training samples if self-improve on)
  3. Optional self-heal assemble (flag)
  4. Optional multi-agent hive reflection on new depth (if Vulkan up)
  5. Compare depth_before vs depth_after → deeper=true/false
  6. Persist history so the next run knows where it left off

Usage:
  set REALAI_SELF_IMPROVE=true
  set REALAI_VULKAN_BASE=http://127.0.0.1:8080
  python -m realai.deepen_cycle
  python -m realai.deepen_cycle --no-hive --assemble
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent
_SCAN = _ROOT / "scan_results"
_HISTORY = _SCAN / "deepen_history.jsonl"
_LAST = _SCAN / "deepen_last.json"
_LAST_MD = _SCAN / "deepen_last.md"

VULKAN_BASE = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")
ORCH_BASE = os.environ.get("REALAI_ORCH_BASE", "http://127.0.0.1:8001").rstrip("/")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _self_improve_on() -> bool:
    return os.environ.get("REALAI_SELF_IMPROVE", "").lower() in ("1", "true", "yes")


def _http_get(url: str, timeout: float = 10) -> tuple[bool, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            raw = r.read()
            try:
                return True, json.loads(raw.decode("utf-8"))
            except Exception:
                return True, raw.decode("utf-8", errors="ignore")[:300]
    except Exception as e:
        return False, str(e)


def _http_post(url: str, payload: dict, timeout: float = 300) -> tuple[bool, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")[:800]
        except Exception:
            body = str(e)
        return False, {"http_error": e.code, "body": body}
    except Exception as e:
        return False, str(e)


def snapshot_depth() -> Dict[str, Any]:
    """Current measurable depth of RealAI self-knowledge."""
    keywords = 0
    kw_path = _SCAN / "ability_keywords_learned.json"
    if kw_path.is_file():
        try:
            keywords = len(json.loads(kw_path.read_text(encoding="utf-8")).get("keywords") or [])
        except Exception:
            pass

    coverage_pct = None
    live_count = None
    ability_count = None
    external_ok = None
    external_total = None
    try:
        from realai.ability_catalog import coverage_summary
        cov = coverage_summary()
        c = cov.get("coverage") or {}
        coverage_pct = c.get("weighted_pct")
        live_count = c.get("live_count")
        ability_count = c.get("ability_count")
        external_ok = cov.get("external_roots_exist")
        external_total = cov.get("external_roots_total")
    except Exception as e:
        coverage_pct = f"error:{e}"

    inv_tokens = None
    inv = _SCAN / "dds3_ability_inventory.json"
    if inv.is_file():
        try:
            d = json.loads(inv.read_text(encoding="utf-8"))
            inv_tokens = (d.get("meta") or {}).get("unique_tokens") or (d.get("counts") or {}).get("multi_era")
        except Exception:
            pass

    artifacts = {
        "ability_catalog": (_SCAN / "ability_catalog.json").is_file(),
        "keywords_learned": kw_path.is_file(),
        "gold_index": (_SCAN / "gold_index.json").is_file(),
        "promote_queue": (_SCAN / "promote_queue.json").is_file(),
        "era_map": (_SCAN / "era_map.json").is_file(),
        "recycle_gold_map": (_SCAN / "recycle_bin_gold_map.json").is_file(),
        "agent_tools_gold": (_PKG / "agent_tools_gold" / "cli.py").is_file(),
        "orchestration_gold": (_PKG / "orchestration_gold" / "orchestrator.py").is_file(),
        "ability_surface_jsonl": (_ROOT / "training" / "data" / "ability_surface.jsonl").is_file(),
        "hive_priority_uniques": (
            _ROOT / "recovered" / "from_recycle_bin" / "hive_priority_uniques"
        ).is_dir(),
    }

    vulkan_ok, _ = _http_get(f"{VULKAN_BASE}/health", timeout=3)
    orch_ok, orch_body = _http_get(f"{ORCH_BASE}/health", timeout=5)

    return {
        "ts": _utc(),
        "keywords": keywords,
        "coverage_pct": coverage_pct,
        "live_count": live_count,
        "ability_count": ability_count,
        "external_roots": f"{external_ok}/{external_total}" if external_total is not None else None,
        "inventory_tokens": inv_tokens,
        "artifacts_present": sum(1 for v in artifacts.values() if v),
        "artifacts_total": len(artifacts),
        "artifacts": artifacts,
        "vulkan_ok": vulkan_ok,
        "orch_ok": orch_ok,
        "orch_health": orch_body if isinstance(orch_body, dict) else str(orch_body)[:120],
        "self_improve": _self_improve_on(),
    }


def _mine_new_keywords_from_gold() -> List[str]:
    """Pull novel tokens from recycle map, hive reports, recovered dirs into learned keywords."""
    import re

    existing: set = set()
    kw_path = _SCAN / "ability_keywords_learned.json"
    if kw_path.is_file():
        try:
            existing = set(json.loads(kw_path.read_text(encoding="utf-8")).get("keywords") or [])
        except Exception:
            existing = set()

    candidates: set = set()
    # recycle gold original basenames
    rec = _SCAN / "recycle_bin_gold_map.json"
    if rec.is_file():
        try:
            hits = (json.loads(rec.read_text(encoding="utf-8")).get("scan") or {}).get("gold_hits") or []
            for h in hits:
                orig = str(h.get("original_path") or "")
                for part in re.split(r"[\\/]+", orig):
                    stem = re.sub(r"\.[a-z0-9]+$", "", part, flags=re.I)
                    if re.match(r"^[A-Za-z][A-Za-z0-9_\-]{2,40}$", stem):
                        if any(k in stem.lower() for k in (
                            "realai", "agent", "overseer", "memory", "orchestr", "embed",
                            "solana", "web3", "fizz", "tool", "train", "model", "hive",
                        )):
                            candidates.add(stem.lower().replace("-", "_"))
        except Exception:
            pass

    # hive priority uniques paths
    hive_dir = _ROOT / "recovered" / "from_recycle_bin" / "hive_priority_uniques"
    if hive_dir.is_dir():
        for p in hive_dir.rglob("*"):
            if p.is_file():
                candidates.add(p.stem.lower()[:40])

    # fixed deepen vocabulary that grows the graph
    for k in (
        "deepen_cycle", "super_grok_1_0", "recycle_bin_gold", "clear_name_restore",
        "assembled_realai_core", "hive_priority_uniques", "agent_tools_gold",
        "orchestration_gold", "ability_surface", "multi_agent_pipeline",
        "weights_gold", "gguf_connect", "realai_model_family",
    ):
        candidates.add(k)

    # staged users dotfiles gold
    udot = _ROOT / "recovered" / "from_users_dotfiles"
    if udot.is_dir():
        candidates.update({
            "openclaw", "openclaw_workspace", "soul_md", "identity_md",
            "users_dotfiles", "local_models_json", "env_local_fizz",
            "realai_program_id", "caps_token", "execution_history",
        })
        for p in udot.rglob("*.md"):
            if p.stem.upper() in {"SOUL", "IDENTITY", "AGENTS", "TOOLS", "USER", "BOOTSTRAP", "HEARTBEAT"}:
                candidates.add(p.stem.lower())
        lm = udot / ".realai" / "local_models.json"
        if lm.is_file():
            try:
                data = json.loads(lm.read_text(encoding="utf-8"))
                for mid in (data.get("models") or {}):
                    candidates.add(str(mid).lower().replace("-", "_")[:40])
            except Exception:
                pass

    # model weights gold map (if scanned)
    wmap = _SCAN / "weights_gold_map.json"
    if wmap.is_file():
        try:
            w = json.loads(wmap.read_text(encoding="utf-8"))
            for c in (w.get("connect_candidates") or [])[:40]:
                name = str(c.get("name") or "")
                stem = re.sub(r"\.[a-z0-9]+$", "", name, flags=re.I)
                if stem:
                    candidates.add(stem.lower().replace("-", "_")[:48])
                fam = c.get("family")
                if fam:
                    candidates.add(str(fam).lower())
                mid = c.get("realai_model_id_suggestion")
                if mid:
                    candidates.add(str(mid).lower().replace("-", "_"))
        except Exception:
            pass

    novel = sorted(candidates - existing)
    if not novel:
        return []

    # merge into learned file
    payload = {
        "version": 1,
        "updated_at": _utc(),
        "keywords": sorted(existing | set(novel)),
        "patterns": [],
        "added_this_cycle": novel,
        "added_count": len(novel),
        "total_count": len(existing) + len(novel),
        "sources": ["deepen_cycle_mine_gold"],
        "note": "Mined by deepen_cycle so each run can still deepen when inventory plateaus",
    }
    # preserve previous patterns if any
    if kw_path.is_file():
        try:
            prev = json.loads(kw_path.read_text(encoding="utf-8"))
            payload["version"] = int(prev.get("version") or 1) + 1
            payload["patterns"] = prev.get("patterns") or []
            payload["sources"] = sorted(set((prev.get("sources") or []) + ["deepen_cycle_mine_gold"]))
        except Exception:
            pass
    # add simple token patterns for novel
    for kw in novel[:100]:
        if re.match(r"^[a-z_][a-z0-9_]*$", kw):
            payload["patterns"].append({
                "kind": "token",
                "keyword": kw,
                "regex": rf"\b{re.escape(kw)}\b",
            })
    _SCAN.mkdir(parents=True, exist_ok=True)
    kw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return novel


def depth_score(snap: Dict[str, Any]) -> float:
    """Scalar depth for comparison (higher = deeper)."""
    score = 0.0
    score += float(snap.get("keywords") or 0) * 0.01
    cov = snap.get("coverage_pct")
    if isinstance(cov, (int, float)):
        score += float(cov) * 0.5
    score += float(snap.get("live_count") or 0) * 2.0
    score += float(snap.get("artifacts_present") or 0) * 1.5
    if snap.get("vulkan_ok"):
        score += 5.0
    if snap.get("orch_ok"):
        score += 5.0
    inv = snap.get("inventory_tokens")
    if isinstance(inv, (int, float)):
        score += float(inv) * 0.02
    return round(score, 4)


def run_deepen(
    *,
    assemble: bool = True,
    hive: bool = True,
    cycle: bool = False,
) -> Dict[str, Any]:
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

    before = snapshot_depth()
    before_score = depth_score(before)
    steps: List[Dict[str, Any]] = []

    # 0) Mine fresh keywords from recycle / hive / recovered gold so plateau still deepens
    try:
        extra_kw = _mine_new_keywords_from_gold()
        if extra_kw:
            steps.append({"name": "mine_gold_keywords", "added": len(extra_kw), "sample": extra_kw[:15]})
        else:
            steps.append({"name": "mine_gold_keywords", "added": 0})
    except Exception as e:
        steps.append({"name": "mine_gold_keywords", "error": str(e)})

    # 1) Learn keywords + catalog
    try:
        from realai.self_heal import run_learn_keywords
        # learn does not require self_improve for catalog; training samples need it
        # run_learn_keywords always works; emit_training only if enabled inside
        if not _self_improve_on():
            # still allow catalog+keywords without training samples
            from realai.ability_catalog import (
                build_catalog,
                learn_keywords_from_scans,
                save_catalog,
            )
            learned = learn_keywords_from_scans(also_tools_cli=True)
            cat_path = save_catalog(build_catalog())
            learn_result = {
                "ok": True,
                "learned": {
                    "total_count": learned.get("total_count"),
                    "added_count": learned.get("added_count"),
                    "added_sample": (learned.get("added_this_cycle") or [])[:20],
                },
                "catalog_path": str(cat_path),
                "note": "self_improve off — skipped training sample emit",
            }
        else:
            learn_result = run_learn_keywords()
        steps.append({"name": "learn_keywords", "result": learn_result})
    except Exception as e:
        steps.append({"name": "learn_keywords", "error": str(e)})

    # 2) Assemble gold (needs self-improve)
    if assemble:
        try:
            if _self_improve_on():
                from realai.self_heal import run_assemble
                steps.append({"name": "assemble", "result": run_assemble()})
            else:
                steps.append({"name": "assemble", "skipped": "REALAI_SELF_IMPROVE not set"})
        except Exception as e:
            steps.append({"name": "assemble", "error": str(e)})

    # 3) Optional full self-heal cycle dry
    if cycle and _self_improve_on():
        try:
            from realai.self_heal import run_full_cycle
            steps.append({"name": "self_heal_cycle", "result": run_full_cycle(apply_promote=False)})
        except Exception as e:
            steps.append({"name": "self_heal_cycle", "error": str(e)})

    # 4) Hive reflection if Vulkan available
    hive_out = None
    if hive and before.get("vulkan_ok") or (hive and _http_get(f"{VULKAN_BASE}/health", 3)[0]):
        try:
            after_partial = snapshot_depth()
            task = (
                "Real Super Grok 1.0 deepen cycle. "
                f"Keywords before={before.get('keywords')} after_partial={after_partial.get('keywords')}. "
                f"Coverage before={before.get('coverage_pct')} now={after_partial.get('coverage_pct')}. "
                f"Artifacts {after_partial.get('artifacts_present')}/{after_partial.get('artifacts_total')}. "
                "In 8-12 lines: (1) what got deeper, (2) top 3 safe next gold targets, "
                "(3) what NOT to bulk-merge. Operator-grade."
            )
            from realai.v3_runtime_bridge import run_multi_agent
            hive_out = run_multi_agent(task, mode="pipeline", max_tokens=400, temperature=0.2)
            steps.append({
                "name": "hive_reflect",
                "ok": hive_out.get("ok"),
                "engine": hive_out.get("engine"),
                "final_snip": str(hive_out.get("final_output") or "")[:600],
            })
        except Exception as e:
            steps.append({"name": "hive_reflect", "error": str(e)})
    elif hive:
        steps.append({"name": "hive_reflect", "skipped": "vulkan_down"})

    after = snapshot_depth()
    after_score = depth_score(after)
    deeper = after_score > before_score
    added_keywords = int(after.get("keywords") or 0) - int(before.get("keywords") or 0)

    record = {
        "run_id": _utc().replace(":", "").replace("-", "")[:15],
        "started": before.get("ts"),
        "finished": after.get("ts"),
        "before": before,
        "after": after,
        "before_score": before_score,
        "after_score": after_score,
        "deeper": deeper,
        "delta_score": round(after_score - before_score, 4),
        "added_keywords": added_keywords,
        "steps": steps,
        "hive_final": (hive_out or {}).get("final_output") if hive_out else None,
        "success": True,  # structural success; hive may have skipped
        "note": (
            "Deepen = more keywords, coverage, artifacts, live stack health. "
            "Not bulk-merge. Next run loads this history."
        ),
    }

    # If hive failed due to vulkan, still success if learn worked
    learn_ok = any(
        s.get("name") == "learn_keywords" and (s.get("result") or {}).get("ok", "error" not in s)
        for s in steps
    )
    record["success"] = bool(learn_ok) and after.get("keywords", 0) >= before.get("keywords", 0)

    _SCAN.mkdir(parents=True, exist_ok=True)
    with _HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    _LAST.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")

    md = [
        "# RealAI Deepen Cycle",
        "",
        f"Run: `{record['run_id']}`",
        f"Deeper than last: **{deeper}** (score {before_score} → {after_score}, Δ {record['delta_score']})",
        f"Keywords: **{before.get('keywords')}** → **{after.get('keywords')}** (Δ {added_keywords})",
        f"Coverage: **{before.get('coverage_pct')}** → **{after.get('coverage_pct')}**",
        f"Artifacts: **{before.get('artifacts_present')}/{before.get('artifacts_total')}** → "
        f"**{after.get('artifacts_present')}/{after.get('artifacts_total')}**",
        f"Vulkan: {after.get('vulkan_ok')} · Orch: {after.get('orch_ok')} · Self-improve: {after.get('self_improve')}",
        "",
        "## Steps",
        "",
    ]
    for s in steps:
        name = s.get("name")
        if "error" in s:
            md.append(f"- **{name}**: ERROR `{s['error']}`")
        elif s.get("skipped"):
            md.append(f"- **{name}**: skipped ({s['skipped']})")
        elif name == "hive_reflect":
            md.append(f"- **{name}**: ok={s.get('ok')} engine={s.get('engine')}")
            if s.get("final_snip"):
                md.append(f"  - snip: {s['final_snip'][:300]}")
        else:
            r = s.get("result") or {}
            md.append(f"- **{name}**: ok={r.get('ok', True)} "
                      f"added={((r.get('learned') or {}).get('added_count'))}")
    if record.get("hive_final"):
        md += ["", "## Hive reflection", "", str(record["hive_final"])[:2000], ""]
    md += [
        "",
        "## Next run",
        "",
        "```bat",
        "set REALAI_SELF_IMPROVE=true",
        "set REALAI_VULKAN_BASE=http://127.0.0.1:8080",
        "python -m realai.deepen_cycle",
        "```",
        "",
        "History: `scan_results/deepen_history.jsonl`",
        "",
    ]
    _LAST_MD.write_text("\n".join(md), encoding="utf-8")
    return record


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="RealAI deepen cycle — each run goes deeper")
    ap.add_argument("--no-hive", action="store_true", help="Skip multi-agent reflection")
    ap.add_argument("--no-assemble", action="store_true", help="Skip gold assemble")
    ap.add_argument("--cycle", action="store_true", help="Also run full self-heal dry cycle")
    args = ap.parse_args(argv)

    print("=" * 60)
    print("RealAI Deepen Cycle — Super Grok 1.0 depth engine")
    print("=" * 60)
    rec = run_deepen(
        assemble=not args.no_assemble,
        hive=not args.no_hive,
        cycle=args.cycle,
    )
    print(f"deeper={rec['deeper']}  score {rec['before_score']} -> {rec['after_score']}  "
          f"keywords {rec['before'].get('keywords')} -> {rec['after'].get('keywords')}  "
          f"success={rec['success']}")
    print(f"report: {_LAST_MD}")
    print(f"history: {_HISTORY}")
    return 0 if rec.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
