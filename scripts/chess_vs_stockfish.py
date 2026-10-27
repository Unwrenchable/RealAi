#!/usr/bin/env python3
"""RealAI vs Stockfish -- a watchable chess match.

The model (OpenAI-compatible endpoint, e.g. llama-server on :8081) picks its own
moves with NO engine help. Stockfish plays at reduced strength. A live board is
served at http://127.0.0.1:8765 and opened in your browser automatically.

Example (Windows):
  C:\\venvs\\realai-train\\Scripts\\python.exe C:\\temp\\chess-match\\chess_vs_stockfish.py

Deps: python-chess only (stdlib for everything else).
"""
from __future__ import annotations

import argparse, datetime as dt, glob, html, json, os, random, re, shutil, sys, threading, time
import urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import chess, chess.engine, chess.pgn, chess.svg

# Rough Elo of Stockfish "Skill Level" settings (very approximate, blitz-ish).
SKILL_ELO = {0: 1350, 1: 1450, 2: 1550, 3: 1650, 4: 1750, 5: 1850, 6: 1950, 7: 2050,
             8: 2150, 9: 2250, 10: 2350}

# ---------------------------------------------------------------- live state
STATE_LOCK = threading.Lock()
STATE: dict = {"board_svg": "", "fen": chess.STARTING_FEN, "san": [], "turn": "", "thinking": "",
               "raw": "", "illegal": 0, "illegal_game": 0, "forfeit_moves": 0, "game": 0, "games": 0,
               "level": "", "model_color": "", "scores": {}, "status": "starting", "log": []}


def update(**kw):
    with STATE_LOCK:
        STATE.update(kw)
        STATE["ts"] = time.time()


def push_log(msg: str):
    print(msg, flush=True)
    with STATE_LOCK:
        STATE["log"] = (STATE["log"] + [f"[{time.strftime('%H:%M:%S')}] {msg}"])[-14:]


def render_board(board: chess.Board, flip: bool):
    last = board.peek() if board.move_stack else None
    check = board.king(board.turn) if board.is_check() else None
    return chess.svg.board(board, lastmove=last, check=check, flipped=flip, size=480)


PAGE = """<!doctype html><html><head><meta charset=utf-8><title>RealAI vs Stockfish</title>
<style>body{font-family:system-ui,sans-serif;background:#1e1f24;color:#eee;margin:16px}
.wrap{display:flex;gap:20px;flex-wrap:wrap}.panel{background:#2a2c33;border-radius:8px;padding:12px;min-width:320px;max-width:520px}
h1{font-size:20px;margin:0 0 10px}.big{font-size:18px;font-weight:600}.think{color:#ffcc55}
.bad{color:#ff6b6b}pre{white-space:pre-wrap;word-break:break-word;background:#111;padding:8px;border-radius:6px;max-height:140px;overflow:auto}
table{border-collapse:collapse}td,th{padding:2px 8px;border-bottom:1px solid #444;text-align:left}
#moves{max-height:200px;overflow:auto;font-family:monospace}</style></head><body>
<h1>RealAI vs Stockfish</h1><div class=wrap><div id=board></div><div class=panel>
<div class=big id=hdr></div><div class=think id=think></div><div id=status></div>
<p>Illegal attempts: <span class=bad id=ill></span> &nbsp; Forfeit (random) moves: <span class=bad id=forf></span></p>
<b>Moves (SAN)</b><div id=moves></div><b>Model's raw reply</b><pre id=raw></pre>
<b>Score per level</b><table id=scores></table><b>Log</b><pre id=log></pre></div></div>
<script>
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function tick(){try{const r=await fetch('/state');const s=await r.json();
document.getElementById('board').innerHTML=s.board_svg;
document.getElementById('hdr').textContent=`Game ${s.game}/${s.games} \u2014 Stockfish ${s.level} \u2014 RealAI plays ${s.model_color}`;
document.getElementById('think').textContent=s.thinking?(s.thinking+' is thinking\u2026'):'';
document.getElementById('status').textContent=s.status+(s.turn?' \u2014 '+s.turn+' to move':'');
document.getElementById('ill').textContent=`${s.illegal_game} this game / ${s.illegal} total`;
document.getElementById('forf').textContent=s.forfeit_moves;
let m='';for(let i=0;i<s.san.length;i+=2){m+=`${i/2+1}. ${s.san[i]} ${s.san[i+1]||''}<br>`}
const mv=document.getElementById('moves');mv.innerHTML=m;mv.scrollTop=1e9;
document.getElementById('raw').textContent=s.raw;
let t='<tr><th>Level</th><th>W</th><th>L</th><th>D</th></tr>';
for(const[k,v]of Object.entries(s.scores))t+=`<tr><td>${esc(k)}</td><td>${v.W}</td><td>${v.L}</td><td>${v.D}</td></tr>`;
document.getElementById('scores').innerHTML=t;document.getElementById('log').textContent=s.log.join('\\n');
}catch(e){document.getElementById('status').textContent='(match server stopped)'}}
setInterval(tick,1000);tick();</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/state"):
            with STATE_LOCK:
                body = json.dumps(STATE).encode()
            ctype = "application/json"
        else:
            body, ctype = PAGE.encode(), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------- model side
SYSTEM = ("You are RealAI playing a game of chess. Think briefly if you like, but your final line "
          "must be exactly one legal move in SAN (for example: Nf3, exd5, O-O, e8=Q).")


def ask_llm(url: str, model: str, messages: list, timeout: float, temperature: float) -> str:
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": 160}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return (data["choices"][0]["message"].get("content") or "").strip()


SAN_RE = re.compile(r"(O-O-O|O-O|0-0-0|0-0|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=?[QRBN])?[+#]?)")


def parse_move(board: chess.Board, reply: str):
    """Return a legal Move found in the reply, or None. Prefers the last line."""
    text = reply.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    lines = [l for l in text.splitlines() if l.strip()][::-1]
    for line in lines:
        for tok in reversed(SAN_RE.findall(line)):
            for cand in (tok, tok.rstrip("+#")):
                try:
                    return board.parse_san(cand)
                except ValueError:
                    pass
            try:  # maybe UCI like e2e4
                mv = chess.Move.from_uci(tok.lower())
                if mv in board.legal_moves:
                    return mv
            except ValueError:
                pass
        for tok in re.findall(r"\b[a-h][1-8][a-h][1-8][qrbn]?\b", line):
            mv = chess.Move.from_uci(tok)
            if mv in board.legal_moves:
                return mv
    return None


def history_text(board: chess.Board) -> str:
    tmp, out = chess.Board(), []
    for i, mv in enumerate(board.move_stack):
        san = tmp.san(mv)
        out.append(f"{i // 2 + 1}. {san}" if i % 2 == 0 else san)
        tmp.push(mv)
    return " ".join(out) or "(no moves yet)"


def model_move(board, args, rng, stats, analyzer=None):
    """Returns (move, raw_text, forfeited, resigned)."""
    color = "White" if board.turn == chess.WHITE else "Black"
    base = (f"You are playing {color}.\nFEN: {board.fen()}\nMoves so far: {history_text(board)}\n"
            f"Reply with one move in SAN.")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": base}]
    raw_all = []
    for attempt in range(args.max_retries + 1):
        try:
            if args.stub_llm:
                legal = list(board.legal_moves)
                reply = ("I'll play " + board.san(rng.choice(legal))) if rng.random() > 0.15 else "Qz9!!"
            else:
                reply = ask_llm(args.llm_url, args.model, messages, args.llm_timeout, args.temperature)
        except Exception as e:  # network / server error
            reply = f"<error: {e}>"
        raw_all.append(reply)
        update(raw="\n---\n".join(raw_all[-3:]))
        mv = parse_move(board, reply)
        stats["model_attempts"] += 1
        if mv is not None:
            return mv, reply, False, False, attempt
        log_experience(board, analyzer, args.analysis_depth, reply, None, False, attempt)
        stats["illegal"] += 1
        with STATE_LOCK:
            STATE["illegal"] += 1
            STATE["illegal_game"] += 1
        push_log(f"illegal/unparseable from RealAI (try {attempt + 1}): {reply[:80]!r}")
        legal_san = ", ".join(board.san(m) for m in board.legal_moves)
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"That is not a legal move here. Legal moves: {legal_san}.\n"
                                                 f"Reply with exactly one of them in SAN."}]
    if args.on_fail == "resign":
        return None, raw_all[-1], False, True, attempt
    mv = rng.choice(list(board.legal_moves))
    stats["forfeit_moves"] += 1
    with STATE_LOCK:
        STATE["forfeit_moves"] += 1
    push_log(f"retries exhausted -> random move {board.san(mv)} (forfeit-move)")
    return mv, raw_all[-1], True, False, args.max_retries


# ---------------------------------------------------------------- engine side
def find_stockfish(explicit: str | None) -> str:
    if explicit:
        return explicit
    cands = []
    for root in (r"C:\tools\stockfish", os.path.expanduser("~/stockfish"), "/usr/games", "/usr/local/bin"):
        if os.path.isdir(root):
            cands += [p for p in glob.glob(os.path.join(root, "**", "stockfish*"), recursive=True)
                      if os.path.isfile(p) and (p.lower().endswith(".exe") or os.access(p, os.X_OK))]
    w = shutil.which("stockfish")
    if w:
        cands.append(w)
    if not cands:
        sys.exit("Stockfish not found; pass --stockfish PATH")
    return sorted(cands, key=lambda p: (not p.lower().endswith(".exe"), len(p)))[0]


def configure(engine, level):
    kind, val = level
    if kind == "skill":
        engine.configure({"Skill Level": val})
    else:
        engine.configure({"UCI_LimitStrength": True, "UCI_Elo": max(1320, val)})


def level_name(level):
    return f"skill {level[1]}" if level[0] == "skill" else f"Elo {level[1]}"


def level_elo(level):
    return SKILL_ELO.get(level[1], 1350 + 100 * level[1]) if level[0] == "skill" else max(1320, level[1])


EXPERIENCE: dict = {"fh": None, "match": "", "game": 0, "level": ""}
_SF_CACHE: dict = {}


def sf_best(analyzer, board, depth):
    """Stockfish best move, PV (SAN) and eval for the side to move (cached per FEN)."""
    key = (board.fen(), depth)
    if key not in _SF_CACHE:
        info = analyzer.analyse(board, chess.engine.Limit(depth=depth), game=object())
        pv = list(info.get("pv") or [])[:6]
        sc = info["score"].pov(board.turn)
        _SF_CACHE[key] = {"best_uci": pv[0].uci() if pv else None,
                          "best_san": board.san(pv[0]) if pv else None,
                          "pv_san": board.variation_san(pv) if pv else "",
                          "pv_uci": [m.uci() for m in pv],
                          "eval_cp": sc.score(mate_score=10000),
                          "mate": sc.mate()}
    return _SF_CACHE[key]


def cp_loss(analyzer, board, move, depth):
    """Centipawn loss of `move` from the mover's point of view (capped at 1000)."""
    best = sf_best(analyzer, board, depth)["eval_cp"]
    b2 = board.copy(); b2.push(move)
    after = analyzer.analyse(b2, chess.engine.Limit(depth=depth), game=object())["score"].pov(board.turn).score(mate_score=10000)
    return max(0, min(1000, best - after))


def log_experience(board, analyzer, depth, reply, move, legal, attempt, forfeited=False, loss=None):
    """One JSONL line per model attempt -- the raw material for chess_selfplay_experience SFT rows."""
    fh = EXPERIENCE["fh"]
    if fh is None:
        return
    rec = {"match": EXPERIENCE["match"], "game": EXPERIENCE["game"], "level": EXPERIENCE["level"],
           "ply": len(board.move_stack), "fen": board.fen(),
           "side": "White" if board.turn else "Black", "history_san": history_text(board),
           "model_reply": reply[:400], "attempt": attempt, "legal": bool(legal), "forfeit": forfeited,
           "model_move_san": board.san(move) if (move is not None and legal) else None,
           "model_move_uci": move.uci() if (move is not None and legal) else None}
    if analyzer is not None:
        b = sf_best(analyzer, board, depth)
        rec.update({"sf_depth": depth, "sf_best_san": b["best_san"], "sf_best_uci": b["best_uci"],
                    "sf_pv_san": b["pv_san"], "sf_eval_cp": b["eval_cp"], "sf_mate": b["mate"],
                    "cp_loss": loss, "matched_best": bool(legal and move is not None and move.uci() == b["best_uci"])})
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()


# ---------------------------------------------------------------- match
def play_game(gi, level, model_white, engine, analyzer, args, rng, stats):
    board = chess.Board()
    flip = not model_white
    mcol = "White" if model_white else "Black"
    update(game=gi, level=level_name(level), model_color=mcol, san=[], raw="", illegal_game=0,
           status="playing", board_svg=render_board(board, flip), fen=board.fen())
    configure(engine, level)
    game = chess.pgn.Game()
    game.headers.update({"Event": "RealAI vs Stockfish", "Date": dt.date.today().strftime("%Y.%m.%d"),
                         "Round": str(gi), "White": args.model if model_white else f"Stockfish ({level_name(level)})",
                         "Black": f"Stockfish ({level_name(level)})" if model_white else args.model})
    node, sans, losses, resigned_by, mistakes = game, [], [], None, []
    EXPERIENCE.update(game=gi, level=level_name(level))
    while not board.is_game_over(claim_draw=True) and board.fullmove_number <= args.max_moves:
        model_turn = (board.turn == chess.WHITE) == model_white
        who = "RealAI" if model_turn else "Stockfish"
        update(turn="White" if board.turn else "Black", thinking=who)
        if model_turn:
            mv, raw, forfeited, resigned, att = model_move(board, args, rng, stats, analyzer)
            if resigned:
                resigned_by = "model"; push_log("RealAI resigns after failed retries"); break
            loss = None
            if analyzer and not forfeited:
                loss = cp_loss(analyzer, board, mv, args.analysis_depth)
                losses.append(loss)
                mistakes.append({"fen": board.fen(), "played": board.san(mv), "loss": loss,
                                 "best": sf_best(analyzer, board, args.analysis_depth)["best_san"]})
            if not forfeited:
                log_experience(board, analyzer, args.analysis_depth, raw, mv, True, att, False, loss)
            comment = "forfeit-move (random)" if forfeited else None
        else:
            mv = engine.play(board, chess.engine.Limit(time=args.movetime / 1000)).move
            comment = None
        san = board.san(mv); sans.append(san)
        node = node.add_variation(mv)
        if comment:
            node.comment = comment
        board.push(mv)
        update(san=list(sans), fen=board.fen(), board_svg=render_board(board, flip), thinking="")
        if args.delay > 0:
            time.sleep(args.delay)
    if resigned_by:
        result = "0-1" if model_white else "1-0"
    elif board.is_game_over(claim_draw=True):
        result = board.result(claim_draw=True)
    else:
        result = "1/2-1/2"; game.headers["Termination"] = f"move cap {args.max_moves}"
    game.headers["Result"] = result
    model_score = {"1-0": 1.0, "0-1": 0.0}.get(result, 0.5)
    if not model_white:
        model_score = 1.0 - model_score
    outcome = "W" if model_score == 1 else "L" if model_score == 0 else "D"
    with STATE_LOCK:
        sc = STATE["scores"].setdefault(level_name(level), {"W": 0, "L": 0, "D": 0}); sc[outcome] += 1
    push_log(f"game {gi} ({level_name(level)}, RealAI {mcol}): {result} -> RealAI {outcome}")
    update(status=f"game {gi} finished: {result}", thinking="")
    return game, {"game": gi, "level": level_name(level), "level_elo": level_elo(level), "model_color": mcol,
                  "result": result, "outcome": outcome, "plies": len(sans),
                  "avg_cp_loss": round(sum(losses) / len(losses), 1) if losses else None, "cp_losses": losses,
                  "worst": sorted(mistakes, key=lambda m: -m["loss"])[:3]}


def remember(summary, args):
    """Best-effort: store a short match summary in RealAI memory. Never fails the match."""
    try:
        if args.realai_home and args.realai_home not in sys.path:
            sys.path.insert(0, args.realai_home)
        from abilities.memory_learning import run as mem_run
        lv = "; ".join(f"{k}: W{d['W']} L{d['L']} D{d['D']}" for k, d in summary["per_level"].items())
        mis = "; ".join(f"played {m['played']} instead of {m['best']} (-{m['loss']}cp)" for m in summary["common_mistakes"][:5])
        text = (f"Chess match {summary['when']} vs Stockfish ({summary['model']}): {lv}. "
                f"Illegal-move rate {summary['illegal_rate']:.0%}, avg centipawn loss {summary['avg_cp_loss']}, "
                f"rough Elo {summary['elo_estimate']}. Biggest mistakes: {mis or 'n/a'}. "
                f"Lesson: for real games use the chess_engine ability (Stockfish) instead of guessing moves.")
        r = mem_run(input=text, context={"action": "remember", "metadata": {"kind": "chess_match", "file": summary["pgn"]}})
        print(f"  Memory: {'saved' if r.get('ok') else r}")
    except Exception as e:
        print(f"  Memory: skipped ({type(e).__name__}: {e})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", type=int, default=4, help="games per level (colors alternate)")
    ap.add_argument("--sf-skill", default="0,3,6", help="comma list of Stockfish Skill Levels")
    ap.add_argument("--sf-elo", default=None, help="comma list of UCI_Elo values (min 1320); overrides --sf-skill")
    ap.add_argument("--movetime", type=int, default=100, help="Stockfish ms per move")
    ap.add_argument("--llm-url", default="http://127.0.0.1:8081/v1/chat/completions")
    ap.add_argument("--model", default="realai-sft-1.5b")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--llm-timeout", type=float, default=120)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--on-fail", choices=["random", "resign"], default="random",
                    help="after retries: play a random legal move (counted as forfeit-move) or resign")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between moves")
    ap.add_argument("--max-moves", type=int, default=150, help="adjudicate draw after this many full moves")
    ap.add_argument("--analysis-depth", type=int, default=12,
                    help="Stockfish depth for best move / cp-loss / experience log (0=off, then no learning data)")
    ap.add_argument("--no-experience", action="store_true", help="do not write results/experience/*.jsonl")
    ap.add_argument("--remember", action="store_true",
                    help="write a match summary into RealAI memory (abilities/memory_learning)")
    ap.add_argument("--realai-home", default=r"C:\RealAI-clean" if os.name == "nt" else None,
                    help="RealAI checkout used for --remember")
    ap.add_argument("--stockfish", default=None)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--results", default=r"C:\temp\chess-match\results" if os.name == "nt"
                    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    ap.add_argument("--stub-llm", action="store_true", help="testing: random legal moves (some illegal) instead of the model")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--hold", type=float, default=30, help="keep page up N seconds after the match")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    levels = ([("elo", int(x)) for x in args.sf_elo.split(",")] if args.sf_elo
              else [("skill", int(x)) for x in args.sf_skill.split(",")])
    sf = find_stockfish(args.stockfish)
    print(f"Stockfish: {sf}\nModel: {'STUB' if args.stub_llm else args.llm_url}")

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Live board: {url}")
    update(games=args.games * len(levels), board_svg=render_board(chess.Board(), False))
    if not args.no_browser:
        webbrowser.open(url)

    engine = chess.engine.SimpleEngine.popen_uci(sf)
    analyzer = chess.engine.SimpleEngine.popen_uci(sf) if args.analysis_depth > 0 else None
    stats = {"model_attempts": 0, "illegal": 0, "forfeit_moves": 0}
    os.makedirs(args.results, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    pgn_path = os.path.join(args.results, f"match-{stamp}.pgn")
    records, gi = [], 0
    exp_path = None
    if not args.no_experience and analyzer is not None:
        os.makedirs(os.path.join(args.results, "experience"), exist_ok=True)
        exp_path = os.path.join(args.results, "experience", f"match-{stamp}.jsonl")
        EXPERIENCE.update(fh=open(exp_path, "w", encoding="utf-8"), match=stamp)
    try:
        with open(pgn_path, "w", encoding="utf-8") as pgn_f:
            for level in levels:
                for g in range(args.games):
                    gi += 1
                    game, rec = play_game(gi, level, g % 2 == 0, engine, analyzer, args, rng, stats)
                    print(game, file=pgn_f, end="\n\n"); pgn_f.flush()
                    records.append(rec)
    except KeyboardInterrupt:
        push_log("interrupted -- saving partial results")
    finally:
        engine.quit()
        if analyzer:
            analyzer.quit()
        if EXPERIENCE["fh"]:
            EXPERIENCE["fh"].close(); EXPERIENCE["fh"] = None

    per_level, perf_pts = {}, []
    for r in records:
        d = per_level.setdefault(r["level"], {"W": 0, "L": 0, "D": 0, "level_elo": r["level_elo"]})
        d[r["outcome"]] += 1
    for name, d in per_level.items():
        n = d["W"] + d["L"] + d["D"]
        d["perf_elo"] = round(d["level_elo"] + 400 * (d["W"] - d["L"]) / n)
        perf_pts.append((d["perf_elo"], n))
    all_losses = [x for r in records for x in r["cp_losses"]]
    model_moves = stats["model_attempts"] - stats["illegal"] + stats["forfeit_moves"]
    summary = {
        "when": stamp, "model": "stub" if args.stub_llm else args.model, "llm_url": args.llm_url,
        "stockfish": sf, "movetime_ms": args.movetime, "games": records, "per_level": per_level,
        "illegal_attempts": stats["illegal"], "model_attempts": stats["model_attempts"],
        "illegal_rate": round(stats["illegal"] / max(1, stats["model_attempts"]), 3),
        "forfeit_moves": stats["forfeit_moves"], "model_moves": model_moves,
        "avg_cp_loss": round(sum(all_losses) / len(all_losses), 1) if all_losses else None,
        "elo_estimate": round(sum(e * n for e, n in perf_pts) / sum(n for _, n in perf_pts)) if perf_pts else None,
        "elo_note": "rough performance rating vs approximate Stockfish level ratings; floor is meaningless when losing every game",
        "pgn": pgn_path, "experience": exp_path,
        "common_mistakes": sorted((m for r in records for m in r.get("worst", [])), key=lambda m: -m["loss"])[:8],
    }
    jpath = os.path.join(args.results, f"match-{stamp}.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("\n=== Summary ===")
    for name, d in per_level.items():
        print(f"  Stockfish {name:10s} W{d['W']} L{d['L']} D{d['D']}  perf~{d['perf_elo']}")
    print(f"  illegal rate {summary['illegal_rate']:.1%}  forfeit-moves {stats['forfeit_moves']}  "
          f"avg cp loss {summary['avg_cp_loss']}  Elo~{summary['elo_estimate']}")
    print(f"  PGN:  {pgn_path}\n  JSON: {jpath}")
    if exp_path:
        print(f"  Experience log (next dataset build turns it into training rows): {exp_path}")
    if args.remember:
        remember(summary, args)
    update(status=f"match over -- Elo~{summary['elo_estimate']}, avg cp loss {summary['avg_cp_loss']}", thinking="", turn="")
    if args.hold > 0:
        time.sleep(args.hold)
    srv.shutdown()


if __name__ == "__main__":
    main()
