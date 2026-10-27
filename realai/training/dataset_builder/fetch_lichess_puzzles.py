"""Stream a small sample of the Lichess puzzle database (CC0) without downloading all of it.

python -m realai.training.dataset_builder.fetch_lichess_puzzles --rows 1500 --scan 30000
-> REALAI_HOME/datasets/_sources/lichess_puzzles_sample.csv (+ SOURCE.md). Only the first
--scan rows are streamed (a few MB of the ~300 MB file); every k-th row is kept.
"""
from __future__ import annotations

import argparse
import csv
import io
import itertools
import time
import urllib.request
from pathlib import Path

from .pipeline import realai_home

URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1500)
    ap.add_argument("--scan", type=int, default=30000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    import zstandard

    out = Path(a.out) if a.out else realai_home() / "datasets" / "_sources" / "lichess_puzzles_sample.csv"
    home = realai_home()
    if home not in out.resolve().parents:
        raise SystemExit(f"refusing to write outside REALAI_HOME: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    step = max(1, a.scan // a.rows)
    with urllib.request.urlopen(URL, timeout=60) as r:
        rd = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(r), encoding="utf-8")
        reader = csv.reader(rd)
        header = next(reader)
        keep = [row for i, row in enumerate(itertools.islice(reader, a.scan)) if i % step == 0][: a.rows]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(keep)
    (out.parent / "lichess_puzzles_SOURCE.md").write_text(
        f"Lichess puzzle database sample\n\nSource: {URL} (CC0 1.0, https://database.lichess.org/)\n"
        f"Fetched: {time.strftime('%Y-%m-%d')} | first {a.scan} rows streamed, every {step}th kept | rows: {len(keep)}\n",
        encoding="utf-8")
    print(f"{len(keep)} puzzles -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
