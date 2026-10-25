"""Tool loop, grounding guard and model planner for hive agents.

Protocol: a simple JSON action protocol (works with any local chat model, no native tool
support needed). Each assistant turn must be ONE JSON object:

  {"action": "list_dir", "args": {"path": "backend"}}
  {"action": "read_file", "args": {"path": "backend/api/quests.js"}}
  {"action": "search", "args": {"pattern": "quest", "glob": "*.js"}}
  {"action": "final", "answer": "...findings citing real paths..."}

``chat`` is any callable(messages) -> str. The loop is capped at ``max_steps`` tool calls.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from .fs_tools import FSDenied, SafeFS

Chat = Callable[[list[dict[str, str]]], str]

PROTOCOL = """You can inspect the project with read-only tools. Reply with exactly ONE JSON object per turn, nothing else.
Tools:
  {"action":"list_dir","args":{"path":"<dir relative to project root>"}}
  {"action":"read_file","args":{"path":"<file relative to project root>"}}
  {"action":"search","args":{"pattern":"<regex>","glob":"<optional, e.g. *.js>"}}
When done: {"action":"final","answer":"<findings>"}
Rules: the ONLY real paths are the ones in tool results; never guess a path. Read at least one file before final.
Only cite file paths you listed, searched or read. Use paths relative to the project root.
You cannot write files; propose fixes as text. Never ask for or reveal secrets."""


def parse_action(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    start = s.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(s[start:i + 1])
                    except ValueError:
                        break
                    if isinstance(obj, dict) and obj.get("action"):
                        return obj
                    break
        start = s.find("{", start + 1)
    return None


def _clip(obj: dict[str, Any], n: int = 6000) -> str:
    t = json.dumps(obj, ensure_ascii=False)
    return t if len(t) <= n else t[:n] + '..."(clipped)'


# ---- grounding -------------------------------------------------------------
_PATH_RX = re.compile(r"(?<![\w/.:-])((?:[A-Za-z]:[\\/])?(?:[\w.@-]+[\\/])+[\w.@-]+\.[A-Za-z0-9]{1,6}|[\w@-]+\.(?:js|ts|tsx|jsx|py|json|md|html|css|rs|toml|yml|yaml|sol|cjs|mjs))(?![\w/])")


def cited_paths(text: str) -> list[str]:
    seen: list[str] = []
    for m in _PATH_RX.finditer(text or ""):
        p = m.group(1).strip("`'\".,;:()[]")
        if re.match(r"^\d+(\.\d+)+$", p) or p.lower().startswith(("http", "www.")):
            continue
        if p not in seen:
            seen.append(p)
    return seen


def check_grounding(text: str, fs: SafeFS) -> tuple[list[str], list[str]]:
    ok, bad = [], []
    for p in cited_paths(text):
        rel = p.replace("\\", "/")
        if fs.exists(rel):
            ok.append(rel)
        elif "/" not in rel and any(h.endswith("/" + rel) for h in fs.read_log):
            ok.append(rel)  # bare file name of something actually read
        else:
            bad.append(p)
    return ok, bad


def strip_invented(text: str, bad: list[str]) -> str:
    for p in sorted(bad, key=len, reverse=True):
        text = text.replace(p, f"[unverified path: {p}]")
    return text


def run_agent(chat: Chat, fs: SafeFS, task: str, role: str = "", max_steps: int = 8,
              emit: Callable[..., None] | None = None, agent: str = "") -> dict[str, Any]:
    from .events import noop, tool_args_public

    emit = emit or noop
    system = (f"You are the {role} agent in the RealAI hive." if role else "You are a RealAI hive agent.") + "\n" + PROTOCOL
    seed = seed_context(fs, task)
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": f"Task: {task}\n{seed}\nNext JSON action:"}]
    calls: list[dict[str, Any]] = []
    seen: set[str] = set()
    answer = ""
    for _ in range(max_steps):
        reply = chat(msgs)
        act = parse_action(reply)
        msgs.append({"role": "assistant", "content": reply})
        if not act:
            answer = reply  # model answered in prose
            break
        name = str(act.get("action"))
        if name == "final":
            answer = str(act.get("answer") or "")
            break
        args = act.get("args") if isinstance(act.get("args"), dict) else {}
        key = name + json.dumps(args, sort_keys=True)
        if key in seen:
            calls.append({"tool": name, "args": args, "error": "repeat"})
            msgs.append({"role": "user", "content": "You already ran that. Pick a different action, e.g. read_file on a path "
                         "from the results above, or final."})
            continue
        seen.add(key)
        res = fs.call(name, args)
        emit("tool.call", agent=agent, tool=name, args=tool_args_public(args), error=res.get("error"),
             hits=len(res.get("hits") or res.get("entries") or []) if isinstance(res, dict) else 0)
        calls.append({"tool": name, "args": act.get("args"), "error": res.get("error")})
        msgs.append({"role": "user", "content": f"Result of {name}: {_clip(res)}\nNext JSON action:"})
    else:
        msgs.append({"role": "user", "content": 'Step limit reached. Reply now with {"action":"final","answer":"..."}.'})
        reply = chat(msgs)
        act = parse_action(reply)
        answer = str(act.get("answer")) if act and act.get("action") == "final" else reply
    ok, bad = check_grounding(answer, fs)
    retried = False
    if bad:
        retried = True
        emit("grounding.flag", agent=agent, invented=bad[:20], action="retry")
        msgs.append({"role": "user", "content": "These cited paths do not exist in the project: " + ", ".join(bad)
                     + '. Rewrite your final answer citing only files you actually read or listed. Reply {"action":"final","answer":"..."}.'})
        reply = chat(msgs)
        act = parse_action(reply)
        answer = str(act.get("answer")) if act and act.get("action") == "final" else reply
        ok, bad = check_grounding(answer, fs)
        if bad:
            answer = strip_invented(answer, bad)
            emit("grounding.flag", agent=agent, invented=bad[:20], action="stripped")
    return {"answer": answer, "tool_calls": calls, "files_read": list(dict.fromkeys(fs.read_log)),
            "cited_ok": ok, "cited_invented": bad, "grounding_retry": retried}


_STOP = {"review", "system", "bugs", "propose", "fixes", "check", "find", "with", "that", "this", "from", "their",
         "about", "report", "concrete", "citing", "real", "file", "paths", "code", "team", "current", "identify",
         "issues", "potential", "codebase", "inconsistencies", "should", "using", "against", "playtest"}


def task_keywords(task: str, n: int = 2) -> list[str]:
    words = [w.lower().rstrip("s") for w in re.findall(r"[A-Za-z]{4,}", task or "")]
    out: list[str] = []
    for w in words:
        if w not in _STOP and w not in out:
            out.append(w)
    return out[:n]


def seed_context(fs: SafeFS, task: str) -> str:
    """Real starting facts (root listing + file-name/content hits) so the model never starts from guesses."""
    parts = []
    top = fs.list_dir(".")
    parts.append("Project root entries: " + ", ".join(top.get("entries", [])[:60]))
    for kw in task_keywords(task):
        r = fs.search(kw, max_hits=25)
        files = list(dict.fromkeys(r.get("files", []) + [h["path"] for h in r.get("hits", [])]))[:20]
        if files:
            parts.append(f"Files matching '{kw}': " + ", ".join(files))
    return "\n".join(parts)


# ---- planner ---------------------------------------------------------------
def model_plan(chat: Chat, goal: str, areas: list[str], fallback: Callable[[str], list[str]]) -> list[dict[str, str]]:
    prompt = ("Break this goal into 2 to 6 concrete, ordered steps for a software team doing a READ-ONLY review "
              "(inspect and analyse code, then propose fixes as text; no implementing, deploying or meetings). Each step gets one owner "
              f"area from this list: {areas}. Reply with ONLY a JSON array like "
              '[{"step":"...","area":"..."}].\nGoal: ' + goal)
    try:
        text = chat([{"role": "user", "content": prompt}])
        m = re.search(r"\[.*\]", text or "", re.S)
        data = json.loads(m.group(0)) if m else None
    except Exception:
        data = None
    steps: list[dict[str, str]] = []
    if isinstance(data, list):
        for d in data:
            if isinstance(d, dict) and str(d.get("step") or "").strip():
                area = str(d.get("area") or "").strip().lower()
                steps.append({"step": str(d["step"]).strip()[:300], "area": area if area in areas else ""})
    if 2 <= len(steps) <= 6:
        return steps
    if len(steps) > 6:
        return steps[:6]
    return [{"step": s, "area": ""} for s in fallback(goal)]


__all__ = ["run_agent", "parse_action", "cited_paths", "check_grounding", "model_plan", "FSDenied"]
