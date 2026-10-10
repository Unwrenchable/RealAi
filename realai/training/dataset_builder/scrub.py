"""Secret / PII scrubbing. Rows with secrets are dropped; PII and local paths are redacted."""
from __future__ import annotations

import re
from typing import Iterable, List, Tuple

# Any match => drop the whole row (never try to "fix" a leaked credential).
SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("openai_key", re.compile(r"(?<![A-Za-z0-9])sk-(?:proj-|ant-|or-v1-)?[A-Za-z0-9_\-]{32,}")),
    ("xai_key", re.compile(r"(?<![A-Za-z0-9])xai-[A-Za-z0-9]{32,}")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("aws_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("db_url_password", re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/@]+:[^\s@]{3,}@")),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9\-_\.=]{30,}")),
    ("hf_token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("solana_secret_array", re.compile(r"\[(?:\s*\d{1,3}\s*,){63}\s*\d{1,3}\s*\]")),
]

EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
WIN_USER = re.compile(r"(?i)\b([A-Z]:[\\/]+Users[\\/]+)([^\\/\s\"'<>|]+)")
WSL_USER = re.compile(r"(?i)(/mnt/[a-z]/Users/)([^/\s\"'<>|]+)")
NIX_HOME = re.compile(r"(/home/|/Users/)([A-Za-z0-9._\-]+)")


def find_secrets(text: str) -> List[str]:
    return [name for name, pat in SECRET_PATTERNS if pat.search(text or "")]


def redact(text: str, usernames: Iterable[str] = ()) -> str:
    out = EMAIL.sub("<EMAIL>", text or "")
    out = WIN_USER.sub(lambda m: m.group(1) + "<USER>", out)
    out = WSL_USER.sub(lambda m: m.group(1) + "<USER>", out)
    out = NIX_HOME.sub(lambda m: m.group(1) + "<USER>", out)
    for name in usernames:
        if name and len(name) >= 3:
            out = re.sub(r"(?i)(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", "<USER>", out)
    return out
