"""Infer one operational Hat for a Natural Mode prompt.

Hats adjust reply shape and tool bias. They are not a Core-desk control
and there is no fifth hat.

Precedence (first decisive match):

1. **Patch** — a clear write / patch / generate / fix / propose-a-change
   verb. Wins over Hive and Smoke ("fix the hive health check",
   "patch the endpoint then smoke it").
2. **Inspect** — read-only inspect (read, grep, what's in, list files,
   a named path) when no Patch verb and no Smoke *action* verb.
   This is the tie-break for ambiguous inspect ("read the smoke test",
   "grep agents", "what's in v3_orchestrator.py").
3. **Smoke** — deploy, smoke, test, or HTTP/API validation. Smoke is
   the HTTP/smoke hat only. It is not the RackUp product and not Coach.
4. **Hive** — system state, health, orchestration, agents, learn queue.
5. **Inspect** — anything still ambiguous, including empty prompts.

``rackup coach`` / ``atomicfizz coach`` do not select Smoke unless a
real deploy/smoke/HTTP verb is also present. Coach stays a plugin.
A bare RackUp product mention is not a Smoke ask.
"""
from __future__ import annotations

import re

HATS = ("Hive", "Inspect", "Patch", "Smoke")

_CANON = {
    "hive": "Hive",
    "inspect": "Inspect",
    "patch": "Patch",
    "smoke": "Smoke",
}

# Clear code-change verbs. ``propose`` counts only when it is a change,
# so "propose next steps" stays free for Hive / Inspect.
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
# so "audit console.html" stays Inspect. "audit this repo" does not.
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
# to contain the word smoke. The RackUp product name is not a verb.
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
    r"\btests?\s+against\b"
    r")"
)

_SMOKE_NOUN_RE = re.compile(
    r"(?i)(\bsmoke\b|\bendpoint\b|\bcurl\b|\bhttps?://)"
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
    "Inspect": (
        "workspace_read, grep, scan. Read a named path before quoting it."
    ),
    "Patch": (
        "write, patch, or propose. Propose is not a write. "
        "Never say LANDED or shipped unless a write tool succeeded."
    ),
    "Smoke": (
        "smoke, execute, and HTTP endpoint checks. "
        "HTTP/smoke only. This hat is not the RackUp product."
    ),
}


def normalize_hat(value: str) -> str:
    """Map Hive, Inspect, Patch, and Smoke onto themselves.

    Anything else, including the retired labels One-tree, Builder, and
    RackUp, is Inspect. Those old strings are not aliases.
    """
    key = " ".join(str(value or "").strip().lower().replace("_", " ").split())
    if not key:
        return "Inspect"
    if key in _CANON:
        return _CANON[key]
    # Already-canonical spellings survive a case fold via _CANON.
    return "Inspect"


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
    """Return Hive, Inspect, Patch, or Smoke for ``prompt``."""
    text = (prompt or "").strip()
    if not text:
        return "Inspect"
    # Grounding appends tool dumps after a blank line. Score the ask only.
    text = text.split("\n\n", 1)[0]
    patch = bool(_PATCH_RE.search(text))
    inspect = bool(_INSPECT_RE.search(text) or _NAMED_FILE_RE.search(text))
    hive = bool(_HIVE_RE.search(text))
    smoke_action, smoke_any = _smoke_flags(text)

    if patch:
        return "Patch"
    # Ambiguous read-only inspect beats Hive nouns and Smoke nouns.
    if inspect and not smoke_action:
        return "Inspect"
    if smoke_action or (smoke_any and not inspect):
        return "Smoke"
    if hive:
        return "Hive"
    return "Inspect"


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
