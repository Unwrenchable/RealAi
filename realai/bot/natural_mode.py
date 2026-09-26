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
# The hat card leads; the four lines from the operator contract stay so both
# shapes coexist. Hat choice itself is per-turn (see hat_routing.infer_hat).
NATURAL_REPLY_CONTRACT = (
    "REPLY CONTRACT: inferred hat card, then four short lines.\n"
    "Mode Active: Hive | One-tree | Builder | RackUp (automatic, no toggle).\n"
    "Action Taken: 1-2 sentences.\n"
    "Key Results: 2-3 bullets.\n"
    "Next Recommended Step: one follow-up.\n"
    "Summary: one sentence.\n"
    "What changed: paths or none.\n"
    "Verify: pass or fail. Never claim success if hive smoke failed.\n"
    "Next: one step.\n"
    "CAPS: MAX_TOOLS_THIS_TURN=3. Chat abort 180s. Do not loosen.\n"
    "Never say LANDED or shipped unless a write tool succeeded. Propose is not a write. "
    "Named paths need workspace_read. No raw JSON in the main reply. "
    "Service down: say Service Unavailable and retry."
)

_REPLY_HEADINGS = ("Summary:", "What changed:", "Verify:", "Next:")

_SIMPLE_PATH_ASK_RE = re.compile(
    r"(?i)\b(quote|read|open|show|propose|suggest|what.?s\s+in|whats\s+in|marker|contents?\s+of)\b"
)

# Same shapes the bridge critic treats as named workspace files
# (_extract_workspace_paths). Keep these in lockstep — a named path with no
# workspace_read is a critic fail.
_NAMED_REL_RE = re.compile(
    r"(?<![\w./-])((?:apps|realai|modules|abilities|docs|scripts|frontend|agents|fusion-ui|\.github)/[\w./\-]+\.[\w]+)",
    re.I,
)
_NAMED_ABS_RE = re.compile(
    r"(?<![\w])([A-Za-z]:/RealAI-clean/[\w./\-]+\.[\w]+)",
    re.I,
)
_NAMED_BARE_RE = re.compile(
    r"(?<![\w./-])(console\.html|package\.json|realai\.toml|models\.yaml|model\.json)\b",
    re.I,
)
_NAMED_READ_VERB_RE = re.compile(r"\bread\s+([\w./\-]+\.[\w]+)", re.I)

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


def canonicalize_named_path(raw: str, *, remap_readme: bool = False) -> str:
    """Map a mentioned path to the repo-relative file the critic would read.

    Bare ``console.html`` is the webview gold file. Bare ``README.md`` is
    remapped only when the bridge would (``read README.md`` or a
    ``C:\\RealAI-clean\\README.md`` path). A plain "create README.md" stays
    at the workspace root.
    """
    p = (raw or "").strip().strip("`'\"").replace("\\", "/")
    p = p.rstrip(".,;:)]")
    if not p:
        return ""
    low = p.lower()
    product_abs = low.startswith("c:/realai-clean/") or low.startswith("/realai-clean/")
    for prefix in ("c:/realai-clean/", "/realai-clean/"):
        if low.startswith(prefix):
            p = p[len(prefix) :]
            low = p.lower()
            break
    while p.startswith("./"):
        p = p[2:]
        low = p.lower()
    if "/" not in p and low == "console.html":
        return "apps/vscode/webview/console.html"
    if "/" not in p and low == "readme.md" and (remap_readme or product_abs):
        return "apps/vscode/README.md"
    return p


def _looks_like_file(path: str) -> bool:
    base = (path or "").rsplit("/", 1)[-1]
    return "." in base and not base.startswith(".")


def named_workspace_paths(text: str) -> List[str]:
    """Concrete files named in free text, critic shapes first.

    Covers ``console.html``, ``C:\\RealAI-clean\\...``, and
    ``apps/vscode/webview/...``. Cap matches the bridge extractor (5). The
    turn planner still spends at most ``MAX_TOOLS_THIS_TURN`` slots.
    """
    raw = text or ""
    norm = raw.replace("\\", "/")
    found: List[str] = []
    seen: set[str] = set()

    def _add(token: str, *, remap_readme: bool = False) -> None:
        canon = canonicalize_named_path(token, remap_readme=remap_readme)
        if not canon or not _looks_like_file(canon):
            return
        key = canon.lower()
        # Prefer the critic's README alias over a second root README read.
        if key == "readme.md" and "apps/vscode/readme.md" in seen:
            return
        if key == "apps/vscode/readme.md" and "readme.md" in seen:
            seen.discard("readme.md")
            found[:] = [p for p in found if p.lower() != "readme.md"]
        if key in seen:
            return
        seen.add(key)
        found.append(canon)

    for m in _NAMED_REL_RE.finditer(norm):
        _add(m.group(1))
    for m in _NAMED_ABS_RE.finditer(norm):
        _add(m.group(1), remap_readme=True)
    for m in _NAMED_READ_VERB_RE.finditer(norm):
        _add(m.group(1), remap_readme=True)
    for m in _NAMED_BARE_RE.finditer(norm):
        _add(m.group(1))
    if re.search(r"apps/vscode/README\.md", norm, re.I):
        _add("apps/vscode/README.md")
    for token in extract_path_tokens(raw):
        _add(token)
    for token in extract_path_tokens(norm):
        _add(token)
    return found[:5]


def resolve_write_path(text: str, raw: str) -> str:
    """Write target. Absolute product paths and ``console.html`` follow the critic."""
    norm = (raw or "").strip().strip("`'\"").replace("\\", "/")
    low = norm.lower()
    remap_readme = low.startswith("c:/realai-clean/") or low.startswith("/realai-clean/")
    canon = canonicalize_named_path(norm, remap_readme=remap_readme)
    if not canon:
        return norm
    for path in named_workspace_paths(text):
        if path.lower() == canon.lower():
            return path
    return canonicalize_named_path(norm, remap_readme=False) or norm


def plan_named_workspace_reads(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """``workspace_read`` plans for named files. One read, one tool slot."""
    return [
        ("workspace_read", {"path": rel})
        for rel in named_workspace_paths(text)[:MAX_TOOLS_THIS_TURN]
    ]


def looks_like_repo_ask(text: str) -> bool:
    """True when a plain-English message is about files / code / the repo."""
    raw = (text or "").strip()
    if not raw or is_explicit_command(raw):
        return False
    if extract_path_tokens(raw) or named_workspace_paths(raw):
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
        # console_verify_pack is Core desk / ability execute only.
        # Do not spend a Natural Mode turn slot on it.
        if not a or a in seen or a in {"learn_git", "git_learn", "console_verify_pack"}:
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
        path = resolve_write_path(t, path) or path
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


def _key_result_lines(changed: str, verify: str, extra: str = "") -> str:
    rows: List[str] = []
    changed_s = _one_line(changed, 140)
    verify_s = _one_line(verify, 160)
    if changed_s and changed_s.lower() != "none":
        rows.append(f"- {changed_s}")
    if verify_s:
        rows.append(f"- {verify_s}")
    extra_s = _one_line(extra, 140) if extra else ""
    if extra_s and extra_s.lower() != "none" and extra_s not in rows:
        rows.append(f"- {extra_s}")
    if not rows:
        rows.append("- none")
    return "\n".join(rows[:3])


def format_operator_reply(
    *,
    summary: str,
    changed: str,
    verify: str,
    nxt: str,
    hat: str = "One-tree",
    extra: str = "",
) -> str:
    """Hat card plus the Summary / What changed / Verify / Next contract.

    Mode Active leads. The four legacy lines stay so older checks and the
    model contract still match.
    """
    from realai.bot.hat_routing import normalize_hat

    name = normalize_hat(hat)
    card = (
        f"Mode Active: {name}\n"
        f"Action Taken: {_one_line(summary)}\n"
        f"Key Results:\n{_key_result_lines(changed, verify, extra)}\n"
        f"Next Recommended Step: {_one_line(nxt)}"
    )
    legacy = (
        f"Summary: {_one_line(summary)}\n"
        f"What changed: {_one_line(changed)}\n"
        f"Verify: {_one_line(verify)}\n"
        f"Next: {_one_line(nxt)}"
    )
    return card + "\n\n" + legacy


def ensure_mode_active(text: str, hat: str = "One-tree") -> str:
    """Put ``Mode Active`` on the first line when a reply does not have it."""
    from realai.bot.hat_routing import normalize_hat

    raw = text or ""
    if re.search(r"(?im)^\s*Mode Active\s*:", raw):
        return raw
    name = normalize_hat(hat)
    if not raw.strip():
        return f"Mode Active: {name}"
    return f"Mode Active: {name}\n{raw}"


def reply_has_contract(text: str) -> bool:
    low = (text or "").lower()
    return all(h.lower() in low for h in _REPLY_HEADINGS)


def scrub_unearned_landed(text: str, *, write_ok: bool) -> str:
    """LANDED / SHIPPED only after a write tool succeeded and smoke did not fail."""
    if write_ok:
        return text or ""
    out = re.sub(r"\bLANDED\b", "PROPOSED", text or "", flags=re.I)
    return re.sub(r"\bSHIPPED\b", "PROPOSED", out, flags=re.I)


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


def _smoke_visible(smoke: Dict[str, Any]) -> tuple[str, str]:
    """Visible smoke line plus a raw appendix payload.

    Transport failures stay out of the card. The exception text is folded.
    """
    from realai.bot.hat_routing import service_down_visible

    err = str((smoke or {}).get("error") or "").strip()
    status = (smoke or {}).get("status")
    snippet = str((smoke or {}).get("snippet") or "").strip()
    try:
        http = int(status) if status is not None and str(status).isdigit() else None
    except (TypeError, ValueError):
        http = None
    collapsed = " ".join(err.split())
    friendly = service_down_visible(err) if err else ""
    raw = err or snippet
    # service_down_visible rewrites only transport failures. Other errors
    # stay in the card when they are already short.
    if err and friendly != collapsed:
        return friendly, err
    if http is not None and http >= 500:
        return "Service Unavailable. Retry GET /health.", raw
    if http is not None:
        return f"HTTP {http}", snippet if len(snippet) > 80 else ""
    if collapsed and (len(collapsed) > 160 or "traceback" in collapsed.lower()):
        return "Service Unavailable. Retry GET /health.", raw
    if collapsed:
        return collapsed, ""
    return service_down_visible(str(status or "unhealthy")), snippet if len(snippet) > 80 else ""


def format_write_verified_reply(
    write_result: Dict[str, Any],
    verify: Dict[str, Any],
    smoke: Optional[Dict[str, Any]] = None,
    hat: str = "Builder",
) -> str:
    """Write reply in the operator contract. Smoke failure is not success."""
    from realai.bot.hat_routing import raw_diagnostic_appendix

    path = (write_result or {}).get("path") or (verify or {}).get("path") or "?"
    nbytes = (write_result or {}).get("bytes")
    disk_ok = isinstance(verify, dict) and not verify.get("error")
    smoke_d = smoke if isinstance(smoke, dict) else {"ok": False, "error": "not_run"}
    smoke_ok = bool(smoke_d.get("ok"))
    raw_payload = ""
    if not disk_ok:
        err = (verify or {}).get("error") if isinstance(verify, dict) else "verify_unavailable"
        verify_line = "FAIL re-read. The file did not verify on disk."
        summary = f"Write of {path} did not verify on disk."
        changed = "none"
        raw_payload = str(err or "")
    elif not smoke_ok:
        visible, raw_payload = _smoke_visible(smoke_d)
        verify_line = (
            f"FAIL hive smoke failed ({visible}). Do not treat this as done."
        )
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
        else "Retry the failed check before treating this change as done."
    )
    text = scrub_unearned_landed(
        format_operator_reply(
            summary=summary,
            changed=changed,
            verify=verify_line,
            nxt=nxt,
            hat=hat,
        ),
        write_ok=bool(disk_ok and smoke_ok),
    )
    if disk_ok:
        content = str((verify or {}).get("content") or "")
        preview = "\n".join(content.splitlines()[:8])
        # Preview is on-disk bytes. Do not rewrite words inside the file.
        text += f"\n--- on disk (first lines) ---\n{preview}"
    if raw_payload and not smoke_ok:
        text += raw_diagnostic_appendix(raw_payload)
    elif raw_payload and not disk_ok:
        text += raw_diagnostic_appendix(raw_payload)
    return text


def _operator_failure(
    summary: str,
    *,
    verify: str = "FAIL",
    nxt: str = "Narrow the ask and retry.",
    hat: str = "One-tree",
) -> str:
    return scrub_unearned_landed(
        format_operator_reply(
            summary=summary, changed="none", verify=verify, nxt=nxt, hat=hat
        ),
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
    smoke_raw = ""
    if smoke is not None and not smoke_ok:
        visible, smoke_raw = _smoke_visible(smoke)
        verify = f"FAIL hive smoke failed ({visible}). Do not treat this as done."
    elif smoke is not None and smoke_ok:
        verify = f"PASS hive health {smoke.get('status')} {smoke.get('url')}"
    else:
        verify = "no write this turn; hive smoke not run"
    tools = nat.get("used_tools") or nat.get("tools") or []
    changed = ", ".join(changed_bits) if changed_bits else (
        ", ".join(str(t) for t in tools) if tools else "none"
    )
    earned = bool(write_ok and smoke_ok)
    from realai.bot.hat_routing import normalize_hat, raw_diagnostic_appendix

    hat = normalize_hat(str(nat.get("hat") or "One-tree"))
    body = scrub_unearned_landed(text or "", write_ok=earned)
    if reply_has_contract(body):
        body = ensure_mode_active(body, hat)
        if smoke is not None and not smoke_ok and "fail" not in body.lower():
            body = body.rstrip() + "\nVerify: " + verify
        if smoke_raw and "View raw diagnostic payload" not in body:
            body = body.rstrip() + raw_diagnostic_appendix(smoke_raw)
        return body, smoke
    first = body.split("\n", 1)[0] if body else ""
    summary = _one_line(first, 220) if first else "Tools finished."
    shaped = format_operator_reply(
        summary=summary,
        changed=changed,
        verify=verify,
        nxt="Continue from Verify.",
        hat=hat,
    )
    if body and body not in shaped:
        shaped += "\n\n" + body
    if smoke_raw and "View raw diagnostic payload" not in shaped:
        shaped = shaped.rstrip() + raw_diagnostic_appendix(smoke_raw)
    return scrub_unearned_landed(shaped, write_ok=earned), smoke


def _explicit_search_verb(text: str) -> bool:
    return bool(re.search(r"(?i)\b(grep|search|list|pwd)\b", text or ""))


def _covered_named_path(path: str, covered: set[str]) -> bool:
    canon = canonicalize_named_path(path).lower()
    return bool(canon) and canon in covered


def _drop_unnamed_storm(
    plans: List[Tuple[str, Dict[str, Any]]],
    text: str,
) -> List[Tuple[str, Dict[str, Any]]]:
    """When a file is named, don't spend the cap on an auto pwd/list/grep storm."""
    explicit_list = bool(re.search(r"(?i)\blist\b", text))
    explicit_grep = bool(re.search(r"(?i)\b(grep|search)\b", text))
    explicit_pwd = bool(re.search(r"(?i)\b(pwd|where am i)\b", text))
    kept: List[Tuple[str, Dict[str, Any]]] = []
    for name, args in plans:
        if name in ("pwd", "here") and not explicit_pwd:
            continue
        if name == "list" and not explicit_list:
            continue
        if name == "grep" and not explicit_grep:
            continue
        kept.append((name, args))
    return kept


def plan_natural_inspect(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Craft ``plan_tools`` plus named-file ``workspace_read`` first.

    Cap: at most ``MAX_TOOLS_THIS_TURN`` tools. A named path spends slot 1 on
    ``workspace_read`` (the critic fails the turn otherwise). Quote / read /
    propose asks that only name files do not add a pwd+list+grep storm.
    """
    from realai.cli.craft import auto_inspect_plans, dedupe_plans, plan_tools

    t = (user_text or "").strip()
    reads = plan_named_workspace_reads(t)
    covered = {
        canonicalize_named_path(str((args or {}).get("path") or "")).lower()
        for _name, args in reads
    }
    covered.discard("")
    # Fast path: "quote/read/propose … path" → workspace_read those files only.
    # An explicit grep/list/pwd still shares the remaining slots.
    if reads and _SIMPLE_PATH_ASK_RE.search(t) and not _explicit_search_verb(t):
        return dedupe_plans(reads)[:MAX_TOOLS_THIS_TURN]

    plans: List[Tuple[str, Dict[str, Any]]] = []
    for name, args in list(plan_tools(t) or []):
        if name in ("read", "workspace_read") and _covered_named_path(
            str((args or {}).get("path") or ""), covered
        ):
            continue
        plans.append((name, args))
    if reads:
        plans = _drop_unnamed_storm(plans, t)
        plans = reads + plans
    names = {n for n, _ in plans}
    if looks_like_repo_ask(t) and not names.intersection(
        {"pwd", "list", "grep", "read", "workspace_read"}
    ):
        plans.extend(auto_inspect_plans(t))
    if reads:
        rest = [
            p
            for p in plans
            if p not in reads
            and not (
                p[0] in ("read", "workspace_read")
                and _covered_named_path(str((p[1] or {}).get("path") or ""), covered)
            )
        ]
        plans = list(reads) + rest
    return dedupe_plans(plans)[:MAX_TOOLS_THIS_TURN]


def _other_natural_intents(text: str) -> bool:
    return bool(
        looks_like_agent_ask(text)
        or looks_like_learn_ask(text)
        or looks_like_broken_ask(text)
        or looks_like_write_ask(text)
        or match_ability_ids(text)
    )


def plan_natural_turn(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """One Natural Mode turn. Named-path ``workspace_read`` is always first.

    Auto-read counts toward ``MAX_TOOLS_THIS_TURN``. Remaining slots go to
    inspect / learn / doctor / agents — never a fourth tool.
    """
    from realai.cli.craft import dedupe_plans

    t = (user_text or "").strip()
    if not t or is_explicit_command(t):
        return []
    reads = plan_named_workspace_reads(t)
    if (
        reads
        and _SIMPLE_PATH_ASK_RE.search(t)
        and not _other_natural_intents(t)
        and not _explicit_search_verb(t)
    ):
        return dedupe_plans(reads)[:MAX_TOOLS_THIS_TURN]

    rest: List[Tuple[str, Dict[str, Any]]] = []
    # Learn should not pick up a pwd storm; the named read (if any) is enough.
    if not looks_like_learn_ask(t) and (looks_like_repo_ask(t) or reads):
        for name, args in plan_natural_inspect(t):
            if name == "workspace_read":
                continue
            rest.append((name, args))
    if not looks_like_write_ask(t):
        rest.extend(plan_natural_auto(t))
    return dedupe_plans(list(reads) + rest)[:MAX_TOOLS_THIS_TURN]


def plans_before_write(text: str, write_path: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Named-path reads before a concrete write.

    Write and the post-write re-read take two slots. Auto-read uses what is
    left (one, while the cap is 3). Paths that are not the write target come
    first so "read A and write B" still reads A.
    """
    slots = max(0, MAX_TOOLS_THIS_TURN - 2)
    if slots <= 0:
        return []
    target = canonicalize_named_path(write_path).lower()
    paths = named_workspace_paths(text)
    others = [p for p in paths if p.lower() != target]
    same = [p for p in paths if p.lower() == target]
    ordered = others + same
    if not ordered and target:
        ordered = [canonicalize_named_path(write_path)]
    return [("workspace_read", {"path": p}) for p in ordered[:slots]]


_AUTO_KINDS = {"learn", "ability", "agents", "doctor"}


def run_natural_turn(user_text: str) -> List[Dict[str, Any]]:
    """Execute ``plan_natural_turn`` in order. Never invents tool results."""
    from realai.cli.craft import apply_workspace, run_tools

    apply_workspace()
    plans = plan_natural_turn(user_text)[:MAX_TOOLS_THIS_TURN]
    out: List[Dict[str, Any]] = []
    craft_buf: List[Tuple[str, Dict[str, Any]]] = []

    def _flush() -> None:
        if not craft_buf:
            return
        out.extend(run_tools(craft_buf))
        craft_buf.clear()

    for kind, args in plans:
        if kind in _AUTO_KINDS:
            _flush()
            out.extend(run_natural_auto([(kind, args)], user_text))
        else:
            craft_buf.append((kind, args))
    _flush()
    return out[:MAX_TOOLS_THIS_TURN]


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
    hat: str = "",
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
    from realai.bot.hat_routing import hat_turn_prefix, infer_hat

    name = hat or infer_hat(user_text)
    follow += (
        "\n\nReply shape after these tools: Mode Active, Action Taken, "
        "Key Results, Next Recommended Step, then Summary / What changed / "
        "Verify / Next. Short sentences. Never say LANDED unless a write tool "
        "succeeded. "
        f"MAX_TOOLS_THIS_TURN={MAX_TOOLS_THIS_TURN}. Abort {CHAT_ABORT_SECONDS}s.\n"
        + hat_turn_prefix(name)
    )
    return f"{user_text}\n\n{tools_txt}\n\n{follow}"


def failure_reply(results: List[Dict[str, Any]], hat: str = "One-tree") -> str:
    from realai.bot.hat_routing import raw_diagnostic_appendix, service_down_visible

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
    visible = service_down_visible(detail)
    # Long tool dumps and tracebacks stay in the appendix, not the card.
    if len(visible) > 180 or "traceback" in visible.lower() or visible[:1] in "{[":
        visible = "Service Unavailable. Retry a narrower ask." if "Service Unavailable" in visible else "tool error folded below"
    text = _operator_failure(
        "Tools failed ("
        + visible
        + "). I won't invent file contents, ability output, or agent results.",
        verify="FAIL",
        nxt="Retry a narrower ask or name a path to read.",
        hat=hat,
    )
    if detail and detail != visible:
        text += raw_diagnostic_appendix(detail)
    return text


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

    from realai.bot.hat_routing import infer_hat, raw_diagnostic_appendix

    hat = infer_hat(text)
    meta["hat"] = hat

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
            meta["failure_text"] = _operator_failure(
                "Could not switch workspace. "
                "Name an existing local folder or a git URL.",
                verify="FAIL workspace switch",
                nxt="Name an existing local folder or a git URL.",
                hat=hat,
            ) + raw_diagnostic_appendix(str(ws_meta.get("error") or ""))
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
                    hat=hat,
                )
                return meta
        meta["mode"] = workspace_route_mode()

    write_ask = looks_like_write_ask(text)
    patch_ask = looks_like_patch_ask(text)
    write_plans = plan_natural_write(text) if write_ask else []

    if write_ask and write_plans:
        meta["should_ground"] = True
        used: List[str] = []
        args = write_plans[0][1]
        path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        # Named-path workspace_read first. It spends a slot; write + verify
        # take the other two. Smoke stays a post-step.
        pre_plans = plans_before_write(text, path)
        if pre_plans:
            try:
                from realai.cli.craft import apply_workspace, run_tools

                apply_workspace()
                pre = run_tools(pre_plans)
            except Exception:
                pre = []
            if pre:
                meta["pre_inspect"] = pre
                used.extend(str(tr.get("tool") or "?") for tr in pre)
        try:
            result = run_natural_write(path, content, mode=str(args.get("mode") or "overwrite"))
        except Exception as exc:
            meta["admit_failure"] = True
            meta["error"] = str(exc)
            used.append("write")
            meta["used_tools"] = used
            meta["tools"] = used
            meta["failure_text"] = _operator_failure(
                f"I tried to write {path} and it failed. "
                "I will not invent a successful write.",
                verify="FAIL write",
                nxt="Fix the path or contents and try again.",
                hat=hat,
            ) + raw_diagnostic_appendix(str(exc))
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
                "Write failed. I will not invent a successful write. "
                "Paths must stay under the workspace.",
                verify="FAIL write",
                nxt="Choose a path inside the workspace.",
                hat=hat,
            ) + raw_diagnostic_appendix(str(err))
            return meta
        verify = verify_natural_write(path)
        used.append("workspace_read")
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
        meta["reply"] = format_write_verified_reply(result, verify, smoke, hat=hat)
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
                    hat=hat,
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
            hat=hat,
        )
        return meta

    extras = plan_natural_auto(text)
    named = named_workspace_paths(text)
    # A learn ask skips the pwd storm, but a named file is still read first.
    inspect_needed = (looks_like_repo_ask(text) or bool(named)) and not (
        looks_like_learn_ask(text) and not named
    )
    if not (inspect_needed or extras or named):
        return meta

    meta["should_ground"] = True
    meta["apply_model_writes"] = bool(patch_ask)
    results = []
    try:
        results.extend(run_natural_turn(text))
    except Exception as exc:
        meta["admit_failure"] = True
        meta["error"] = str(exc)
        meta["failure_text"] = _operator_failure(
            "I tried to run tools and they failed. "
            "I will not invent file contents, ability output, or agent results.",
            verify="FAIL",
            nxt="Retry a narrower ask.",
            hat=hat,
        ) + raw_diagnostic_appendix(str(exc))
        return meta

    names = [str(tr.get("tool") or "?") for tr in results]
    meta["tools"] = names
    meta["used_tools"] = names
    meta["tool_count"] = len(results)
    meta["auto"] = [k for k, _ in extras]
    meta["admit_failure"] = tools_all_failed(results)
    if meta["admit_failure"]:
        meta["failure_text"] = failure_reply(results, hat=hat)
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
                    hat=hat,
                )
                return meta
            break

    msgs = list(body.get("messages") or [])
    grounded = format_grounding_block(
        text, results, want_writes=bool(patch_ask), hat=hat
    )
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
