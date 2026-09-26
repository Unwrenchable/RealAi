"""Infer one operational Hat for a Natural Mode prompt.

Hats adjust reply shape and tool bias. They are not a Core-desk control
and there is no fifth hat.

Precedence (first decisive match):

1. **Builder** — a clear write / patch / generate / fix / propose-a-change
   verb. Wins over Hive and RackUp ("fix the hive health check",
   "patch the endpoint then smoke it").
2. **One-tree** — read-only inspect (read, grep, what's in, list files,
   a named path) when no Builder verb and no RackUp *action* verb.
   This is the tie-break for ambiguous inspect ("read the smoke test",
   "grep agents", "what's in v3_orchestrator.py").
3. **RackUp** — deploy, smoke, test, or HTTP/API validation. RackUp is
   the hive HTTP client, not a second product tree, and not Coach.
4. **Hive** — system state, health, orchestration, agents, learn queue.
5. **One-tree** — anything still ambiguous, including empty prompts.

``rackup coach`` / ``atomicfizz coach`` do not select RackUp unless a
real deploy/smoke/HTTP verb is also present. Coach stays a plugin.
"""
from __future__ import annotations

import re

HATS = ("Hive", "One-tree", "Builder", "RackUp")

_CANON = {
    "hive": "Hive",
    "one-tree": "One-tree",
    "onetree": "One-tree",
    "one tree": "One-tree",
    "builder": "Builder",
    "rackup": "RackUp",
    "rack-up": "RackUp",
    "rack up": "RackUp",
}

# Clear code-change verbs. ``propose`` counts only when it is a change,
# so "propose next steps" stays free for Hive / One-tree.
_BUILDER_RE = re.compile(
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
# so "audit console.html" stays One-tree. "audit this repo" does not.
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

# Verbs that mean "hit the hive over HTTP", not a filename that happens
# to contain the word smoke.
_RACK_ACTION_RE = re.compile(
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
    r"\btests?\s+against\b"
    r")"
)

_RACK_NOUN_RE = re.compile(
    r"(?i)(\bsmoke\b|\bendpoint\b|\brackup\b|\bcurl\b|\bhttps?://)"
)

_COACH_RE = re.compile(
    r"(?i)\b(rackup_coach|atomicfizz_coach|rackup\s+coach|atomicfizz\s+coach|"
    r"pyramid coach|practice plan)\b"
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
    "One-tree": (
        "workspace_read, grep, scan. Read a named path before quoting it."
    ),
    "Builder": (
        "write, patch, or propose. Propose is not a write. "
        "Never say LANDED or shipped unless a write tool succeeded."
    ),
    "RackUp": (
        "smoke, execute, and HTTP endpoint checks. "
        "RackUp is the HTTP client for this hive."
    ),
}


def normalize_hat(value: str) -> str:
    """Map aliases onto the four hats. Anything else is One-tree."""
    key = " ".join(str(value or "").strip().lower().replace("_", " ").split())
    if not key:
        return "One-tree"
    if key in _CANON:
        return _CANON[key]
    # Already-canonical spellings survive a case fold via _CANON.
    return "One-tree"


def _rack_flags(text: str) -> tuple[bool, bool]:
    """Return ``(action, any)`` after stripping Coach phrasing.

    Coach mentions drop the word ``rackup`` so a practice-plan ask is not
    an HTTP validation. A leftover deploy/smoke/HTTP verb still counts.
    """
    sample = text or ""
    if _COACH_RE.search(sample):
        sample = _COACH_RE.sub(" ", sample)
        sample = re.sub(r"(?i)\brackup\b", " ", sample)
    action = bool(_RACK_ACTION_RE.search(sample))
    noun = action or bool(_RACK_NOUN_RE.search(sample))
    return action, noun


def infer_hat(prompt: str) -> str:
    """Return Hive, One-tree, Builder, or RackUp for ``prompt``."""
    text = (prompt or "").strip()
    if not text:
        return "One-tree"
    # Grounding appends tool dumps after a blank line. Score the ask only.
    text = text.split("\n\n", 1)[0]
    builder = bool(_BUILDER_RE.search(text))
    inspect = bool(_INSPECT_RE.search(text) or _NAMED_FILE_RE.search(text))
    hive = bool(_HIVE_RE.search(text))
    rack_action, rack_any = _rack_flags(text)

    if builder:
        return "Builder"
    # Ambiguous read-only inspect beats Hive nouns and RackUp nouns.
    if inspect and not rack_action:
        return "One-tree"
    if rack_action or (rack_any and not inspect):
        return "RackUp"
    if hive:
        return "Hive"
    return "One-tree"


def hat_turn_prefix(hat: str) -> str:
    """Short system/grounding block for the inferred hat. One turn only."""
    name = normalize_hat(hat)
    bias = HAT_TOOL_BIAS[name]
    return (
        f"Mode Active: {name}\n"
        f"Tool bias this turn: {bias}\n"
        "Lead with Mode Active, Action Taken (1-2 sentences), "
        "Key Results (2-3 bullets), Next Recommended Step. "
        "Then Summary / What changed / Verify / Next. "
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
