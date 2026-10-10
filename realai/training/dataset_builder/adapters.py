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
        excl = [str(x) for x in spec.get("exclude", [])]
        files = [root] if root.is_file() else sorted(
            p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts and "node_modules" not in p.parts
        )
        files = [f for f in files if not any(f.match(x) for x in excl)]
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
    # Script via stdin: Windows caps command lines (~32K), the catalogue is larger.
    out = subprocess.run([node, "-"], input=js, capture_output=True, text=True, encoding="utf-8",
                         timeout=60, check=True)
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


# --------------------------------------------------------------------------- SOTD shot maps (geometry)
_MAPS_ARRAY = re.compile(r"SOTD_SHOT_MAPS\s*:\s*[^=]+=\s*(\[.*?\n\]);", re.S)
DIAMOND_IN = 12.5  # 9 ft table: 100 x 50 in playing surface, 8 x 4 diamonds


def load_sotd_maps(path: Path) -> List[Dict[str, Any]]:
    """SOTD_SHOT_MAPS from sotd-shot-maps.ts (array body is JSON) or a .json export."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    m = _MAPS_ARRAY.search(text)
    if not m:
        raise RuntimeError("SOTD_SHOT_MAPS array not found")
    body = re.sub(r",(\s*[\]}])", r"\1", m.group(1))
    return json.loads(body)


def _fmt_pt(p: Dict[str, float]) -> str:
    x, y = float(p["x"]), float(p["y"])
    return f"x={x:g}, y={y:g} ({x / DIAMOND_IN:.1f} diamonds from the head rail, {y / DIAMOND_IN:.1f} from the y=0 long rail)"


def _dist(a, b) -> float:
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def _seg_point_dist(p, a, b) -> float:
    ax, ay, bx, by, px, py = a["x"], a["y"], b["x"], b["y"], p["x"], p["y"]
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return ((ax + t * dx - px) ** 2 + (ay + t * dy - py) ** 2) ** 0.5


def _angle(u, v) -> Optional[float]:
    import math

    nu, nv = math.hypot(*u), math.hypot(*v)
    if nu == 0 or nv == 0:
        return None
    c = max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / (nu * nv)))
    return math.degrees(math.acos(c))


_POCKETS = {(0, 0): "head corner on the y=0 rail", (0, 50): "head corner on the y=50 rail",
            (100, 0): "foot corner on the y=0 rail", (100, 50): "foot corner on the y=50 rail",
            (50, 0): "side pocket on the y=0 rail", (50, 50): "side pocket on the y=50 rail"}
_KIND = {"ground": "cue ball rolls", "airborne": "cue ball is airborne (jump hop)", "object": "object ball travels",
         "cue_after": "cue ball continues"}
MAP_FRAME = ("Shot-map frame: 9-foot table, x = 0 at the head rail to 100 at the foot rail, y = 0 to 50 between "
             "the long rails, units are inches; 1 diamond = 12.5 in.")


def map_facts(m: Dict[str, Any], pocket_names: Optional[Dict[str, str]] = None,
              routes: Optional[Dict[str, str]] = None) -> Iterator[List[Dict[str, str]]]:
    """Q&A computed only from the map's own coordinates (no invented numbers)."""
    n = m.get("name", m.get("id"))
    balls = m.get("object_ball_positions") or []
    cb = m.get("cue_ball_start")
    if cb and balls:
        lines = [f"Cue ball: {_fmt_pt(cb)}."]
        for b in balls:
            lines.append(f"{b['ballId']}-ball ({b.get('role', 'object')}): {_fmt_pt(b)}.")
        yield _msgs(f"Using the shot map, where are the balls for the {n}?", "\n".join(lines))
    segs = m.get("intended_path") or []
    if segs:
        blockers = [b for b in balls if b.get("role") == "blocker"]
        steps = []
        for i, s in enumerate(segs, 1):
            line = f"{i}. {_KIND.get(s.get('kind'), 'path leg') if s.get('kind') else 'path leg'} from ({s['from']['x']:g}, {s['from']['y']:g}) to ({s['to']['x']:g}, {s['to']['y']:g}), {_dist(s['from'], s['to']):.1f} in"
            if s.get("kind") == "airborne":
                over = [b for b in blockers if _seg_point_dist(b, s["from"], s["to"]) <= 2.25]
                if over:
                    line += ", passing over the " + " and ".join(f"{b['ballId']}-ball" for b in over)
            steps.append(line + ".")
        pt = m.get("pocket_target")
        if pt and m.get("shot_goal", "pocket") == "pocket":
            key = (int(round(pt["x"])), int(round(pt["y"])))
            steps.append("Target pocket: " + ((pocket_names or {}).get(m.get("id")) or _POCKETS.get(key, f"({pt['x']:g}, {pt['y']:g})")) + ".")
        if (routes or {}).get(m.get("id")):
            steps.append(routes[m["id"]])
        yield _msgs(f"Trace the path of the {n} on the shot map.", "\n".join(steps))
        air = [s for s in segs if s.get("kind") == "airborne"]
        if air:
            facts = []
            for s in air:
                over = [b for b in blockers if _seg_point_dist(b, s["from"], s["to"]) <= 2.25]
                facts.append(
                    f"Takeoff ({s['from']['x']:g}, {s['from']['y']:g}), landing ({s['to']['x']:g}, {s['to']['y']:g}): "
                    f"a straight hop of {_dist(s['from'], s['to']):.1f} in"
                    + (", directly over the " + " and ".join(f"{b['ballId']}-ball" for b in over) if over else "")
                    + "."
                )
            yield _msgs(f"What does the cue ball jump over in the {n}, and how long is the hop?", "\n".join(facts))
        # Cut angle from drawn paths: last cue segment into the object ball vs object segment to pocket.
        obj = next((s for s in segs if s.get("kind") == "object"), None)
        if obj:
            into = [s for s in segs if s.get("kind") in {"ground", "airborne"} and _dist(s["to"], obj["from"]) < 0.6]
            if into:
                s = into[-1]
                ang = _angle((s["to"]["x"] - s["from"]["x"], s["to"]["y"] - s["from"]["y"]),
                             (obj["to"]["x"] - obj["from"]["x"], obj["to"]["y"] - obj["from"]["y"]))
                if ang is not None:
                    yield _msgs(
                        f"How thin is the cut on the {n}?",
                        f"From the drawn paths, the cue ball arrives at about {ang:.0f} degrees to the object ball's line to the pocket "
                        f"({'nearly straight-in' if ang < 10 else 'a thin cut' if ang > 45 else 'a moderate cut'}).",
                    )
    rest = next((z for z in m.get("landing_zones") or [] if z.get("label") == "cb_rest"), None)
    if rest:
        yield _msgs(f"Where should the cue ball finish on the {n}?", f"Cue ball rest zone on the map: {_fmt_pt(rest)}.")


@adapter("sotd_maps")
def sotd_maps_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    pocket_names: Dict[str, str] = {}
    routes: Dict[str, str] = {}
    for cat in _resolve(spec.get("catalog_paths", []), ctx["roots"]):
        try:
            shots = load_shot_catalog(cat)
        except Exception:
            continue
        pocket_names.update({s["id"]: s["pocket"] for s in shots if s.get("pocket")})
        routes.update({s["id"]: r for s in shots for r in s.get("setup", []) if str(r).startswith("Route:")})
    for path in _resolve(spec.get("paths", []), ctx["roots"]):
        for m in load_sotd_maps(path):
            for msgs in map_facts(m, pocket_names, routes):
                yield {"messages": [{"role": "system", "content": MAP_FRAME}] + msgs,
                       "meta": {"file": path.name, "shot": m.get("id"), "category": m.get("category")}}


# --------------------------------------------------------------------------- RackUp rules from code
@adapter("rackup_rules")
def rackup_rules_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """Pyramid + league/ROC rules read from the live rackup_coach modules (values from code only)."""
    from realai.plugins.rackup_coach import leagues, pyramid
    from realai.plugins.rackup_coach.abilities import league_validate

    mx = pyramid.pyramid_matrix()
    for row in mx["skill_matrix"]:
        sk = row["skill_level"]
        yield {"messages": _msgs(f"How many points to win RackUp Pyramid at {sk} level?",
                                 f"{row['7ft_10ball_points']} on a 7-foot table (10-ball rack), {row['9ft_15ball_points']} on a 9-foot table (15-ball rack)."),
               "meta": {"rule": "pyramid_points"}}
        yield {"messages": _msgs(f"Is call-shot required in Pyramid at {sk} level?",
                                 {"no": "No, call-shot is not required.", "optional": "Call-shot is optional.", "yes": "Yes, call-shot is on."}[row["call_shot"]]),
               "meta": {"rule": "pyramid_call_shot"}}
        yield {"messages": _msgs(f"What rating weight does a {sk} Pyramid result carry?", f"A {sk} Pyramid result is weighted {row['rating_weight']} in rating updates."),
               "meta": {"rule": "pyramid_weight"}}
        for table in ("7ft", "9ft"):
            cfg = pyramid.resolve_pyramid(table_size=table, skill_level=sk)
            tips = pyramid.classical_mindset_tips(cfg)
            yield {"messages": _msgs(f"Give me Pyramid strategy tips for a {sk} player on a {table} table.", _bullets(tips)),
                   "meta": {"rule": "pyramid_tips"}}
    sc = mx["scoring"]
    yield {"messages": _msgs("How is RackUp Pyramid scored?",
                             f"Classical scoring: a pocketed ball scores its number, except the 1-ball, which scores {sc['ball_1']}. "
                             f"Designated cue ball only. First to the target score wins. A 7-foot table uses a {mx['table_to_rack']['7ft']}-ball rack; a 9-foot table uses a {mx['table_to_rack']['9ft']}-ball rack."),
           "meta": {"rule": "pyramid_scoring"}}
    for rack in (10, 15):
        yield {"messages": _msgs(f"How many points are in a full {rack}-ball Pyramid rack?", f"{pyramid.max_rack_points(rack)} points."),
               "meta": {"rule": "pyramid_rack_points"}}
    # Display bands: derive ranges by evaluating the code.
    bands, prev, start = [], None, leagues.RACKUP_MIN
    for r in range(leagues.RACKUP_MIN, leagues.RACKUP_MAX + 1):
        b = leagues.display_band(r)
        if b != prev and prev is not None:
            bands.append(f"{prev}: {start}–{r - 1}")
            start = r
        prev = b
    bands.append(f"{prev}: {start}–{leagues.RACKUP_MAX}")
    yield {"messages": _msgs("What are the ROC rating display bands?",
                             "\n".join(bands) + f"\nChips read like \"{leagues.format_rating_chip(547)}\". Bands are labels only; they do not drive matchmaking or rating updates."),
           "meta": {"rule": "roc_bands"}}
    for sl, roc in sorted(leagues.APA_TO_ROC.items()):
        yield {"messages": _msgs(f"What ROC rating does an APA skill level {sl} start near?",
                                 f"About {roc} on the ROC continuous scale (an onboarding estimate, not an official handicap)."),
               "meta": {"rule": "apa_to_roc"}}
    yield {"messages": _msgs("What ROC rating does a new player start at?", f"{leagues.DEFAULT_SEED}, on a scale clamped to {leagues.RACKUP_MIN}–{leagues.RACKUP_MAX}."),
           "meta": {"rule": "roc_seed"}}
    doc = (league_validate.__doc__ or "").strip()
    if doc:
        yield {"messages": _msgs("In what order is a league or ROC match finalized?", doc), "meta": {"rule": "league_finalize"}}
    vdoc = (league_validate.validate_league_submission.__doc__ or "").strip()
    if vdoc:
        yield {"messages": _msgs("What does league_validate need in its payload?", vdoc), "meta": {"rule": "league_payload"}}


# --------------------------------------------------------------------------- hive run dirs (req/resp pairs)
_WORD = re.compile(r"[A-Za-z0-9_./:\-]{5,}")


def grounding_overlap(user: str, answer: str) -> float:
    """Share of distinctive GROUNDING terms that the answer actually uses."""
    g = user.split("GROUNDING", 1)[-1]
    terms = {t.lower().strip(".:,") for t in _WORD.findall(g)}
    terms = {t for t in terms if t not in {"answer", "which", "there", "their", "should"}}
    if not terms:
        return 1.0
    a = answer.lower()
    return sum(1 for t in terms if t in a) / len(terms)


@adapter("hive_run_dir")
def hive_run_dir_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """N_*_req.json + N_*_resp.json captured hive turns. Quality gate: grounding overlap >= min_grounding."""
    min_g = float(spec.get("min_grounding", 0.3))
    for d in _resolve(spec.get("paths", []), ctx["roots"]):
        for req in sorted(d.glob("*_req.json")):
            resp = req.with_name(req.name.replace("_req.json", "_resp.json"))
            if not resp.is_file():
                continue
            try:
                rq = json.loads(req.read_text(encoding="utf-8-sig"))
                rs = json.loads(resp.read_text(encoding="utf-8-sig"))
                ans = rs["choices"][0]["message"]["content"]
            except Exception:
                continue
            msgs = [m for m in rq.get("messages", []) if m.get("role") in {"system", "user"}] + [{"role": "assistant", "content": ans}]
            user = " ".join(m["content"] for m in msgs if m["role"] == "user")
            score = grounding_overlap(user, ans)
            if score < min_g:
                ctx.setdefault("_gate_drops", []).append({"file": req.name, "grounding": round(score, 2)})
                continue
            yield {"messages": row_to_messages({"messages": msgs}) or msgs, "meta": {"file": req.name, "grounding": round(score, 2)}}


from . import adapters_extra  # noqa: E402,F401  (registers chess_stockfish, device_profiles)
