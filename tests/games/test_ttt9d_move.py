"""ttt9d_move ability: legal moves, tactics, determinism, schema, speed, logging, tools/execute routing."""
import json
import random
import time
from pathlib import Path

import pytest

from abilities import ttt9d_move as T

_ROOT = Path(__file__).resolve().parents[2]


def _random_state(seed, plies):
    rng = random.Random(seed)
    s = T.parse_state(T.empty_state())
    for _ in range(plies):
        ms = T._moves(s)
        if not ms:
            break
        T._play(s, rng.choice(ms))
    return s


def _legal(pub):
    return {(m // 9, m % 9) for m in T._moves(T.parse_state(pub))}


def test_legal_moves_all_difficulties():
    for i in range(30):
        s = _random_state(i, i % 35)
        if s.result:
            continue
        pub = T.to_public(s)
        for d in ("easy", "medium", "hard", "expert"):
            r = T.get_move(pub, d, seed=i, iterations=60)
            assert (r["move"]["board"], r["move"]["cell"]) in _legal(pub)
            assert -1.0 <= r["eval"] <= 1.0


def test_respects_active_board():
    s = T.parse_state(T.empty_state())
    T._play(s, 4 * 9 + 2)
    pub = T.to_public(s)
    assert pub["activeBoard"] == 2
    for seed in range(5):
        assert T.get_move(pub, "easy", seed=seed)["move"]["board"] == 2


def test_win_in_one_constructed():
    st = T.empty_state()
    st["boards"][0] = ["X", "X", "X", None, "O", None, "O", None, None]
    st["boards"][1] = ["X", "X", "X", "O", None, "O", None, None, None]
    st["boards"][2] = ["X", "X", None, "O", "O", None, None, None, None]
    st["activeBoard"], st["currentPlayer"] = 2, "X"
    for d in ("medium", "hard", "expert"):
        for seed in range(10):
            r = T.get_move(st, d, seed=seed, iterations=50)
            assert r["move"] == {"board": 2, "cell": 2} and r["eval"] == 1.0


def test_hard_never_misses_win_in_one_random():
    checked = 0
    for i in range(500):
        s = _random_state(1000 + i, 20 + i % 40)
        if s.result:
            continue
        wins = []
        for m in T._moves(s):
            t = s.copy()
            T._play(t, m)
            if t.result == s.player:
                wins.append({"board": m // 9, "cell": m % 9})
        if not wins:
            continue
        checked += 1
        assert T.get_move(T.to_public(s), "hard", seed=i, iterations=50)["move"] in wins
        if checked >= 20:
            break
    assert checked >= 5


def test_deterministic():
    pub = T.to_public(_random_state(7, 12))
    assert T.get_move(pub, "hard", seed=3) == T.get_move(pub, "hard", seed=3)
    assert T.run(context={"state": pub, "difficulty": "expert"}) == T.run(context={"state": pub, "difficulty": "expert"})


def test_speed_default_budgets():
    pub = T.empty_state()
    for d, cap in (("easy", 1.0), ("medium", 2.0), ("hard", 4.0), ("expert", 10.0)):
        t = time.time()
        T.get_move(pub, d)
        assert time.time() - t < cap, d


def test_run_schema_errors_and_commentary():
    out = T.run(context={"state": T.empty_state(), "difficulty": "medium", "commentary": True})
    assert out["ok"] and out["ability"] == "ttt9d_move" and out["source"] == "realai"
    assert set(out["move"]) == {"board", "cell"} and isinstance(out["eval"], float)
    assert "board" in out["commentary"]
    assert T.run(context={})["ok"] is False
    assert T.run(context={"state": {"boards": [[None] * 9] * 3}})["ok"] is False
    full = T.empty_state()
    full["boards"][0] = full["boards"][1] = full["boards"][2] = ["X"] * 9
    assert T.run(context={"state": full})["ok"] is False  # game over
    # JSON string input
    assert T.run(input=json.dumps({"state": T.empty_state(), "difficulty": "easy"}))["ok"]


def test_commentary_hook(monkeypatch):
    monkeypatch.setattr(T, "COMMENTARY_HOOK", lambda st, r: "custom")
    assert T.run(context={"state": T.empty_state(), "commentary": True})["commentary"] == "custom"


def test_logging(tmp_path, monkeypatch):
    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert out["logged_to"] == str(p)
    rec = json.loads(p.read_text().splitlines()[0])
    assert rec["difficulty"] == "easy" and set(rec) >= {"state", "move", "eval", "iterations"}


def test_logging_defaults_to_data_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("REALAI_TTT9D_LOG", raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy", "log": True})
    expected = tmp_path / "data" / "games" / "ttt9d_moves.jsonl"
    assert out["logged_to"] == str(expected) and expected.exists()


def test_caller_log_path_is_ignored(tmp_path, monkeypatch):
    """A caller-supplied log path must never be written (no arbitrary file append)."""
    monkeypatch.delenv("REALAI_TTT9D_LOG", raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    evil = tmp_path / "elsewhere" / "evil.jsonl"
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy", "log": str(evil)})
    assert not evil.exists() and not evil.parent.exists()
    assert out["logged_to"] == str(tmp_path / "data" / "games" / "ttt9d_moves.jsonl")


def test_no_logging_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("REALAI_TTT9D_LOG", raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert "logged_to" not in out and not (tmp_path / "data").exists()


def test_tools_execute_routing():
    bridge = pytest.importorskip("realai.orchestration.v3_runtime_bridge")
    out = bridge.execute_registry_tool("ttt9d_move", {"state": T.empty_state(), "difficulty": "easy"})
    assert out.get("ok") is True and "move" in out, out


def _won(mark):
    other = "O" if mark == "X" else "X"
    return [mark, mark, mark, other, other, mark, other, mark, other]


def _draw_board():
    return ["X", "O", "X", "O", "X", "O", "O", "X", "O"]


def test_rejects_invalid_cells_and_player():
    """Cells outside \"X\" | \"O\" | null, and a bad side to move, are input errors."""
    st = T.empty_state()
    st["boards"][0][0] = "x"
    with pytest.raises(ValueError, match="must be"):
        T.parse_state(st)
    st = T.empty_state()
    st["boards"][4][8] = 0
    with pytest.raises(ValueError, match="must be"):
        T.parse_state(st)
    st = T.empty_state()
    st["boards"][2][3] = {"mark": "X"}
    with pytest.raises(ValueError, match="must be"):
        T.parse_state(st)
    assert T.run(context={"state": st})["ok"] is False
    # JSON body (the input= path) is validated the same way, not coerced.
    raw = T.empty_state()
    raw["boards"][1][1] = "x"
    assert T.run(input=json.dumps(raw))["ok"] is False
    raw = T.empty_state()
    raw["currentPlayer"] = "x"
    assert T.run(input=json.dumps({"state": raw}))["ok"] is False
    raw["currentPlayer"] = 0
    assert T.run(context={"state": raw})["ok"] is False
    ok = T.empty_state()
    ok["boards"][0][0] = "X"
    ok["boards"][0][1] = "O"
    parsed = T.parse_state(ok)
    assert parsed.cells[0] == 1 and parsed.cells[1] == 2 and parsed.cells[2] == 0
    assert parsed.player == 1


def test_forced_move_terminal_eval():
    """A sole legal move that ends the game is scored from the side to move, not left at 0."""
    meta = T.empty_state()
    meta["boards"][1] = _won("X")
    meta["boards"][2] = _won("X")
    meta["boards"][0] = ["X", "X", None, "O", "O", "X", "X", "O", "O"]
    meta["activeBoard"] = 0
    meta["currentPlayer"] = "X"
    root = T.parse_state(meta)
    assert len(T._moves(root)) == 1 and root.result == 0
    for d in ("easy", "medium", "hard", "expert"):
        r = T.get_move(meta, d, seed=1, iterations=1)
        assert r["move"] == {"board": 0, "cell": 2} and r["eval"] == 1.0 and r["iterations"] == 0

    points = T.empty_state()
    points["boards"][0] = _won("O")
    points["boards"][1] = _won("X")
    points["boards"][2] = _draw_board()
    points["boards"][3] = _won("X")
    points["boards"][4] = _draw_board()
    points["boards"][5] = _won("O")
    points["boards"][6] = _draw_board()
    points["boards"][7] = _draw_board()
    points["boards"][8] = ["X", "X", None, "O", "O", "X", "O", "X", "O"]
    points["activeBoard"] = 8
    points["currentPlayer"] = "X"
    assert len(T._moves(T.parse_state(points))) == 1
    r = T.get_move(points, "easy", seed=1, iterations=1)
    assert r["move"] == {"board": 8, "cell": 2} and r["eval"] == 1.0

    losing = T.empty_state()
    losing["boards"][0] = _won("O")
    losing["boards"][1] = _won("X")
    losing["boards"][2] = _draw_board()
    losing["boards"][3] = _won("X")
    losing["boards"][4] = _draw_board()
    losing["boards"][5] = _won("O")
    losing["boards"][6] = _draw_board()
    losing["boards"][7] = _won("O")
    losing["boards"][8] = ["O", "X", "O", "X", "O", "X", "X", "O", None]
    losing["activeBoard"] = 8
    losing["currentPlayer"] = "X"
    assert len(T._moves(T.parse_state(losing))) == 1
    r = T.get_move(losing, "hard", seed=1, iterations=1)
    assert r["move"] == {"board": 8, "cell": 8} and r["eval"] == -1.0

    drawn = T.empty_state()
    for i in range(8):
        drawn["boards"][i] = _draw_board()
    drawn["boards"][8] = ["O", "X", "O", "X", "O", "X", "X", "O", None]
    drawn["activeBoard"] = 8
    r = T.get_move(drawn, "medium", seed=1, iterations=1)
    assert r["move"] == {"board": 8, "cell": 8} and r["eval"] == 0.0

    quiet = T.empty_state()
    quiet["boards"][0] = ["X", "O", None, "O", "X", "X", "O", "X", "O"]
    quiet["activeBoard"] = 0
    r = T.get_move(quiet, "expert", seed=1, iterations=1)
    assert r["move"] == {"board": 0, "cell": 2} and r["eval"] == 0.0


def test_commentary_follows_post_move_state():
    text = T.default_commentary(T.empty_state(), {"move": {"board": 0, "cell": 4}, "eval": 0.0})
    assert "sending the opponent to board 5" in text

    sent_away = T.empty_state()
    sent_away["boards"][4] = _won("X")
    text = T.default_commentary(sent_away, {"move": {"board": 0, "cell": 4}, "eval": 0.0})
    assert "any open board" in text
    assert "sending the opponent to board 5" not in text

    completes = T.empty_state()
    completes["boards"][0] = [None, "X", "X", "O", "O", "X", "O", "X", "O"]
    completes["activeBoard"] = 0
    text = T.default_commentary(completes, {"move": {"board": 0, "cell": 0}, "eval": 0.2})
    assert "any open board" in text
    assert "sending the opponent" not in text

    meta = T.empty_state()
    meta["boards"][1] = _won("X")
    meta["boards"][2] = _won("X")
    meta["boards"][0] = ["X", "X", None, "O", "O", "X", "X", "O", "O"]
    meta["activeBoard"] = 0
    text = T.default_commentary(meta, {"move": {"board": 0, "cell": 2}, "eval": 1.0})
    assert "game is over" in text and "wins" in text
    assert "sending the opponent" not in text

    losing = T.empty_state()
    losing["boards"][0] = _won("O")
    losing["boards"][1] = _won("X")
    losing["boards"][2] = _draw_board()
    losing["boards"][3] = _won("X")
    losing["boards"][4] = _draw_board()
    losing["boards"][5] = _won("O")
    losing["boards"][6] = _draw_board()
    losing["boards"][7] = _won("O")
    losing["boards"][8] = ["O", "X", "O", "X", "O", "X", "X", "O", None]
    losing["activeBoard"] = 8
    text = T.default_commentary(losing, {"move": {"board": 8, "cell": 8}, "eval": -1.0})
    assert "game is over" in text and "loses" in text
    assert "sending the opponent" not in text


def test_caller_log_rejects_absolute_and_traversal(tmp_path, monkeypatch):
    """Caller log paths are not opened. Absolute paths and '..' never leave the fixed log directory."""
    monkeypatch.delenv("REALAI_TTT9D_LOG", raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)
    safe = tmp_path / "data" / "games" / "ttt9d_moves.jsonl"
    escape = tmp_path.parent / "ttt9d-escape-pr157.jsonl"
    absolute = tmp_path / "abs-evil.jsonl"
    posix_abs = Path("/tmp/ttt9d-should-not-exist-pr157.jsonl")
    cases = [
        str(absolute),
        "../ttt9d-escape-pr157.jsonl",
        "games/../../ttt9d-escape-pr157.jsonl",
        "..\\ttt9d-escape-pr157.jsonl",
        "C:\\Windows\\Temp\\ttt9d-pr157.jsonl",
        "\\\\server\\share\\ttt9d-pr157.jsonl",
        str(posix_abs),
        "safe\x00.jsonl",
    ]
    ctx = {"state": T.empty_state(), "difficulty": "easy", "iterations": 1, "seed": 1}
    for raw in cases:
        out = T.run(context={**ctx, "log": raw})
        assert out["ok"] is True, raw
        assert out.get("logged_to") == str(safe), raw
        assert "log_rejected" in out, raw
        assert "absolute" in out["log_rejected"] or "traversal" in out["log_rejected"] or "invalid" in out["log_rejected"]
    assert safe.is_file()
    assert not absolute.exists()
    assert not escape.exists()
    assert not posix_abs.exists()
    # A relative name is not a write target either; the fixed file is.
    other = tmp_path / "data" / "games" / "other.jsonl"
    out = T.run(context={**ctx, "log": "other.jsonl"})
    assert out["logged_to"] == str(safe) and not other.exists()
    logged = Path(out["logged_to"]).resolve()
    assert logged.parent == (tmp_path / "data" / "games").resolve()
    assert logged.name == "ttt9d_moves.jsonl"


def test_provenance_and_generated_surface():
    """Cite the real 9dttt commit/path, and keep the generated catalog consumers in sync."""
    src = Path(T.__file__).read_text(encoding="utf-8")
    catalog = (_ROOT / "realai" / "ability_catalog.py").read_text(encoding="utf-8")
    for text in (src, catalog):
        assert "cad17a9641e24f03bb8f1acfdbd5603866e951af" in text
        assert "Public/js/ultimate-tictactoe.js" in text
        assert "Public/js/ai/ttt9d-engine.js" in text
        assert "no Public/js/ai" in text or "no ``Public/js/ai``" in text
    md = (_ROOT / "docs" / "ABILITY_SURFACE.md").read_text(encoding="utf-8")
    assert "| `ttt9d_move` |" in md
    samples = (_ROOT / "training" / "data" / "ability_surface.jsonl").read_text(encoding="utf-8")
    assert "`ttt9d_move`" in samples and "is LIVE" in samples


def test_tools_execute_rejects_caller_log_path(tmp_path, monkeypatch):
    monkeypatch.delenv("REALAI_TTT9D_LOG", raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    bridge = pytest.importorskip("realai.orchestration.v3_runtime_bridge")
    evil = tmp_path / "from-execute.jsonl"
    out = bridge.execute_registry_tool(
        "ttt9d_move",
        {
            "state": T.empty_state(),
            "difficulty": "easy",
            "iterations": 1,
            "seed": 1,
            "log": str(evil),
        },
    )
    assert out.get("ok") is True, out
    assert not evil.exists()
    assert "absolute" in out.get("log_rejected", "")
    assert out.get("logged_to") == str(tmp_path / "data" / "games" / "ttt9d_moves.jsonl")
