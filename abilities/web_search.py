"""Ability: keyless web search / browse / arXiv / RSS (realai.core.tools.web)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "web_search",
    "name": "web_search",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.core.tools.web (DuckDuckGo HTML, arXiv API, RSS)",
    "dest": "abilities/web_search.py",
    "capabilities": ["web_search", "browse", "arxiv", "rss", "monitor"],
    "secrets_policy": "none (keyless)",
}


def run(input: str = "", context: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    from realai.core.tools import web

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "search").lower()
    n = int(ctx.get("max_results") or 5)
    if action in {"browse", "fetch", "page"}:
        out = web.fetch_page(str(ctx.get("url") or input), int(ctx.get("max_chars") or 4000))
    elif action in {"arxiv", "academic"}:
        out = web.arxiv(str(ctx.get("query") or input), n)
    elif action in {"rss", "feed"}:
        out = web.rss(str(ctx.get("url") or input), n)
    elif action == "monitor":
        feeds = list(ctx.get("feeds") or [])
        topics = [t for t in (ctx.get("topics") or [input]) if t]
        items = []
        for f in feeds:
            r = web.rss(f, n)
            items.extend(r.get("items", []))
        for t in topics:
            r = web.arxiv(t, n) if ctx.get("academic") else web.search(t, n)
            items.extend(r.get("results", []))
        out = {"ok": bool(items), "items": items, "feeds": feeds, "topics": topics}
    else:
        out = web.search(str(ctx.get("query") or input), n)
    return {"ability": "web_search", "action": action, "status": "success" if out.get("ok") else "unavailable", **out}


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Back-compat function name."""
    return run(query, {"max_results": max_results})
