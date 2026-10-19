"""Trade mode bridge (read-only research + dry-run proposals) to the local RealAI Node CLI (C:\\tools\\realai).

OFF by default: the live tool loop offers these tools only with REALAI_TRADE_TOOLS=1 (they are not in the default catalog,
so spot-check / training catalogs are unchanged unless a suite or row asks for them explicitly).

  trade_research  op = spot | token_check | scan | health | paper_status | backtest | kill_status   (read-only)
  trade_propose   dry-run swap proposal for the BOT wallet (Solana): stores a proposal record in the CLI state and returns the
                  approval-card preview (amount, USD, slippage, min-out, route, impact, caps, safety verdict) + previewHash.
                  Nothing is signed or sent. A live trade then needs request_approval(action="trade_execute", proposal_id=...)
                  and a human approving that card (see realai/core/approval_gate.py).

Backends: "cli" (live tool loop: `node realai.js <allowlisted argv> --json`, no shell, timeout, redacted, capped) and "sim"
(offline self_data / spot-check / tests: a deterministic simulator, no network, no CLI). Never handles keys, never sends.
Env: REALAI_TRADE_TOOLS=1 (offer the tools), REALAI_TRADE_CLI (path to realai.js), REALAI_TRADE_BACKEND=sim|cli, REALAI_NODE.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from realai.hive_tools.extended import _fn

_S = {"type": "string"}
_N = {"type": "number"}
OUT_LIMIT = 3000
TIMEOUT_S = 60
OPS = ("spot", "token_check", "scan", "health", "paper_status", "backtest", "kill_status")
MINT = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
SYMBOL = re.compile(r"^[A-Za-z0-9]{2,12}(/[A-Za-z]{2,6})?$")
STRATEGIES = ("dca", "grid", "momentum", "meanReversion", "dipBuy")

SPECS: Dict[str, Dict[str, Any]] = {
    "trade_research": _fn(
        "trade_research",
        "Read-only market/token research via the local trading CLI: op spot (symbol), token_check (Solana mint: fail-closed "
        "safety verdict), scan (new-token candidates), health, paper_status, backtest (strategy, symbol), kill_status. "
        "Never trades.",
        {"op": {"type": "string", "enum": list(OPS)}, "symbol": _S, "mint": _S, "strategy": _S}, ["op"]),
    "trade_propose": _fn(
        "trade_propose",
        "Dry-run swap proposal for the bot wallet (Solana): returns proposal_id and the approval preview (amount, USD, "
        "slippage, min-out, route, caps, safety). Nothing is sent; a live trade needs request_approval action "
        "trade_execute with that proposal_id.",
        {"from": _S, "to": _S, "amount": _N, "slippage_bps": _N, "reason": _S}, ["from", "to", "amount"]),
}


def enabled() -> bool:
    return os.environ.get("REALAI_TRADE_TOOLS", "").strip().lower() in ("1", "true", "yes", "on")


def cli_path() -> Optional[Path]:
    p = os.environ.get("REALAI_TRADE_CLI") or (r"C:\tools\realai\realai.js" if os.name == "nt" else "")
    return Path(p) if p else None


def backend(ctx: Optional[Dict[str, Any]] = None) -> str:
    b = str((ctx or {}).get("trade_backend") or os.environ.get("REALAI_TRADE_BACKEND") or "cli").lower()
    return "sim" if b == "sim" else "cli"


# ----------------------------------------------------------------------------- CLI backend
def _redact(obj: Any) -> Any:
    from realai.hive_tools.repo_search import redact

    s = json.dumps(obj, ensure_ascii=False, default=str)
    out = redact(s)
    out = out[0] if isinstance(out, tuple) else out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"text": out[:OUT_LIMIT]}


def run_cli(argv: List[str], timeout: int = TIMEOUT_S) -> Dict[str, Any]:
    """Run an allowlisted CLI argv (no shell). Returns parsed JSON or {"ok": False, "error"}."""
    cli = cli_path()
    if not cli or not cli.is_file():
        return {"ok": False, "error": "trading CLI not found (set REALAI_TRADE_CLI to realai.js)"}
    node = os.environ.get("REALAI_NODE") or "node"
    env = {k: v for k, v in os.environ.items() if not re.search(r"(KEY|SECRET|TOKEN|PASSWORD|MNEMONIC)", k, re.I)}
    try:
        cp = subprocess.run([node, str(cli), *argv], cwd=str(cli.parent), capture_output=True, text=True,
                            timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": f"trading CLI failed: {type(e).__name__}"}
    txt = cp.stdout.strip()
    start = min([i for i in (txt.find("{"), txt.find("[")) if i >= 0] or [-1])
    if start < 0:
        return {"ok": False, "error": "trading CLI returned no JSON", "exit_code": cp.returncode}
    try:
        data = json.JSONDecoder().raw_decode(txt[start:])[0]
    except json.JSONDecodeError:
        return {"ok": False, "error": "trading CLI returned malformed JSON", "exit_code": cp.returncode}
    if isinstance(data, list):
        data = {"items": data}
    data.setdefault("ok", cp.returncode == 0)
    return _redact(data)


def _research_argv(op: str, a: Dict[str, Any]) -> List[str]:
    sym, mint, strat = str(a.get("symbol") or "").strip(), str(a.get("mint") or "").strip(), str(a.get("strategy") or "").strip()
    if op == "spot":
        if not SYMBOL.match(sym):
            raise ValueError("symbol required (e.g. SOL or SOL/USD)")
        return ["market", "spot", sym if "/" in sym else sym.upper() + "/USD", "--json"]
    if op == "token_check":
        if not MINT.match(mint):
            raise ValueError("a Solana mint address is required")
        return ["token", "check", mint, "--json"]
    if op == "scan":
        return ["scan", "--limit", "10", "--check", "3", "--json"]
    if op == "health":
        return ["health", "--no-probe", "--json"]
    if op == "paper_status":
        return ["paper", "status", "--json"]
    if op == "backtest":
        if strat not in STRATEGIES or not SYMBOL.match(sym):
            raise ValueError(f"strategy one of {', '.join(STRATEGIES)} and a symbol are required")
        return ["backtest", "run", "--strategy", strat, "--symbol", sym if "/" in sym else sym.upper() + "/USD", "--json"]
    if op == "kill_status":
        return ["trade", "kill", "--status", "--json"]
    raise ValueError(f"op must be one of {', '.join(OPS)}")


# ----------------------------------------------------------------------------- sim backend (offline, deterministic)
SIM_PRICES = {"SOL": 150.0, "BTC": 60000.0, "ETH": 3000.0, "USDC": 1.0, "BONK": 0.00002, "JUP": 0.8}
SIM_SAFE_MINTS = {"JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP"}
SIM_CAPS = {"wallet": "bot", "chains": ["solana"], "maxTradeUsd": 5, "maxDailyUsd": 15, "maxDailyTrades": 5, "maxSlippageBps": 300}
_SIM_PROPOSALS: Dict[str, Dict[str, Any]] = {}


def _canonical(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sim_price(sym: str) -> Optional[float]:
    s = sym.upper().split("/")[0]
    return SIM_PRICES.get(s) or (SIM_PRICES.get(SIM_SAFE_MINTS.get(sym, "")) if sym in SIM_SAFE_MINTS else None)


def _sim_research(op: str, a: Dict[str, Any]) -> Dict[str, Any]:
    _research_argv(op, a)  # same validation as the CLI path
    if op == "spot":
        sym = str(a["symbol"]).upper().split("/")[0]
        p = SIM_PRICES.get(sym)
        return {"ok": p is not None, "symbol": sym + "/USD", "price": p, "source": "sim"} if p else {"ok": False, "error": f"no price for {sym}"}
    if op == "token_check":
        m = str(a["mint"])
        if m in SIM_SAFE_MINTS:
            return {"ok": True, "safety": {"mint": m, "verdict": "pass", "blockers": []}, "alertOnly": True}
        return {"ok": True, "safety": {"mint": m, "verdict": "block", "blockers": ["holderConcentration", "roundTrip"]}, "alertOnly": True}
    if op == "scan":
        return {"ok": True, "candidates": [{"mint": k, "symbol": v, "verdict": "pass", "score": 72} for k, v in SIM_SAFE_MINTS.items()]}
    if op == "health":
        return {"ok": True, "overall": "ok", "feeds": {"jupiter": "ok", "dexscreener": "ok", "rpc": "ok"}}
    if op == "paper_status":
        return {"ok": True, "cash": 9854.91, "positions": {"SOL": {"qty": 1.3095}}, "realizedPnl": 13.09}
    if op == "backtest":
        return {"ok": True, "strategy": a["strategy"], "symbol": str(a["symbol"]).upper(), "trades": 12, "winRate": 0.5, "pnlPct": 1.8, "maxDrawdownPct": 4.2}
    return {"ok": True, "killed": False, "usage": {"usd": 0, "trades": 0}, "caps": SIM_CAPS}


def _sim_propose(a: Dict[str, Any]) -> Dict[str, Any]:
    frm, to = str(a.get("from") or "").strip(), str(a.get("to") or "").strip()
    amt = float(a.get("amount") or 0)
    slip = int(a.get("slippage_bps") or 50)
    pin, pout = _sim_price(frm), _sim_price(to)
    pid = "prop_" + hashlib.sha1(_canonical([frm, to, amt, slip]).encode()).hexdigest()[:10]
    usd = round(amt * pin, 6) if pin else None
    out = round(usd / pout, 6) if usd and pout else None
    buying = to.upper() not in ("USDC", "USDT", "SOL", "WSOL")
    safety = {"required": buying, "verdict": ("pass" if to in SIM_SAFE_MINTS or to.upper() in ("JUP",) else "block") if buying else "n/a"}
    trade = {"v": 1, "proposalId": pid, "chain": "solana", "wallet": "bot", "side": "sell", "from": frm, "to": to, "amountIn": amt,
             "usd": usd, "slippageBps": slip, "expectedOut": out, "minOut": round(out * (1 - slip / 10000), 6) if out else None,
             "dex": "jupiter", "route": "sim", "priceImpactBps": 12.0, "guardsOk": True, "riskAllowed": bool(usd),
             "safety": safety, "caps": SIM_CAPS, "usedToday": {"usd": 0, "trades": 0}, "ticketTtlSec": 90}
    problems = []
    if not usd:
        problems.append("trade cannot be valued in USD")
    elif usd > SIM_CAPS["maxTradeUsd"]:
        problems.append(f"usd {usd} > per-trade cap {SIM_CAPS['maxTradeUsd']}")
    if slip > SIM_CAPS["maxSlippageBps"]:
        problems.append(f"slippage {slip} bps > cap {SIM_CAPS['maxSlippageBps']}")
    if safety["required"] and safety["verdict"] != "pass":
        problems.append("token safety check failed (block)")
    res = {"ok": not problems, "proposalId": pid, "status": "proposed", "preview": trade,
           "previewHash": hashlib.sha256(_canonical(trade).encode()).hexdigest(), "problems": problems,
           "note": "dry-run proposal only: nothing was signed or sent. Live needs an approved RealAI trade_execute card."}
    _SIM_PROPOSALS[pid] = res
    return res


def sim_preview(proposal_id: str) -> Dict[str, Any]:
    r = _SIM_PROPOSALS.get(proposal_id)
    return dict(r) if r else {"ok": False, "error": f"unknown proposal {proposal_id}"}


# ----------------------------------------------------------------------------- executors
def trade_research(args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    op = str(args.get("op") or "").strip()
    try:
        if backend(ctx) == "sim":
            return _sim_research(op, args)
        return run_cli(_research_argv(op, args))
    except ValueError as e:
        return {"ok": False, "error": str(e)}


def trade_propose(args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    frm, to = str(args.get("from") or "").strip(), str(args.get("to") or "").strip()
    try:
        amt = float(args.get("amount"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "amount must be a number"}
    if not (SYMBOL.match(frm) or MINT.match(frm)) or not (SYMBOL.match(to) or MINT.match(to)) or not (0 < amt < 1e9):
        return {"ok": False, "error": "from/to must be a symbol or Solana mint and amount > 0"}
    slip = args.get("slippage_bps")
    if slip is not None:
        try:
            slip = int(slip)
        except (TypeError, ValueError):
            return {"ok": False, "error": "slippage_bps must be a number"}
    if backend(ctx) == "sim":
        return _sim_propose({**args, "amount": amt, "slippage_bps": slip})
    argv = ["trade", "propose", frm, to, repr(amt), "--realai", "--json", "--chain", "solana"]
    if slip is not None:
        argv += ["--slippage", str(slip)]
    return run_cli(argv)


EXECUTORS = {"trade_research": trade_research, "trade_propose": trade_propose}


def key_facts(name: str, result: Dict[str, Any], args: Dict[str, Any]) -> List[List[str]]:
    """Facts a grounded answer must carry (verifier)."""
    if not result.get("ok") and result.get("error"):
        return []
    if name == "trade_propose":
        pv = result.get("preview") or {}
        facts = [[str(result.get("proposalId"))]] if result.get("proposalId") else []
        if pv.get("usd") is not None:
            facts.append([f"{pv['usd']:g}", f"{pv['usd']:.2f}"])
        return facts
    if args.get("op") == "spot" and result.get("price") is not None:
        p = float(result["price"])
        return [[f"{p:g}", f"{p:,.2f}", f"{p:.2f}"]]
    if args.get("op") == "token_check":
        v = str((result.get("safety") or {}).get("verdict") or "")
        return [[v, v.upper()]] if v else []
    return []
