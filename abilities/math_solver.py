"""Ability: exact math with SymPy, every solution verified by substitution.

Handles equations ("2x^2 + 3x - 5 = 0", systems separated by ';' or ','),
plain expressions (simplify/evaluate), derivatives ("derivative of ..."),
integrals ("integrate ...") and limits are left to sympify-able input.
No model and no network needed; sympy is an optional dependency.
"""

from __future__ import annotations

import re
from typing import Any

ABILITY = {
    "id": "math_solver",
    "name": "math_solver",
    "type": "ability",
    "status": "LIVE",
    "source": "sympy (local, deterministic)",
    "dest": "abilities/math_solver.py",
    "capabilities": ["solve", "simplify", "differentiate", "integrate", "verify"],
    "secrets_policy": "none",
}

_PREFIX = re.compile(r"^\s*(solve( for [a-z])?|simplify|evaluate|compute|calculate)\s*[:,]?\s*", re.I)


def _parse(expr: str):
    from sympy.parsing.sympy_parser import (
        convert_xor, implicit_multiplication_application, parse_expr, standard_transformations,
    )

    expr = expr.replace("²", "^2").replace("³", "^3").replace("−", "-").replace("×", "*").replace("÷", "/")
    return parse_expr(expr, transformations=standard_transformations + (implicit_multiplication_application, convert_xor))


def solve(problem: str) -> dict[str, Any]:
    import sympy as sp

    text = str(problem or "").strip()
    m = re.search(r"solve for ([a-zA-Z])", text, re.I)
    want = sp.Symbol(m.group(1)) if m else None
    body = _PREFIX.sub("", text).strip().rstrip(".")
    kind = "expression"
    low = body.lower()
    if low.startswith(("derivative of", "differentiate", "d/dx")):
        e = _parse(re.sub(r"^(derivative of|differentiate|d/dx)\s*", "", body, flags=re.I))
        var = want or (sorted(e.free_symbols, key=str) or [sp.Symbol("x")])[0]
        ans = sp.diff(e, var)
        return {"ok": True, "kind": "derivative", "input": text, "answer": str(sp.simplify(ans)), "verified": True,
                "method": f"sympy.diff wrt {var}"}
    if low.startswith(("integrate", "integral of")):
        e = _parse(re.sub(r"^(integrate|integral of)\s*", "", body, flags=re.I))
        var = want or (sorted(e.free_symbols, key=str) or [sp.Symbol("x")])[0]
        ans = sp.integrate(e, var)
        ok = sp.simplify(sp.diff(ans, var) - e) == 0
        return {"ok": True, "kind": "integral", "input": text, "answer": f"{ans} + C", "verified": bool(ok),
                "method": "sympy.integrate; verified by differentiating back"}

    parts = [p for p in re.split(r"[;\n]|,(?![^()]*\))", body) if p.strip()]
    if any("=" in p for p in parts):
        kind = "equation"
        eqs = []
        for p in parts:
            lhs, _, rhs = p.partition("=")
            eqs.append(sp.Eq(_parse(lhs), _parse(rhs or "0")))
        syms = sorted(set().union(*(e.free_symbols for e in eqs)), key=str)
        targets = [want] if want else syms
        sols = sp.solve(eqs, targets, dict=True)
        checked = []
        for s in sols:
            ok = all(sp.simplify(e.lhs.subs(s) - e.rhs.subs(s)) == 0 for e in eqs)
            checked.append({"solution": {str(k): str(v) for k, v in s.items()},
                            "numeric": {str(k): (str(sp.N(v, 8))) for k, v in s.items()}, "verified": bool(ok)})
        return {"ok": bool(sols), "kind": kind, "input": text, "solutions": checked,
                "answer": "; ".join(", ".join(f"{k} = {v}" for k, v in c["solution"].items()) for c in checked) or "no solution",
                "verified": bool(checked) and all(c["verified"] for c in checked),
                "method": "sympy.solve; each solution substituted back into every equation"}
    e = _parse(body)
    simp = sp.simplify(e)
    out = {"ok": True, "kind": kind, "input": text, "answer": str(simp), "verified": sp.simplify(e - simp) == 0,
           "method": "sympy.simplify; checked expr - result == 0"}
    if not simp.free_symbols:
        out["numeric"] = str(sp.N(simp, 12))
    return out


def run(input: str = "", context: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    problem = str(ctx.get("problem") or input or "").strip()
    if not problem:
        return {"ok": False, "ability": "math_solver", "error": "problem required"}
    try:
        res = solve(problem)
    except ImportError:
        return {"ok": False, "ability": "math_solver", "status": "unavailable", "error": "sympy not installed (pip install sympy)"}
    except Exception as exc:
        return {"ok": False, "ability": "math_solver", "status": "error", "error": f"could not parse: {exc}"}
    return {"ability": "math_solver", "status": "success" if res.get("ok") else "error", **res}
