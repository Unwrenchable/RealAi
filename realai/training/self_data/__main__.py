"""python -m realai.training.self_data {generate,verify-traffic,improve,export-shots,stats}"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m realai.training.self_data")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="hive writes questions -> real tools -> verified rows")
    g.add_argument("--base-url", default="http://127.0.0.1:8080", help="teacher model endpoint (OpenAI-compatible)")
    g.add_argument("--model", default="local")
    g.add_argument("--minutes", type=float, default=30)
    g.add_argument("--max-rows", type=int, default=800)
    g.add_argument("--per-batch", type=int, default=6)
    g.add_argument("--sleep", type=float, default=0.0, help="pause between requests to keep the endpoint usable")
    g.add_argument("--plan", default="even", help="'even', 'auto' (latest improvement report), or JSON {tool: weight}")
    g.add_argument("--tools", nargs="*", help="limit to these targets")
    g.add_argument("--judge", action="store_true", help="also ask the teacher to judge grounding (slower)")
    g.add_argument("--shot-catalog")
    g.add_argument("--seed", type=int, default=0)
    sub.add_parser("verify-traffic", help="captured real traffic -> verifier -> hive_selfplay")
    i = sub.add_parser("improve", help="spot-check + self-play failures -> plan + report")
    i.add_argument("--spotcheck")
    e = sub.add_parser("export-shots", help="cache RackUp shot catalogue as REALAI_HOME/datasets/_sources/shot_catalog.json")
    e.add_argument("catalog")
    a = ap.parse_args(argv)

    from . import generate as gen

    if a.cmd == "export-shots":
        from realai.training.dataset_builder.adapters import load_shot_catalog

        shots = load_shot_catalog(Path(a.catalog))
        p = gen.home() / "datasets" / "_sources" / "shot_catalog.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(shots, ensure_ascii=False), encoding="utf-8")
        print(f"{len(shots)} shots -> {p}")
        return 0
    if a.cmd == "improve":
        from .improve import analyse, write_report

        rep = analyse(Path(a.spotcheck) if a.spotcheck else None)
        print(json.dumps({k: rep[k] for k in ("spotcheck_pass_rate", "weak", "plan")}, indent=1))
        print("report:", write_report(rep))
        return 0
    if a.cmd == "verify-traffic":
        print(json.dumps(gen.verify_traffic(), indent=1))
        return 0
    from realai import hive_tools
    from realai.hive_tools import tool_loop

    if a.shot_catalog:
        from realai.training.dataset_builder.adapters import load_shot_catalog

        hive_tools.set_shot_catalog(load_shot_catalog(Path(a.shot_catalog)))
    chat = tool_loop.http_chat(a.base_url, a.model, temperature=0.2, max_tokens=500)
    propose_chat = tool_loop.http_chat(a.base_url, a.model, temperature=0.9, max_tokens=900)
    if a.plan == "even":
        plan = {t: 1.0 for t in gen.TARGETS}
    elif a.plan == "auto":
        from .improve import latest_plan

        plan = latest_plan() or {t: 1.0 for t in gen.TARGETS}
    else:
        plan = json.loads(a.plan)
    if a.tools:
        plan = {t: w for t, w in plan.items() if t in a.tools}
    judge = None
    if a.judge:
        from .verify import llm_judge

        judge = llm_judge(tool_loop.http_chat(a.base_url, a.model, temperature=0.0, max_tokens=8))
    s = gen.run(chat, model=f"{a.model}@{a.base_url}", plan=plan, minutes=a.minutes, max_rows=a.max_rows,
                per_batch=a.per_batch, sleep=a.sleep, seed=a.seed, judge=judge, propose_chat=propose_chat, log=lambda m: print(m, flush=True))
    print(json.dumps(s, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
