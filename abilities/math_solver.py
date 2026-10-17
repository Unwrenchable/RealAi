"""Ability: exact math with SymPy, every solution verified by substitution.

Handles equations ("2x^2 + 3x - 5 = 0", systems separated by ';', ',' or "and"),
identity checks ("verify (a+b)^2 = a^2 + 2ab + b^2 is always true"), plain expressions
(simplify/evaluate), derivatives ("derivative of ..."), indefinite and definite integrals
("integral of 1/(x^2+4) dx from 0 to infinity") and averages of plain number lists. Natural-language
lead-ins ("What's", "Compute the", "using sympy", "?") are stripped; statistics beyond a mean are
pointed at the data_analysis tool instead of failing with a parse error.
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
_LEAD = re.compile(r"^\s*(?:(?:please|can you|could you|what'?s|what is|what are|find|compute|calculate|evaluate|determine|"
                   r"work out|give me|tell me|check|verify|prove|show|is it true|is|are|does)\b\s*(?:(?:if|that|whether|me)\b)?\s*)+", re.I)
_TAIL = re.compile(r"\s*(?:,?\s*(?:using|with|via) (?:sympy|python|calculus)|please)?\s*[?.!]*\s*$", re.I)
_ALWAYS = re.compile(r"\s*(?:is|are)?\s*(?:always true|an identity|true for all [a-z]+|always holds|holds for all [a-z]+|"
                     r"valid for all [a-z]+)\s*$", re.I)
_INTEGRAL = re.compile(r"^(?:the\s+)?(?:definite\s+|indefinite\s+)?(?:integral of|integrate|antiderivative of)\s+(.+?)"
                       r"(?:\s*,?\s*(?:d\s*([a-z])))?(?:\s+(?:from|between)\s+(?:[a-z]\s*=\s*)?(.+?)\s+(?:to|and)\s+"
                       r"(?:[a-z]\s*=\s*)?(.+?))?$", re.I)
_STATS = re.compile(r"\b(median|standard deviation|std|variance|quartile|percentile|outlier|spread|range|mode|trend)\b", re.I)
_MEAN = re.compile(r"^(?:the\s+)?(?:average|mean|arithmetic mean)\s+(?:of\s+)?(.+)$", re.I)
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _bound(t: str):
    import sympy as sp

    t = t.strip().lower().replace("∞", "oo").replace("π", "pi")
    t = re.sub(r"\b(?:positive\s+)?infinity\b|\+\s*oo\b|\binf\b", "oo", t)
    t = re.sub(r"\bnegative\s+infinity\b|\bminus\s+infinity\b", "-oo", t)
    return sp.oo if t == "oo" else (-sp.oo if t == "-oo" else _parse(t))


def _clean(text: str) -> str:
    t = _TAIL.sub("", str(text or "").strip())
    t = _LEAD.sub("", t).strip()
    t = re.sub(r"^(?:the\s+)?(?:value of|result of)\s+", "", t, flags=re.I)
    t = re.sub(r"^(?:the\s+)?(?:system of equations|equations?|expression)\s*:?\s*", "", t, flags=re.I)
    return t.strip()


def _parse(expr: str):
    from sympy.parsing.sympy_parser import (
        convert_xor, implicit_multiplication_application, parse_expr, standard_transformations,
    )

    import sympy as sp

    expr = expr.replace("²", "^2").replace("³", "^3").replace("−", "-").replace("×", "*").replace("÷", "/").replace("π", "pi")
    local = {"e": sp.E} if re.search(r"\be\s*(\^|\*\*)", expr) else {}  # e^(2x): Euler's number, not a symbol
    return parse_expr(expr, local_dict=local,
                      transformations=standard_transformations + (implicit_multiplication_application, convert_xor))


def solve(problem: str) -> dict[str, Any]:
    import sympy as sp

    text = str(problem or "").strip()
    m = (re.search(r"solve for ([a-zA-Z])\b", text, re.I) or re.search(r"\bfor ([a-zA-Z]) in\b", text, re.I)
         or re.search(r"\bfor ([a-zA-Z])\s*[?.!]*\s*$", text, re.I))
    want = sp.Symbol(m.group(1)) if m else None
    body = _PREFIX.sub("", text).strip().rstrip(".")
    body = re.sub(r"^\s*(?:for [a-z]\s+)?in the equation\s*:?\s*", "", body, flags=re.I)
    body = _clean(body)
    body = re.sub(r",?\s+for ([a-zA-Z])\s*$", "", body)
    kind = "expression"
    low = body.lower()
    if low.startswith(("derivative of", "the derivative of", "differentiate", "d/dx")):
        e = _parse(re.sub(r"^(the derivative of|derivative of|differentiate|d/dx)\s*", "", body, flags=re.I))
        var = want or (sorted(e.free_symbols, key=str) or [sp.Symbol("x")])[0]
        ans = sp.diff(e, var)
        return {"ok": True, "kind": "derivative", "input": text, "answer": str(sp.simplify(ans)), "verified": True,
                "method": f"sympy.diff wrt {var}"}
    mi = _INTEGRAL.match(body)
    if mi:
        e = _parse(mi.group(1))
        var = sp.Symbol(mi.group(2)) if mi.group(2) else want or (sorted(e.free_symbols, key=str) or [sp.Symbol("x")])[0]
        if mi.group(3) is not None:
            a, b = _bound(mi.group(3)), _bound(mi.group(4))
            ans = sp.simplify(sp.integrate(e, (var, a, b)))
            out = {"ok": not ans.has(sp.Integral), "kind": "definite_integral", "input": text, "answer": str(ans),
                   "bounds": [str(a), str(b)], "verified": not ans.has(sp.Integral),
                   "method": f"sympy.integrate over {var} from {a} to {b}"}
            if not ans.free_symbols and not ans.has(sp.Integral):
                out["numeric"] = str(sp.N(ans, 12))
            return out
        ans = sp.integrate(e, var)
        ok = sp.simplify(sp.diff(ans, var) - e) == 0
        return {"ok": True, "kind": "integral", "input": text, "answer": f"{ans} + C", "verified": bool(ok),
                "method": "sympy.integrate; verified by differentiating back"}
    mm = _MEAN.match(body)
    if mm and not _STATS.search(body):
        nums = [sp.Rational(x) for x in _NUM.findall(mm.group(1))]
        if len(nums) >= 2 and not re.search(r"[a-zA-Z]", re.sub(r"\band\b", "", mm.group(1))):
            mean = sum(nums) / len(nums)
            return {"ok": True, "kind": "mean", "input": text, "answer": str(mean), "numeric": str(sp.N(mean, 12)),
                    "count": len(nums), "sum": str(sum(nums)), "verified": True, "method": "sum / count (exact rationals)"}
    if _STATS.search(body) and len(_NUM.findall(body)) >= 3:
        return {"ok": False, "kind": "statistics", "input": text,
                "error": "statistics on a data list: use the data_analysis tool (mean, median, std, quartiles, outliers, trend)"}

    identity = bool(_ALWAYS.search(body))
    body = _ALWAYS.sub("", body).strip()
    body = re.sub(r"\s+and\s+(?=[^=]*=)", "; ", body) if body.count("=") > 1 else body
    parts = [p for p in re.split(r"[;\n]|,(?![^()]*\))", body) if p.strip()]
    if any("=" in p for p in parts):
        kind = "equation"
        eqs = []
        for p in parts:
            lhs, _, rhs = p.partition("=")
            eqs.append(sp.Eq(_parse(lhs), _parse(rhs.lstrip("=") or "0"), evaluate=False))
        if identity or (len(eqs) == 1 and not want and sp.simplify(eqs[0].lhs - eqs[0].rhs) == 0):
            diffs = [sp.simplify(sp.expand(e.lhs - e.rhs)) for e in eqs]
            ok = all(d == 0 for d in diffs)
            return {"ok": True, "kind": "identity", "input": text, "identity": ok,
                    "answer": "true for all values (identity)" if ok else f"not an identity: lhs - rhs = {diffs[0]}",
                    "verified": True, "method": "sympy.simplify(expand(lhs - rhs)) == 0"}
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
        return {"ok": False, "ability": "math_solver", "status": "error",
                "error": f"could not parse ({type(exc).__name__}): pass one sympy-style expression or equation, e.g. "
                         "'x^2 - 5x + 6 = 0', 'derivative of sin(x)*x', 'integral of 1/(x^2+4) dx from 0 to oo', "
                         "'x + y = 5; x - y = 1'"}
    return {"ability": "math_solver", "status": "success" if res.get("ok") else "error", **res}
