"""ttt9d_move ability: legal moves, tactics, determinism, schema, speed, logging, tools/execute routing."""
import json
import random
import time

import pytest

from abilities import ttt9d_move as T


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
    assert out["logged_to"] == "enabled"
    rec = json.loads(p.read_text().splitlines()[0])
    assert rec["difficulty"] == "easy" and set(rec) >= {"state", "move", "eval", "iterations"}


def test_logging_defaults_to_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_TTT9D_LOG", "1")
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy", "log": True})
    expected = tmp_path / "data" / "games" / "ttt9d_moves.jsonl"
    assert out["logged_to"] == "enabled" and expected.exists()


def test_caller_log_path_is_ignored(tmp_path, monkeypatch):
    """A caller-supplied log path must never be written (no arbitrary file append)."""
    monkeypatch.setenv("REALAI_TTT9D_LOG", "1")
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    evil = tmp_path / "elsewhere" / "evil.jsonl"
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy", "log": str(evil)})
    assert not evil.exists() and not evil.parent.exists()
    assert out["logged_to"] == "enabled" and (tmp_path / "data" / "games" / "ttt9d_moves.jsonl").exists()


def test_no_logging_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("REALAI_TTT9D_LOG", raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert "logged_to" not in out and not (tmp_path / "data").exists()


def test_m1_caller_log_true_alone_does_not_log(tmp_path, monkeypatch):
    monkeypatch.delenv("REALAI_TTT9D_LOG", raising=False)
    monkeypatch.setenv("REALAI_DATA_DIR", str(tmp_path / "data"))
    for v in (True, "1", str(tmp_path / "evil.jsonl")):
        out = T.run(context={"state": T.empty_state(), "difficulty": "easy", "log": v})
        assert "logged_to" not in out
    assert not (tmp_path / "data").exists() and not (tmp_path / "evil.jsonl").exists()


def test_m1_log_file_size_cap(tmp_path, monkeypatch):
    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    monkeypatch.setattr(T, "MAX_LOG_BYTES", 2000)
    for _ in range(40):
        T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    size = p.stat().st_size
    assert 0 < size <= 2000
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert out.get("log_skipped") == "log_full" and p.stat().st_size == size


def test_m1_record_size_cap(tmp_path, monkeypatch):
    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    monkeypatch.setattr(T, "MAX_RECORD_BYTES", 100)
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert out["ok"] and out.get("log_skipped") == "record_too_large" and not p.exists()


def test_m1_default_caps():
    assert T.MAX_LOG_BYTES == 5 * 1024 * 1024 and 0 < T.MAX_RECORD_BYTES <= 64 * 1024


def test_m2_iterations_clamped():
    assert T.clamp_iterations(10**12) == T.MAX_ITERATIONS
    assert T.clamp_iterations(-5) == T.MIN_ITERATIONS
    assert T.clamp_iterations(0) == T.MIN_ITERATIONS
    assert T.clamp_iterations("50") == 50
    r = T.get_move(T.empty_state(), "hard", seed=1, iterations=10**9, max_seconds=0.2)
    assert r["iterations"] <= T.MAX_ITERATIONS


def test_m2_seconds_clamped():
    assert T.clamp_seconds(10**9) == T.MAX_SECONDS
    assert T.clamp_seconds(0.0001) == T.MIN_SECONDS
    assert T.clamp_seconds(-3) == T.MIN_SECONDS
    assert T.clamp_seconds(None) is None and T.clamp_seconds(0) is None


@pytest.mark.parametrize("field", ["iterations", "max_seconds"])
@pytest.mark.parametrize("bad", [True, "abc", float("nan"), float("inf"), [1], {"a": 1}])
def test_m2_bad_types_rejected(field, bad):
    out = T.run(context={"state": T.empty_state(), "difficulty": "hard", field: bad})
    assert out["ok"] is False and field in out["error"]


def test_m2_huge_budget_is_bounded_in_time():
    t0 = time.monotonic()
    out = T.run(context={"state": T.empty_state(), "difficulty": "expert", "seed": 3,
                         "iterations": 10**9, "max_seconds": 0.3})
    assert out["ok"] and time.monotonic() - t0 < 5


def test_low1_open_flags_and_mode(tmp_path, monkeypatch):
    import os

    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    seen = {}
    real_open = os.open

    def spy(path, flags, mode=0o777, *a, **k):
        seen["flags"], seen["mode"] = flags, mode
        return real_open(path, flags, mode, *a, **k)

    monkeypatch.setattr(T.os, "open", spy)
    T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    for f in ("O_WRONLY", "O_APPEND", "O_CREAT"):
        assert seen["flags"] & getattr(os, f)
    if hasattr(os, "O_NOFOLLOW"):
        assert seen["flags"] & os.O_NOFOLLOW
    assert seen["mode"] == 0o600


@pytest.mark.skipif(not hasattr(__import__("os"), "O_NOFOLLOW"), reason="O_NOFOLLOW not available")
def test_low1_symlink_refused(tmp_path, monkeypatch):
    import os

    target = tmp_path / "target.txt"
    target.write_text("x")
    link = tmp_path / "ttt.jsonl"
    os.symlink(target, link)
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(link))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert out["ok"] and out["log_error"] == "log_failed" and target.read_text() == "x"


def test_low1_size_from_fstat(tmp_path, monkeypatch):
    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    calls = []
    real = T.os.fstat
    monkeypatch.setattr(T.os, "fstat", lambda fd: calls.append(fd) or real(fd))
    T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert calls


@pytest.mark.parametrize("bad", [-1, 2 ** 63, 1.5, True, "abc", float("nan"), [1]])
def test_low2_bad_seed_rejected(bad):
    out = T.run(context={"state": T.empty_state(), "difficulty": "hard", "seed": bad})
    assert out["ok"] is False and "seed" in out["error"]


def test_low2_good_seeds():
    assert T.validate_seed(0) == 0 and T.validate_seed(2 ** 63 - 1) == 2 ** 63 - 1
    assert T.validate_seed("42") == 42 and T.validate_seed(7.0) == 7


def test_low3_logs_normalized_board(tmp_path, monkeypatch):
    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    st = T.empty_state()
    st["junk"] = "FAKE-extra-" + "z" * 50
    st["boards"][0][0] = "X"
    T.run(context={"state": st, "difficulty": "easy"})
    rec = json.loads(p.read_text().splitlines()[0])
    assert "junk" not in rec["state"] and "FAKE-extra" not in p.read_text()
    assert rec["state"]["boards"][0][0] == "X"


@pytest.mark.parametrize("exc", [RecursionError("deep"), OSError("disk"), ValueError("x")])
def test_low3_log_failure_never_breaks_move(tmp_path, monkeypatch, exc):
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(tmp_path / "ttt.jsonl"))

    def boom(_):
        raise exc

    monkeypatch.setattr(T, "_log", boom)
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert out["ok"] and "move" in out and out["log_error"] == "log_failed"


def test_low4_lock_held_around_fstat_and_write(tmp_path, monkeypatch):
    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    events = []
    real_fstat, real_write = T.os.fstat, T.os.write
    monkeypatch.setattr(T, "_lock_fd", lambda fd: events.append("lock"))
    monkeypatch.setattr(T, "_unlock_fd", lambda fd: events.append("unlock"))
    monkeypatch.setattr(T.os, "fstat", lambda fd: events.append("fstat") or real_fstat(fd))
    monkeypatch.setattr(T.os, "write", lambda fd, d: events.append("write") or real_write(fd, d))
    T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert events == ["lock", "fstat", "write", "unlock"]


def test_low4_real_lock_roundtrip(tmp_path, monkeypatch):
    p = tmp_path / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    for _ in range(3):
        assert T.run(context={"state": T.empty_state(), "difficulty": "easy"})["logged_to"] == "enabled"
    assert len(p.read_text().splitlines()) == 3


def test_low5_no_server_paths_in_output(tmp_path, monkeypatch):
    p = tmp_path / "secretdir" / "ttt.jsonl"
    monkeypatch.setenv("REALAI_TTT9D_LOG", str(p))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert out["logged_to"] == "enabled" and "secretdir" not in json.dumps(out)
    monkeypatch.setattr(T, "_log", lambda r: (_ for _ in ()).throw(OSError(str(p))))
    out = T.run(context={"state": T.empty_state(), "difficulty": "easy"})
    assert out["log_error"] == "log_failed" and "secretdir" not in json.dumps(out)


def test_tools_execute_routing():
    bridge = pytest.importorskip("realai.orchestration.v3_runtime_bridge")
    out = bridge.execute_registry_tool("ttt9d_move", {"state": T.empty_state(), "difficulty": "easy"})
    assert out.get("ok") is True and "move" in out, out
