import json

import pytest

chess = pytest.importorskip("chess")

from realai.training.dataset_builder.adapters import ADAPTERS

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _rec(**kw):
    base = {"fen": START, "side": "White", "history_san": "(no moves yet)", "legal": True, "model_move_san": "a3",
            "model_move_uci": "a2a3", "sf_depth": 12, "sf_best_san": "e4", "sf_best_uci": "e2e4",
            "sf_pv_san": "1. e4 e5 2. Nf3", "sf_eval_cp": 30, "sf_mate": None, "cp_loss": 40, "matched_best": False}
    base.update(kw)
    return base


def test_target_is_stockfish_not_model_and_dedup(tmp_path):
    p = tmp_path / "match-1.jsonl"
    recs = [_rec(), _rec(fen=START.replace(" 0 1", " 0 7")),  # same position, different counters -> dedup
            _rec(legal=False, model_move_san=None, model_move_uci=None),
            {"fen": START, "legal": True}]  # no engine analysis -> skipped
    p.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
    rows = list(ADAPTERS["chess_selfplay_experience"]({"paths": [str(tmp_path / "*.jsonl")]}, {"roots": {}}))
    assert len(rows) == 1
    ans = rows[0]["messages"][-1]["content"]
    assert ans.splitlines()[-1] == "e4" and "a3" not in ans
    assert "own-data" in rows[0]["meta"]["tags"]


def test_no_files_no_rows(tmp_path):
    assert list(ADAPTERS["chess_selfplay_experience"]({"paths": [str(tmp_path / "x" / "*.jsonl")]}, {"roots": {}})) == []
