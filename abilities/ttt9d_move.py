"""9D (Ultimate) Tic-Tac-Toe move engine as a RealAI ability.

Pure-Python Monte-Carlo tree search. No LLM, no network, no third-party deps; deterministic
for a given (state, difficulty, seed).

Board rules (nine local boards, active board, section points equal to the filled count,
meta-line win, then points when every board is complete) match the public 9dttt client:

    https://github.com/9dtictactoe/9dttt/blob/cad17a9641e24f03bb8f1acfdbd5603866e951af/Public/js/ultimate-tictactoe.js

That commit (``cad17a9641e24f03bb8f1acfdbd5603866e951af``) is the last change to
``Public/js/ultimate-tictactoe.js``. The repository has no ``Public/js/ai`` directory and
no ``ttt9d-engine.js``. ``getMove`` and the search live in this module.

Call:  POST /v1/tools/execute {"name": "ttt9d_move", "arguments": {"state": {...}, "difficulty": "hard"}}
       or abilities.ttt9d_move.run(context={"state": ..., "difficulty": ...}) in-process.

Input:
    state = {"boards": [[9 x "X"|"O"|null] x 9], "activeBoard": 0..8 | null, "currentPlayer": "X"|"O"}
    difficulty = "easy" | "medium" | "hard" | "expert"   (default "medium")
    optional: seed (int), iterations (int), commentary (bool), log (bool)
Output:
    {"ok": true, "ability": "ttt9d_move", "move": {"board": b, "cell": c}, "eval": float in [-1, 1]
     (side-to-move perspective), "difficulty": ..., "iterations": n, "source": "realai",
     "legal_moves": n, ["commentary": str]}

Optional training-data logging (off by default): set ``log`` true, or set the operator
environment variable ``REALAI_TTT9D_LOG``. A caller-supplied ``log`` string is never a file
path. Absolute paths and ``..`` traversal are rejected and not opened. The file is
``REALAI_TTT9D_LOG`` when the operator sets it, otherwise
``REALAI_DATA_DIR/games/ttt9d_moves.jsonl`` (``data/games`` when ``REALAI_DATA_DIR`` is unset).
Each call appends {"ts", "state", "difficulty", "move", "eval", "iterations"}.
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ABILITY = {
    "id": "ttt9d_move",
    "name": "ttt9d_move",
    "type": "ability",
    "status": "LIVE",
    "source": (
        "pure-Python MCTS; board rules from github.com/9dtictactoe/9dttt "
        "commit cad17a9641e24f03bb8f1acfdbd5603866e951af "
        "path Public/js/ultimate-tictactoe.js "
        "(that repo has no Public/js/ai/ttt9d-engine.js)"
    ),
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


def _cell_code(v: Any, board: int, cell: int) -> int:
    """Map a schema cell to 0/1/2. Anything else is an input error, not an empty square."""
    if v is None:
        return 0
    if v == "X":
        return 1
    if v == "O":
        return 2
    raise ValueError(f'state.boards[{board}][{cell}] must be "X", "O", or null (got {v!r})')


def parse_state(state: Dict[str, Any]) -> State:
    boards = state.get("boards") if isinstance(state, dict) else None
    if not isinstance(boards, list) or len(boards) != 9 or any(not isinstance(b, list) or len(b) != 9 for b in boards):
        raise ValueError("state.boards must be 9 arrays of 9")
    s = State.__new__(State)
    s.cells = [_cell_code(v, b, i) for b, bd in enumerate(boards) for i, v in enumerate(bd)]
    s.meta, s.pts = [0] * 9, [0, 0, 0]
    for b in range(9):
        _update_meta(s, b)
    player = state.get("currentPlayer")
    if player not in ("X", "O"):
        raise ValueError('state.currentPlayer must be "X" or "O"')
    s.player = 2 if player == "O" else 1
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


def get_move(state: Dict[str, Any], difficulty: str = "medium", seed: Optional[int] = None,
             iterations: Optional[int] = None, max_seconds: Optional[float] = None) -> Dict[str, Any]:
    level = difficulty if difficulty in DIFFICULTY else "medium"
    cfg = DIFFICULTY[level]
    s = parse_state(state)
    legal = _moves(s)
    if not legal:
        raise ValueError("no legal moves: game is over")
    rng = random.Random(DEFAULT_SEED if seed is None else int(seed))

    def done(m: int, ev: float, iters: int) -> Dict[str, Any]:
        return {"move": {"board": m // 9, "cell": m % 9}, "eval": round(max(-1.0, min(1.0, ev)), 3),
                "difficulty": level, "iterations": iters, "legal_moves": len(legal)}

    if len(legal) == 1:
        # A forced move can still finish the game (meta-line or points). Score that
        # terminal result from the side to move; a non-terminal sole move stays 0.
        m = legal[0]
        after = s.copy()
        _play(after, m)
        return done(m, _side_eval(s.player, after.result), 0)
    if cfg["tactics"]:
        w = _winning_move(s, s.player)
        if w >= 0:
            return done(w, 1.0, 0)
    if cfg["blunder"] and rng.random() < cfg["blunder"]:
        return done(legal[int(rng.random() * len(legal))], 0.0, 0)
    n = min(int(iterations if iterations is not None else cfg["iterations"]), MAX_ITERATIONS)
    deadline = time.monotonic() + float(max_seconds) if max_seconds else 0.0
    kids, iters = _mcts(s, max(1, n), rng, deadline)
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


def _side_eval(player: int, result: int) -> float:
    """Side-to-move eval of a terminal result. 0 when the game is still going or drawn."""
    if result == player:
        return 1.0
    if result == 3 - player:
        return -1.0
    return 0.0


def _commentary_follow(state: Dict[str, Any], mv: Dict[str, Any]) -> str:
    """Describe the opponent's situation from the position after the move.

    ``_play`` sends the opponent to the cell's board only when that board is still
    open. A completed destination, a move that completes it, or a finished game
    leaves free choice or a terminal result instead.
    """
    try:
        s = parse_state(state)
        mover = s.player
        _play(s, int(mv["board"]) * 9 + int(mv["cell"]))
    except (ValueError, TypeError, KeyError):
        return f"sending the opponent to board {int(mv['cell']) + 1}."
    if s.result == mover:
        return "and the game is over: that move wins."
    if s.result == 3 - mover:
        return "and the game is over: that move loses."
    if s.result == 3:
        return "and the game is over in a draw."
    if s.active < 0:
        return "and the opponent may play on any open board."
    return f"sending the opponent to board {s.active + 1}."


def default_commentary(state: Dict[str, Any], res: Dict[str, Any]) -> str:
    mv, ev = res["move"], res["eval"]
    who = state.get("currentPlayer") if state.get("currentPlayer") in ("X", "O") else "X"
    mood = ("winning" if ev > 0.6 else "better" if ev > 0.15 else "roughly level" if ev > -0.15
            else "worse" if ev > -0.6 else "losing")
    return (f"{who} plays board {mv['board'] + 1}, cell {mv['cell'] + 1}, "
            f"{_commentary_follow(state, mv)} Position looks {mood} (eval {ev:+.2f}).")


_LOG_FILENAME = "ttt9d_moves.jsonl"


def _safe_log_dir() -> Path:
    """Fixed directory for move logs: ``REALAI_DATA_DIR/games`` (default ``data/games``)."""
    base = Path(os.environ.get("REALAI_DATA_DIR", "data"))
    return (base / "games").resolve()


def _caller_log_path_error(raw: str) -> Optional[str]:
    """Reject a caller-supplied log path. The string is never opened.

    Absolute paths (POSIX, drive-letter, UNC) and any ``..`` segment are rejected.
    A relative name that would resolve outside the fixed log directory is rejected too.
    """
    if "\x00" in raw:
        return "log path rejected: invalid path"
    normalized = raw.strip().replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//"):
        return "log path rejected: absolute paths are not allowed"
    if len(normalized) >= 2 and normalized[1] == ":":
        return "log path rejected: absolute paths are not allowed"
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if ".." in parts:
        return "log path rejected: path traversal is not allowed"
    try:
        safe = _safe_log_dir()
        candidate = (safe / raw).resolve()
        if os.path.commonpath([str(safe), str(candidate)]) != str(safe):
            return "log path rejected: path escapes the log directory"
    except (OSError, ValueError):
        return "log path rejected: invalid path"
    return None


def _log_path() -> Path:
    """Where move logs go.

    Operators may set ``REALAI_TTT9D_LOG``. Otherwise the file is the fixed name
    inside ``_safe_log_dir``. Callers cannot choose the file.
    """
    override = os.environ.get("REALAI_TTT9D_LOG")
    if override:
        return Path(override)
    return _safe_log_dir() / _LOG_FILENAME


def _log(record: Dict[str, Any]) -> Optional[str]:
    pp = _log_path()
    pp.parent.mkdir(parents=True, exist_ok=True)
    with pp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(pp)


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
    log = ctx.get("log")
    if isinstance(log, str):
        rejected = _caller_log_path_error(log)
        if rejected:
            # Do not open the caller path. A truthy log still records to the fixed file.
            out["log_rejected"] = rejected
    if log or os.environ.get("REALAI_TTT9D_LOG"):
        try:
            out["logged_to"] = _log({
                "ts": time.time(), "state": state, "difficulty": res["difficulty"], "move": res["move"],
                "eval": res["eval"], "iterations": res["iterations"]})
        except OSError as exc:
            out["log_error"] = str(exc)
    return out
