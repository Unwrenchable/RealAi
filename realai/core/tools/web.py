"""Keyless web tools: DuckDuckGo HTML search, page fetch, arXiv and RSS.

No API keys. ``beautifulsoup4`` is optional (``pip install realai[web]``);
without it a regex fallback extracts links/text.
"""

from __future__ import annotations

import html as _html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

from ..tools.base import Tool
from ..tools.permissions import Permissions

USER_AGENT = "RealAI/2.0 (+local; keyless research)"
DDG_URL = "https://html.duckduckgo.com/html/"
ARXIV_URL = "https://export.arxiv.org/api/query"


def _get(url: str, params: Dict[str, Any] | None = None, timeout: float = 10.0) -> str:
    if requests is None:
        raise RuntimeError("requests unavailable in runtime")
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.text


def _strip_tags(s: str) -> str:
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def _ddg_target(href: str) -> str:
    if "uddg=" in href:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        return (q.get("uddg") or [href])[0]
    if href.startswith("//"):
        return "https:" + href
    return href


def parse_ddg_html(text: str, max_results: int = 5) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(text, "html.parser")
        for res in soup.select(".result"):
            a = res.select_one("a.result__a")
            if not a or not a.get("href"):
                continue
            snip = res.select_one(".result__snippet")
            results.append({
                "title": a.get_text(" ", strip=True),
                "url": _ddg_target(a["href"]),
                "snippet": snip.get_text(" ", strip=True) if snip else "",
            })
            if len(results) >= max_results:
                break
        return results
    except ImportError:
        pass
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.S):
        results.append({"title": _strip_tags(m.group(2)), "url": _ddg_target(_html.unescape(m.group(1))), "snippet": ""})
        if len(results) >= max_results:
            break
    return results


def search(query: str, max_results: int = 5) -> Dict[str, Any]:
    query = str(query or "").strip()
    if not query:
        return {"ok": False, "query": query, "results": [], "error": "query required"}
    try:
        text = _get(DDG_URL, params={"q": query})
    except Exception as exc:
        return {"ok": False, "query": query, "results": [], "error": str(exc), "source": "duckduckgo"}
    return {"ok": True, "query": query, "results": parse_ddg_html(text, max_results), "source": "duckduckgo"}


def extract_page(text: str, max_chars: int = 4000) -> Dict[str, Any]:
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(text, "html.parser")
        for t in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            t.decompose()
        title = soup.title.get_text(strip=True) if soup.title else ""
        body = soup.get_text(" ", strip=True)
        links = [a["href"] for a in soup.find_all("a", href=True)][:50]
    except ImportError:
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
        title = _strip_tags(m.group(1)) if m else ""
        cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        body = _strip_tags(cleaned)
        links = re.findall(r'href="(https?://[^"]+)"', text)[:50]
    return {"title": title, "text": body[:max_chars], "chars": len(body), "links": links}


def fetch_page(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    url = str(url or "").strip()
    if not re.match(r"^https?://", url):
        return {"ok": False, "url": url, "error": "http(s) url required"}
    try:
        text = _get(url)
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}
    return {"ok": True, "url": url, **extract_page(text, max_chars)}


def parse_arxiv(xml_text: str) -> List[Dict[str, Any]]:
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall("a:entry", ns):
        out.append({
            "title": " ".join((e.findtext("a:title", "", ns) or "").split()),
            "url": e.findtext("a:id", "", ns),
            "published": e.findtext("a:published", "", ns),
            "summary": " ".join((e.findtext("a:summary", "", ns) or "").split())[:500],
            "authors": [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)],
        })
    return out


def arxiv(query: str, max_results: int = 5) -> Dict[str, Any]:
    try:
        text = _get(ARXIV_URL, params={"search_query": f"all:{query}", "start": 0, "max_results": max_results,
                                       "sortBy": "submittedDate", "sortOrder": "descending"}, timeout=15)
        return {"ok": True, "query": query, "results": parse_arxiv(text), "source": "arxiv"}
    except Exception as exc:
        return {"ok": False, "query": query, "results": [], "error": str(exc), "source": "arxiv"}


def parse_feed(xml_text: str, max_items: int = 10) -> List[Dict[str, str]]:
    root = ET.fromstring(xml_text)
    items: List[Dict[str, str]] = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in {"item", "entry"}:
            continue
        get = lambda name: next((c for c in it if c.tag.split("}")[-1] == name), None)  # noqa: E731
        t, l = get("title"), get("link")
        d = next((x for x in (get("pubDate"), get("updated"), get("published")) if x is not None), None)
        link = (l.get("href") if l is not None and l.get("href") else (l.text if l is not None else "")) or ""
        items.append({"title": (t.text or "").strip() if t is not None else "", "url": link.strip(),
                      "date": (d.text or "").strip() if d is not None else ""})
        if len(items) >= max_items:
            break
    return items


def rss(url: str, max_items: int = 10) -> Dict[str, Any]:
    try:
        return {"ok": True, "url": url, "items": parse_feed(_get(url), max_items), "source": "rss"}
    except Exception as exc:
        return {"ok": False, "url": url, "items": [], "error": str(exc), "source": "rss"}


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web (keyless DuckDuckGo)"
    params_schema = {"query": {"type": "string"}}
    permissions = [Permissions.NETWORK]

    def __call__(self, **kwargs: Any) -> Dict[str, Any]:
        context = kwargs.get("_context") if isinstance(kwargs.get("_context"), dict) else {}
        if context:
            allowed = set(context.get("allowed_permissions", []))
            if Permissions.NETWORK not in allowed:
                raise PermissionError("Network access denied")
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return {"results": [], "query": query}
        out = search(query, int(kwargs.get("max_results") or 5))
        return {"results": out.get("results", []), "query": query, **({"error": out["error"]} if out.get("error") else {})}
