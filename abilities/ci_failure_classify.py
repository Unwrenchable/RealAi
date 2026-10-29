"""ci_failure_classify: read-only, pure-function CI failure classifier.

Reads a CI log excerpt (a string you already have) and returns one of

    stale-branch | lockfile-conflict | test-failure | env-missing | unknown

plus a next step. No network, no file writes, no re-runs. Rules are plain regexes checked in a
fixed priority order; the result names the rule that matched, never the log text.

Call:  POST /v1/tools/execute {"name": "ci_failure_classify", "arguments": {"log": "..."}}
       or abilities.ci_failure_classify.run(context={"log": "..."}) in-process.
Optional input: branch_behind (bool) when the PR's mergeStateStatus is BEHIND/DIRTY.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

ABILITY = {
    "id": "ci_failure_classify",
    "name": "ci_failure_classify",
    "type": "ability",
    "status": "LIVE",
    "source": "RealAI hive: recurring bot CI-fix work",
    "dest": "abilities/ci_failure_classify.py",
    "capabilities": ["ci_failure_classify", "ci_triage", "read_only"],
    "secrets_policy": "none",
}

MAX_LOG_CHARS = 200_000
CLASSES = ("stale-branch", "lockfile-conflict", "test-failure", "env-missing", "unknown")

# (classification, rule id, regex, next step) in priority order.
_RULES: List[Tuple[str, str, "re.Pattern[str]", str]] = [
    ("lockfile-conflict", "pnpm_outdated_lockfile", re.compile(r"ERR_PNPM_OUTDATED_LOCKFILE|frozen-lockfile.{0,80}(?:cannot|not up to date)|lockfile.{0,40}not up to date", re.I | re.S),
     "regenerate the lockfile locally with the same package manager version as CI, commit only the lockfile, push"),
    ("lockfile-conflict", "npm_ci_out_of_sync", re.compile(r"npm ci.{0,80}(?:in sync|lock file)|package-lock\.json.{0,60}(?:out of sync|not in sync)", re.I | re.S),
     "run the package manager install locally to refresh package-lock.json, commit the lockfile, push"),
    ("lockfile-conflict", "lockfile_merge_markers", re.compile(r"CONFLICT \(content\).{0,80}(?:pnpm-lock|package-lock|yarn\.lock|poetry\.lock)|<{7} .{0,200}?(?:lock)", re.I | re.S),
     "merge the base branch into the PR branch, resolve the lockfile by regenerating it (not by hand), push"),
    ("stale-branch", "merge_conflict", re.compile(r"CONFLICT \(content\)|Automatic merge failed|merge conflict", re.I),
     "merge the base branch into the PR branch (no history rewrite), resolve conflicts, push and re-run checks"),
    ("stale-branch", "behind_base", re.compile(r"branch is out[- ]of[- ]date|behind (?:the )?base|head branch is behind", re.I),
     "update the branch from base (merge base in), push and re-run checks"),
    ("env-missing", "python_module_missing", re.compile(r"ModuleNotFoundError|No module named|ImportError: cannot import name", re.I),
     "a dependency is missing in CI: add it to requirements-ci.txt / the test extras, then re-run"),
    ("env-missing", "command_missing", re.compile(r"command not found|is not recognized as an internal or external command|ENOENT.{0,60}spawn", re.I),
     "a tool is missing on the runner: add the setup step or install it in the workflow, then re-run"),
    ("env-missing", "env_var_missing", re.compile(r"(?:missing|undefined|unset|not set)[^\n]{0,40}(?:environment variable|env var|\benv\b)|(?:environment variable|env var)[^\n]{0,60}(?:missing|not set|required|undefined)|(?-i:KeyError: ['\"][A-Z][A-Z0-9_]{2,}['\"])", re.I),
     "a required env var/secret is not set in CI: add a safe test value or mock in the workflow (never commit real values)"),
    ("test-failure", "pytest_failed", re.compile(r"=+ .*\b\d+ failed\b|^FAILED [\w/.\-]+::|AssertionError", re.M),
     "reproduce with the failing test id locally, fix the code or the test, push"),
    ("test-failure", "repo_runner_failed", re.compile(r"^Test Results: \d+ passed, [1-9]\d* failed|^\u2717 test_\w+", re.M),
     "find the \u2717 test lines in the log, reproduce that test locally, fix, push"),
    ("test-failure", "js_test_failed", re.compile(r"Tests?:\s+\d+ failed|✕|ELIFECYCLE.{0,40}test|npm ERR! (?:code ELIFECYCLE|Test failed)|● .+ › ", re.I),
     "run the failing test file locally, fix, push"),
]


# GitHub Actions `gh run view --log[-failed]` prefixes every line with "job<TAB>step<TAB>timestamp ";
# raw step logs prefix "2026-10-29T12:23:47.6418363Z ". Strip both so ^-anchored rules (pytest FAILED) see the line.
_GHA_PREFIX = re.compile(r"^(?:[^\t\n]*\t[^\t\n]*\t)?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z ?", re.M)


def _strip_ci_prefixes(text: str) -> str:
    return _GHA_PREFIX.sub("", text)


def classify(log: str, branch_behind: bool = False) -> Dict[str, Any]:
    text = _strip_ci_prefixes((log or "")[-MAX_LOG_CHARS:])
    for cls, rule, rx, step in _RULES:
        if rx.search(text):
            return {"ok": True, "ability": "ci_failure_classify", "read_only": True,
                    "classification": cls, "rule": rule, "next_step": step}
    if branch_behind:
        return {"ok": True, "ability": "ci_failure_classify", "read_only": True, "classification": "stale-branch",
                "rule": "branch_behind_flag", "next_step": "update the branch from base (merge base in), push and re-run checks"}
    return {"ok": True, "ability": "ci_failure_classify", "read_only": True, "classification": "unknown",
            "rule": "no_match", "next_step": "read the first failing step in the CI log; escalate to the owner with the job link"}


def run(input: str = "", context: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    log = ctx.get("log")
    if log is None and input:
        log = input
    if not isinstance(log, str) or not log.strip():
        return {"ok": False, "ability": "ci_failure_classify", "error": "pass log=<CI log excerpt>"}
    return classify(log, branch_behind=bool(ctx.get("branch_behind")))
