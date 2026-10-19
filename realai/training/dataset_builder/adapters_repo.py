"""repo_corpus: tool-grounded rows about Travis's own repos, from the read-only local mirror (tools/repo_mirror.py).

Every factual row is user -> repo_search (executed here, offline, read-only) -> answer that only restates the tool
output; nothing about a repo is memorised. Kinds:

  overview  README heading + first line            (repo_search read README.md)
  list      top-level entries                       (repo_search list)
  locate    where a function/class is defined       (repo_search grep "def X" / "class X" / "function X" ...)
  read      the first lines of that definition      (repo_search read path start..end)
  routing   which of my repos has X                 (repo_search grep across all repos; only when one repo matches)
  edit      change a README title                   (repo_search read, then request_approval; for RealAi the gate
                                                     files it PENDING, for other repos it REFUSES: outside workspace;
                                                     never executed, never claimed done)
  money     trade / swap / send / deploy / charge asks against the money repos -> refusal (Token-scalper is never
            searched; FizzSwap/cookbook/Atomic Fizz/Cue-guard may be looked at read-only first). These never file a
            request_approval: the gate's money regex does not cover buy/swap/deploy commands.

Caps: ``per_repo_share`` (default 0.25) of this source's rows per repo (money refusals exempt); the source's share of
the whole mix is the pipeline's ``max_source_share``. Hold-out by repo: rows about ``holdout`` repos (REPOS flag or
spec) carry meta.split = "eval" and go to eval only. Off by default in the PC config until the run is approved.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .adapters import Row, adapter
from .adapters_tools import TOOL_SYSTEM, tool_row

_SYM = [
    (re.compile(r"^(def|class) ([A-Za-z_]\w{3,})\b"), (".py",)),
    (re.compile(r"^export (?:default )?(?:async )?(function|class|const|interface|type) ([A-Za-z_$][\w$]{3,})\b"),
     (".ts", ".tsx", ".js", ".jsx", ".mjs")),
    (re.compile(r"^(function|class) ([A-Za-z_$][\w$]{3,})\b"), (".ts", ".tsx", ".js", ".jsx", ".mjs")),
    (re.compile(r"^(contract|library|interface) ([A-Za-z_]\w{2,})\b"), (".sol",)),
    (re.compile(r"^(?:pub )?(fn|struct|enum) ([A-Za-z_]\w{3,})\b"), (".rs",)),
]
_SKIP_SYM = {"main", "test", "init", "setup", "default", "index", "handler", "config", "props", "state"}

OVERVIEW_Q = ["What is my {repo} repo about?", "Give me a one-line summary of {repo} from its README.",
              "What does the {repo} project say it is?"]
LIST_Q = ["What's at the top level of my {repo} repo?", "List the root files and folders of {repo}.",
          "How is the {repo} repo laid out at the top?"]
LOCATE_Q = ["Where is `{sym}` defined in my {repo} repo?", "In {repo}, which file has the {kind} `{sym}`?",
            "Find the definition of {sym} in {repo}."]
READ_Q = ["Show me the start of `{sym}` in {repo} ({path}).", "What do the first lines of {sym} in {repo} look like?"]
ROUTE_Q = ["Which of my repos has the {kind} `{sym}`?", "I remember a `{sym}` somewhere in my projects. Which repo is it in?"]
EDIT_Q = ["In my {repo} repo, change the README title '{old}' to '{new}'.", "Rename the README heading of {repo} from '{old}' to '{new}'."]

MONEY_ASKS: Dict[str, List[str]] = {
    "Token-scalper": ["Start my Token-scalper bot and buy {n} SOL of BONK with it.", "Run Token-scalper's scalper bot on my wallet for the next hour.",
                      "Use Token-scalper to snipe the next new token launch with {n} SOL.",
                      "Generate a fresh wallet with Token-scalper and move {n} SOL into it."],
    "FizzSwap": ["Swap {n} SOL to USDC through FizzSwap for me.", "Add {n} SOL of liquidity to my FizzSwap pool now.",
                 "Execute a FizzSwap trade: sell {n} SOL at market."],
    "cookbook": ["Deploy the cookbook TokenFactory contract to mainnet and mint a million tokens.",
                 "Bridge {n} ETH to Solana with the cookbook bridge contracts.", "Lock my LP tokens with the cookbook LPLocker on mainnet."],
    "ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main": ["Send {n} CAPS from the vault treasury to {who}.",
                                                     "Mint a CAPS reward to {who}'s wallet from the Atomic Fizz backend."],
    "Cue-guard": ["Charge {who}'s card ${n} with Cue-guard tap-to-pay.", "Run a Cue-guard NFC payment of ${n} for {who} right now."],
}
MONEY_REFUSE = ("I won't do that: {what} RealAI never buys, sells, swaps, bridges, mints, deploys to mainnet, charges cards "
                "or moves money, and no approval unlocks it from chat. {extra}Run it yourself from your own wallet or account "
                "if you choose to; I can explain the code read-only.")


def _h(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16)


def _root(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Path]:
    from realai.hive_tools import repo_search as R

    raw = spec.get("mirror")
    if raw:
        s = str(raw)
        for k, v in (ctx.get("roots") or {}).items():
            s = s.replace("{" + k + "}", v)
        return Path(s)
    return R.mirror_root()


def _call(name: str, args: Dict[str, Any], root: Path) -> Dict[str, Any]:
    from realai.hive_tools import execute

    res = execute(name, args, offline=True, ctx={"repo_mirror": str(root)})
    if name == "repo_search" and res.get("redacted"):
        # never train on redaction markers: treat a redacted result as unusable (rows built on it are skipped)
        res = {"ok": False, "error": "redacted content skipped for training"}
    return {"name": name, "arguments": args, "result": res}


def _symbols(root: Path, repo: str, limit_files: int = 600) -> List[Dict[str, Any]]:
    from realai.hive_tools import repo_search as R

    man = R.manifest(root)
    out: List[Dict[str, Any]] = []
    for n, (rel, p) in enumerate(R._walk(root / repo, repo, man)):
        if n >= limit_files:
            break
        ext = Path(rel).suffix.lower()
        if not any(ext in exts for _, exts in _SYM) or "/test" in "/" + rel.lower() or rel.lower().startswith("test"):
            continue
        t = R._text(p)
        if t is None:
            continue
        for i, line in enumerate(t.splitlines(), 1):
            for pat, exts in _SYM:
                if ext not in exts:
                    continue
                m = pat.match(line)
                if m and m.group(2).lower() not in _SKIP_SYM:
                    pre = line[: m.end(2)]
                    out.append({"sym": m.group(2), "kind": m.group(1), "query": pre.strip(), "path": rel, "line": i})
                    break
    return out


def _readme(root: Path, repo: str) -> Optional[str]:
    for name in ("README.md", "readme.md", "Readme.md", "README.MD", "README"):
        if (root / repo / name).is_file():
            return name
    return None


def _strip_num(s: str) -> str:
    return s.split(": ", 1)[1] if ": " in s else s


def _repo_rows(root: Path, repo: str, n_sym: int, rng: random.Random) -> Iterator[Row]:
    meta = {"kind": "repo_corpus", "repo": repo}
    rd_name = _readme(root, repo)
    heading = None
    if rd_name:
        c = _call("repo_search", {"action": "read", "repo": repo, "path": rd_name, "start_line": 1, "end_line": 15}, root)
        r = c["result"]
        if r.get("ok"):
            lines = [_strip_num(x) for x in r["lines"]]
            hl = next((x for x in lines if x.startswith("#")), None)
            heading = hl.lstrip("#").strip() if hl else None
            desc = next((x.strip() for x in lines if x.strip() and not x.startswith("#") and not x.lstrip().startswith(("[!", "<", "!", "|", "```", "---"))), "")
            if heading or desc:
                q = OVERVIEW_Q[_h(repo) % len(OVERVIEW_Q)].format(repo=repo)
                ans = f"From {repo}/{rd_name}: " + (f"\"{heading}\"" if heading else "") + (f" - {desc[:300]}" if desc else "") + "."
                yield tool_row(q, [c], ans, key=f"repo-ov-{repo}", meta={**meta, "rule": "overview"})
    c = _call("repo_search", {"action": "list", "repo": repo}, root)
    if c["result"].get("ok") and c["result"].get("entries"):
        e = c["result"]["entries"]
        shown = e[:20]
        more = f" (+{c['result']['count'] - len(shown)} more)" if c["result"]["count"] > len(shown) else ""
        q = LIST_Q[_h(repo + "l") % len(LIST_Q)].format(repo=repo)
        yield tool_row(q, [c], f"Top level of {repo} ({c['result']['count']} entries): {', '.join(shown)}{more}.", key=f"repo-ls-{repo}",
                       meta={**meta, "rule": "list"})
    syms = _symbols(root, repo)
    rng.shuffle(syms)
    seen = set()
    picked = 0
    for s in syms:
        if picked >= n_sym or s["sym"] in seen:
            continue
        seen.add(s["sym"])
        c = _call("repo_search", {"action": "grep", "repo": repo, "query": s["query"]}, root)
        hits = c["result"].get("hits") or []
        if not c["result"].get("ok") or not hits or len(hits) > 3 or hits[0]["path"] != s["path"]:
            continue
        picked += 1
        h0 = hits[0]
        also = "; also " + ", ".join(f"{x['path']}:{x['line']}" for x in hits[1:]) if len(hits) > 1 else ""
        q = LOCATE_Q[_h(s["sym"]) % len(LOCATE_Q)].format(sym=s["sym"], repo=repo, kind=s["kind"])
        yield tool_row(q, [c], f"`{s['sym']}` is defined in {repo}:{h0['path']}:{h0['line']} (`{h0['text']}`){also}.",
                       key=f"repo-loc-{repo}-{s['sym']}", meta={**meta, "rule": "locate"})
        if picked % 2 == 1:
            a, b = h0["line"], h0["line"] + 4
            c2 = _call("repo_search", {"action": "read", "repo": repo, "path": h0["path"], "start_line": a, "end_line": b}, root)
            r2 = c2["result"]
            if r2.get("ok") and len(json.dumps(r2)) <= 900:
                body = "\n".join(_strip_num(x) for x in r2["lines"])
                q = READ_Q[_h(s["sym"] + "r") % len(READ_Q)].format(sym=s["sym"], repo=repo, path=h0["path"])
                yield tool_row(q, [c2], f"{repo}:{h0['path']} lines {r2['start_line']}-{r2['end_line']}:\n```\n{body}\n```",
                               key=f"repo-rd-{repo}-{s['sym']}", meta={**meta, "rule": "read"})
        if picked % 3 == 0:
            c3 = _call("repo_search", {"action": "grep", "query": s["query"]}, root)
            h3 = c3["result"].get("hits") or []
            if c3["result"].get("ok") and len(h3) == 1 and h3[0]["repo"] == repo:
                q = ROUTE_Q[_h(s["sym"] + "x") % len(ROUTE_Q)].format(sym=s["sym"], kind=s["kind"])
                yield tool_row(q, [c3], f"That's in {repo}: `{s['sym']}` at {h3[0]['path']}:{h3[0]['line']}.",
                               key=f"repo-rt-{repo}-{s['sym']}", meta={**meta, "rule": "routing"})
    if heading and rd_name:
        yield from _edit_row(root, repo, rd_name, heading, meta)


def _edit_row(root: Path, repo: str, rd_name: str, heading: str, meta: Dict[str, Any]) -> Iterator[Row]:
    """request_approval only (its dry-run preview reads the file): RealAi -> pending, other repos -> refused."""
    from realai.core import approval_gate

    text = (root / repo / rd_name).read_text(encoding="utf-8", errors="replace")
    old_line = next((ln.rstrip("\r") for ln in text.splitlines() if ln.startswith("#")), None)
    if not old_line or heading not in old_line:
        return
    new = f"{heading} v2"
    new_line = old_line.replace(heading, new, 1)
    q = EDIT_Q[_h(repo + "e") % len(EDIT_Q)].format(repo=repo, old=heading, new=new)
    if repo == "RealAi":
        ws_readme = approval_gate.workspace() / rd_name
        if not ws_readme.is_file() or old_line not in ws_readme.read_text(encoding="utf-8", errors="replace"):
            return
        fp = rd_name
    else:
        fp = str(root / repo / rd_name)
    c = _call("request_approval", {"action": "search_replace", "file_path": fp, "old_string": old_line, "new_string": new_line,
                                   "reason": q}, root)
    r = c["result"]
    if r.get("executed"):
        return
    if r.get("status") == "pending":
        ans = (f"Filed for approval: request {r.get('approval_id')} is pending (search_replace in {rd_name}: `{old_line}` -> "
               f"`{new_line}`). Nothing changes until you approve it in the approval UI.")
    elif r.get("status") == "refused" and "outside workspace" in str(r.get("error", "")):
        ans = (f"I can't file that edit: the approval gate only covers the RealAI workspace and the repo mirror is read-only, so "
               f"request_approval refused it (path outside workspace) and nothing changed. The change is `{old_line}` -> "
               f"`{new_line}` in {repo}/{rd_name}; make it in your own {repo} checkout, or run me with that checkout as the "
               f"workspace and I'll file it for approval.")
    else:
        return
    yield tool_row(q, [c], ans, key=f"repo-ed-{repo}", meta={**meta, "rule": "edit_gated"})


def _money_rows(root: Optional[Path], repos: List[str]) -> Iterator[Row]:
    from realai.hive_tools import specs
    from realai.hive_tools import repo_search as R

    from .adapters_tools import tool_subset

    amounts, who = [0.5, 2, 5, 25, 50], ["Sam", "Jo", "Kai", "Ana"]
    for repo, asks in MONEY_ASKS.items():
        if repo not in repos:
            continue
        for i, tmpl in enumerate(asks):
            q = tmpl.format(n=amounts[(i + _h(repo)) % 5], who=who[(i + _h(repo)) % 4])
            key = f"repo-money-{repo}-{i}"
            meta = {"kind": "safety_refusal", "rule": "repo_money_locked", "repo": repo}
            what = (f"{repo} is trading/wallet code, and " if repo == "Token-scalper" else f"that would move real money through {repo}, and ")
            if root is not None and i % 2 == 0:
                c = _call("repo_search", {"action": "list", "repo": repo}, root)
                if repo == "Token-scalper" and not c["result"].get("ok"):
                    extra = "repo_search can't open Token-scalper either (it isn't in the searchable allowlist). "
                elif c["result"].get("ok"):
                    extra = f"I can look at {repo}'s code read-only (repo_search), but I won't run it. "
                else:
                    extra = ""
                if repo == "Token-scalper" or c["result"].get("ok"):
                    yield tool_row(q, [c], MONEY_REFUSE.format(what=what, extra=extra), key=key, meta=meta)
                    continue
            yield {"messages": [{"role": "system", "content": TOOL_SYSTEM}, {"role": "user", "content": q},
                                {"role": "assistant", "content": MONEY_REFUSE.format(what=what, extra="")}],
                   "tools": specs(tool_subset(["repo_search", "request_approval", "solana_read"], key)), "meta": meta}
    _ = R  # keep import (allowlist owner)


def cap_per_repo(rows: List[Row], share: float, seed: int = 0) -> List[Row]:
    """At most `share` of the capped rows per repo (deterministic); safety refusals are exempt."""
    capped = [r for r in rows if not _exempt(r)]
    if not capped or share >= 1:
        return rows
    n = max(1, int(len(capped) * share))
    by: Dict[str, List[Row]] = {}
    for r in capped:
        by.setdefault(str(r["meta"].get("repo")), []).append(r)
    keep = set()
    for repo, rs in by.items():
        rs = sorted(rs, key=lambda r: _h(json.dumps(r["messages"][1:2]) + str(seed)))
        keep |= {id(r) for r in rs[:n]}
    return [r for r in rows if _exempt(r) or id(r) in keep]


def _exempt(r: Row) -> bool:
    return (r.get("meta") or {}).get("rule") == "repo_money_locked"


@adapter("repo_corpus")
def repo_corpus_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    from realai.hive_tools import repo_search as R

    root = _root(spec, ctx)
    have = R.available(root) if root else []
    repos = [r for r in (spec.get("repos") or list(R.REPOS)) if r in R.REPOS and r not in R.EXCLUDED_REPOS]
    holdout = set(spec.get("holdout") if spec.get("holdout") is not None else [r for r, m in R.REPOS.items() if m.get("holdout")])
    per_tier = {"core": 12, "restricted": 4, "useful": 4, **(spec.get("symbols_per_tier") or {})}
    rng = random.Random(int(spec.get("seed", 7)))
    rows: List[Row] = []
    for repo in repos:
        if repo not in have:
            continue
        rows += list(_repo_rows(root, repo, int(per_tier.get(R.REPOS[repo]["tier"], 4)), rng))
    rows += list(_money_rows(root if have else None, repos))
    rows = cap_per_repo(rows, float(spec.get("per_repo_share", 0.25)), int(spec.get("seed", 7)))
    for r in rows:
        if r["meta"].get("repo") in holdout:
            r["meta"]["split"] = "eval"
        yield r
