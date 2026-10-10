"""Ability: real descriptive statistics on numbers or tabular rows (stdlib; pandas optional)."""

from __future__ import annotations

import math
import statistics as st
from typing import Any

ABILITY = {
    "id": "data_analysis",
    "name": "data_analysis",
    "type": "ability",
    "status": "LIVE",
    "source": "python statistics (pandas optional for tables)",
    "dest": "abilities/data_analysis.py",
    "capabilities": ["descriptive_stats", "outliers", "trend", "correlation"],
    "secrets_policy": "none",
}


def describe(values: list[float]) -> dict[str, Any]:
    xs = [float(v) for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    n = len(xs)
    if n == 0:
        return {"count": 0}
    out: dict[str, Any] = {"count": n, "sum": sum(xs), "min": min(xs), "max": max(xs), "mean": st.fmean(xs),
                           "median": st.median(xs)}
    if n > 1:
        out["stdev"] = st.stdev(xs)
        q = st.quantiles(xs, n=4, method="inclusive")
        out["q1"], out["q3"] = q[0], q[2]
        iqr = q[2] - q[0]
        lo, hi = q[0] - 1.5 * iqr, q[2] + 1.5 * iqr
        out["outliers"] = [x for x in xs if x < lo or x > hi]
        idx = list(range(n))
        slope = st.linear_regression(idx, xs).slope if len(set(xs)) > 1 else 0.0
        out["trend_slope_per_step"] = slope
        out["trend"] = "rising" if slope > 0 else "falling" if slope < 0 else "flat"
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out.items()}


def run(input: str = "", context: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    data = ctx.get("data", input)
    if isinstance(data, str):
        data = [float(t) for t in data.replace(",", " ").split() if t.replace(".", "", 1).lstrip("-").isdigit()]
    if not data:
        return {"ok": False, "ability": "data_analysis", "error": "data required (list of numbers or list of dict rows)"}
    if isinstance(data, list) and all(isinstance(r, dict) for r in data):
        cols: dict[str, list[float]] = {}
        for r in data:
            for k, v in r.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    cols.setdefault(k, []).append(float(v))
        stats = {k: describe(v) for k, v in cols.items()}
        corr = {}
        keys = [k for k, v in cols.items() if len(v) == len(data) and len(set(v)) > 1]
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                corr[f"{a}~{b}"] = round(st.correlation(cols[a], cols[b]), 6)
        return {"ok": True, "ability": "data_analysis", "status": "success", "rows": len(data), "columns": stats,
                "correlation": corr, "real": True}
    try:
        stats = describe(list(data))
    except (TypeError, ValueError) as exc:
        return {"ok": False, "ability": "data_analysis", "error": f"non-numeric data: {exc}"}
    return {"ok": True, "ability": "data_analysis", "status": "success", "statistics": stats, "real": True}
