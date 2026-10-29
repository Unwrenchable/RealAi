"""Validator for raw hive records (schema_version ``hive.v1``).

``validate_record`` returns a list of short error codes such as ``task.category:invalid``.
Codes name the field and the problem only; they never echo the offending value, so a
rejects report built from them cannot leak content.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlparse

SCHEMA_VERSION = "hive.v1"

CATEGORIES = ("pr_triage", "vuln_triage", "ci_fix", "dep_update", "deploy", "data", "other")
TOOL_KINDS = ("git", "gh", "npm", "pnpm", "pytest", "http", "other")
RESULTS = ("pass", "fail")
OUTCOMES = ("done", "partial", "blocked")

TOP_LEVEL_KEYS = {
    "schema_version", "id", "ts", "bot", "product", "task", "actions", "verification",
    "outcome", "blockers", "links", "reviewer", "approval", "redaction",
}
REQUIRED_KEYS = TOP_LEVEL_KEYS - {"reviewer", "approval"}

MAX_ASK = 2000
MAX_SUMMARY = 500
MAX_COMMAND = 500
MAX_EVIDENCE = 500
MAX_ACTIONS = 50
MAX_BLOCKERS = 20
MAX_BLOCKER_LEN = 300
MAX_LINKS = 20
MAX_LINK_LEN = 500
MAX_SHORT = 128


def _is_str(v: Any, max_len: int, allow_empty: bool = False) -> bool:
    return isinstance(v, str) and len(v) <= max_len and (allow_empty or bool(v.strip()))


def _check_obj(obj: Any, allowed: set, required: set, prefix: str, errs: List[str]) -> bool:
    if not isinstance(obj, dict):
        errs.append(f"{prefix}:not_object")
        return False
    for k in obj:
        if k not in allowed:
            errs.append(f"{prefix}:unknown_field")
            break
    for k in sorted(required):
        if k not in obj:
            errs.append(f"{prefix}.{k}:missing")
    return True


def validate_record(rec: Any) -> List[str]:
    """Return a list of error codes; empty list means the record is valid hive.v1."""
    errs: List[str] = []
    if not isinstance(rec, dict):
        return ["record:not_object"]

    if "verification" not in rec or rec.get("verification") in (None, {}, ""):
        errs.append("verification:missing")
    if rec.get("schema_version") != SCHEMA_VERSION:
        errs.append("schema_version:invalid")
    for k in rec:
        if k not in TOP_LEVEL_KEYS:
            errs.append("record:unknown_field")
            break
    for k in sorted(REQUIRED_KEYS):
        if k not in rec and k != "verification":
            errs.append(f"{k}:missing")

    # id
    if "id" in rec:
        try:
            ok = isinstance(rec["id"], str) and str(uuid.UUID(rec["id"])) == rec["id"].lower()
        except (ValueError, AttributeError, TypeError):
            ok = False
        if not ok:
            errs.append("id:invalid_uuid")

    # ts (ISO-8601 with explicit offset)
    if "ts" in rec:
        ok = False
        if isinstance(rec["ts"], str):
            try:
                dt = datetime.fromisoformat(rec["ts"])
                ok = dt.tzinfo is not None and dt.utcoffset() is not None
            except ValueError:
                ok = False
        if not ok:
            errs.append("ts:invalid_iso8601_offset")

    # bot
    if "bot" in rec and _check_obj(rec["bot"], {"name", "id"}, {"name", "id"}, "bot", errs):
        b = rec["bot"]
        for k in ("name", "id"):
            if k in b and not _is_str(b[k], MAX_SHORT):
                errs.append(f"bot.{k}:invalid")

    if "product" in rec and not _is_str(rec["product"], MAX_SHORT):
        errs.append("product:invalid")

    # task
    if "task" in rec and _check_obj(rec["task"], {"ask", "category"}, {"ask", "category"}, "task", errs):
        t = rec["task"]
        if "ask" in t and not _is_str(t["ask"], MAX_ASK):
            errs.append("task.ask:invalid")
        if "category" in t and t["category"] not in CATEGORIES:
            errs.append("task.category:invalid")

    # actions
    if "actions" in rec:
        acts = rec["actions"]
        if not isinstance(acts, list) or not acts:
            errs.append("actions:invalid")
        elif len(acts) > MAX_ACTIONS:
            errs.append("actions:too_many")
        else:
            for i, a in enumerate(acts):
                p = f"actions[{i}]"
                if not _check_obj(a, {"step", "tool_kind", "summary"}, {"step", "tool_kind", "summary"}, p, errs):
                    continue
                if "step" in a and not (isinstance(a["step"], int) and not isinstance(a["step"], bool) and a["step"] >= 1):
                    errs.append(f"{p}.step:invalid")
                if "tool_kind" in a and a["tool_kind"] not in TOOL_KINDS:
                    errs.append(f"{p}.tool_kind:invalid")
                if "summary" in a and not _is_str(a["summary"], MAX_SUMMARY):
                    errs.append(f"{p}.summary:invalid")

    # verification
    v = rec.get("verification")
    if isinstance(v, dict) and v:
        _check_obj(v, {"command", "result", "evidence"}, {"command", "result", "evidence"}, "verification", errs)
        if "command" in v and not _is_str(v["command"], MAX_COMMAND):
            errs.append("verification.command:invalid")
        if "result" in v and v["result"] not in RESULTS:
            errs.append("verification.result:invalid")
        if "evidence" in v and not _is_str(v["evidence"], MAX_EVIDENCE, allow_empty=True):
            errs.append("verification.evidence:invalid")
    elif "verification" in rec and v not in (None, {}, ""):
        errs.append("verification:not_object")

    if "outcome" in rec and rec["outcome"] not in OUTCOMES:
        errs.append("outcome:invalid")

    # blockers
    if "blockers" in rec:
        bl = rec["blockers"]
        if not isinstance(bl, list) or len(bl) > MAX_BLOCKERS or not all(_is_str(x, MAX_BLOCKER_LEN) for x in bl):
            errs.append("blockers:invalid")

    # links (http/https only)
    if "links" in rec:
        ls = rec["links"]
        if not isinstance(ls, list) or len(ls) > MAX_LINKS:
            errs.append("links:invalid")
        else:
            for i, u in enumerate(ls):
                good = False
                if isinstance(u, str) and len(u) <= MAX_LINK_LEN and not any(c.isspace() for c in u):
                    try:
                        pu = urlparse(u)
                        good = pu.scheme in ("http", "https") and bool(pu.hostname)
                    except ValueError:
                        good = False
                if not good:
                    errs.append(f"links[{i}]:not_http_url")

    for k in ("reviewer", "approval"):
        if k in rec and rec[k] is not None and not _is_str(rec[k], 200):
            errs.append(f"{k}:invalid")

    # redaction attestation (ingest still re-scans every record)
    if "redaction" in rec and _check_obj(rec["redaction"], {"scanned", "scanner_version"},
                                         {"scanned", "scanner_version"}, "redaction", errs):
        r = rec["redaction"]
        if "scanned" in r and r["scanned"] is not True:
            errs.append("redaction.scanned:not_true")
        if "scanner_version" in r and not _is_str(r["scanner_version"], 64):
            errs.append("redaction.scanner_version:invalid")

    return errs


def is_valid(rec: Any) -> bool:
    return not validate_record(rec)


__all__ = ["validate_record", "is_valid", "SCHEMA_VERSION", "CATEGORIES", "TOOL_KINDS", "RESULTS", "OUTCOMES"]
