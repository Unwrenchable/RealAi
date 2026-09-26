"""Infer one ROLE hat and one job class for a Natural Mode prompt.

Hats adjust reply shape and tool bias. They are not a Core-desk control,
not pills, and not a switcher. There is no fifth hat.

ROLE names (the only strings that belong after ``Mode:``):

- **Hive** — health, topology, learn queue, agents, observability.
- **One-Tree** — repo and workspace read, architecture, grep, file tree.
  Live label that used to say Inspect.
- **Builder** — write, patch, refactor, propose diffs.
  Live label that used to say Patch.
- **RackUp** — HTTP-only product, API, coach, and smoke checks.
  Live label that used to say Smoke. Never vendor RealAI into RackUp.

Precedence (first decisive match):

1. **Builder** — a clear write / patch / generate / fix / propose-a-change
   verb. Wins over Hive and RackUp ("fix the hive health check",
   "patch the endpoint then smoke it").
2. **One-Tree** — read-only inspect (read, grep, what's in, list files,
   a named path) when no Builder verb and no RackUp *action* verb.
   Tie-break for ambiguous reads ("read the smoke test", "grep agents").
3. **RackUp** — deploy, smoke, test, or HTTP/API validation, including a
   RackUp product check that is itself an HTTP call. Not a practice plan.
4. **Hive** — system state, health, orchestration, agents, learn queue.
5. **One-Tree** — anything still ambiguous, including empty prompts.

``rackup coach`` / ``atomicfizz coach`` do not select RackUp unless a
real deploy/smoke/HTTP verb is also present. Coach stays a plugin.
A bare RackUp product mention is not an HTTP check.

Job class (separate from the hat):

- **EXECUTE** — one concrete act.
- **PHASE** — open, multi-step, or architectural.
- **MIXED** — both: a short phase, then one execute next step.
"""
from __future__ import annotations

import re

HATS = ("Hive", "One-Tree", "Builder", "RackUp")
JOBS = ("EXECUTE", "PHASE", "MIXED")

# Display map. Old live names are aliases of the ROLE names, not a fifth hat.
_CANON = {
    "hive": "Hive",
    "inspect": "One-Tree",
    "one tree": "One-Tree",
    "onetree": "One-Tree",
    "patch": "Builder",
    "builder": "Builder",
    "smoke": "RackUp",
    "rackup": "RackUp",
    "rack up": "RackUp",
}

# Clear code-change verbs. ``propose`` counts only when it is a change,
# so "propose next steps" stays free for Hive / One-Tree.
_PATCH_RE = re.compile(
    r"(?i)("
    r"\b(patch|refactor|implement|overwrite|regenerate)\b|"
    r"\bgenerate\b|"
    r"\bfix\b|"
    r"\b(create|make|add|write|save)\b.{0,60}\b(file|module|function|class|patch|handler)\b|"
    r"\b(update|edit|modify)\b.{0,40}\b(file|code|function|module)\b|"
    r"\bpropose\b.{0,48}\b(change|patch|fix|edit|diff|css|refactor)\b"
    r")"
)

_INSPECT_RE = re.compile(
    r"(?i)("
    r"\b(read|open|quote|grep|scan)\b|"
    r"what'?s?\s+in\b|"
    r"\bcontents?\s+of\b|"
    r"\blook\s+(at|in|through)\b|"
    r"\bshow\s+(me\s+)?(the\s+)?(file|code|repo|workspace|directory)\b|"
    r"\blist\s+(the\s+)?(repo|workspace|files|directory|dir)\b|"
    r"\bwhere\s+(is|are)\b|"
    r"\b(codebase|this repo|the repo)\b"
    r")"
)

# A named source file is a read-only inspect cue even without a read verb,
# so "audit console.html" stays One-Tree. "audit this repo" does not.
_NAMED_FILE_RE = re.compile(
    r"(?i)(?<![\w./-])(?:[\w.-]+[\\/])+[\w.-]+\.\w+"
    r"|(?<![\w./-])[\w.-]+\.(?:py|html|md|json|ts|tsx|js|css|yml|yaml|toml)\b"
)

_HIVE_RE = re.compile(
    r"(?i)("
    r"\bhive\b|"
    r"\borchestrat\w*\b|"
    r"\bagents?\b|"
    r"\blearn\s+queue\b|"
    r"\blearn\s+status\b|"
    r"\b(system|hive)\s+(state|health|status)\b|"
    r"\bhealth\s+check\b|"
    r"\bwhat'?s\s+broken\b|"
    r"\bwhats\s+broken\b|"
    r"\bself[- ]?heal\b|"
    r"\bdoctor\b|"
    r"\btopology\b|"
    r"\bobservability\b|"
    r"\boverseer\b|"
    r"\bmulti[- ]agent\b|"
    r"\baudit\b"
    r")"
)

# Verbs that mean "hit a product or the hive over HTTP". The RackUp product
# name alone is not a verb. A RackUp API/health check is.
_SMOKE_ACTION_RE = re.compile(
    r"(?i)("
    r"\b(deploy|redeploy|rollout)\b|"
    r"\b(run|do|start|kick)\s+(a\s+|the\s+)?smoke\b|"
    r"\bsmoke\s+(the|this|hive|api|endpoint|health|it|get|post)\b|"
    r"\bsmoke\s+test\s+(the|hive|api|endpoint)\b|"
    r"\bcurl\b|"
    r"\b(?:GET|POST|PUT|DELETE|HEAD)\s+/|"
    r"\bhttps?://|"
    r"\b(?:hit|ping|validate)\s+(?:the\s+)?(?:api|endpoint|health)\b|"
    r"\b(?:run|execute)\s+(?:the\s+)?(?:tests?|suite)\b|"
    r"\b(?:unit|integration|e2e)\s+tests?\b|"
    r"\bapi\s+(?:check|validation|smoke|test)s?\b|"
    r"\bendpoint\s+(?:check|test|smoke)\b|"
    r"\btest\s+(?:the\s+)?(?:api|endpoint|hive|health|deploy)\b|"
    r"\btests?\s+against\b|"
    r"\brackup\b.{0,48}\b(?:api|endpoint|health|https?)\b|"
    r"\b(?:check|hit|ping|validate)\b.{0,32}\brackup\b"
    r")"
)

_SMOKE_NOUN_RE = re.compile(
    r"(?i)(\bsmoke\b|\bendpoint\b|\bcurl\b|\bhttps?://)"
)

_COACH_RE = re.compile(
    r"(?i)\b(rackup_coach|atomicfizz_coach|rackup\s+coach|atomicfizz\s+coach|"
    r"pyramid coach|practice plan)\b"
)

# Open / multi-step / architectural. A bare "architecture" read stays EXECUTE.
_PHASE_RE = re.compile(
    r"(?i)("
    r"\b(redesign|overhaul|roadmap|strategy)\b|"
    r"\bmigrat\w*\b|"
    r"\barchitectural\b|"
    r"\b(plan|design)\b.{0,48}\b(how|out|migration|split|refactor|phases?|system)\b|"
    r"\bhow should (we|i)\b|"
    r"\bmulti[- ]step\b|"
    r"\bphases?\b|"
    r"\bend[- ]to[- ]end\b|"
    r"\bbreak (this|it) down\b|"
    r"\bwhere do we start\b|"
    r"\bfrom scratch\b"
    r")"
)

_EXECUTE_RE = re.compile(
    r"(?i)("
    r"\b(read|open|quote|grep|scan|fix|patch|refactor|implement|smoke|curl|"
    r"write|create|list|deploy|edit|modify)\b|"
    r"\b(?:GET|POST|PUT|DELETE|HEAD)\s+/|"
    r"what'?s?\s+(in|the|broken)\b|"
    r"\bhealth\b|"
    r"\bendpoint\b"
    r")"
)

_TRANSPORT_RE = re.compile(
    r"(?i)(connection refused|timed out|timeout|urlerror|unreachable|"
    r"failed to fetch|econnrefused|errno|service unavailable|"
    r"name or service|network is unreachable|connection reset|"
    r"winerror|nodename nor servname)"
)

HAT_TOOL_BIAS = {
    "Hive": (
        "diagnostics, topology, observability "
        "(doctor, agents, hive status). GET /v1/agents stays the live hive."
    ),
    "One-Tree": (
        "workspace_read, grep, scan. Read a named path before quoting it."
    ),
    "Builder": (
        "write, patch, or propose. Propose is not a write. "
        "Never say LANDED or shipped unless a write tool succeeded."
    ),
    "RackUp": (
        "HTTP-only product, API, coach, and smoke checks. "
        "Never vendor RealAI into RackUp."
    ),
}

_JOB_SHAPE = {
    "EXECUTE": (
        "Job: EXECUTE. Reply shape: Mode / Action / Results (2-3 facts) / Next. "
        "One concrete act. No roadmap."
    ),
    "PHASE": (
        "Job: PHASE. Reply shape: Mode / Goal / Now / Then. "
        "Then uses 2-4 of See, Change, Prove, Keep. "
        "Blockers only if a real blocker exists. No 12-item roadmap."
    ),
    "MIXED": (
        "Job: MIXED. Reply shape: a short phase (Mode / Goal / Now / one Then line) "
        "then one EXECUTE next step (Action / Results / Next). "
        "No 12-item roadmap."
    ),
}


def normalize_hat(value: str) -> str:
    """Map a hat string onto Hive, One-Tree, Builder, or RackUp.

    Inspect, Patch, and Smoke are the previous live labels. They display
    as One-Tree, Builder, and RackUp. Anything else is One-Tree.
    """
    key = " ".join(
        str(value or "").strip().lower().replace("_", " ").replace("-", " ").split()
    )
    if not key:
        return "One-Tree"
    if key in _CANON:
        return _CANON[key]
    return "One-Tree"


def normalize_job(value: str) -> str:
    """Map a job string onto EXECUTE, PHASE, or MIXED. Default EXECUTE."""
    key = " ".join(str(value or "").strip().upper().split())
    if key in JOBS:
        return key
    return "EXECUTE"


def _smoke_flags(text: str) -> tuple[bool, bool]:
    """Return ``(action, any)`` after stripping Coach phrasing.

    Coach mentions drop the word ``rackup`` so a practice-plan ask is not
    an HTTP validation. A leftover deploy/smoke/HTTP verb still counts.
    The RackUp product name alone is not a smoke noun.
    """
    sample = text or ""
    if _COACH_RE.search(sample):
        sample = _COACH_RE.sub(" ", sample)
        sample = re.sub(r"(?i)\brackup\b", " ", sample)
    action = bool(_SMOKE_ACTION_RE.search(sample))
    noun = action or bool(_SMOKE_NOUN_RE.search(sample))
    return action, noun


def infer_hat(prompt: str) -> str:
    """Return Hive, One-Tree, Builder, or RackUp for ``prompt``."""
    text = (prompt or "").strip()
    if not text:
        return "One-Tree"
    # Grounding appends tool dumps after a blank line. Score the ask only.
    text = text.split("\n\n", 1)[0]
    patch = bool(_PATCH_RE.search(text))
    inspect = bool(_INSPECT_RE.search(text) or _NAMED_FILE_RE.search(text))
    hive = bool(_HIVE_RE.search(text))
    smoke_action, smoke_any = _smoke_flags(text)

    if patch:
        return "Builder"
    # Ambiguous read-only inspect beats Hive nouns and RackUp nouns.
    if inspect and not smoke_action:
        return "One-Tree"
    if smoke_action or (smoke_any and not inspect):
        return "RackUp"
    if hive:
        return "Hive"
    return "One-Tree"


def infer_job_class(prompt: str) -> str:
    """Return EXECUTE, PHASE, or MIXED for ``prompt``.

    A single concrete act is EXECUTE. An open or architectural ask is
    PHASE. Both together are MIXED: a short phase, then one execute step.
    Empty and vague prompts stay EXECUTE so the reply does not grow a roadmap.
    """
    text = (prompt or "").strip()
    if not text:
        return "EXECUTE"
    text = text.split("\n\n", 1)[0]
    phase = bool(_PHASE_RE.search(text))
    execute = bool(_EXECUTE_RE.search(text))
    if phase and execute:
        return "MIXED"
    if phase:
        return "PHASE"
    return "EXECUTE"


def hat_turn_prefix(hat: str, job: str = "EXECUTE") -> str:
    """Short system/grounding block for the inferred hat. One turn only."""
    name = normalize_hat(hat)
    kind = normalize_job(job)
    bias = HAT_TOOL_BIAS[name]
    return (
        f"Mode: {name}\n"
        f"Tool bias this turn: {bias}\n"
        f"{_JOB_SHAPE[kind]} "
        "Keep raw JSON and stack traces in a folded diagnostic. "
        "If a service is down, say Service Unavailable and how to retry."
    )


def raw_diagnostic_appendix(payload: str, *, limit: int = 1200) -> str:
    """Fold a raw payload so the main reply stays a card.

    Console renders this ``<details>`` block when it sees the summary
    label. Other clients show it as a labeled appendix.
    """
    body = (payload or "").strip()
    if not body:
        return ""
    if len(body) > limit:
        body = body[: limit - 1].rstrip() + "..."
    return (
        "\n<details><summary>View raw diagnostic payload</summary>\n"
        + body
        + "\n</details>"
    )


def service_down_visible(detail: str) -> str:
    """Operator-facing line for a transport failure. Raw text stays folded."""
    one = " ".join(str(detail or "").split())
    if not one:
        return "Service Unavailable. Retry in a moment."
    if _TRANSPORT_RE.search(one):
        return "Service Unavailable. Retry in a moment."
    return one
