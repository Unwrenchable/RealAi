"""Natural Mode — plain-English Console chat grounded in tools.

Console posts to ``POST /v1/chat/completions``. Vulkan never executes tools
(the orchestrator strips the catalog before proxy), so a Craft-style inspect
pass must run *before* the model call when the user asks about files, code,
or the repo in plain English (not an explicit slash command).

Keep this module free of top-level Craft / meta_router imports so both can
call the detector without cycles.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Short lock for small local models (they ignore long system essays).
NATURAL_GROUNDING_RULE = (
    "GROUNDING LOCK: Never invent file contents, paths, or API results. "
    "Only quote tool results you were given. If tools fail or return empty, say so."
)

# Path-ish tokens: relative files with a real extension.
_PATH_RE = re.compile(
    r"(?i)(?:^|[\s`'\"(\[])("
    r"(?:[\w.-]+[\\/])+[\w.-]+\.[\w]+"
    r"|[\w.-]+\.(?:py|ts|tsx|js|jsx|mjs|cjs|html|css|md|json|yml|yaml|toml|"
    r"go|rs|java|kt|swift|sql|sh|bat|ps1|txt)"
    r")"
)

# Plain-English inspect / fix / find / read — not slash, not smalltalk.
_REPO_ASK_RE = re.compile(
    r"(?i)("
    r"what'?s?\s+in\b|"
    r"contents?\s+of\b|"
    r"\bread\b|"
    r"\bopen\s+(the\s+)?file\b|"
    r"\blook\s+(at|in|through)\b|"
    r"\bshow\s+(me\s+)?(the\s+)?(file|code|repo|workspace|directory)\b|"
    r"\blist\s+(the\s+)?(repo|workspace|files|directory|dir)\b|"
    r"\b(fix|find|grep|patch|refactor|implement|audit|inspect)\b|"
    r"\b(bug|broken)\b|"
    r"\bthis\s+(file|repo|workspace|code)\b|"
    r"\bwhere\s+(is|are)\b"
    r")"
)

_EXPLICIT_CMD_RE = re.compile(r"^\s*[/$@]")


def is_explicit_command(text: str) -> bool:
    """True for slash / $ / @ operator messages — leave those to easy_tools / live_exec."""
    return bool(_EXPLICIT_CMD_RE.match(text or ""))


def extract_path_tokens(text: str) -> List[str]:
    """Relative file paths mentioned in free text (console.html, apps/foo.py)."""
    seen: set[str] = set()
    out: List[str] = []
    for m in _PATH_RE.finditer(text or ""):
        raw = (m.group(1) or "").strip().strip("`'\"").replace("\\", "/")
        if not raw or raw.lower() in seen:
            continue
        seen.add(raw.lower())
        out.append(raw)
    return out


def looks_like_repo_ask(text: str) -> bool:
    """True when a plain-English message is about files / code / the repo."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    if extract_path_tokens(raw):
        return True
    return bool(_REPO_ASK_RE.search(raw))


def workspace_route_mode() -> str:
    """Craft workspace mode: ``product`` vs ``project`` (foreign)."""
    try:
        from realai.cli.craft import fingerprint_stack

        fp = fingerprint_stack() or {}
        mode = str(fp.get("mode") or "").strip().lower()
        if mode in {"project", "foreign"}:
            return "project"
        return "product"
    except Exception:
        return "product"


def plan_natural_inspect(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Craft ``plan_tools`` plus explicit path reads; inspect even in the product tree."""
    from realai.cli.craft import auto_inspect_plans, dedupe_plans, plan_tools

    t = (user_text or "").strip()
    plans: List[Tuple[str, Dict[str, Any]]] = list(plan_tools(t) or [])
    for rel in extract_path_tokens(t):
        plans.append(("read", {"path": rel}))
    names = {n for n, _ in plans}
    if looks_like_repo_ask(t) and not names.intersection({"pwd", "list", "grep", "read"}):
        plans.extend(auto_inspect_plans(t))
    return dedupe_plans(plans)


def run_natural_inspect(user_text: str) -> List[Dict[str, Any]]:
    """Execute the inspect plan. Never invent results — errors stay as errors."""
    from realai.cli.craft import apply_workspace, run_tools

    apply_workspace()
    plans = plan_natural_inspect(user_text)
    if not plans:
        return []
    return run_tools(plans)


def _tool_failed(tr: Dict[str, Any]) -> bool:
    if tr.get("error"):
        return True
    result = tr.get("result")
    if isinstance(result, dict) and result.get("ok") is False:
        return True
    return False


def tools_all_failed(results: List[Dict[str, Any]]) -> bool:
    if not results:
        return True
    return all(_tool_failed(tr) for tr in results)


def format_grounding_block(user_text: str, results: List[Dict[str, Any]]) -> str:
    """Append-only grounding for the last user message."""
    from realai.cli.craft import _format_tools

    tools_txt = _format_tools(results) if results else "(no tool results)"
    failed = tools_all_failed(results)
    follow = (
        "Tools failed or returned nothing. Say so. Do not invent file contents, paths, or API results."
        if failed
        else (
            "Use ONLY the tool results above. Cite real paths you read. "
            "If a tool errored, admit it. Never invent file contents, paths, or API results."
        )
    )
    return f"{user_text}\n\n{tools_txt}\n\n{follow}"


def failure_reply(results: List[Dict[str, Any]]) -> str:
    bits: List[str] = []
    for tr in results or []:
        name = tr.get("tool") or "tool"
        if tr.get("error"):
            bits.append(f"{name}: {tr.get('error')}")
            continue
        result = tr.get("result") if isinstance(tr.get("result"), dict) else {}
        err = (result or {}).get("error") or (result or {}).get("message")
        if err:
            bits.append(f"{name}: {err}")
        elif _tool_failed(tr):
            bits.append(f"{name}: failed")
    detail = "; ".join(bits) if bits else "no inspect tools ran"
    return (
        "I tried to inspect the repo and the tools failed "
        f"({detail}). I won't invent file contents or paths."
    )


def apply_natural_grounding(body: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """Mutate chat ``body`` for a plain-English repo/code ask.

    Returns meta for ``realai_meta``. Caller should short-circuit when
    ``admit_failure`` is True instead of proxying to Vulkan.
    """
    meta: Dict[str, Any] = {
        "should_ground": False,
        "admit_failure": False,
        "tools": [],
        "mode": workspace_route_mode(),
    }
    text = (user_text or "").strip()
    if not text or is_explicit_command(text) or not looks_like_repo_ask(text):
        return meta

    meta["should_ground"] = True
    try:
        results = run_natural_inspect(text)
    except Exception as exc:
        meta["admit_failure"] = True
        meta["error"] = str(exc)
        meta["failure_text"] = (
            f"I tried to inspect the repo and the tools failed ({exc}). "
            "I won't invent file contents or paths."
        )
        return meta

    names = [str(tr.get("tool") or "?") for tr in results]
    meta["tools"] = names
    meta["tool_count"] = len(results)
    meta["admit_failure"] = tools_all_failed(results)
    if meta["admit_failure"]:
        meta["failure_text"] = failure_reply(results)
        return meta

    msgs = list(body.get("messages") or [])
    grounded = format_grounding_block(text, results)
    spliced = False
    for i in range(len(msgs) - 1, -1, -1):
        msg = msgs[i]
        if isinstance(msg, dict) and str(msg.get("role") or "").lower() == "user":
            updated = dict(msg)
            updated["content"] = grounded
            msgs[i] = updated
            spliced = True
            break
    if not spliced:
        msgs.append({"role": "user", "content": grounded})
    body["messages"] = msgs
    body["realai_natural_grounded"] = True
    return meta
