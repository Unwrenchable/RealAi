"""Extra sources: chess_stockfish (Lichess CC0 positions + local Stockfish) and device_profiles."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List

from .adapters import Row, _msgs, _resolve, adapter

CHESS_SYSTEM = ("You are RealAI. For strong chess play call the chess_engine ability (local Stockfish) and report "
                "its result; do not guess moves.")


def _words(theme: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", theme).lower()


def _h(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16)


CHESS_Q = [
    "Position (FEN): {fen}\nWhat is the best move?",
    "{side} to move: {fen}\nWhat should {side} play?",
    "Analyse this chess position and give the engine's best move and evaluation.\nFEN: {fen}",
    "FEN {fen}\nWhose move is it, and what does Stockfish recommend?",
    "Find the strongest continuation for the side to move: {fen}",
]


def chess_answer(a: Dict[str, Any], themes: List[str], puzzle_san: str | None, line: str) -> str:
    parts = [f"{a['side_to_move']} to move. Best move ({a['engine']}, depth {a['depth']}): "
             f"{a['best_move_san']} ({a['best_move_uci']}).", f"Evaluation: {a['eval']}.", f"Main line: {line}."]
    if themes:
        parts.append("Lichess puzzle themes: " + ", ".join(_words(t) for t in themes) + ".")
    if puzzle_san and puzzle_san != a["best_move_san"]:
        parts.append(f"The Lichess puzzle solution move is {puzzle_san}.")
    return " ".join(parts)


@adapter("chess_stockfish")
def chess_stockfish_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """Lichess puzzle CSV (CC0): the position after the opponent's first move, analysed by Stockfish.

    Engine results are cached (fen+depth) under the CSV's folder so rebuilds are fast and identical."""
    from abilities.chess_engine import find_engine

    depth = int(spec.get("depth", 12))
    limit = int(spec.get("limit", 1500))
    engine = find_engine(spec.get("engine"))
    if not engine:
        raise RuntimeError("Stockfish not found (set REALAI_STOCKFISH or source.engine)")
    yield from _chess_rows(spec, ctx, depth, limit, engine)


def _chess_rows(spec, ctx, depth, limit, engine):
    import chess
    import chess.engine

    from abilities.chess_engine import analyse

    eng = None
    for path in _resolve(spec.get("paths", []), ctx["roots"]):
        cache_p = path.with_name(path.stem + f".stockfish_d{depth}.jsonl")
        cache: Dict[str, Dict[str, Any]] = {}
        if cache_p.is_file():
            for line in cache_p.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                cache[r["fen"]] = r
        new = []
        with path.open(encoding="utf-8") as f:
            for n, row in enumerate(csv.DictReader(f)):
                if n >= limit:
                    break
                board = chess.Board(row["FEN"])
                moves = row["Moves"].split()
                board.push_uci(moves[0])  # opponent's move; the puzzle starts after it
                fen = board.fen()
                sol = board.san(chess.Move.from_uci(moves[1])) if len(moves) > 1 else None
                a = cache.get(fen)
                if a is None:
                    if eng is None:
                        eng = chess.engine.SimpleEngine.popen_uci(engine)
                        eng.configure({"Threads": 1, "Hash": 64})
                    a = analyse(fen, depth=depth, eng=eng)
                    if not a.get("ok"):
                        continue
                    cache[fen] = a
                    new.append(a)
                line = chess.Board(fen).variation_san([chess.Move.from_uci(u) for u in a["pv_uci"]])
                themes = [t for t in row.get("Themes", "").split() if t]
                q = CHESS_Q[_h(row["PuzzleId"]) % len(CHESS_Q)].format(fen=fen, side=a["side_to_move"])
                yield {"messages": [{"role": "system", "content": CHESS_SYSTEM}] + _msgs(q, chess_answer(a, themes, sol, line)),
                       "meta": {"puzzle": row["PuzzleId"], "rating": row.get("Rating"), "agrees": sol == a["best_move_san"]}}
        if new:
            with cache_p.open("a", encoding="utf-8") as f:
                for a in new:
                    f.write(json.dumps(a, ensure_ascii=False) + "\n")
    if eng is not None:
        eng.quit()


# --------------------------------------------------------------------------- device profiles
# Published VRAM for common cards (spec sheets). iGPUs report shared memory only.
DGPUS = [("NVIDIA GeForce RTX 4090", 24), ("NVIDIA GeForce RTX 3090", 24), ("NVIDIA GeForce RTX 4070", 12),
         ("NVIDIA GeForce RTX 3060", 12), ("NVIDIA GeForce RTX 4060", 8), ("NVIDIA GeForce GTX 1650", 4),
         ("AMD Radeon RX 7900 XTX", 24), ("AMD Radeon RX 6700 XT", 12), ("AMD Radeon RX 6600", 8),
         ("AMD Radeon RX 580", 8), ("Intel(R) Arc(TM) A770 Graphics", 16), ("NVIDIA RTX A2000", 6)]
IGPUS = ["AMD Radeon(TM) Graphics", "Intel(R) UHD Graphics 770", "Intel(R) Iris(R) Xe Graphics"]


def mock_profiles() -> List[Dict[str, Any]]:
    out = []
    for i, (name, vram) in enumerate(DGPUS):
        for with_igpu in (False, True):
            ig = IGPUS[i % len(IGPUS)]
            gpus = [{"name": name, "vram_gb": vram}] + ([{"name": ig, "vram_gb": 0.5}] if with_igpu else [])
            vk = [{"name": name, "vram_gb": vram}] + ([{"name": ig, "vram_gb": 8.0}] if with_igpu else [])
            if with_igpu and i % 2 == 0:
                vk.reverse()  # iGPU enumerated first: must still pick the discrete card
            vk = [dict(v, id=f"Vulkan{k}") for k, v in enumerate(vk)]
            out.append({"os": "Windows 11", "ram_gb": 32 if vram >= 12 else 16, "cpu_threads": 16, "gpus": gpus,
                        "vulkan_devices": vk, "directml_adapters": [g["name"] for g in gpus], "hints": {}})
    for ram in (4, 8, 16, 32, 64):
        out.append({"os": "Linux 6.8", "ram_gb": ram, "cpu_threads": 8, "gpus": [], "vulkan_devices": [],
                    "directml_adapters": [], "hints": {}})
    for ig, ram in zip(IGPUS, (8, 16, 32)):
        out.append({"os": "Windows 11", "ram_gb": ram, "cpu_threads": 8, "gpus": [{"name": ig, "vram_gb": 0.5}],
                    "vulkan_devices": [{"id": "Vulkan0", "name": ig, "vram_gb": ram / 2}], "directml_adapters": [ig], "hints": {}})
    out.append({"os": "Linux 6.6 (aarch64, Raspberry Pi 5)", "ram_gb": 8, "cpu_threads": 4, "gpus": [], "vulkan_devices": [],
                "directml_adapters": [], "hints": {"serial_ports": ["/dev/ttyACM0"], "gpio": True, "ros": {"ROS_DISTRO": "humble"}}})
    out.append({"os": "Linux 6.8 (Jetson-class robot base)", "ram_gb": 16, "cpu_threads": 8,
                "gpus": [{"name": "NVIDIA GeForce RTX 3060", "vram_gb": 12}], "vulkan_devices": [],
                "directml_adapters": [], "hints": {"serial_ports": ["/dev/ttyUSB0", "/dev/ttyUSB1"], "gpio": False, "ros": {"ROS_DISTRO": "jazzy"}}})
    return out


def report_text(p: Dict[str, Any]) -> str:
    g = ", ".join(f"{x['name']} ({x['vram_gb']} GB)" for x in p.get("gpus") or []) or "none"
    lines = [f"OS: {p.get('os')}", f"RAM: {p.get('ram_gb')} GB, CPU threads: {p.get('cpu_threads')}", f"GPUs: {g}"]
    if p.get("vulkan_devices"):
        lines.append("llama-server --list-devices: " + "; ".join(f"{v['id']}: {v['name']} ({int(v['vram_gb'] * 1024)} MiB)" for v in p["vulkan_devices"]))
    h = p.get("hints") or {}
    if h.get("serial_ports") or h.get("gpio") or h.get("ros"):
        lines.append(f"Serial: {', '.join(h.get('serial_ports') or []) or 'none'}; GPIO: {'yes' if h.get('gpio') else 'no'}; "
                     f"ROS: {', '.join(f'{k}={v}' for k, v in (h.get('ros') or {}).items()) or 'none'}")
    return "\n".join(lines)


def rec_text(r: Dict[str, Any]) -> str:
    if "model" not in r:
        return "Nothing in the Qwen2.5 Instruct ladder fits this machine. " + " ".join(r["reasons"])
    where = f"on the {r['gpu']} ({r['vram_gb']} GB)" if r["target"] == "gpu" else "on the CPU"
    s = [f"Run {r['model']} {r['quant']} with a {r['ctx']}-token context {where}: about {r['need_gb']} GB "
         f"(weights {r['weights_gb']} GB + KV cache + overhead) within a {r['budget_gb']} GB budget.",
         "llama-server " + " ".join(r["llama_server_args"]) + "."]
    if r.get("dml_adapter"):
        s.append(f"For DirectML training pick the adapter by name: --dml-adapter \"{r['dml_adapter']}\".")
    if r.get("integrated_ignored"):
        s.append("Do not use the integrated GPU (" + ", ".join(r["integrated_ignored"]) + ").")
    if r.get("robot_hints"):
        s.append("Robot/sensor hardware detected, so keep the model local and loaded; no cloud dependency.")
    return " ".join(s)


@adapter("device_profiles")
def device_profiles_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    from realai.core.device_profile import collect, recommend

    profiles = mock_profiles()
    if spec.get("include_local"):
        profiles.append(collect())
    qs = ["Here's my hardware:\n{r}\nWhich local model, quant, context size and device should RealAI use?",
          "{r}\nWhat should I run locally on this machine, and on which GPU?",
          "Pick a RealAI local model setup for this box:\n{r}"]
    for i, p in enumerate(profiles):
        r = recommend(p)
        yield {"messages": _msgs(qs[i % len(qs)].format(r=report_text(p)), rec_text(r)),
               "meta": {"target": r.get("target"), "model": r.get("model")}}
