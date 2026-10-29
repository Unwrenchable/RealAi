"""Secret rejection for hive records.

POLICY: reject, never rewrite. ``scan_record`` returns reason codes; a non-empty list means
the whole record must be dropped. Codes name the *kind* of finding only, never the matched text.

Each string is scanned in several views (security review of PR #191):
  * raw text: zero-width / bidi control characters -> ``obfuscation``
  * NFKC-normalized text with zero-width characters stripped (all checks)
  * ``urllib.parse.unquote`` of that text (all checks)
  * a whitespace-stripped copy (token / PEM patterns only; catches secrets split over lines)
  * bounded base64 decodes of candidate substrings (all checks, one level deep)

Heuristics here are a safety net, not a guarantee: bots must also keep secrets out of records
at the source.
"""
from __future__ import annotations

import base64
import binascii
import json
import math
import re
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Any, Iterator, List, Set

SCANNER_VERSION = "hive-redact-2"

# --- obfuscation ------------------------------------------------------------------------
_ZERO_WIDTH = re.compile("[\u200b-\u200f\u2060\ufeff\u00ad]")
_OBFUSCATION = re.compile("[\u200b-\u200f\u2060-\u2064\ufeff\u00ad\u061c\u202a-\u202e\u2066-\u2069]")

# --- token prefixes (all case-insensitive) ------------------------------------------------
_NB = r"(?<![A-Za-z0-9])"
_TOKEN_PATTERNS = [
    ("token:sk", re.compile(r"(?i)\bsk[-_](?:live|test|ant|proj)?[-_]?[A-Za-z0-9_-]{10,}")),
    ("token:github", re.compile(r"(?i)" + _NB + r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("token:github_pat", re.compile(r"(?i)" + _NB + r"github_pat_[A-Za-z0-9_]{16,}")),
    ("token:slack", re.compile(r"(?i)" + _NB + r"xox[a-z]-[A-Za-z0-9\-]{8,}")),
    ("token:slack_webhook", re.compile(r"(?i)hooks\.slack\.com/services/")),
    ("token:aws_akia", re.compile(r"(?i)" + _NB + r"AKIA[0-9A-Z]{16}")),
    ("token:gitlab", re.compile(r"(?i)" + _NB + r"glpat-[\w-]{20}")),
    # Review asked for AIza[\w-]{35} / hf_[A-Za-z]{30,}; widened so shorter/digit-bearing
    # bodies (as in the review probes) are matched explicitly, not only by entropy.
    ("token:google", re.compile(r"(?i)" + _NB + r"AIza[\w-]{30,}")),
    ("token:huggingface", re.compile(r"(?i)" + _NB + r"hf_[A-Za-z0-9]{20,}")),
    ("token:npm", re.compile(r"(?i)" + _NB + r"npm_[A-Za-z0-9]{36}")),
    ("token:xai", re.compile(r"(?i)" + _NB + r"xai-[A-Za-z0-9]{20,}")),
    ("token:jwt", re.compile(r"\beyJ[\w-]{5,}\.eyJ[\w-]{5,}\.[\w-]{5,}")),
    ("token:bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=\-]{16,}")),
]

# --- PEM / private key blocks -----------------------------------------------------------
_PEM = re.compile(r"(?i)-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----")

# --- connection URLs --------------------------------------------------------------------
_CONN_SCHEME = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|rediss?|amqps?)://")
_USERPASS_URL = re.compile(r"(?i)\b[a-z][a-z0-9+.\-]{0,20}://[^/\s:@]{1,256}:[^/\s@]{1,256}@[^\s/]")

# --- env / JSON / YAML style secret assignments ------------------------------------------
_SECRET_PARTS = frozenset(
    "key secret secrets token tokens password passwd pass pwd passphrase credential credentials "
    "private seed mnemonic dsn apikey".split()
)
_STRONG_SINGLE = frozenset("password passwd pwd secret token apikey mnemonic passphrase dsn".split())
_ASSIGN = re.compile(
    r"(?<![A-Za-z0-9_.\-])([\"']?)([A-Za-z][A-Za-z0-9_.\-]{0,63})\1\s{0,8}[:=]\s{0,8}"
    r"(?=([\"']?)([^\s\"',;}\]]{3,64}))"
)
_PLACEHOLDER = re.compile(r"^(?:<|\$|\*{3}|x{3,}$|null$|none$|true$|false$|redacted|\.\.\.)", re.I)


def _env_secret(text: str) -> bool:
    for m in _ASSIGN.finditer(text):
        key, quoted, value = m.group(2), m.group(1), m.group(4)
        lk = key.lower()
        parts = [p for p in re.split(r"[_.\-]", lk) if p]
        if not (set(parts) & _SECRET_PARTS or lk.endswith("database_url")):
            continue
        # single bare word like "Key: findings" is prose unless it is a strong word,
        # quoted, or ALL CAPS
        if len(parts) == 1 and lk not in _STRONG_SINGLE and not quoted and not key.isupper():
            continue
        if _PLACEHOLDER.match(value) or value.isdigit():
            continue
        return True
    return False


# --- high entropy -----------------------------------------------------------------------
_CAND = re.compile(r"[A-Za-z0-9_+=\-]{24,}")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_HEX = re.compile(r"^[0-9a-fA-F]+$")
ENTROPY_MIN_LEN = 24
ENTROPY_THRESHOLD = 4.0

# --- base64 rescan (bounded) ------------------------------------------------------------
_B64_CAND = re.compile(r"[A-Za-z0-9+/_\-]{16,}={0,2}")
B64_MAX_LEN = 4096
B64_MAX_CANDIDATES = 32

# --- wallets ----------------------------------------------------------------------------
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_CAND = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{85,90}(?![1-9A-HJ-NP-Za-km-z])")
_INT_ARRAY = re.compile(r"\[\s*((?:\d{1,3}\s*,\s*){31}\d{1,3}|(?:\d{1,3}\s*,\s*){63}\d{1,3})\s*\]")
_HEX64_KEYISH = re.compile(r"(?i)(?:0x|key|secret|private|seed|mnemonic)[\s:=\"']{0,6}[0-9a-f]{64}(?![0-9a-fA-F])")

# --- seed phrases -------------------------------------------------------------------------
_BIP39 = frozenset(
    (Path(__file__).with_name("bip39_english.txt")).read_text(encoding="utf-8").split()
)
assert len(_BIP39) == 2048, "bip39_english.txt must hold the 2048-word BIP39 English list"
_STOPWORDS = frozenset(
    w for w in (
        "the a an and or to of is are was were in on for with by from that this it as be has have had "
        "not no if then than but so we i you he she they our your its into up will"
    ).split() if w not in _BIP39
)
_WORD = re.compile(r"[a-z]{3,8}")
_SEED_SPLIT = re.compile(r"[\s,;\-_|/.\d\"'\[\]():{}]+")
SEED_RUN = 12
SEED_MIN_BIP39 = 6  # in a 12-word run: all-BIP39, or a word-list-shaped run with >= half BIP39


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
    """True if a run of 12+ seed-like words appears.

    A run is consecutive lowercase 3-8 letter non-stopword tokens (split on whitespace,
    punctuation, digits, dashes). It is flagged if any 12-token window holds at least
    SEED_MIN_BIP39 BIP39 words (12 straight wordlist words always qualify). Plain prose
    rarely has 6 BIP39 words in 12 consecutive non-stopword tokens.
    """
    window: List[bool] = []
    for tok in _SEED_SPLIT.split(text.lower()):
        if not tok:
            continue
        if _WORD.fullmatch(tok) and tok not in _STOPWORDS:
            window.append(tok in _BIP39)
            if len(window) > SEED_RUN:
                window.pop(0)
            if len(window) == SEED_RUN and sum(window) >= SEED_MIN_BIP39:
                return True
        else:
            window = []
    return False


def _int_array_text(text: str) -> bool:
    for m in _INT_ARRAY.finditer(text):
        if all(int(x) <= 255 for x in re.findall(r"\d+", m.group(1))):
            return True
    return False


def _scan_view(text: str, found: Set[str]) -> None:
    """All checks on one normalized view of a string."""
    for code, rx in _TOKEN_PATTERNS:
        if rx.search(text):
            found.add(code)
    if _PEM.search(text):
        found.add("pem_private_key")
    if _CONN_SCHEME.search(text) or _USERPASS_URL.search(text):
        found.add("connection_url")
    if _env_secret(text):
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
    if _int_array_text(text):
        found.add("solana_key_bytes")
    if _HEX64_KEYISH.search(text):
        found.add("hex_private_key")
    if _seed_phrase_run(text):
        found.add("seed_phrase")


def _b64_views(text: str) -> Iterator[str]:
    n = 0
    for m in _B64_CAND.finditer(text):
        cand = m.group(0)
        if len(cand) > B64_MAX_LEN:
            continue
        n += 1
        if n > B64_MAX_CANDIDATES:
            return
        body = cand.rstrip("=")
        body = body + "=" * (-len(body) % 4)
        try:
            raw = base64.b64decode(body.replace("-", "+").replace("_", "/"), validate=True)
            dec = raw.decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if dec and sum(c.isprintable() or c in "\r\n\t" for c in dec) >= 0.9 * len(dec):
            yield dec


def _normalize(text: str) -> str:
    return _ZERO_WIDTH.sub("", unicodedata.normalize("NFKC", text))


def scan_text(text: str, _depth: int = 0) -> List[str]:
    """Reason codes for one string. Never returns matched content."""
    found: Set[str] = set()
    if _OBFUSCATION.search(text):
        found.add("obfuscation")
    norm = _normalize(text)
    _scan_view(norm, found)
    unq = urllib.parse.unquote(norm)
    if unq != norm:
        _scan_view(unq, found)
    squeezed = re.sub(r"\s+", "", unq)
    if squeezed != unq:
        for code, rx in _TOKEN_PATTERNS:
            if rx.search(squeezed):
                found.add(code)
        if _PEM.search(squeezed):
            found.add("pem_private_key")
    if _depth == 0:
        for dec in _b64_views(norm):
            inner = scan_text(dec, _depth=1)
            if inner:
                found.update(inner)
                found.add("base64_encoded")
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
    elif obj is not None and not isinstance(obj, (bool, int, float)):
        yield repr(obj)


def _walk_values(obj: Any) -> Iterator[str]:
    """String values only (no keys), in order; used for cross-field concatenation."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_values(v)


def _is_byte_key(seq: Any) -> bool:
    return (
        len(seq) in (32, 64)
        and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255 for v in seq)
    )


def _has_int_key_array(obj: Any) -> bool:
    if isinstance(obj, dict):
        vals = list(obj.values())
        return _is_byte_key(vals) or any(_has_int_key_array(v) for v in vals)
    if isinstance(obj, (list, tuple)):
        return _is_byte_key(obj) or any(_has_int_key_array(v) for v in obj)
    return False


def scan_record(rec: Any) -> List[str]:
    """Scan every string (keys and values) in a record, the concatenation of all string
    values (secrets / seed phrases split across fields), and the serialized JSON."""
    found: Set[str] = set()
    for s in _walk(rec):
        found.update(scan_text(s))
    joined = "\n".join(_walk_values(rec))
    if joined:
        found.update(scan_text(joined))
    if _has_int_key_array(rec):
        found.add("solana_key_bytes")
    try:
        found.update(scan_text(json.dumps(rec, ensure_ascii=False, sort_keys=True)))
    except (TypeError, ValueError):
        found.add("unserializable")
    return sorted(found)


def is_clean(rec: Any) -> bool:
    return not scan_record(rec)


__all__ = ["scan_text", "scan_record", "is_clean", "SCANNER_VERSION"]
