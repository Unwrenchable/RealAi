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

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Short lock for small local models (they ignore long system essays).
NATURAL_GROUNDING_RULE = (
    "GROUNDING LOCK: Never invent file contents, paths, API results, "
    "ability output, or agent results. Only quote tool results you were given. "
    "If tools fail or return empty, say so."
)

# One operator turn: inspect/auto tools hard-capped (no pwd+git+grep storms).
MAX_TOOLS_THIS_TURN = 3

# Chat HTTP abort (Console hivePost). Do not loosen.
CHAT_ABORT_SECONDS = 180

# Always-on reply contract. Also documented in docs/CONSOLE_OPERATOR_DIRECTIVE.md.
NATURAL_REPLY_CONTRACT = (
    "REPLY CONTRACT when tools finish, four short lines:\n"
    "Summary: one sentence.\n"
    "What changed: paths or none.\n"
    "Verify: pass or fail. Never claim success if hive smoke failed.\n"
    "Next: one step.\n"
    "CAPS: MAX_TOOLS_THIS_TURN=3. Chat abort 180s. Do not loosen.\n"
    "Never say LANDED unless a write tool succeeded. Propose is not a write. "
    "Named paths need workspace_read."
)

_REPLY_HEADINGS = ("Summary:", "What changed:", "Verify:", "Next:")

_SIMPLE_PATH_ASK_RE = re.compile(
    r"(?i)\b(quote|read|open|show|what.?s\s+in|whats\s+in|marker|contents?\s+of)\b"
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
    if path:
        try:
            from realai.cli.craft import is_protected_core_path

            if is_protected_core_path(path):
                return []  # orchestrator should surface need_write / protected via apply path
        except Exception:
            # Fail closed for obvious core paths even if import fails.
            rel = path.replace("\\", "/").lower()
            if rel.startswith("realai/bot/") or rel.startswith("realai/orchestration/"):
                return []

    if not path or content is None or not str(content).strip():
        return []
    return [("write", {"path": path, "content": content, "mode": "overwrite"})]


def run_natural_write(path: str, content: str, mode: str = "overwrite") -> Dict[str, Any]:
    """Execute Craft tool_write. Workspace bounds via safe_under_write."""
    from realai.cli.craft import apply_workspace, tool_write

    apply_workspace()
    return tool_write(str(path or ""), content=str(content or ""), mode=str(mode or "overwrite"))


def verify_natural_write(path: str, *, limit: int = 12) -> Dict[str, Any]:
    """Re-read a path after write. Never invent contents — errors stay as errors."""
    from realai.cli.craft import apply_workspace, tool_read

    apply_workspace()
    try:
        return tool_read(str(path or ""), start=1, limit=int(limit))
    except Exception as exc:
        return {"error": str(exc), "path": path}


def _one_line(text: Any, limit: int = 220) -> str:
    raw = " ".join(str(text or "").split())
    if not raw:
        return "none"
    if len(raw) > limit:
        return raw[: limit - 1].rstrip() + "..."
    return raw


def format_operator_reply(*, summary: str, changed: str, verify: str, nxt: str) -> str:
    """Natural Mode reply contract: Summary / What changed / Verify / Next."""
    return (
        f"Summary: {_one_line(summary)}\n"
        f"What changed: {_one_line(changed)}\n"
        f"Verify: {_one_line(verify)}\n"
        f"Next: {_one_line(nxt)}"
    )


def reply_has_contract(text: str) -> bool:
    low = (text or "").lower()
    return all(h.lower() in low for h in _REPLY_HEADINGS)


def scrub_unearned_landed(text: str, *, write_ok: bool) -> str:
    """LANDED is allowed only after a write tool succeeded and smoke did not fail."""
    if write_ok:
        return text or ""
    return re.sub(r"\bLANDED\b", "PROPOSED", text or "", flags=re.I)


def post_write_smoke(*, timeout: float = 2.5) -> Dict[str, Any]:
    """One hive health GET after a successful write.

    This is a post-step, not a registry tool, so it does not spend
    ``MAX_TOOLS_THIS_TURN`` and does not start a tool storm. A down hive
    is a failed verify. Calls are guarded: no orch is required to import.
    """
    import json
    import urllib.request

    base = (
        os.environ.get("REALAI_API_BASE")
        or os.environ.get("REALAI_PROVIDER_URL")
        or "http://127.0.0.1:8001"
    ).rstrip("/")
    url = base + "/health"
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "RealAI-natural-smoke/1.0"},
        )
        with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            raw = resp.read(1200).decode("utf-8", "replace")
        http_ok = 200 <= status < 300
        body_ok = True
        try:
            payload = json.loads(raw) if raw else {}
            flag = str((payload or {}).get("status") or "").lower()
            if flag and flag not in {"ok", "degraded", "healthy", "up"}:
                body_ok = False
        except Exception:
            pass
        return {
            "ok": bool(http_ok and body_ok),
            "status": status,
            "url": url,
            "post_step": True,
            "snippet": raw[:240],
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": str(exc),
            "post_step": True,
            "guarded": True,
        }


def format_write_verified_reply(
    write_result: Dict[str, Any],
    verify: Dict[str, Any],
    smoke: Optional[Dict[str, Any]] = None,
) -> str:
    """Write reply in the operator contract. Smoke failure is not success."""
    path = (write_result or {}).get("path") or (verify or {}).get("path") or "?"
    nbytes = (write_result or {}).get("bytes")
    disk_ok = isinstance(verify, dict) and not verify.get("error")
    smoke_d = smoke if isinstance(smoke, dict) else {"ok": False, "error": "not_run"}
    smoke_ok = bool(smoke_d.get("ok"))
    if not disk_ok:
        err = (verify or {}).get("error") if isinstance(verify, dict) else "verify_unavailable"
        verify_line = f"FAIL re-read ({err})"
        summary = f"Write of {path} did not verify on disk."
        changed = "none"
    elif not smoke_ok:
        detail = smoke_d.get("error") or smoke_d.get("status") or "unhealthy"
        verify_line = f"FAIL hive smoke ({detail}) at {smoke_d.get('url') or 'hive'}. Do not treat this as done."
        summary = f"Wrote {path} on disk ({nbytes} bytes), but hive smoke failed."
        changed = str(path)
    else:
        total = (verify or {}).get("total_lines")
        verify_line = (
            f"PASS on-disk lines={total}; hive health {smoke_d.get('status')} {smoke_d.get('url')}"
        )
        summary = f"Wrote {path} ({nbytes} bytes) and hive smoke passed."
        changed = str(path)
    nxt = (
        "Ask for the next edit."
        if disk_ok and smoke_ok
        else "Fix the failed check before treating this change as done."
    )
    text = scrub_unearned_landed(
        format_operator_reply(
            summary=summary, changed=changed, verify=verify_line, nxt=nxt
        ),
        write_ok=bool(disk_ok and smoke_ok),
    )
    if disk_ok:
        content = str((verify or {}).get("content") or "")
        preview = "\n".join(content.splitlines()[:8])
        # Preview is on-disk bytes. Do not rewrite words inside the file.
        text += f"\n--- on disk (first lines) ---\n{preview}"
    return text


def _operator_failure(summary: str, *, verify: str = "FAIL", nxt: str = "Narrow the ask and retry.") -> str:
    return scrub_unearned_landed(
        format_operator_reply(summary=summary, changed="none", verify=verify, nxt=nxt),
        write_ok=False,
    )


def finalize_natural_choice_text(
    text: str,
    natural: Optional[Dict[str, Any]] = None,
    *,
    applied: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Shape a model reply after Natural Mode tools. Smoke only if a write landed.

    Returns ``(reply, smoke_or_none)``. Smoke is one health GET, not another tool.
    """
    nat = natural if isinstance(natural, dict) else {}
    applied_rows = list(applied or [])
    write_ok = False
    changed_bits: List[str] = []
    for row in applied_rows:
        result = row.get("result") if isinstance(row, dict) else None
        if isinstance(result, dict) and result.get("ok") and not result.get("error"):
            write_ok = True
            path = result.get("path") or row.get("path")
            if path:
                changed_bits.append(str(path))
    smoke: Optional[Dict[str, Any]] = None
    if write_ok and not isinstance(nat.get("post_write_smoke"), dict):
        smoke = post_write_smoke()
    elif isinstance(nat.get("post_write_smoke"), dict):
        smoke = nat.get("post_write_smoke")
    smoke_ok = True if smoke is None else bool(smoke.get("ok"))
    if smoke is not None and not smoke_ok:
        if smoke.get("error") or smoke.get("status"):
            verify = (
                f"FAIL hive smoke ({smoke.get('error') or smoke.get('status')}). "
                "Do not treat this as done."
            )
        else:
            verify = "FAIL hive smoke. Do not treat this as done."
    elif smoke is not None and smoke_ok:
        verify = f"PASS hive health {smoke.get('status')} {smoke.get('url')}"
    else:
        verify = "no write this turn; hive smoke not run"
    tools = nat.get("used_tools") or nat.get("tools") or []
    changed = ", ".join(changed_bits) if changed_bits else (
        ", ".join(str(t) for t in tools) if tools else "none"
    )
    earned = bool(write_ok and smoke_ok)
    body = scrub_unearned_landed(text or "", write_ok=earned)
    if reply_has_contract(body):
        if smoke is not None and not smoke_ok and "fail" not in body.lower():
            body = body.rstrip() + "\nVerify: " + verify
        return body, smoke
    first = body.split("\n", 1)[0] if body else ""
    summary = _one_line(first, 220) if first else "Tools finished."
    shaped = format_operator_reply(
        summary=summary,
        changed=changed,
        verify=verify,
        nxt="Continue from Verify.",
    )
    if body and body not in shaped:
        shaped += "\n\n" + body
    return scrub_unearned_landed(shaped, write_ok=earned), smoke


def plan_natural_inspect(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Craft ``plan_tools`` plus explicit path reads; inspect even in the product tree.

    Cap: at most ``MAX_TOOLS_THIS_TURN`` tools. Named-file quote/read asks
    prefer ``read`` only — never pwd+list+grep storms on one path ask.
    """
    from realai.cli.craft import auto_inspect_plans, dedupe_plans, plan_tools

    t = (user_text or "").strip()
    paths = extract_path_tokens(t)
    # Fast path: "quote/read … path.md" → read those files only
    if paths and _SIMPLE_PATH_ASK_RE.search(t):
        plans = [("read", {"path": rel}) for rel in paths[:MAX_TOOLS_THIS_TURN]]
        return dedupe_plans(plans)[:MAX_TOOLS_THIS_TURN]

    plans: List[Tuple[str, Dict[str, Any]]] = list(plan_tools(t) or [])
    for rel in paths:
        plans.append(("read", {"path": rel}))
    names = {n for n, _ in plans}
    if looks_like_repo_ask(t) and not names.intersection({"pwd", "list", "grep", "read"}):
        plans.extend(auto_inspect_plans(t))
    # Prefer named reads first when capping a mixed plan
    if paths:
        preferred = [("read", {"path": rel}) for rel in paths]
        rest = [p for p in plans if p not in preferred and not (
            p[0] == "read" and (p[1] or {}).get("path") in paths
        )]
        plans = preferred + rest
    return dedupe_plans(plans)[:MAX_TOOLS_THIS_TURN]


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
    for kind, args in (plans or [])[:MAX_TOOLS_THIS_TURN]:
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
    follow += (
        "\n\nReply shape after these tools: Summary / What changed / Verify / Next. "
        "Short sentences. Never say LANDED unless a write tool succeeded. "
        f"MAX_TOOLS_THIS_TURN={MAX_TOOLS_THIS_TURN}. Abort {CHAT_ABORT_SECONDS}s."
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
    return _operator_failure(
        "Tools failed ("
        + detail
        + "). I won't invent file contents, ability output, or agent results.",
        verify="FAIL",
        nxt="Retry a narrower ask or name a path to read.",
    )


def _session_id_from_body(body: Dict[str, Any]) -> str:
    for key in ("session_id", "sessionId", "conversation_id", "conversationId"):
        val = str((body or {}).get(key) or "").strip()
        if val:
            return val
    return "console-default"


def apply_workspace_intent(
    text: str,
    *,
    session_id: str = "console-default",
    learn_then_work: bool = True,
) -> Dict[str, Any]:
    """Switch Craft workspace from chat. Optionally learn+bind git URLs."""
    from realai.bot.workspace_intent import (
        extract_workspace_target,
        is_git_source,
        resolve_local_workspace,
        set_session_workspace,
    )
    from realai.workspace import realai_workspace, set_request_workspace

    out: Dict[str, Any] = {
        "switched": False,
        "target": None,
        "workspace": str(realai_workspace()),
    }
    target = extract_workspace_target(text)
    if not target:
        return out
    out["target"] = target

    if is_git_source(target):
        if not learn_then_work:
            out["error"] = "git_url_needs_learn"
            return out
        try:
            from realai.cli.craft import tool_learn
            from realai.learn_git import compact_learn_result

            learned = compact_learn_result(tool_learn(source=target, write=False))
        except Exception as exc:
            out["error"] = f"learn_failed: {exc}"
            return out
        out["learn"] = learned
        src = learned.get("source") if isinstance(learned, dict) else None
        tree = None
        if isinstance(src, dict):
            tree = src.get("path") or src.get("local_path")
        if not tree and isinstance(learned, dict):
            tree = learned.get("path")
        if not tree:
            out["error"] = learned.get("error") if isinstance(learned, dict) else "learn_no_path"
            out["admit_failure"] = True
            return out
        path = Path(str(tree))
        if not path.is_dir():
            out["error"] = f"learned path missing: {path}"
            out["admit_failure"] = True
            return out
        set_session_workspace(session_id, str(path))
        set_request_workspace(path)
        out["switched"] = True
        out["workspace"] = str(path)
        out["kind"] = "git"
        return out

    path, err = resolve_local_workspace(target)
    if err or path is None:
        out["error"] = err or "resolve_failed"
        out["admit_failure"] = True
        return out
    set_session_workspace(session_id, str(path))
    set_request_workspace(path)
    out["switched"] = True
    out["workspace"] = str(path)
    out["kind"] = "local"
    return out


def apply_natural_grounding(body: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """Mutate chat ``body`` for a plain-English repo/code/ability/agent ask.

    Runs Craft inspect plus auto-planned abilities / learn / hive agents.
    When create/update has a concrete path+content, executes Craft write
    (same ``tool_write`` as ``/write``). Never invents tool output. Returns
    meta for ``realai_meta``. Caller should short-circuit when
    ``admit_failure`` or ``short_circuit`` is True instead of proxying to Vulkan.
    """
    from realai.bot.workspace_intent import (
        bind_session_workspace_for_request,
        looks_like_workspace_switch,
    )
    from realai.workspace import realai_workspace

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

    session_id = _session_id_from_body(body if isinstance(body, dict) else {})
    bind_session_workspace_for_request(session_id)
    meta["workspace"] = str(realai_workspace())
    meta["session_id"] = session_id

    # Chat-driven workspace switch (local folder or git URL → learn then work).
    if looks_like_workspace_switch(text):
        meta["should_ground"] = True
        ws_meta = apply_workspace_intent(text, session_id=session_id)
        meta["workspace_switch"] = ws_meta
        meta["workspace"] = ws_meta.get("workspace") or meta["workspace"]
        meta["used_tools"] = ["workspace"]
        meta["tools"] = ["workspace"]
        if ws_meta.get("learn"):
            meta["used_tools"].append("learn")
            meta["tools"].append("learn")
        if ws_meta.get("admit_failure") or ws_meta.get("error"):
            meta["admit_failure"] = True
            meta["failure_text"] = (
                f"Could not switch workspace ({ws_meta.get('error')}). "
                "Name an existing local folder or a git URL."
            )
            return meta
        # Pure switch ("work in C:\foo") short-circuits; follow-on inspect/write
        # in the same message still runs below when those intents are present.
        only_switch = (
            not looks_like_write_ask(text)
            and not looks_like_learn_ask(text)
            and not looks_like_repo_ask(text)
        )
        # "work in X" alone, or "work in X then list" — if repo ask remains, continue.
        if only_switch or (
            not looks_like_write_ask(text)
            and not looks_like_learn_ask(text)
            and not looks_like_repo_ask(text.replace(str(ws_meta.get("target") or ""), " "))
        ):
            # If the message is only a switch (maybe with trailing punctuation), stop.
            remainder = text
            tgt = str(ws_meta.get("target") or "")
            if tgt:
                remainder = remainder.replace(tgt, " ")
            remainder_l = remainder.lower()
            for cue in (
                "work in",
                "use workspace",
                "switch to",
                "switch workspace to",
                "set workspace to",
                "set workspace",
                "open the repo",
                "open repo",
                "open the project",
                "open project",
                "open the folder",
                "open folder",
                "cd to",
            ):
                remainder_l = remainder_l.replace(cue, " ")
            if not looks_like_repo_ask(remainder_l) and not looks_like_write_ask(remainder_l):
                meta["short_circuit"] = True
                kind = ws_meta.get("kind") or "local"
                meta["reply"] = format_operator_reply(
                    summary=f"Workspace is {ws_meta.get('workspace')} ({kind}).",
                    changed="none",
                    verify="PASS workspace switch",
                    nxt="Say what to read or change. I will inspect, write, and verify.",
                )
                return meta
        meta["mode"] = workspace_route_mode()

    write_ask = looks_like_write_ask(text)
    patch_ask = looks_like_patch_ask(text)
    write_plans = plan_natural_write(text) if write_ask else []

    if write_ask and write_plans:
        meta["should_ground"] = True
        used: List[str] = []
        # Multi-step: when the ask also wants inspect, read/list/grep first
        # (never collapse "read X then write Y" into a blind write).
        if looks_like_repo_ask(text):
            try:
                pre = run_natural_inspect(text)
            except Exception:
                pre = []
            if pre:
                meta["pre_inspect"] = pre
                used.extend(str(tr.get("tool") or "?") for tr in pre)
        args = write_plans[0][1]
        path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        try:
            result = run_natural_write(path, content, mode=str(args.get("mode") or "overwrite"))
        except Exception as exc:
            meta["admit_failure"] = True
            meta["error"] = str(exc)
            used.append("write")
            meta["used_tools"] = used
            meta["tools"] = used
            meta["failure_text"] = _operator_failure(
                f"I tried to write {path} and it failed ({exc}). "
                "I will not invent a successful write.",
                verify="FAIL write",
                nxt="Fix the path or contents and try again.",
            )
            return meta
        failed = isinstance(result, dict) and (
            result.get("ok") is False or bool(result.get("error"))
        )
        used.append("write")
        meta["write_result"] = result
        if failed:
            meta["admit_failure"] = True
            meta["used_tools"] = used
            meta["tools"] = used
            meta["tool_count"] = len(used)
            err = (result or {}).get("error") or "write_failed"
            meta["failure_text"] = _operator_failure(
                f"Write failed ({err}). I will not invent a successful write. "
                "Paths must stay under the workspace.",
                verify="FAIL write",
                nxt="Choose a path inside the workspace.",
            )
            return meta
        verify = verify_natural_write(path)
        used.append("read")
        # Post-step health GET. Not counted in MAX_TOOLS_THIS_TURN.
        smoke = post_write_smoke()
        meta["smoke"] = smoke
        meta["post_write_smoke"] = smoke
        used.append("post_write_smoke")
        meta["verify"] = verify
        meta["tools"] = used
        meta["used_tools"] = used
        meta["tool_count"] = len([u for u in used if u != "post_write_smoke"])
        meta["wrote"] = True
        meta["short_circuit"] = True
        meta["reply"] = format_write_verified_reply(result, verify, smoke)
        return meta

    if write_ask and not write_plans:
        spec_path, spec_content = extract_write_spec(text)
        if spec_path:
            try:
                from realai.cli.craft import is_protected_core_path

                protected = is_protected_core_path(spec_path)
            except Exception:
                rel = spec_path.replace("\\", "/").lower()
                protected = rel.startswith("realai/bot/") or rel.startswith(
                    "realai/orchestration/"
                )
            if protected:
                meta["should_ground"] = True
                meta["admit_failure"] = True
                meta["used_tools"] = ["write"]
                meta["tools"] = ["write"]
                meta["failure_text"] = _operator_failure(
                    f"refusing_natural_write_protected_path: {spec_path}. "
                    "Use /write path|||content.",
                    verify="FAIL protected path",
                    nxt="Use an explicit /write if this core path should change.",
                )
                return meta
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
        meta["failure_text"] = _operator_failure(
            need_write_args_reply(spec_path, spec_content) + extra,
            verify="FAIL missing write args",
            nxt="Name a relative path and the file contents.",
        )
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
        budget = max(0, MAX_TOOLS_THIS_TURN - len(results))
        if extras and budget:
            results.extend(run_natural_auto(extras[:budget], text))
    except Exception as exc:
        meta["admit_failure"] = True
        meta["error"] = str(exc)
        meta["failure_text"] = _operator_failure(
            f"I tried to run tools and they failed ({exc}). "
            "I will not invent file contents, ability output, or agent results.",
            verify="FAIL",
            nxt="Retry a narrower ask.",
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

    # "learn from X and work there" → bind session workspace to the learned tree.
    if any(k == "learn" for k, _ in extras) and re.search(
        r"(?i)\bwork\s+(there|here|in\s+it|on\s+it)\b", text
    ):
        for tr in results:
            if str(tr.get("tool") or "") != "learn":
                continue
            payload = tr.get("result") if isinstance(tr, dict) else None
            if not isinstance(payload, dict):
                continue
            src = payload.get("source") if isinstance(payload.get("source"), dict) else {}
            tree = src.get("path") or payload.get("path")
            if not tree:
                continue
            p = Path(str(tree))
            if p.is_dir():
                from realai.bot.workspace_intent import set_session_workspace
                from realai.workspace import set_request_workspace

                set_session_workspace(session_id, str(p))
                set_request_workspace(p)
                meta["workspace"] = str(p)
                meta["workspace_switch"] = {
                    "switched": True,
                    "kind": "learn_then_work",
                    "workspace": str(p),
                }
                meta["short_circuit"] = True
                meta["reply"] = format_operator_reply(
                    summary=f"Learned tree is now the workspace ({p}).",
                    changed=str(payload.get("packet_path") or payload.get("slug") or "learn packet"),
                    verify="PASS learn+workspace",
                    nxt="Ask me to list, read, or patch files.",
                )
                return meta
            break

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
