"""9D (Ultimate) Tic-Tac-Toe move engine as a RealAI ability.

Pure-Python Monte-Carlo tree search port of 9dttt's ``Public/js/ai/ttt9d-engine.js``. No LLM,
no network, no third-party deps; deterministic for a given (state, difficulty, seed).

Call:  POST /v1/tools/execute {"name": "ttt9d_move", "arguments": {"state": {...}, "difficulty": "hard"}}
       or abilities.ttt9d_move.run(context={"state": ..., "difficulty": ...}) in-process.

Input (same schema as the JS engine's getMove(state, difficulty)):
    state = {"boards": [[9 x "X"|"O"|null] x 9], "activeBoard": 0..8 | null, "currentPlayer": "X"|"O"}
    difficulty = "easy" | "medium" | "hard" | "expert"   (default "medium")
    optional: seed (int, 0 <= seed < 2**63), iterations (int, clamped), max_seconds (float, clamped), commentary (bool)
Output:
    {"ok": true, "ability": "ttt9d_move", "move": {"board": b, "cell": c}, "eval": float in [-1, 1]
     (side-to-move perspective), "difficulty": ..., "iterations": n, "source": "realai",
     "legal_moves": n, ["commentary": str]}

Optional training-data logging (off by default): operator sets REALAI_TTT9D_LOG=1 (or a path); callers cannot enable it.
Each call appends {"ts", "state", "difficulty", "move", "eval", "iterations"} — a position→engine-move
record in the same spirit as the chess_stockfish dataset cache (``*.stockfish_d{depth}.jsonl``).
"""
from __future__ import annotations

import json
import math
import os
import random
import time

try:  # file locking for the move log (fix 4)
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None  # type: ignore
try:
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ABILITY = {
    "id": "ttt9d_move",
    "name": "ttt9d_move",
    "type": "ability",
    "status": "LIVE",
    "source": "pure-Python MCTS port of 9dttt Public/js/ai/ttt9d-engine.js",
    "dest": "abilities/ttt9d_move.py",
    "capabilities": ["ultimate_tic_tac_toe", "9dttt", "best_move", "evaluation", "game_ai"],
    "secrets_policy": "none",
}

LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))
# Python is ~20-50x slower than V8, so iteration budgets are smaller than the JS engine's.
DIFFICULTY = {
    "easy": {"iterations": 100, "blunder": 0.35, "tactics": False},
    "medium": {"iterations": 800, "blunder": 0.10, "tactics": True},
    "hard": {"iterations": 3000, "blunder": 0.0, "tactics": True},
    "expert": {"iterations": 8000, "blunder": 0.0, "tactics": True},
}
MAX_ITERATIONS = 20000
MIN_ITERATIONS = 1
MIN_SECONDS = 0.05
MAX_SECONDS = 10.0
# Move log limits (M1): logging needs the operator flag, the path is server-side only.
MAX_LOG_BYTES = 5 * 1024 * 1024
MAX_RECORD_BYTES = 16 * 1024
_LOG_FLAG_VALUES = {"1", "true", "yes", "on"}
DEFAULT_SEED = 0x9D77

# Optional commentary hook: callable(state, result) -> str. Default is a template (no LLM).
COMMENTARY_HOOK: Optional[Callable[[Dict[str, Any], Dict[str, Any]], str]] = None


class State:
    __slots__ = ("cells", "meta", "pts", "player", "active", "result")

    def copy(self) -> "State":
        s = State.__new__(State)
        s.cells = self.cells[:]
        s.meta = self.meta[:]
        s.pts = self.pts[:]
        s.player, s.active, s.result = self.player, self.active, self.result
        return s


def _update_meta(s: State, b: int) -> None:
    o = b * 9
    c = s.cells
    filled = sum(1 for i in range(9) if c[o + i])
    for a, d, e in LINES:
        v = c[o + a]
        if v and v == c[o + d] and v == c[o + e]:
            s.meta[b] = v
            s.pts[v] += filled
            return
    s.meta[b] = 3 if filled == 9 else 0


def _compute_result(s: State) -> int:
    m = s.meta
    for a, b, c in LINES:
        v = m[a]
        if v in (1, 2) and v == m[b] and v == m[c]:
            return v
    if 0 in m:
        return 0
    return 1 if s.pts[1] > s.pts[2] else 2 if s.pts[2] > s.pts[1] else 3


def parse_state(state: Dict[str, Any]) -> State:
    boards = state.get("boards") if isinstance(state, dict) else None
    if not isinstance(boards, list) or len(boards) != 9 or any(not isinstance(b, list) or len(b) != 9 for b in boards):
        raise ValueError("state.boards must be 9 arrays of 9")
    s = State.__new__(State)
    s.cells = [1 if v == "X" else 2 if v == "O" else 0 for bd in boards for v in bd]
    s.meta, s.pts = [0] * 9, [0, 0, 0]
    for b in range(9):
        _update_meta(s, b)
    s.player = 2 if state.get("currentPlayer") == "O" else 1
    ab = state.get("activeBoard")
    s.active = int(ab) if ab is not None else -1
    if s.active >= 0 and (s.active > 8 or s.meta[s.active] != 0):
        s.active = -1
    s.result = _compute_result(s)
    return s


def to_public(s: State) -> Dict[str, Any]:
    sym = {0: None, 1: "X", 2: "O"}
    return {"boards": [[sym[s.cells[b * 9 + i]] for i in range(9)] for b in range(9)],
            "activeBoard": None if s.active < 0 else s.active, "currentPlayer": "X" if s.player == 1 else "O"}


def empty_state() -> Dict[str, Any]:
    return {"boards": [[None] * 9 for _ in range(9)], "activeBoard": None, "currentPlayer": "X"}


def _moves(s: State) -> List[int]:
    if s.result:
        return []
    out = []
    for b in range(9):
        if s.meta[b] or (s.active >= 0 and s.active != b):
            continue
        o = b * 9
        out.extend(o + i for i in range(9) if not s.cells[o + i])
    return out


def _play(s: State, m: int) -> None:
    b, i = divmod(m, 9)
    s.cells[m] = s.player
    _update_meta(s, b)
    s.active = i if s.meta[i] == 0 else -1
    s.player = 3 - s.player
    s.result = _compute_result(s)


def _winning_move(s: State, player: int) -> int:
    for m in _moves(s):
        t = s.copy()
        t.player = player
        _play(t, m)
        if t.result == player:
            return m
    return -1


def _rollout(s: State, rng: random.Random) -> int:
    while not s.result:
        ms = _moves(s)
        _play(s, ms[int(rng.random() * len(ms))])
    return s.result


def _mcts(root: State, iterations: int, rng: random.Random, deadline: float):
    # node: [parent, move, children(list|None), untried, wins, visits, mover]
    nodes = [[-1, -1, None, _moves(root), 0.0, 0, 3 - root.player]]
    it = 0
    while it < iterations:
        if deadline and (it & 63) == 0 and it and time.monotonic() > deadline:
            break
        idx, s = 0, root.copy()
        while not nodes[idx][3] and nodes[idx][2]:
            p = nodes[idx]
            ln = math.log(p[5])
            best, bv = -1, -1e18
            for c in p[2]:
                ch = nodes[c]
                v = ch[4] / ch[5] + 1.2 * math.sqrt(ln / ch[5])
                if v > bv:
                    bv, best = v, c
            idx = best
            _play(s, nodes[idx][1])
        node = nodes[idx]
        if node[3] and not s.result:
            k = int(rng.random() * len(node[3]))
            m = node[3][k]
            node[3][k] = node[3][-1]
            node[3].pop()
            mover = s.player
            _play(s, m)
            nodes.append([idx, m, None, _moves(s), 0.0, 0, mover])
            if node[2] is None:
                node[2] = []
            node[2].append(len(nodes) - 1)
            idx = len(nodes) - 1
        r = _rollout(s, rng)
        j = idx
        while j != -1:
            nd = nodes[j]
            nd[5] += 1
            nd[4] += 0.5 if r == 3 else (1.0 if r == nd[6] else 0.0)
            j = nd[0]
        it += 1
    kids = sorted((nodes[c] for c in (nodes[0][2] or [])), key=lambda n: (-n[5], n[1]))
    return kids, it


def _number(name: str, v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise TypeError(f"{name} must be a number")
    try:
        f = float(v)
    except ValueError:
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(f):
        raise ValueError(f"{name} must be finite")
    return f


def clamp_iterations(v: Any) -> int:
    """Clamp a caller iteration budget to [MIN_ITERATIONS, MAX_ITERATIONS]; reject non-numbers."""
    return int(max(MIN_ITERATIONS, min(MAX_ITERATIONS, _number("iterations", v))))


def clamp_seconds(v: Any) -> Optional[float]:
    """None/0 = no time limit; otherwise clamp to [MIN_SECONDS, MAX_SECONDS]; reject non-numbers."""
    if v is None:
        return None
    f = _number("max_seconds", v)
    if f == 0:
        return None
    return max(MIN_SECONDS, min(MAX_SECONDS, f))


MAX_SEED = 2 ** 63


def validate_seed(v: Any) -> int:
    """Seed must be an integer with 0 <= seed < 2**63 (bools, floats with fractions, NaN rejected)."""
    if isinstance(v, int) and not isinstance(v, bool):
        n = v
    else:
        f = _number("seed", v)
        if not f.is_integer():
            raise ValueError("seed must be an integer")
        n = int(f)
    if not 0 <= n < MAX_SEED:
        raise ValueError("seed must be in [0, 2**63)")
    return n


def get_move(state: Dict[str, Any], difficulty: str = "medium", seed: Optional[int] = None,
             iterations: Optional[int] = None, max_seconds: Optional[float] = None) -> Dict[str, Any]:
    level = difficulty if difficulty in DIFFICULTY else "medium"
    cfg = DIFFICULTY[level]
    s = parse_state(state)
    legal = _moves(s)
    if not legal:
        raise ValueError("no legal moves: game is over")
    rng = random.Random(DEFAULT_SEED if seed is None else validate_seed(seed))

    def done(m: int, ev: float, iters: int) -> Dict[str, Any]:
        return {"move": {"board": m // 9, "cell": m % 9}, "eval": round(max(-1.0, min(1.0, ev)), 3),
                "difficulty": level, "iterations": iters, "legal_moves": len(legal)}

    if len(legal) == 1:
        return done(legal[0], 0.0, 0)
    if cfg["tactics"]:
        w = _winning_move(s, s.player)
        if w >= 0:
            return done(w, 1.0, 0)
    if cfg["blunder"] and rng.random() < cfg["blunder"]:
        return done(legal[int(rng.random() * len(legal))], 0.0, 0)
    n = clamp_iterations(iterations if iterations is not None else cfg["iterations"])
    secs = clamp_seconds(max_seconds)
    deadline = time.monotonic() + secs if secs else 0.0
    kids, iters = _mcts(s, n, rng, deadline)
    pick = kids[0]
    if cfg["tactics"]:
        for ch in kids:  # avoid handing the opponent an immediate game win
            t = s.copy()
            _play(t, ch[1])
            if _winning_move(t, t.player) < 0:
                pick = ch
                break
    ev = (2 * pick[4] / pick[5] - 1) if pick[5] else 0.0
    return done(pick[1], ev, iters)


def default_commentary(state: Dict[str, Any], res: Dict[str, Any]) -> str:
    mv, ev = res["move"], res["eval"]
    mood = ("winning" if ev > 0.6 else "better" if ev > 0.15 else "roughly level" if ev > -0.15
            else "worse" if ev > -0.6 else "losing")
    return (f"{state.get('currentPlayer', 'X')} plays board {mv['board'] + 1}, cell {mv['cell'] + 1}, "
            f"sending the opponent to board {mv['cell'] + 1}. Position looks {mood} (eval {ev:+.2f}).")


def _log_enabled() -> bool:
    """Logging is an operator decision: only the REALAI_TTT9D_LOG env var turns it on."""
    return bool(os.environ.get("REALAI_TTT9D_LOG", "").strip())


def _log_path() -> Path:
    """Server-side log path, never from the caller.

    REALAI_TTT9D_LOG=1/true/yes/on -> REALAI_DATA_DIR/games/ttt9d_moves.jsonl;
    any other non-empty value is an operator-chosen path.
    """
    p = os.environ.get("REALAI_TTT9D_LOG", "").strip()
    if not p or p.lower() in _LOG_FLAG_VALUES:
        p = str(Path(os.environ.get("REALAI_DATA_DIR", "data")) / "games" / "ttt9d_moves.jsonl")
    return Path(p)


def _lock_fd(fd: int) -> None:
    if msvcrt is not None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
    elif fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_EX)


def _unlock_fd(fd: int) -> None:
    if msvcrt is not None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    elif fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _log_open_flags() -> int:
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    flags |= getattr(os, "O_NOFOLLOW", 0)  # refuse symlinks where the OS supports it
    flags |= getattr(os, "O_BINARY", 0)
    return flags


def _log(record: Dict[str, Any]) -> Dict[str, Any]:
    """Append one record. Returns {"logged_to": "enabled"} or {"log_skipped": reason}.

    Never returns a server path. Size comes from fstat on the open fd, under a lock.
    """
    data = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
    if len(data) > MAX_RECORD_BYTES:
        return {"log_skipped": "record_too_large"}
    pp = _log_path()
    pp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(pp), _log_open_flags(), 0o600)
    try:
        _lock_fd(fd)
        try:
            if os.fstat(fd).st_size + len(data) > MAX_LOG_BYTES:
                return {"log_skipped": "log_full"}
            os.write(fd, data)
        finally:
            _unlock_fd(fd)
    finally:
        os.close(fd)
    return {"logged_to": "enabled"}


def run(input: str = "", context: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    state = ctx.get("state")
    if state is None and input:
        try:
            parsed = json.loads(input)
            state = parsed.get("state", parsed) if isinstance(parsed, dict) else None
            if isinstance(parsed, dict):
                ctx.setdefault("difficulty", parsed.get("difficulty"))
        except (ValueError, TypeError):
            state = None
    if not isinstance(state, dict):
        return {"ok": False, "ability": "ttt9d_move", "error": "pass state={boards, activeBoard, currentPlayer}"}
    try:
        res = get_move(state, str(ctx.get("difficulty") or "medium"), seed=ctx.get("seed"),
                       iterations=ctx.get("iterations"), max_seconds=ctx.get("max_seconds"))
    except (ValueError, TypeError) as exc:
        return {"ok": False, "ability": "ttt9d_move", "error": f"{type(exc).__name__}: {exc}"}
    out: Dict[str, Any] = {"ok": True, "ability": "ttt9d_move", "source": "realai", **res}
    if ctx.get("commentary"):
        hook = COMMENTARY_HOOK or default_commentary
        try:
            out["commentary"] = hook(state, res)
        except Exception as exc:  # hook must never break move generation
            out["commentary_error"] = str(exc)
    # ctx["log"] is ignored: callers can neither enable logging nor pick the file (M1).
    if _log_enabled():
        try:
            board = to_public(parse_state(state))  # normalized board, not the raw caller state
            out.update(_log({
                "ts": time.time(), "state": board, "difficulty": res["difficulty"], "move": res["move"],
                "eval": res["eval"], "iterations": res["iterations"]}))
        except (Exception, RecursionError):  # logging must never break the move
            out["log_error"] = "log_failed"
    return out
