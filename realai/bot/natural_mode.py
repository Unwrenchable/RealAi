"""Natural Mode — plain-English Console chat grounded in tools.

Console posts to ``POST /v1/chat/completions``. Vulkan never executes tools
(the orchestrator strips the catalog before proxy), so a Craft-style inspect
pass must run *before* the model call when the user asks about files, code,
or the repo in plain English (not an explicit slash command).

Write path: when path + content are concrete (create/update), this module
plans Craft ``write`` and the orchestrator executes it — same TOOLS as
``/write`` / ``/craft write``. Inspect-only asks never write. Ambiguous
create/fix returns a clear need-path/content failure instead of a fake ok.
Scattered ability nests are not the runtime; live wiring is
``v3_orchestrator`` + ``cli/craft`` + this module.

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

# Plain-English create/update — not inspect, not slash /write.
_WRITE_ASK_RE = re.compile(
    r"(?i)("
    r"\b(create|make|add)\b.{0,80}\bfiles?\b|"
    r"\b(create|make|write|save)\s+[^\s]+\.\w+|"
    r"\b(write|save|put)\b.{0,80}\b(to|into|in)\b|"
    r"\bupdate\s+(the\s+)?file\b|"
    r"\boverwrite\s+(the\s+)?file\b"
    r")"
)

# Fix/implement after inspect → model may emit /write path|||content (Craft Phase 2).
_PATCH_ASK_RE = re.compile(
    r"(?i)\b(fix|patch|implement|refactor|apply (the )?(patch|fix|change)s?)\b"
)

_CONTENT_MARKER_RE = re.compile(
    r"(?is)\b(?:with\s+content|containing|that\s+says|with\s+the\s+text|"
    r"contents?\s*[:=]|with\s+body)\s*(.*)$"
)

_WRITE_TO_RE = re.compile(
    r"(?is)\b(?:write|save|put|drop)\s+(.+?)\s+(?:to|into|in)\s+(\S+)"
)

_CONTENT_STOPWORDS = {
    "a file",
    "the file",
    "this file",
    "new file",
    "a new file",
    "the new file",
    "file",
    "path",
}


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


def looks_like_write_ask(text: str) -> bool:
    """True when plain English asks to create/update a file (not slash /write)."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    return bool(_WRITE_ASK_RE.search(raw))


def looks_like_patch_ask(text: str) -> bool:
    """True for fix/implement/patch — inspect first, then apply model /write blocks."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    if looks_like_write_ask(raw):
        return False
    return bool(_PATCH_ASK_RE.search(raw))


def _strip_content_quotes(raw: str) -> str:
    s = (raw or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'`":
        return s[1:-1]
    return s


def _content_usable(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    s = _strip_content_quotes(str(raw)).strip()
    if not s:
        return None
    if s.lower().strip(".,;:") in _CONTENT_STOPWORDS:
        return None
    # Don't treat a lone path as file contents.
    if extract_path_tokens(s) == [s.replace("\\", "/").strip("`'\"")]:
        return None
    return s


def extract_write_spec(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort (path, content) from a create/update ask. Never invents either."""
    raw = (text or "").strip()
    if not raw:
        return (None, None)

    paths = extract_path_tokens(raw)
    path = paths[0] if paths else None

    content: Optional[str] = None

    if "|||" in raw:
        left, right = raw.split("|||", 1)
        if not path:
            bits = left.split()
            cand = bits[-1].strip().replace("\\", "/") if bits else ""
            if cand:
                path = cand
        content = _content_usable(right)

    if content is None:
        fence = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\s*\n([\s\S]*?)```", raw)
        if fence:
            content = _content_usable(fence.group(1).strip("\n"))

    if content is None:
        marked = _CONTENT_MARKER_RE.search(raw)
        if marked:
            blob = marked.group(1) or ""
            # Drop a trailing path if the marker captured "PROBE_OK in foo.txt"
            blob = re.split(r"(?i)\s+(?:in|into|to)\s+\S+\s*$", blob, maxsplit=1)[0]
            content = _content_usable(blob)

    if content is None:
        wt = _WRITE_TO_RE.search(raw)
        if wt:
            maybe_content = _content_usable(wt.group(1))
            maybe_path = (wt.group(2) or "").strip().strip("`'\"").replace("\\", "/")
            if maybe_path and not path:
                toks = extract_path_tokens(maybe_path)
                path = toks[0] if toks else maybe_path
            if maybe_content:
                content = maybe_content

    if content is None:
        for m in re.finditer(r"\"([^\"]+)\"|'([^']+)'", raw):
            val = (m.group(1) or m.group(2) or "").strip()
            if not val:
                continue
            norm = val.replace("\\", "/")
            if path and norm == path:
                continue
            if extract_path_tokens(val) == [norm] and path is None:
                path = norm
                continue
            content = _content_usable(val)
            if content:
                break

    return (path, content)


def need_write_args_reply(path: Optional[str], content: Optional[str]) -> str:
    missing = []
    if not (path or "").strip():
        missing.append("a workspace-relative path")
    if content is None or not str(content).strip():
        missing.append("the file contents")
    need = " and ".join(missing) if missing else "path and contents"
    return (
        f"I won't invent a file write. Need {need}. "
        "Example: create file docs/note.txt with content hello — "
        "or /write docs/note.txt hello"
    )


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
    if looks_like_write_ask(raw) or looks_like_patch_ask(raw):
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


def plan_natural_write(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Craft write when path+content are concrete. Empty if inspect-only or ambiguous."""
    t = (user_text or "").strip()
    if not t or is_explicit_command(t) or not looks_like_write_ask(t):
        return []
    path, content = extract_write_spec(t)
    if not path or content is None or not str(content).strip():
        return []
    return [("write", {"path": path, "content": content, "mode": "overwrite"})]


def run_natural_write(path: str, content: str, mode: str = "overwrite") -> Dict[str, Any]:
    """Execute Craft tool_write. Workspace bounds via safe_under_write."""
    from realai.cli.craft import apply_workspace, tool_write

    apply_workspace()
    return tool_write(str(path or ""), content=str(content or ""), mode=str(mode or "overwrite"))


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


def format_grounding_block(
    user_text: str,
    results: List[Dict[str, Any]],
    want_writes: bool = False,
) -> str:
    """Append-only grounding for the last user message."""
    from realai.cli.craft import _format_tools

    tools_txt = _format_tools(results) if results else "(no tool results)"
    failed = tools_all_failed(results)
    if failed:
        follow = (
            "Tools failed or returned nothing. Say so. Do not invent file contents, "
            "paths, ability output, agent results, or API results."
        )
    elif want_writes:
        follow = (
            "Use ONLY the tool results above. Cite real paths you read. "
            "If a tool errored, admit it. Never invent file contents. "
            "When sure, emit one or more apply blocks exactly as:\n"
            "/write relative/path|||<full file contents>\n"
            "Put only file contents after ||| (Craft will apply /write)."
        )
    else:
        follow = (
            "Use ONLY the tool results above. Cite real paths you read. "
            "If a tool errored, admit it. Never invent file contents, paths, "
            "ability output, agent results, or API results."
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
    When create/update has a concrete path+content, executes Craft write
    (same ``tool_write`` as ``/write``). Never invents tool output. Returns
    meta for ``realai_meta``. Caller should short-circuit when
    ``admit_failure`` or ``short_circuit`` is True instead of proxying to Vulkan.
    """
    meta: Dict[str, Any] = {
        "should_ground": False,
        "admit_failure": False,
        "short_circuit": False,
        "wrote": False,
        "apply_model_writes": False,
        "tools": [],
        "used_tools": [],
        "mode": workspace_route_mode(),
    }
    text = (user_text or "").strip()
    if not text or is_explicit_command(text):
        return meta

    write_ask = looks_like_write_ask(text)
    patch_ask = looks_like_patch_ask(text)
    write_plans = plan_natural_write(text) if write_ask else []

    if write_ask and write_plans:
        meta["should_ground"] = True
        args = write_plans[0][1]
        path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        try:
            result = run_natural_write(path, content, mode=str(args.get("mode") or "overwrite"))
        except Exception as exc:
            meta["admit_failure"] = True
            meta["error"] = str(exc)
            meta["used_tools"] = ["write"]
            meta["tools"] = ["write"]
            meta["failure_text"] = (
                f"I tried to write {path} and it failed ({exc}). "
                "I won't invent a successful write."
            )
            return meta
        failed = isinstance(result, dict) and (
            result.get("ok") is False or bool(result.get("error"))
        )
        meta["tools"] = ["write"]
        meta["used_tools"] = ["write"]
        meta["tool_count"] = 1
        meta["write_result"] = result
        if failed:
            meta["admit_failure"] = True
            err = (result or {}).get("error") or "write_failed"
            meta["failure_text"] = (
                f"Write failed ({err}). I won't invent a successful write. "
                "Paths must stay under the workspace."
            )
            return meta
        meta["wrote"] = True
        meta["short_circuit"] = True
        try:
            from realai.bot.easy_tools import format_easy_result

            meta["reply"] = format_easy_result("write", result)
        except Exception:
            meta["reply"] = (
                f"[RealAI write]\nok=true  path={result.get('path')}  "
                f"bytes={result.get('bytes')}"
            )
        return meta

    if write_ask and not write_plans:
        spec_path, spec_content = extract_write_spec(text)
        meta["should_ground"] = True
        results: List[Dict[str, Any]] = []
        if spec_path:
            try:
                results.extend(run_natural_inspect(text))
            except Exception:
                results = []
        meta["tools"] = [str(tr.get("tool") or "?") for tr in results]
        meta["used_tools"] = meta["tools"]
        meta["admit_failure"] = True
        extra = f" I looked at `{spec_path}` but still need the contents." if spec_path else ""
        meta["failure_text"] = need_write_args_reply(spec_path, spec_content) + extra
        return meta

    extras = plan_natural_auto(text)
    inspect_needed = looks_like_repo_ask(text) and not any(k == "learn" for k, _ in extras)
    if not (inspect_needed or extras):
        return meta

    meta["should_ground"] = True
    meta["apply_model_writes"] = bool(patch_ask)
    results = []
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
    grounded = format_grounding_block(text, results, want_writes=bool(patch_ask))
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
