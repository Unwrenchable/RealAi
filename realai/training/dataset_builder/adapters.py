"""Pluggable source adapters. Each yields rows: {"messages": [...], "source": str, "meta": {...}}.

Register new adapters with ``@adapter("type")``. All adapters read local files only;
GitHub repos are read from local clones (see config ``roots``).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

Row = Dict[str, Any]
ADAPTERS: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Iterator[Row]]] = {}

_INSTR = re.compile(r"^\s*### Instruction:\s*\n(?P<q>.*?)\n\s*### Response:\s*\n(?P<a>.*)$", re.S)
_ROLE = re.compile(r"<\|(system|user|assistant)\|>\s*\n", re.S)


def adapter(name: str):
    def deco(fn):
        ADAPTERS[name] = fn
        return fn

    return deco


def _msgs(user: str, assistant: str, system: Optional[str] = None) -> List[Dict[str, str]]:
    out = [{"role": "system", "content": system}] if system else []
    out += [{"role": "user", "content": user.strip()}, {"role": "assistant", "content": assistant.strip()}]
    return out


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    """Tolerant JSONL reader (from realai/scripts/wire_training.py iter_jsonl)."""
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def row_to_messages(obj: Dict[str, Any]) -> Optional[List[Dict[str, str]]]:
    """messages / instruction+response|output / '### Instruction' text / '<|role|>' text."""
    msgs = obj.get("messages")
    if isinstance(msgs, list) and msgs:
        clean = [
            {"role": str(m.get("role") or "user"), "content": str(m.get("content") or "").strip()}
            for m in msgs
            if isinstance(m, dict) and str(m.get("content") or "").strip()
        ]
        clean = [m for m in clean if m["role"] in {"system", "user", "assistant"}]
        if any(m["role"] == "assistant" for m in clean) and any(m["role"] == "user" for m in clean):
            return clean
        return None
    q = obj.get("instruction") or obj.get("prompt") or obj.get("question")
    a = obj.get("response") or obj.get("output") or obj.get("answer") or obj.get("completion")
    if isinstance(q, str) and isinstance(a, str) and q.strip() and a.strip():
        return _msgs(q, a)
    text = obj.get("text")
    if isinstance(text, str):
        m = _INSTR.match(text)
        if m:
            return _msgs(m.group("q"), m.group("a"))
        parts = _ROLE.split(text)
        if len(parts) >= 5:
            out = [{"role": parts[i], "content": parts[i + 1].strip()} for i in range(1, len(parts) - 1, 2)]
            out = [x for x in out if x["content"]]
            if any(x["role"] == "assistant" for x in out):
                return out
    return None


def _resolve(paths: Iterable[str], roots: Dict[str, str]) -> List[Path]:
    out: List[Path] = []
    for raw in paths:
        s = str(raw)
        for k, v in roots.items():
            s = s.replace("{" + k + "}", v)
        p = Path(s).expanduser()
        if any(ch in p.name for ch in "*?["):
            out.extend(sorted(p.parent.glob(p.name)))
        elif "**" in s:
            base, pat = s.split("**", 1)
            out.extend(sorted(Path(base).glob("**" + pat)))
        else:
            out.append(p)
    return [p for p in out if p.exists()]


# --------------------------------------------------------------------------- jsonl
@adapter("jsonl")
def jsonl_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """Existing RealAI datasets (provider_traces, ability_surface, packA, finetune set, ...)."""
    for path in _resolve(spec.get("paths", []), ctx["roots"]):
        for obj in iter_jsonl(path):
            msgs = row_to_messages(obj)
            if msgs:
                yield {"messages": msgs, "meta": {"file": path.name, "ability": obj.get("ability")}}


# --------------------------------------------------------------------------- sessions
@adapter("self_builder_sessions")
def sessions_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """Self-builder / hive sessions via extract_from_agent_tools.sessions_to_instruction_samples.

    ``require_success`` (default true) skips sessions whose result.status is not success/done.
    """
    from realai.training.extract_from_agent_tools import sessions_to_instruction_samples

    ok = {"success", "ok", "done", "completed"}
    for path in _resolve(spec.get("paths", []), ctx["roots"]):
        sessions = list(iter_jsonl(path))
        if spec.get("require_success", True):
            sessions = [
                s for s in sessions
                if str((s.get("result") or {}).get("status", "")).lower() in ok
                or (isinstance(s.get("messages"), list) and not s.get("result"))
            ]
        for sample in sessions_to_instruction_samples(sessions):
            msgs = row_to_messages(sample)
            if msgs:
                yield {"messages": msgs, "meta": {"file": path.name}}


# --------------------------------------------------------------------------- agent docs
_FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
_H2 = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.M)


def _frontmatter(text: str) -> Dict[str, str]:
    m = _FRONT.match(text)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip().lower()] = v.strip().strip("'\"")
    return out


def _bullets(items: Any) -> str:
    if isinstance(items, (list, tuple)):
        return "\n".join(f"- {str(i).strip()}" for i in items if str(i).strip())
    return str(items or "").strip()


def agent_json_pairs(d: Dict[str, Any], label: str) -> Iterator[List[Dict[str, str]]]:
    """Grounded Q&A from structured agent manifests. Answers quote manifest fields only."""
    name = str(d.get("name") or d.get("role") or d.get("id") or label)
    desc = d.get("description") or d.get("summary")
    if desc:
        yield _msgs(f"What is the {name} agent responsible for?", str(desc))
    for key, q in (
        ("goals", f"What are the goals of the {name} agent?"),
        ("capabilities", f"What capabilities does the {name} agent have?"),
        ("tools_allowed", f"Which tools is the {name} agent allowed to use?"),
        ("constraints", f"What constraints does the {name} agent follow?"),
        ("rules", f"What rules does the {name} agent follow?"),
        ("routing_tags", f"Which kinds of tasks get routed to the {name} agent?"),
    ):
        val = d.get(key)
        if isinstance(val, (list, tuple)) and val:
            yield _msgs(q, _bullets(val))
    sp = d.get("system_prompt") or d.get("instructions") or d.get("prompt")
    if isinstance(sp, str) and len(sp) > 40:
        yield _msgs(f"Give the operating instructions for the {name} agent.", sp)


def agent_md_pairs(text: str, label: str, max_section_chars: int = 2500) -> Iterator[List[Dict[str, str]]]:
    """Grounded Q&A from persona/instruction markdown: one pair per section, answer = section text."""
    fm = _frontmatter(text)
    body = _FRONT.sub("", text, count=1)
    name = fm.get("name") or label
    if fm.get("description"):
        yield _msgs(f"What does the {name} agent do?", fm["description"])
    heads = list(_H2.finditer(body))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        sec = body[h.end() : end].strip()
        if len(sec) < 60:
            continue
        title = re.sub(r"[*_`#]", "", h.group(2)).strip()
        yield _msgs(f"According to the {name} guidance, what is covered under \"{title}\"?", sec[:max_section_chars])


@adapter("agent_docs")
def agent_docs_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """.agentx/, .github/{agents,instructions,prompts}, copilot-instructions.md, agents/ folders."""
    exts = {".agentx", ".json", ".md"}
    for root in _resolve(spec.get("paths", []), ctx["roots"]):
        files = [root] if root.is_file() else sorted(
            p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts and "node_modules" not in p.parts
        )
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            label = f.name.split(".")[0].replace("_", " ").replace("-", " ")
            rel = f"{root.name}/{f.relative_to(root).as_posix()}" if root.is_dir() else f.name
            pairs: Iterable[List[Dict[str, str]]] = ()
            if f.suffix.lower() in {".agentx", ".json"}:
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                items = data if isinstance(data, list) else data.get("agents", [data]) if isinstance(data, dict) else []
                pairs = (p for d in items if isinstance(d, dict) for p in agent_json_pairs(d, label))
            else:
                pairs = agent_md_pairs(text, label)
            for msgs in pairs:
                yield {"messages": msgs, "meta": {"file": rel}}


# --------------------------------------------------------------------------- RackUp shots
_SHOT_ARRAY = re.compile(r"SHOT_CATALOG\s*:\s*[^=]+=\s*(\[.*?\n\]);", re.S)


def load_shot_catalog(path: Path) -> List[Dict[str, Any]]:
    """Load RackUp's SHOT_CATALOG from shot-catalog.ts (via node, offline) or a JSON export."""
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    m = _SHOT_ARRAY.search(path.read_text(encoding="utf-8"))
    node = shutil.which("node")
    if not m or not node:
        raise RuntimeError("shot catalog needs node (or pass a .json export)")
    js = "process.stdout.write(JSON.stringify(" + m.group(1) + "))"
    out = subprocess.run([node, "-e", js], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(out.stdout)


def shot_pairs(s: Dict[str, Any]) -> Iterator[List[Dict[str, str]]]:
    """Coach Q&A built only from catalogue fields (geometry-true: setup/route lines verbatim)."""
    n = s.get("name", s.get("id"))
    if s.get("setup"):
        yield _msgs(f"How do I set up the {n} shot?", _bullets(s["setup"]) + (f"\nObject ball: {s['objectBall']}. Pocket: {s['pocket']}." if s.get("objectBall") else ""))
    if s.get("what") or s.get("why"):
        yield _msgs(f"What is the {n} shot and what does it train?", " ".join(x for x in (s.get("what"), s.get("why")) if x))
    if s.get("tipZone"):
        yield _msgs(
            f"Where do I hit the cue ball for the {n}, and how hard?",
            f"Tip: {s.get('tipZone')} — {s.get('tipDetail', '')}\nEnglish: {s.get('english', '')}\n"
            f"Cue elevation: {s.get('elevation', '')}\nSpeed: {s.get('speed', '')} — {s.get('speedDetail', '')}\nBridge: {s.get('bridge', '')}",
        )
    if s.get("steps"):
        yield _msgs(f"Walk me through the {n} step by step.", "\n".join(f"{i}. {x}" for i, x in enumerate(s["steps"], 1)))
    if s.get("commonMistakes") or s.get("tips"):
        ans = ""
        if s.get("commonMistakes"):
            ans += "Common mistakes:\n" + _bullets(s["commonMistakes"])
        if s.get("tips"):
            ans += ("\n" if ans else "") + "Fixes and tips:\n" + _bullets(s["tips"])
        yield _msgs(f"My {n} keeps missing. What am I doing wrong?", ans)
    if s.get("successLooksLike"):
        yield _msgs(f"How do I know I hit the {n} correctly?", s["successLooksLike"])


@adapter("rackup_shots")
def rackup_shots_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    conv = spec.get("convention")
    for path in _resolve(spec.get("paths", []), ctx["roots"]):
        shots = load_shot_catalog(path)
        for s in shots:
            for msgs in shot_pairs(s):
                if conv:
                    msgs = [{"role": "system", "content": conv}] + msgs
                yield {"messages": msgs, "meta": {"file": path.name, "shot": s.get("id"), "category": s.get("category")}}


# --------------------------------------------------------------------------- big persona dump (filtered)
_PERSONA = re.compile(r"^You are the (?P<name>[^\n]{3,80}?) agent\.\s*\nDescription:\s*(?P<desc>[^\n]+)")
_TABLE_ART = re.compile(r"^(\|\s*)+\|?\s*$", re.M)


@adapter("filtered_text")
def filtered_text_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """The 21.8 MB dataset.jsonl: off unless enabled; keeps only real Q/A turns.

    Drops: rows without an assistant turn, table-art (>``max_table_ratio`` of lines are '|  |'),
    persona boilerplate ("You are the RealAI — X agent" with no answer), very short answers.
    """
    max_ratio = float(spec.get("max_table_ratio", 0.2))
    min_answer = int(spec.get("min_answer_chars", 80))
    for path in _resolve(spec.get("paths", []), ctx["roots"]):
        for obj in iter_jsonl(path):
            msgs = row_to_messages(obj)
            if not msgs and spec.get("persona_pairs", True):
                m = _PERSONA.match(str(obj.get("text") or ""))
                if m and len(m.group("desc")) >= min_answer:
                    msgs = _msgs(f"What does the {m.group('name').strip()} agent do?", m.group("desc"))
            if not msgs:
                continue
            ans = " ".join(m["content"] for m in msgs if m["role"] == "assistant")
            lines = [ln for ln in ans.splitlines() if ln.strip()] or [""]
            if len(ans) < min_answer or sum(bool(_TABLE_ART.match(ln)) for ln in lines) / len(lines) > max_ratio:
                continue
            yield {"messages": msgs, "meta": {"file": path.name}}


@adapter("ide_chat")
def ide_chat_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """Other-vendor IDE chat logs. Excluded unless config allow_vendor_chat=true (licence/terms)."""
    if not ctx.get("allow_vendor_chat"):
        return
    yield from jsonl_source(spec, ctx)
