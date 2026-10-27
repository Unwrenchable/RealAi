"""Secret rejection for hive records.

POLICY: reject, never rewrite. ``scan_record`` returns reason codes; a non-empty list means
the whole record must be dropped. Codes name the *kind* of finding only, never the matched text.

SECURITY REVIEW REQUIRED before first ingest / merge (see docs/HIVE.md). Heuristics here are a
safety net, not a guarantee: bots must also keep secrets out of records at the source.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Iterator, List, Set

SCANNER_VERSION = "hive-redact-1"

# --- token prefixes -------------------------------------------------------------------
_TOKEN_PATTERNS = [
    ("token:sk", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{10,}")),
    ("token:github", re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{16,}")),
    ("token:github_pat", re.compile(r"(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{16,}")),
    ("token:slack", re.compile(r"(?<![A-Za-z0-9])xox[a-zA-Z]-[A-Za-z0-9\-]{8,}")),
    ("token:aws_akia", re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}")),
    ("token:bearer", re.compile(r"(?i)\bBearer\s+(?=[A-Za-z0-9._~+/=\-]*\d)[A-Za-z0-9._~+/=\-]{16,}")),
]

# --- PEM / private key blocks -----------------------------------------------------------
_PEM = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----")

# --- connection URLs --------------------------------------------------------------------
_CONN_SCHEME = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|rediss?|amqps?)://")
_USERPASS_URL = re.compile(r"(?i)\b[a-z][a-z0-9+.\-]*://[^/\s:@]+:[^/\s@]+@[^\s/]+")

# --- .env style secret assignments -------------------------------------------------------
_SECRET_WORDS = r"(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD|CREDENTIAL|PRIVATE|SEED|MNEMONIC|DSN|DATABASE_URL)"
_ENV_UPPER = re.compile(
    r"(?<![A-Za-z0-9_])[A-Z0-9_]*?" + _SECRET_WORDS + r"[A-Z0-9_]*\s*=\s*(?![<$\s]|['\"]?(?:<|\$\{))\S"
)
_ENV_LOWER = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key)"
    r"\s*=\s*(?![<$\s]|['\"]?(?:<|\$\{))\S{4,}"
)

# --- high entropy -----------------------------------------------------------------------
_CAND = re.compile(r"[A-Za-z0-9_+=\-]{24,}")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_HEX = re.compile(r"^[0-9a-fA-F]+$")
ENTROPY_MIN_LEN = 24
ENTROPY_THRESHOLD = 4.0

# --- wallets ----------------------------------------------------------------------------
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_CAND = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{85,90}(?![1-9A-HJ-NP-Za-km-z])")
_BYTE_ARRAY_64 = re.compile(r"\[\s*(?:\d{1,3}\s*,\s*){63}\d{1,3}\s*\]")
_HEX64_KEYISH = re.compile(r"(?i)(?:0x|key|secret|private|seed|mnemonic)[\s:=\"']{0,6}[0-9a-f]{64}(?![0-9a-fA-F])")

# --- seed phrases (BIP39-like; no wordlist bundled) ----------------------------------------
_STOPWORDS = frozenset(
    "the a an and or to of is are was were in on for with by from that this it as be has have had "
    "not no if then than but so we i you he she they our your its into out up all any can will".split()
)
_WORD = re.compile(r"[a-z]{3,8}")


def _b58_decode_len(s: str) -> int:
    n = 0
    for ch in s:
        n = n * 58 + _B58_ALPHABET.index(ch)
    byte_len = (n.bit_length() + 7) // 8
    pad = len(s) - len(s.lstrip("1"))
    return byte_len + pad


def _entropy(s: str) -> float:
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def _seed_phrase_run(text: str) -> bool:
    """True if 12+ consecutive lowercase 3-8 letter words (no stopwords) appear."""
    run = 0
    for tok in re.split(r"\s+", text.lower().strip()):
        tok = tok.strip(",.;:\"'[]()")
        if _WORD.fullmatch(tok) and tok not in _STOPWORDS:
            run += 1
            if run >= 12:
                return True
        else:
            run = 0
    return False


def scan_text(text: str) -> List[str]:
    """Reason codes for one string. Never returns matched content."""
    found: Set[str] = set()
    for code, rx in _TOKEN_PATTERNS:
        if rx.search(text):
            found.add(code)
    if _PEM.search(text):
        found.add("pem_private_key")
    if _CONN_SCHEME.search(text) or _USERPASS_URL.search(text):
        found.add("connection_url")
    if _ENV_UPPER.search(text) or _ENV_LOWER.search(text):
        found.add("env_secret_line")
    for m in _CAND.finditer(text):
        tok = m.group(0)
        if _UUID.match(tok):
            continue
        if _HEX.match(tok) and len(tok) in (40, 64):  # git SHA-1 / SHA-256 digests
            continue
        if _HEX.match(tok) and len(tok) < 40:
            continue
        has_digit = any(c.isdigit() for c in tok)
        has_alpha = any(c.isalpha() for c in tok)
        if has_digit and has_alpha and _entropy(tok) >= ENTROPY_THRESHOLD:
            found.add("high_entropy")
            break
    for m in _B58_CAND.finditer(text):
        try:
            if _b58_decode_len(m.group(0)) == 64:
                found.add("solana_key_base58")
                break
        except ValueError:
            pass
    if _BYTE_ARRAY_64.search(text):
        found.add("solana_key_bytes")
    if _HEX64_KEYISH.search(text):
        found.add("hex_private_key")
    if _seed_phrase_run(text):
        found.add("seed_phrase")
    return sorted(found)


def _walk(obj: Any) -> Iterator[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                yield k
            yield from _walk(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk(v)
        strs = [v for v in obj if isinstance(v, str)]
        if len(strs) >= 12:  # word list split across array elements
            yield " ".join(strs)
    elif obj is not None and not isinstance(obj, (bool, int, float)):
        yield repr(obj)


def scan_record(rec: Any) -> List[str]:
    """Scan every string (keys and values) in a record; also the serialized JSON as a whole."""
    found: Set[str] = set()
    for s in _walk(rec):
        found.update(scan_text(s))
    try:
        found.update(scan_text(json.dumps(rec, ensure_ascii=False, sort_keys=True)))
    except (TypeError, ValueError):
        found.add("unserializable")
    return sorted(found)


def is_clean(rec: Any) -> bool:
    return not scan_record(rec)


__all__ = ["scan_text", "scan_record", "is_clean", "SCANNER_VERSION"]
