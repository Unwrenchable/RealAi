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
