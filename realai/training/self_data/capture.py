"""Opt-in capture of real RealAI activity as candidate training rows (REALAI_CAPTURE=1).

Every interaction is tagged by project (rackup / atomicfizz / cli / chess / hive / realai), redacted
(secrets -> row dropped; emails, user paths, wallet addresses, tx signatures, bearer tokens -> placeholders)
and written under REALAI_HOME/datasets/_sources/hive_traffic/<project>-<date>.jsonl. Candidates only:
``python -m realai.training.self_data verify-traffic`` runs the same verifier as self-play before anything
reaches hive_selfplay. Rows touching real money (payouts, transfers, trades, sends) are stored with
``replay: false`` and are never re-executed; their tool calls are not replayed by any loop.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS = ("rackup", "atomicfizz", "cli", "chess", "hive", "realai")
_PROJECT_HINTS = [
    ("rackup", re.compile(r"rackup|rack ?of ?champions|rackofchampions|pyramid|sotd|shot of the day|\broc\b|league|cue ball|8-ball|9-ball", re.I)),
    ("atomicfizz", re.compile(r"atomic ?fizz|atomicfizzcaps|overseer|vault ?77|wasteland|\bfizz\b|solana|wallet", re.I)),
    ("chess", re.compile(r"\bchess\b|stockfish|\bfen\b|[rnbqkp1-8]{1,8}(/[rnbqkp1-8]{1,8}){7}", re.I)),
]
MONEY = re.compile(r"\b(payouts?|withdraw\w*|transfer\w*|swap|trade|buy|sell|place_order|sign(_|\s)?tx|airdrop|mint|stake)\b"
                   r"|\bsend\b[^.\n]{0,40}\b(sol|usdc|usdt|eth|btc|fizz|tokens?|lamports|coins?|money|\$\d+)", re.I)
MONEY_TOOLS = {"solana_send", "trade", "place_order", "payout", "transfer", "web3_send"}
_WALLET = re.compile(r"(?<![A-Za-z0-9])[1-9A-HJ-NP-Za-km-z]{32,44}(?![A-Za-z0-9])")
_EVM = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
_SIG = re.compile(r"(?<![A-Za-z0-9])[1-9A-HJ-NP-Za-km-z]{80,90}(?![A-Za-z0-9])")
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{12,}")
_KEYTALK = re.compile(r"seed phrase|mnemonic|recovery phrase|private key|secret key", re.I)  # row dropped


def infer_project(text: str, explicit: Optional[str] = None, channel: str = "") -> str:
    if explicit and str(explicit).lower() in PROJECTS:
        return str(explicit).lower()
    if channel == "cli":
        return "cli"
    for name, rx in _PROJECT_HINTS:
        if rx.search(text or ""):
            return name
    return "hive" if channel in ("hive", "agents") else "realai"


def redact_text(text: str, users: Optional[List[str]] = None) -> str:
    from realai.training.dataset_builder.scrub import redact

    t = redact(str(text or ""), users or [])
    t = _SIG.sub("<TX_SIG>", t)
    t = _EVM.sub("<WALLET>", t)
    t = _WALLET.sub(lambda m: m.group(0) if _is_fenish(m.group(0)) else "<WALLET>", t)
    t = _BEARER.sub("Bearer <TOKEN>", t)
    return t


def _is_fenish(s: str) -> bool:
    return "/" in s


def redact_obj(o: Any, users: Optional[List[str]] = None) -> Any:
    if isinstance(o, str):
        return redact_text(o, users)
    if isinstance(o, list):
        return [redact_obj(x, users) for x in o]
    if isinstance(o, dict):
        return {k: redact_obj(v, users) for k, v in o.items()}
    return o


def is_money(messages: List[Dict[str, Any]], calls: Optional[List[Dict[str, Any]]] = None) -> bool:
    for c in calls or []:
        if str(c.get("name")) in MONEY_TOOLS or MONEY.search(json.dumps(c.get("arguments") or {})):
            return True
    return any(m.get("role") == "user" and MONEY.search(str(m.get("content") or "")) for m in messages)


def traffic_dir() -> Path:
    home = Path(os.environ.get("REALAI_HOME") or Path.cwd()).resolve()
    return home / "datasets" / "_sources" / "hive_traffic"


def enabled() -> bool:
    return os.environ.get("REALAI_CAPTURE", "").lower() in ("1", "true", "on")


def capture(messages: List[Dict[str, Any]], tools=None, calls=None, project: Optional[str] = None, channel: str = "chat",
            force: bool = False) -> Optional[Path]:
    """Append one interaction (redacted) to the traffic log. No-op unless REALAI_CAPTURE=1 (or force)."""
    if not (force or enabled()):
        return None
    from realai.training.dataset_builder.scrub import find_secrets

    raw = json.dumps({"m": messages, "c": calls}, ensure_ascii=False, default=str)
    if find_secrets(raw) or _KEYTALK.search(raw):
        return None  # never store a row that held a real secret
    users = [u for u in os.environ.get("REALAI_REDACT_USERS", "").split(",") if u]
    text = " ".join(str(m.get("content") or "") for m in messages if m.get("role") == "user")
    row = {
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "project": infer_project(text, project, channel),
        "channel": channel,
        "messages": redact_obj(messages, users),
        "tools": tools if isinstance(tools, list) else None,
        "calls": redact_obj(calls or [], users),
        "replay": not is_money(messages, calls),
        "origin": "traffic",
    }
    d = traffic_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{row['project']}-{_dt.date.today().isoformat()}.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return p
