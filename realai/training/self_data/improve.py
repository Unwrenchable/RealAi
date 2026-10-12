"""Improvement loop: failures -> targeted questions -> verified rows -> next dataset, with a per-run report.

Reads the latest spot-check report(s) (REALAI_HOME/runs/spotcheck-*.json) and self-play summaries
(hive_selfplay/summary-*.json), scores each tool/ability, and writes:
  hive_selfplay/reports/improvement-<stamp>.json  (plan: weights per tool for the next generate run)
  hive_selfplay/reports/improvement-<stamp>.md    (weak areas, reject reasons, rows added)
``python -m realai.training.self_data generate --plan auto`` uses the newest plan.
"""
from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from realai.hive_tools import NEW_TOOLS

from .generate import TARGETS, home, out_dir

# tools added by the 2026-10-12 wire audit start WEAK: no accepted rows yet -> weight bumped until they have some
NEW_TOOL_WEAK_WEIGHT = 2.5
NEW_TOOL_MIN_ROWS = 40
ABILITY_TO_TOOL = {**{t: t for t in NEW_TOOLS},"rackup_invoke": "rackup_invoke", "shot_lookup": "shot_lookup", "chess_engine": "chess_engine",
                   "device_profile": "device_profile", "ability_lookup": "ability_lookup", "route_to_agent": "route_to_agent",
                   "math_solver": "math_solver", "data_analysis": "data_analysis", "list_agents": "list_agents"}


def _latest(pattern: str, base: Path, n: int = 1) -> List[Path]:
    return sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime)[-n:] if base.is_dir() else []


def analyse(spotcheck: Optional[Path] = None) -> Dict[str, Any]:
    sc_paths = [spotcheck] if spotcheck else _latest("spotcheck-*.json", home() / "runs")
    sc = json.loads(sc_paths[0].read_text(encoding="utf-8")) if sc_paths else None
    fail: Counter = Counter()
    total: Counter = Counter()
    failures = []
    if sc:
        for r in sc["results"]:
            t = ABILITY_TO_TOOL.get(r["ability"])
            if not t:
                continue
            total[t] += 1
            if not r["passed"]:
                fail[t] += 1
                failures.append({"id": r["id"], "tool": t, "routed": r["routed"], "fact_ok": r["fact_ok"], "answer": r["answer"][:200]})
    sp: Dict[str, Counter] = {}
    rows_added = 0
    reasons: Counter = Counter()
    for p in _latest("summary-*.json", out_dir(), 5):
        s = json.loads(p.read_text(encoding="utf-8"))
        rows_added += s.get("accepted", 0)
        reasons.update(s.get("reject_reasons") or {})
        for t, st in (s.get("per_tool") or {}).items():
            sp.setdefault(t, Counter()).update(st)
    plan = {}
    weak = []
    for t in TARGETS:
        sc_fail = fail[t] / total[t] if total[t] else 0.0
        st = sp.get(t, Counter())
        tried = st.get("accepted", 0) + st.get("rejected", 0)
        rej = st.get("rejected", 0) / tried if tried else 0.0
        w = round(1.0 + 3.0 * sc_fail + 1.0 * rej, 2)
        new_weak = t in NEW_TOOLS and st.get("accepted", 0) < NEW_TOOL_MIN_ROWS
        if new_weak:
            w = max(w, NEW_TOOL_WEAK_WEIGHT)
        plan[t] = w
        if sc_fail > 0 or rej > 0.5 or new_weak:
            weak.append({"tool": t, "spotcheck_fail_rate": round(sc_fail, 2), "selfplay_reject_rate": round(rej, 2),
                         "accepted_rows": st.get("accepted", 0), "new_tool": t in NEW_TOOLS})
    weak.sort(key=lambda w: -(w["spotcheck_fail_rate"] * 3 + w["selfplay_reject_rate"]))
    return {"ts": _dt.datetime.now().isoformat(timespec="seconds"), "spotcheck": str(sc_paths[0]) if sc_paths else None,
            "spotcheck_pass_rate": sc.get("pass_rate") if sc else None, "weak": weak, "failures": failures,
            "selfplay_rows_added_recent": rows_added, "reject_reasons": dict(reasons.most_common(12)), "plan": plan}


def write_report(rep: Dict[str, Any]) -> Path:
    d = out_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (d / f"improvement-{stamp}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Improvement report {rep['ts']}", "",
             f"Spot-check: {rep['spotcheck'] or 'none'} (pass rate {rep['spotcheck_pass_rate']})",
             f"Verified self-play rows added (recent runs): {rep['selfplay_rows_added_recent']}", "",
             "## Weak areas", "", "| tool | spot-check fail | self-play reject | accepted rows |", "|---|---|---|---|"]
    lines += [f"| {w['tool']} | {w['spotcheck_fail_rate']} | {w['selfplay_reject_rate']} | {w['accepted_rows']} |" for w in rep["weak"]] or ["| none | | | |"]
    lines += ["", "## Spot-check failures", ""] + [f"- {f['id']} ({f['tool']}): routed={f['routed']} fact_ok={f['fact_ok']}: {f['answer'][:140]!r}"
                                                    for f in rep["failures"]]
    lines += ["", "## Top reject reasons", ""] + [f"- {k}: {v}" for k, v in rep["reject_reasons"].items()]
    lines += ["", "## Next generate plan (weights)", "", "```json", json.dumps(rep["plan"], indent=1), "```"]
    md = d / f"improvement-{stamp}.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


def latest_plan() -> Optional[Dict[str, float]]:
    p = _latest("improvement-*.json", out_dir() / "reports")
    return json.loads(p[0].read_text(encoding="utf-8"))["plan"] if p else None
