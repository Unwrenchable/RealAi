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
    "GROUNDING LOCK: Never invent file contents, paths, API results, "
    "ability output, or agent results. Only quote tool results you were given. "
    "If tools fail or return empty, say so."
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

# Learn from a local folder or git URL without typing /learn.
_LEARN_ASK_RE = re.compile(
    r"(?i)("
    r"\b(git[- ]?learn|learn[- ]git)\b|"
    r"\blearn(?:ing)?\s+(from|this|the)\b|"
    r"\bingest\s+(this\s+)?(repo|folder|tree|git)\b|"
    r"\bscan\s+(this\s+)?(git|repo)\s+(for\s+learn|and\s+learn)"
    r")"
)

_LEARN_SOURCE_URL_RE = re.compile(r"(https?://[^\s]+|git@[\w.-]+:[^\s]+)", re.I)
_LEARN_OWNER_REPO_RE = re.compile(r"\b([\w.-]+/[\w.-]+)(?:\.git)?\b")
_LEARN_WIN_PATH_RE = re.compile(r"(?i)\b([a-z]:[\\/][^\s\"']+)")
_LEARN_POSIX_PATH_RE = re.compile(r"(?<![\w])((?:\.{1,2})?/[^\s\"']+|~/[^\s\"']+|\./[^\s\"']+)")

# Hive agents / multi — not a simple file read.
_AGENT_ASK_RE = re.compile(
    r"(?i)("
    r"\baudit\b|"
    r"\bhive\s+(next|health|status|brief)\b|"
    r"\bnext actions\b|"
    r"\bmulti[- ]agent\b|"
    r"\brun (the )?agents\b|"
    r"\boverseer\b"
    r")"
)

_BROKEN_ASK_RE = re.compile(
    r"(?i)("
    r"what'?s\s+broken|"
    r"\bbroken\b|"
    r"\bdoctor\b|"
    r"\bself[- ]?heal status\b|"
    r"\bhive health\b"
    r")"
)

_SIMPLE_FILE_RE = re.compile(
    r"(?i)^\s*(read|open|show|what's in|whats in)\s+[\w./\\-]+\s*$"
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


def looks_like_learn_ask(text: str) -> bool:
    """True for plain-English git-learn (local folder or git URL)."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    return bool(_LEARN_ASK_RE.search(raw))


def looks_like_agent_ask(text: str) -> bool:
    """True when hive agents / audit should run (not a one-file read)."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    if _SIMPLE_FILE_RE.match(raw):
        return False
    return bool(_AGENT_ASK_RE.search(raw))


def looks_like_broken_ask(text: str) -> bool:
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    return bool(_BROKEN_ASK_RE.search(raw))


def extract_learn_source(text: str) -> str:
    """Best-effort local folder / git URL from a learn ask. Default: workspace."""
    raw = (text or "").strip()
    if not raw:
        return "."
    for m in re.finditer(r"\"([^\"]+)\"|'([^']+)'", raw):
        val = (m.group(1) or m.group(2) or "").strip()
        if val:
            return val
    url = _LEARN_SOURCE_URL_RE.search(raw)
    if url:
        return url.group(1).rstrip(".,;)]")
    win = _LEARN_WIN_PATH_RE.search(raw)
    if win:
        return win.group(1).rstrip(".,;)]")
    posix = _LEARN_POSIX_PATH_RE.search(raw)
    if posix:
        return posix.group(1).rstrip(".,;)]")
    owner = _LEARN_OWNER_REPO_RE.search(raw)
    if owner and "/" in owner.group(1) and not owner.group(1).lower().startswith("this/"):
        cand = owner.group(1)
        if cand.lower() not in {"learn/from", "from/this"}:
            return cand
    low = raw.lower()
    if re.search(r"\b(this|the)\s+(repo|folder|tree|workspace|project)\b", low):
        return "."
    return "."


def match_ability_ids(text: str) -> List[str]:
    """Catalog abilities the ask clearly needs. Never invents results."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return []
    low = raw.lower()
    hits: List[str] = []
    seen: set[str] = set()

    def _add(aid: str) -> None:
        a = (aid or "").strip()
        if not a or a in seen or a in {"learn_git", "git_learn"}:
            return
        seen.add(a)
        hits.append(a)

    for rx, aid in (
        (re.compile(r"(?i)\b(rackup\s+)?coach\b|\bpyramid coach\b|\bpractice plan\b"), "coach"),
        (re.compile(r"(?i)\bshot of the day\b|\bsotd\b"), "shot_of_the_day"),
        (
            re.compile(
                r"(?i)\b(text[- ]to[- ]speech|\btts\b|speak (this|aloud)|say this( out loud)?|"
                r"audio[- ]speech|speech abilit)"
            ),
            "audio_speech",
        ),
        (re.compile(r"(?i)\bvoice[- ]stream|\bkokoro\b"), "voice_streaming"),
        (re.compile(r"(?i)\bwrist\s+(ui|hint|coach)\b|\batomicfizz\b"), "atomicfizz_coach"),
    ):
        if rx.search(raw):
            _add(aid)

    try:
        from realai.ability_catalog import build_catalog

        cat = build_catalog() or {}
        for row in cat.get("abilities") or []:
            if not isinstance(row, dict):
                continue
            aid = str(row.get("id") or "").strip()
            if not aid:
                continue
            needle = aid.replace("_", " ").replace("-", " ")
            if len(needle) >= 5 and needle in low:
                _add(aid)
                continue
            for kw in row.get("keywords") or []:
                k = str(kw or "").strip().lower()
                if len(k) >= 6 and " " in k and k in low:
                    _add(aid)
                    break
    except Exception:
        pass
    return hits[:3]


def plan_natural_auto(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Abilities / learn / hive agents / doctor — beyond file inspect."""
    t = (user_text or "").strip()
    if not t or is_explicit_command(t):
        return []
    plans: List[Tuple[str, Dict[str, Any]]] = []
    if looks_like_learn_ask(t):
        plans.append(("learn", {"source": extract_learn_source(t), "write": False}))
    for aid in match_ability_ids(t):
        plans.append(("ability", {"id": aid, "input": t}))
    if looks_like_broken_ask(t):
        plans.append(("doctor", {}))
    if looks_like_agent_ask(t):
        target = "coder"
        try:
            from realai.meta_router import route_task

            d = route_task(t, mode=workspace_route_mode())
            tgt = str(getattr(d, "target", "") or "")
            if tgt and tgt not in {"raw-model"}:
                target = tgt
        except Exception:
            pass
        plans.append(
            (
                "agents",
                {
                    "agent_id": target,
                    "task": t,
                    "multi": bool(re.search(r"(?i)\b(audit|multi[- ]agent|next actions|hive next)\b", t)),
                },
            )
        )
    return plans[:6]


def should_natural_act(text: str) -> bool:
    """True when plain chat should auto-run inspect / abilities / learn / agents."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    if looks_like_repo_ask(raw) or looks_like_learn_ask(raw):
        return True
    if looks_like_broken_ask(raw) or looks_like_agent_ask(raw):
        return True
    return bool(match_ability_ids(raw))


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


def run_natural_auto(
    plans: List[Tuple[str, Dict[str, Any]]],
    user_text: str,
) -> List[Dict[str, Any]]:
    """Execute ability / learn / agent / doctor plans. Never invent results."""
    out: List[Dict[str, Any]] = []
    for kind, args in plans or []:
        name = str(kind)
        try:
            if kind == "learn":
                from realai.cli.craft import tool_learn
                from realai.learn_git import compact_learn_result

                result = compact_learn_result(
                    tool_learn(
                        str(args.get("source") or "."),
                        write=bool(args.get("write")),
                        refresh=bool(args.get("refresh")),
                    )
                )
                out.append({"tool": "learn", "result": result})
            elif kind == "ability":
                from realai.v3_runtime_bridge import execute_registry_tool

                aid = str(args.get("id") or "").strip()
                name = aid if aid.startswith("ability.") else f"ability.{aid}"
                result = execute_registry_tool(
                    name,
                    {
                        "input": str(args.get("input") or user_text or ""),
                        "action": "run",
                        "task": str(args.get("input") or user_text or ""),
                    },
                )
                out.append({"tool": name, "result": result})
            elif kind == "agents":
                from realai.agent_activity import run_agent_task

                result = run_agent_task(
                    str(args.get("agent_id") or "coder"),
                    str(args.get("task") or user_text or ""),
                    use_multi=bool(args.get("multi")),
                )
                out.append({"tool": "agents_run", "result": result})
            elif kind == "doctor":
                from realai.cli.craft import tool_doctor

                out.append({"tool": "doctor", "result": tool_doctor()})
            else:
                out.append({"tool": name, "error": f"unknown_natural_kind:{kind}"})
        except Exception as exc:
            out.append({"tool": name, "error": str(exc)})
    return out


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
        "Tools failed or returned nothing. Say so. Do not invent file contents, "
        "paths, ability output, agent results, or API results."
        if failed
        else (
            "Use ONLY the tool results above. Cite real paths you read. "
            "If a tool errored, admit it. Never invent file contents, paths, "
            "ability output, agent results, or API results."
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
        "I tried the tools that matched this ask and they failed "
        f"({detail}). I won't invent file contents, ability output, or agent results."
    )


def apply_natural_grounding(body: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """Mutate chat ``body`` for a plain-English repo/code/ability/agent ask.

    Runs Craft inspect plus auto-planned abilities / learn / hive agents.
    Never invents tool output. Returns meta for ``realai_meta``. Caller
    should short-circuit when ``admit_failure`` is True instead of proxying
    to Vulkan.
    """
    meta: Dict[str, Any] = {
        "should_ground": False,
        "admit_failure": False,
        "tools": [],
        "used_tools": [],
        "mode": workspace_route_mode(),
    }
    text = (user_text or "").strip()
    extras = plan_natural_auto(text) if text and not is_explicit_command(text) else []
    inspect_needed = looks_like_repo_ask(text) and not any(k == "learn" for k, _ in extras)
    if not text or is_explicit_command(text) or not (inspect_needed or extras):
        return meta

    meta["should_ground"] = True
    results: List[Dict[str, Any]] = []
    try:
        if inspect_needed:
            results.extend(run_natural_inspect(text))
        if extras:
            results.extend(run_natural_auto(extras, text))
    except Exception as exc:
        meta["admit_failure"] = True
        meta["error"] = str(exc)
        meta["failure_text"] = (
            f"I tried to run tools and they failed ({exc}). "
            "I won't invent file contents, ability output, or agent results."
        )
        return meta

    names = [str(tr.get("tool") or "?") for tr in results]
    meta["tools"] = names
    meta["used_tools"] = names
    meta["tool_count"] = len(results)
    meta["auto"] = [k for k, _ in extras]
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
