"""Redaction scanner tests. Every 'secret' below is synthetic and assembled at runtime so no
real-looking credential literal is committed to git."""
import pytest

from realai.hive_records.redact import SCANNER_VERSION, scan_record, scan_text

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    return "1" * (len(data) - len(data.lstrip(b"\0"))) + out


FAKE = {
    "sk": "sk-" + "FAKE" * 6,
    "ghp": "ghp_" + "FAKE" * 6,
    "gho": "gho_" + "FAKE" * 6,
    "github_pat": "github_pat_" + "FAKE" * 8,
    "slack": "xo" + "xb-" + "FAKE" * 4,
    "akia": "AK" + "IA" + "FAKE" * 4,
    "bearer": "Bearer " + "FAKE1234" * 3,
}


@pytest.mark.parametrize("name", sorted(FAKE))
def test_token_prefixes_rejected(name):
    codes = scan_text(f"used {FAKE[name]} in the call")
    assert codes, name
    assert all(FAKE[name] not in c for c in codes)


def test_pem_block_rejected():
    txt = "-----BEGIN " + "RSA PRIVATE KEY-----\nFAKEFAKE\n-----END " + "RSA PRIVATE KEY-----"
    assert "pem_private_key" in scan_text(txt)
    assert "pem_private_key" in scan_text("-----BEGIN " + "PRIVATE KEY-----")
    assert "pem_private_key" not in scan_text("-----BEGIN " + "CERTIFICATE-----")


@pytest.mark.parametrize("url", [
    "postgres://user:pw@db.example.test:5432/app",
    "postgresql://db.example.test/app",
    "mysql://root:pw@localhost/x",
    "mongodb://u:p@host/db",
    "mongodb+srv://u:p@cluster.example.test/db",
    "redis://:pw@cache.example.test:6379/0",
    "https://user:pass@example.test/path",
    "ftp://alice:hunter2@files.example.test/",
])
def test_connection_urls_rejected(url):
    assert "connection_url" in scan_text("connect with " + url)


def test_plain_https_url_is_fine():
    assert scan_text("see https://github.com/example/repo/pull/12 for details") == []


@pytest.mark.parametrize("line", [
    "DATABASE_URL=something-fake",
    "export API_KEY=fakevalue123",
    "GITHUB_TOKEN=fake",
    "STRIPE_SECRET_KEY = fake-fake",
    "password=notarealpass",
])
def test_env_secret_lines_rejected(line):
    assert "env_secret_line" in scan_text("ran:\n" + line + "\ndone")


def test_env_placeholders_allowed():
    assert scan_text("set API_KEY=<redacted> and TOKEN=${TOKEN}") == []
    assert scan_text("REALAI_DATA_DIR=C:/data pytest -q") == []


def test_high_entropy_string_rejected():
    fake = "Zx9Qm2Lp7Vd4Rt8Ys3Hn6Kc1Wb5Jf0Gq"  # synthetic random-looking, not a credential
    assert "high_entropy" in scan_text("value " + fake)


def test_digests_uuids_and_identifiers_allowed():
    assert scan_text("commit 9c10e0c8f1a2b3c4d5e6f708192a3b4c5d6e7f80") == []
    assert scan_text("sha256 41D31FEE78AD299FAE359409805D2C5ECC2C4101342978270E04212CD6A12CE0") == []
    assert scan_text("id 123e4567-e89b-12d3-a456-426614174000") == []
    assert scan_text("training/data/_staging/hive_candidates_2026-10-27.jsonl") == []
    assert scan_text("hive_candidates_ability_surface_catalog_honesty_pr") == []


def test_solana_base58_64_byte_key_rejected():
    fake_key = b58encode(bytes(range(1, 65)))  # synthetic 64 bytes
    assert 85 <= len(fake_key) <= 90
    assert "solana_key_base58" in scan_text("key " + fake_key)


def test_solana_pubkey_32_byte_allowed():
    pub = b58encode(bytes(range(1, 33)))
    assert "solana_key_base58" not in scan_text("wallet " + pub)


def test_solana_byte_array_rejected():
    arr = "[" + ",".join(str(i) for i in range(64)) + "]"
    assert "solana_key_bytes" in scan_text("keypair " + arr)


def test_hex_private_key_context_rejected():
    assert "hex_private_key" in scan_text("private key: " + "ab" * 32)
    assert "hex_private_key" in scan_text("0x" + "cd" * 32)


@pytest.mark.parametrize("n", [12, 24])
def test_seed_phrase_rejected(n):
    words = ("abandon ability able about above absent absorb abstract absurd abuse access accident "
             "account accuse achieve acid acoustic acquire across action actor actress actual adapt").split()[:n]
    assert "seed_phrase" in scan_text(" ".join(words))
    assert "seed_phrase" in scan_text("mnemonic: " + ", ".join(words))


def test_ordinary_prose_not_seed_phrase():
    assert scan_text("the build passed after the fix was merged into the base branch today and checks were green") == []


def test_scan_record_walks_nested_values_and_keys():
    rec = {"a": {"b": [{"c": FAKE["ghp"]}]}}
    assert scan_record(rec)
    assert scan_record({FAKE["sk"]: 1})
    words = ("abandon ability able about above absent absorb abstract absurd abuse access accident").split()
    assert "seed_phrase" in scan_record({"w": words})


def test_clean_record_passes_and_reasons_never_echo_content():
    assert scan_record({"ask": "triage PR 5", "links": ["https://example.test/pr/5"]}) == []
    codes = scan_record({"x": FAKE["akia"]})
    assert codes and all(FAKE["akia"] not in c for c in codes)
    assert SCANNER_VERSION.startswith("hive-redact-")


# ---------------------------------------------------------------------------------------
# Security review of PR #191: every probe from review191_probes.py (43 cases), all FAKE.
# ---------------------------------------------------------------------------------------
import base64 as _b64
import json as _json
import time as _time

_F = "FAKEfake0123456789abcdEFGH"
_FAKE64 = [i % 250 + 1 for i in range(64)]
_WORDS = "apple brave cider delta eagle fable giant hover ivory joker koala lemon".split()

PROBE_TEXT = {
    "BEARER upper": "BEARER " + _F,
    "Bearer letters-only": "Authorization: Bearer " + "abcdefghijklmnopqrstuvwxyz",
    "Sk- mixed": "Sk-" + _F,
    "SK_live stripe": "sk_" + "live_" + _F,
    "sk-ant": "sk-" + "ant-api03-" + _F,
    "sk-proj": "sk-" + "proj-" + _F,
    "glpat": "glp" + "at-" + "aB3dE5gH7jK9mN1pQ2rS",
    "AIza": "AI" + "za" + "SyFAKEfakeFAKEfake12345678901234",
    "hf_": "hf" + "_" + "aBcDeFgHiJkLmNoPqRsTuVwXyZ12",
    "npm_": "np" + "m_" + "aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890",
    "xai-": "xa" + "i-" + "aBcDeFgHiJkLmNoPqRsTuVwX",
    "slack webhook": "https://hooks." + "slack.com/services/T0FAKE/B0FAKE/abcdefghijklmnopqrstuvwx",
    "short lowercase key (low entropy)": "token is xa" + "i-abcdefghabcdefghabcdefgh",
    "zero-width sk": "s\u200bk-" + _F,
    "zero-width ghp": "gh\u200bp_" + "aBcDeFgHiJkLmNoPqRsT12",
    "fullwidth AKIA": "\uff21KIA" + "ABCDEFGHIJ123456",
    "url-encoded userpass": "postgres%3A%2F%2Fu%3Ap%40h/db",
    "base64 wrapped sk": _b64.b64encode(("sk-" + _F).encode()).decode(),
    "base64 short PEM header": _b64.b64encode(b"-----BEGIN " + b"PRIVATE KEY-----").decode(),
    "split across lines": "sk-\nFAKEfake0123",
    "JWT": "ey" + "JhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJlZmFrZQ",
    "env lower other word": "db_pass=hunter2xyz",
    "env json style": '"password": "hunter2xyz"',
    "env yaml": "API_KEY: abcd1234wxyz",
    "export with spaces": "export GITHUB_TOKEN = 'abc'",
    "solana bytes": _json.dumps(_FAKE64),
    "solana bytes no spaces": str(_FAKE64).replace(" ", ""),
    "solana bytes 32": _json.dumps(_FAKE64[:32]),
    "seed comma sep": ",".join(_WORDS),
    "seed dash sep": "-".join(_WORDS),
    "seed numbered": " ".join(f"{i+1}.{w}" for i, w in enumerate(_WORDS)),
    "seed with real bip39 stopword-ish words": " ".join(_WORDS[:6] + ["all"] + _WORDS[6:]),
    "seed 12 caps": " ".join(w.upper() for w in _WORDS),
    "ssh openssh": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
    "pgp": "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----",
    "https userpass": "https://user:pa55word@example.com",
}

PROBE_RECORDS = {
    "secret in key": {"sk-" + _F: 1},
    "seed split over list": {"x": _WORDS},
    "seed split over nested lists 6+6": {"x": [_WORDS[:6], _WORDS[6:]]},
    "seed split across fields": {"a": " ".join(_WORDS[:6]), "b": " ".join(_WORDS[6:])},
    "sk split across fields": {"a": "sk-", "b": _F},
    "bytes as list of ints": {"k": _FAKE64},
    "bytes as nested ints dict": {"k": {str(i): v for i, v in enumerate(_FAKE64)}},
}


def test_probe_count_is_43():
    assert len(PROBE_TEXT) + len(PROBE_RECORDS) == 43


@pytest.mark.parametrize("name", sorted(PROBE_TEXT))
def test_review_probe_text_rejected(name):
    codes = scan_record({"t": PROBE_TEXT[name]})
    assert codes, name
    assert all(PROBE_TEXT[name] not in c for c in codes)


@pytest.mark.parametrize("name", sorted(PROBE_RECORDS))
def test_review_probe_record_rejected(name):
    assert scan_record(PROBE_RECORDS[name]), name


@pytest.mark.parametrize("text", [
    "id 3f2b1c9e-1a2b-4c3d-9e8f-0a1b2c3d4e5f",
    "test_hive_ingest_rejects_records_with_42_fields",
    "https://github.com/Unwrenchable/RealAi/pull/191",
    "deploy staging build passed after rebase fixed lint config cache tests green ship today",
    "tests passed: 91, checks: green",
    "Key findings: redact misses lowercase tokens",
    "the task risk - management note",
])
def test_review_false_positive_checks(text):
    assert scan_record({"t": text}) == []


def test_plain_12_word_prose_not_seed_phrase():
    prose = "deploy staging build passed after rebase fixed lint config cache tests green"
    assert len(prose.split()) == 12
    assert "seed_phrase" not in scan_text(prose)


def test_bip39_wordlist_run_flagged():
    words = ("abandon ability able about above absent absorb abstract absurd abuse access accident").split()
    assert "seed_phrase" in scan_text("|".join(words))


def test_zero_width_and_bidi_rejected_as_obfuscation():
    assert "obfuscation" in scan_text("hello\u200bworld")
    assert "obfuscation" in scan_text("abc\u202edef")
    assert "obfuscation" in scan_record({"t": "x\u2066y"})


_REDOS = {
    "env": lambda: "A" * 50000 + "KEY",
    "cand": lambda: "a" * 60000,
    "b58": lambda: "1" * 60000,
    "userpass": lambda: "a://" + "a:" * 30000,
    "bearer": lambda: "bearer " + "a" * 60000,
    "b64": lambda: "QUJD" * 15000,
}


@pytest.mark.parametrize("label", sorted(_REDOS))
def test_redos_60k_under_half_second(label):
    text = _REDOS[label]()
    t = _time.perf_counter()
    scan_text(text)
    assert _time.perf_counter() - t < 0.5, label
