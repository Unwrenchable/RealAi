"""Local Stockfish as a RealAI ability: the model defers strong chess play to the engine.

Engine lookup: context['engine'] -> $REALAI_STOCKFISH -> C:\\tools\\stockfish\\**\\stockfish*.exe ->
`stockfish` on PATH. Stockfish is GPLv3; it is called as an external tool, never bundled.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "chess_engine",
    "name": "chess_engine",
    "type": "ability",
    "status": "PARTIAL",
    "source": "local Stockfish via python-chess (operator installs C:\\tools\\stockfish)",
    "dest": "abilities/chess_engine.py",
    "capabilities": ["chess", "best_move", "evaluation", "stockfish"],
    "secrets_policy": "none",
}


def find_engine(explicit: Optional[str] = None) -> Optional[str]:
    for c in (explicit, os.environ.get("REALAI_STOCKFISH")):
        if c and Path(c).is_file():
            return str(c)
    root = Path(r"C:\tools\stockfish")
    if root.is_dir():
        hits = sorted(root.rglob("stockfish*.exe"))
        if hits:
            return str(hits[0])
    return shutil.which("stockfish")


def score_text(score, turn_white: bool) -> str:
    """Human eval from White's perspective, e.g. '+1.35 (White better)' or 'mate in 3 for Black'."""
    w = score.white()
    if w.is_mate():
        m = w.mate()
        side = "White" if m > 0 else "Black"
        return f"mate in {abs(m)} for {side}"
    cp = w.score()
    side = "White" if cp > 0 else "Black" if cp < 0 else "neither side"
    return f"{cp / 100:+.2f} pawns ({side} better)" if cp else "0.00 (equal)"


def analyse(fen: str, depth: int = 14, movetime: Optional[float] = None, engine: Optional[str] = None,
            pv_len: int = 6, threads: int = 1, hash_mb: int = 64, eng: Any = None) -> Dict[str, Any]:
    """Best move + eval + PV. Pass an open python-chess engine as ``eng`` to reuse one process."""
    import chess
    import chess.engine

    path = find_engine(engine) if eng is None else "open"
    if not path:
        return {"ok": False, "error": "Stockfish not found (set REALAI_STOCKFISH or install to C:\\tools\\stockfish)"}
    board = chess.Board(fen)
    if not board.is_valid():
        return {"ok": False, "error": f"invalid position: {board.status()!r}"}
    limit = chess.engine.Limit(time=movetime) if movetime else chess.engine.Limit(depth=depth)
    if eng is not None:
        info = eng.analyse(board, limit, game=object())  # fresh search tree per position (no ucinewgame reuse)
        name = eng.id.get("name", "Stockfish")
    else:
        with chess.engine.SimpleEngine.popen_uci(path) as e:
            e.configure({"Threads": threads, "Hash": hash_mb})
            info = e.analyse(board, limit)
            name = e.id.get("name", "Stockfish")
    pv: List[Any] = list(info.get("pv") or [])[:pv_len]
    if not pv:
        return {"ok": False, "error": "engine returned no move", "engine": name}
    b = board.copy()
    san_pv = []
    for mv in pv:
        san_pv.append(b.san(mv))
        b.push(mv)
    return {
        "ok": True, "engine": name, "fen": fen, "side_to_move": "White" if board.turn else "Black",
        "best_move_uci": pv[0].uci(), "best_move_san": san_pv[0], "pv_san": san_pv, "pv_uci": [m.uci() for m in pv],
        "eval": score_text(info["score"], board.turn), "depth": info.get("depth"),
    }


def run(input: str = "", context: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    fen = str(ctx.get("fen") or input or "").strip()
    if not fen:
        return {"ok": False, "ability": "chess_engine", "error": "pass a FEN"}
    try:
        out = analyse(fen, depth=int(ctx.get("depth", 14)), movetime=ctx.get("movetime"), engine=ctx.get("engine"))
    except Exception as exc:  # bad FEN, engine crash
        out = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    out["ability"] = "chess_engine"
    return out
