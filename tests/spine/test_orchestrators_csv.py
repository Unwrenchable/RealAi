"""QA: docs/spine/orchestrators.csv must be reproducible from git blobs (CRLF/LF independent)."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "docs/spine/build_orchestrators_csv.py"
CSV = ROOT / "docs/spine/orchestrators.csv"


def test_csv_regenerates_byte_identical(tmp_path):
    out = tmp_path / "orchestrators.csv"
    subprocess.run([sys.executable, str(SCRIPT), "--out", str(out)], cwd=ROOT, check=True, capture_output=True)
    committed = subprocess.run(["git", "show", ":docs/spine/orchestrators.csv"], cwd=ROOT, capture_output=True)
    expected = committed.stdout if committed.returncode == 0 else CSV.read_bytes().replace(b"\r\n", b"\n")
    assert out.read_bytes() == expected, "orchestrators.csv is stale: run python docs/spine/build_orchestrators_csv.py"


def test_csv_excludes_docs_spine():
    assert b"docs/spine/" not in CSV.read_bytes().replace(b"\r\n", b"\n")
