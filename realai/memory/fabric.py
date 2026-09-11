"""RealAI Memory Fabric — Orchestrator 2.0 scoped durable memory (stdlib JSONL).

Canonical store: state/memory/fabric.jsonl (override with REALAI_MEMORY_FABRIC).
Does not mutate sqlite_memory schemas. No network.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

SCOPES = frozenset({"episodic", "semantic", "procedural", "world", "agent"})
SENSITIVITIES = frozenset({"normal", "high", "secret"})
TTL_ALIASES = {
    "30d": timedelta(days=30),
    "7d": timedelta(days=7),
    "1d": timedelta(days=1),
    "90d": timedelta(days=90),
    "forever": None,
    "none": None,
    "": None,
}

_DEFAULT_REL = Path("state") / "memory" / "fabric.jsonl"
_lock = threading.RLock()


def _workspace_root() -> Path:
    env = (os.environ.get("REALAI_WORKSPACE") or "").strip()
    if env:
        return Path(env)
    return Path(r"C:\RealAI-clean")


def fabric_path() -> Path:
    override = (os.environ.get("REALAI_MEMORY_FABRIC") or "").strip()
    if override:
        return Path(override)
    return _workspace_root() / _DEFAULT_REL


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_ttl(ttl: Optional[str]) -> tuple[str, Optional[datetime]]:
    raw = (ttl or "30d").strip().lower() or "30d"
    if raw in TTL_ALIASES:
        delta = TTL_ALIASES[raw]
        if delta is None:
            return "forever", None
        return raw, _utcnow() + delta
    m = re.fullmatch(r"(\d+)\s*d", raw)
    if m:
        days = int(m.group(1))
        label = f"{days}d"
        return label, _utcnow() + timedelta(days=days)
    # unknown → treat as forever label but keep string
    return raw, None


@dataclass
class MemoryRecord:
    id: str
    text: str
    scope: str = "episodic"
    owner: str = "system"
    ttl: str = "30d"
    sensitivity: str = "normal"
    created_at: str = ""
    expires_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        meta = data.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {"value": meta}
        return cls(
            id=str(data.get("id") or ""),
            text=str(data.get("text") or ""),
            scope=str(data.get("scope") or "episodic"),
            owner=str(data.get("owner") or "system"),
            ttl=str(data.get("ttl") or "30d"),
            sensitivity=str(data.get("sensitivity") or "normal"),
            created_at=str(data.get("created_at") or ""),
            expires_at=data.get("expires_at"),
            tags=list(tags),
            meta=dict(meta),
        )


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_all(path: Optional[Path] = None) -> List[MemoryRecord]:
    p = path or fabric_path()
    if not p.is_file():
        return []
    out: List[MemoryRecord] = []
    try:
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    out.append(MemoryRecord.from_dict(obj))
    except OSError:
        return []
    return out


def _append_record(rec: MemoryRecord, path: Optional[Path] = None) -> None:
    p = path or fabric_path()
    _ensure_parent(p)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")


def _rewrite_all(records: Sequence[MemoryRecord], path: Optional[Path] = None) -> None:
    p = path or fabric_path()
    _ensure_parent(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
    tmp.replace(p)


def _is_expired(rec: MemoryRecord, now: Optional[datetime] = None) -> bool:
    if not rec.expires_at:
        return False
    exp = _parse_iso(rec.expires_at)
    if exp is None:
        return False
    return exp <= (now or _utcnow())


def _should_redact(
    sensitivity: str,
    *,
    privacy: Optional[str] = None,
    redact_high: Optional[bool] = None,
) -> bool:
    sens = (sensitivity or "normal").lower()
    if sens not in {"high", "secret"}:
        return False
    if redact_high is True:
        return True
    if redact_high is False:
        return sens == "secret" and (privacy or "").lower() in {
            "cloud-allowed",
            "cloud",
            "remote",
        }
    priv = (privacy or "").lower()
    # Cloud-bound decisions never get full high/secret text
    if priv in {"cloud-allowed", "cloud", "remote"}:
        return True
    if priv == "cloud-blocked" and sens == "secret":
        return True
    return False


def _redact_record(rec: MemoryRecord) -> Dict[str, Any]:
    d = rec.to_dict()
    d["text"] = "[REDACTED]"
    d["redacted"] = True
    return d


def _tokenize(query: str) -> Set[str]:
    return {t for t in re.findall(r"[a-z0-9_]{2,}", (query or "").lower()) if t}


def _score(rec: MemoryRecord, tokens: Set[str], query_l: str) -> float:
    if not tokens and not query_l:
        return 0.01
    text_l = (rec.text or "").lower()
    blob = " ".join(
        [
            text_l,
            (rec.owner or "").lower(),
            (rec.scope or "").lower(),
            " ".join(str(t).lower() for t in rec.tags),
        ]
    )
    score = 0.0
    if query_l and query_l in blob:
        score += 5.0
    hits = sum(1 for t in tokens if t in blob)
    score += float(hits)
    if rec.scope == "semantic":
        score += 0.2
    return score


def write_memory(
    text: str,
    *,
    scope: str = "episodic",
    owner: str = "system",
    ttl: str = "30d",
    sensitivity: str = "normal",
    tags: Optional[Iterable[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
    record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one MemoryRecord to the JSONL fabric store."""
    body = (text or "").strip()
    if not body:
        return {"ok": False, "error": "empty_text"}

    scope_n = (scope or "episodic").strip().lower()
    if scope_n not in SCOPES:
        scope_n = "episodic"
    sens_n = (sensitivity or "normal").strip().lower()
    if sens_n not in SENSITIVITIES:
        sens_n = "normal"
    ttl_label, expires = _parse_ttl(ttl)
    created = _utcnow()
    rec = MemoryRecord(
        id=record_id or uuid.uuid4().hex,
        text=body,
        scope=scope_n,
        owner=(owner or "system").strip() or "system",
        ttl=ttl_label,
        sensitivity=sens_n,
        created_at=_iso(created) or "",
        expires_at=_iso(expires),
        tags=[str(t) for t in (tags or []) if str(t).strip()],
        meta=dict(meta or {}),
    )
    with _lock:
        _append_record(rec)
    return {"ok": True, "id": rec.id, "record": rec.to_dict()}


def read_memory(
    query: str,
    *,
    scopes: Optional[Sequence[str]] = None,
    owner: Optional[str] = None,
    limit: int = 8,
    include_expired: bool = False,
    privacy: Optional[str] = None,
    redact_high: Optional[bool] = None,
) -> Dict[str, Any]:
    """Search fabric records; redact high/secret when cloud-bound or flagged."""
    lim = max(1, min(int(limit or 8), 64))
    scope_filter: Optional[Set[str]] = None
    if scopes:
        scope_filter = {str(s).lower() for s in scopes if str(s).strip()}
    owner_n = (owner or "").strip() or None
    tokens = _tokenize(query)
    query_l = (query or "").strip().lower()
    now = _utcnow()

    with _lock:
        records = _load_all()

    scored: List[tuple[float, MemoryRecord]] = []
    for rec in records:
        if not include_expired and _is_expired(rec, now):
            continue
        if scope_filter and rec.scope not in scope_filter:
            continue
        if owner_n and rec.owner != owner_n:
            continue
        sc = _score(rec, tokens, query_l)
        if tokens and sc <= 0:
            continue
        scored.append((sc, rec))

    scored.sort(key=lambda x: (-x[0], x[1].created_at))

    hits: List[Dict[str, Any]] = []
    for sc, rec in scored[:lim]:
        if _should_redact(rec.sensitivity, privacy=privacy, redact_high=redact_high):
            item = _redact_record(rec)
        else:
            item = rec.to_dict()
        item["score"] = round(sc, 3)
        hits.append(item)

    return {
        "ok": True,
        "query": (query or "")[:200],
        "count": len(hits),
        "hits": hits,
        "path": str(fabric_path()),
    }


def purge_expired() -> Dict[str, Any]:
    """Remove expired records from the JSONL store (callable; not a daemon)."""
    now = _utcnow()
    with _lock:
        records = _load_all()
        keep = [r for r in records if not _is_expired(r, now)]
        purged = len(records) - len(keep)
        if purged:
            _rewrite_all(keep)
    return {
        "ok": True,
        "purged": purged,
        "remaining": len(keep) if purged else len(records),
        "path": str(fabric_path()),
    }


def memory_fabric_status() -> Dict[str, Any]:
    """Lightweight status for hooks / diagnostics (no network)."""
    p = fabric_path()
    with _lock:
        records = _load_all(p)
    now = _utcnow()
    expired = sum(1 for r in records if _is_expired(r, now))
    by_scope: Dict[str, int] = {}
    by_sens: Dict[str, int] = {}
    for r in records:
        by_scope[r.scope] = by_scope.get(r.scope, 0) + 1
        by_sens[r.sensitivity] = by_sens.get(r.sensitivity, 0) + 1
    size = 0
    try:
        size = p.stat().st_size if p.is_file() else 0
    except OSError:
        size = 0
    return {
        "ok": True,
        "active": True,
        "backend": "jsonl",
        "path": str(p),
        "exists": p.is_file(),
        "bytes": size,
        "records": len(records),
        "expired": expired,
        "by_scope": by_scope,
        "by_sensitivity": by_sens,
        "env_override": bool((os.environ.get("REALAI_MEMORY_FABRIC") or "").strip()),
    }


__all__ = [
    "MemoryRecord",
    "SCOPES",
    "SENSITIVITIES",
    "fabric_path",
    "write_memory",
    "read_memory",
    "purge_expired",
    "memory_fabric_status",
]
