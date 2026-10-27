"""Route RealAIClient capabilities to real local abilities; label the rest honestly.

``RealAIClient.__init__`` calls :func:`wire_client`. Each wrapped method:

1. calls the real ``abilities.<id>.run()`` (or a local backend) when one exists;
2. otherwise falls back to the legacy ``RealAI`` method, and
3. passes every result through :func:`honest`, which replaces fake success
   (``example.com`` URLs, all-zero vectors, "no GGUF loaded" placeholders) with
   ``status: "template"`` / ``"unavailable"`` and ``real: False``.

No outside API keys are used. LLM-backed abilities use the local chat endpoint
(``REALAI_CHAT_URL`` / ``REALAI_LLM_BASE_URL`` / :8001 / :8080).
"""

from __future__ import annotations

import functools
import json
import importlib
import re
from typing import Any, Callable, Dict, List, Optional

_PLACEHOLDER_MARKERS = (
    "no GGUF loaded",
    "RealAI has researched your query comprehensively",
    "RealAI has processed your Web3 operation",
    "RealAI has generated code based on your requirements",
    "[Translated to",
)


def call_ability(ability_id: str, input: str = "", context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Run ``abilities.<ability_id>.run``; ``None`` if the ability can't be imported."""
    try:
        mod = importlib.import_module(f"abilities.{ability_id}")
    except Exception:
        return None
    fn = getattr(mod, "run", None)
    if fn is None:
        return None
    try:
        out = fn(input=input, context=dict(context or {}))
    except Exception as exc:
        return {"ok": False, "ability": ability_id, "status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}
    return out if isinstance(out, dict) else {"ok": True, "ability": ability_id, "result": out}


def _walk_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_strings(v)


def _is_zero_vector(obj: Any) -> bool:
    try:
        vecs = [d.get("embedding") for d in obj.get("data", [])]
        return bool(vecs) and all(isinstance(v, list) and v and not any(v) for v in vecs)
    except Exception:
        return False


def honest(result: Any, *, real: Optional[bool] = None, reason: str = "") -> Any:
    """Stamp ``real`` and correct ``status`` on a capability result."""
    if not isinstance(result, dict):
        return result
    if real is True:
        result.setdefault("real", True)
        return result
    texts = list(_walk_strings(result))
    fake_url = any("example.com" in t for t in texts)
    placeholder = any(m in t for t in texts for m in _PLACEHOLDER_MARKERS)
    zeros = _is_zero_vector(result)
    if real is False or fake_url or placeholder or zeros:
        result["real"] = False
        if placeholder and any("no GGUF loaded" in t for t in texts):
            result["status"] = "unavailable"
            result.setdefault("reason", "no local model reachable (load a GGUF or start llama-server; see REALAI_CHAT_URL)")
        else:
            result["status"] = "template"
            result.setdefault("reason", reason or "no real backend for this capability yet; output is a template")
        if fake_url:
            for k in ("url", "audio_url", "image_url"):
                if isinstance(result.get(k), str) and "example.com" in result[k]:
                    result[k] = None
            if isinstance(result.get("sources"), list):
                result["sources"] = [s for s in result["sources"] if "example.com" not in str(s)]
            if isinstance(result.get("data"), list):
                for d in result["data"]:
                    if isinstance(d, dict) and "example.com" in str(d.get("url", "")):
                        d["url"] = None
    else:
        result.setdefault("real", True)
    return result


def _llm(prompt: str, system: str, max_tokens: int = 512) -> Dict[str, Any]:
    from realai.local_media import hive_chat

    return hive_chat(prompt, system=system, max_tokens=max_tokens)


def _wrap(obj: Any, name: str, fn: Callable[..., Dict[str, Any]]) -> None:
    orig = getattr(obj, name, None)

    @functools.wraps(fn)
    def bound(*args: Any, **kwargs: Any) -> Any:
        return fn(orig, *args, **kwargs)

    setattr(obj, name, bound)


def _honest_all(obj: Any, names: List[str], reason: str = "") -> None:
    for n in names:
        orig = getattr(obj, n, None)
        if orig is None:
            continue

        def make(o: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(o)
            def w(*a: Any, **k: Any) -> Any:
                return honest(o(*a, **k), reason=reason)
            return w

        setattr(obj, n, make(orig))


# ---------------------------------------------------------------- embeddings
def local_embeddings(texts: List[str], model: Optional[str] = None) -> Dict[str, Any]:
    """sentence-transformers -> local llama-server /v1/embeddings -> labeled hash fallback."""
    import json
    import os
    import urllib.request

    st_model = model or os.environ.get("REALAI_EMBED_MODEL") or "sentence-transformers/all-MiniLM-L6-v2"
    try:
        from realai.server.embeddings_backend import SentenceTransformerBackend

        vecs = SentenceTransformerBackend().embed(st_model, texts)
        if vecs:
            return {"vectors": vecs, "backend": "sentence-transformers", "model": st_model, "semantic": True}
    except Exception:
        pass
    from realai.local_media import chat_url_candidates

    for url in chat_url_candidates():
        eurl = url.replace("/chat/completions", "/embeddings")
        try:
            req = urllib.request.Request(eurl, data=json.dumps({"input": texts, "model": "local"}).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            vecs = [d["embedding"] for d in data.get("data", [])]
            if vecs and any(any(v) for v in vecs):
                return {"vectors": vecs, "backend": "local_http", "endpoint": eurl, "model": data.get("model"), "semantic": True}
        except Exception:
            continue
    from realai.server.embeddings_backend import DeterministicEmbeddingBackend

    return {"vectors": DeterministicEmbeddingBackend().embed("hash", texts), "backend": "deterministic-hash",
            "model": "hash-64", "semantic": False}


# ---------------------------------------------------------------- wiring
def wire_client(client: Any) -> Any:  # noqa: C901 - one place to see all routes
    model = client.model

    # ---- chat: legacy path, then local HTTP fallback is inside chat_completion
    _honest_all(client.chat, ["create"])

    # ---- translation
    def translate(orig, text: str = "", target_language: str = "es", source_language: Optional[str] = None, **kw):
        r = call_ability("translation", text, {"target": target_language, "source": source_language or "auto"})
        if r and r.get("ok") and r.get("translation"):
            return {"status": "success", "real": True, "translated_text": r["translation"], "source_language": r.get("source_lang"),
                    "target_language": target_language, "backend": r.get("backend"), "model": r.get("model")}
        return honest(orig(text=text, target_language=target_language, source_language=source_language, **kw)
                      if orig else {"translated_text": None}, real=False, reason="translation needs a local chat model")
    _wrap(model, "translate", translate)

    # ---- code generation: local LLM + syntax check
    def generate_code(orig, prompt: str = "", language: str = "python", **kw):
        r = _llm(f"Write {language} code for: {prompt}\nReturn only one fenced code block.",
                 "You are RealAI's code generator. Output correct, minimal, runnable code.", 800)
        if r.get("ok") and r.get("text"):
            m = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)```", r["text"], re.S)
            code = (m.group(1) if m else r["text"]).strip()
            check: Dict[str, Any] = {"checked": False}
            if language.lower() in {"python", "py"}:
                try:
                    compile(code, "<generated>", "exec")
                    check = {"checked": True, "syntax_ok": True}
                except SyntaxError as exc:
                    check = {"checked": True, "syntax_ok": False, "error": str(exc)}
            return {"status": "success", "real": True, "code": code, "language": language, "verification": check,
                    "backend": "local_chat", "model": r.get("model")}
        return honest(orig(prompt=prompt, language=language, **kw), real=False, reason="code generation needs a local chat model")
    _wrap(model, "generate_code", generate_code)

    # ---- memory / learning
    def learn(orig, interaction_data: Optional[Dict[str, Any]] = None, *a, **kw):
        interaction = interaction_data if interaction_data is not None else kw.pop("interaction", None)
        base = orig(interaction or {}, *a, **kw)
        text = ""
        if isinstance(interaction, dict):
            text = " | ".join(f"{k}: {json.dumps(v, default=str) if isinstance(v, (dict, list)) else v}" for k, v in interaction.items())
        mem = call_ability("memory_learning", text, {"action": "remember", "text": text, "metadata": {"source": "learn_from_interaction"}}) if text else None
        if isinstance(base, dict):
            base["memory"] = mem
            base["real"] = bool(mem and mem.get("ok"))
            base["note"] = "stored in local memory for recall and future training data; model weights change only when you retrain"
        return base
    _wrap(model, "learn_from_interaction", learn)

    # ---- therapy / business / tasks (LLM abilities)
    def therapy(orig, message: str = "", *a, **kw):
        r = call_ability("therapy_counseling", message, kw)
        if r and r.get("ok"):
            return {"status": "success", "real": True, "response": r.get("response") or r.get("reply") or r.get("text"), **r}
        return honest(orig(message, *a, **kw))
    _wrap(client.therapy, "support", therapy)
    def therapy_session(orig, message: str = "", **kw):
        msg = message or kw.pop("message", "")
        r = call_ability("therapy_counseling", msg, kw)
        if r and r.get("ok"):
            return {"status": "success", "real": True, "response": r.get("response") or r.get("reply") or r.get("text"), **r}
        return honest(orig(message=msg, **kw))
    _wrap(client.therapy, "session", therapy_session)

    def business(orig, business_type: str = "", *a, **kw):
        brief = business_type or kw.get("business_type", "")
        if kw.get("details"):
            brief = f"{brief}. Details: {kw['details']}"
        r = call_ability("business_planning", brief, {"stage": kw.get("stage")})
        if r and r.get("ok"):
            return {"status": "success", "real": True, "business_type": business_type, **r}
        return honest(orig(business_type, *a, **kw))
    _wrap(client.business, "build", business)

    for n in ("automate", "order_groceries", "book_appointment"):
        orig_fn = getattr(client.tasks, n)

        def plan_only(*a, _o=orig_fn, **kw):
            res = _o(*a, **kw)
            if isinstance(res, dict):
                res = honest(res)
                res["executed"] = False
                if res.get("status") not in {"unavailable"}:
                    res["status"] = "plan_only"
                res["real"] = False
                res.setdefault("reason", "planning only; no calendar/shop integration is connected (by design)")
            return res
        setattr(client.tasks, n, plan_only)

    # ---- audio / voice
    def audio_gen(orig, text: str = "", **kw):
        r = call_ability("audio_speech", text, kw)
        if r and r.get("ok"):
            return {"status": "success", "real": True, **r}
        res = {"status": "unavailable", "real": False, "audio_url": None, "text": text,
               "reason": "no local TTS engine (install piper/kokoro)", "detail": (r or {}).get("error") or (r or {}).get("backend")}
        return res
    _wrap(client.audio, "generate", audio_gen)

    def audio_tx(orig, **kw):
        r = call_ability("audio_transcription", "", kw)
        if r and r.get("ok"):
            return {"status": "success", "real": True, **r}
        return {"status": "unavailable", "real": False, "text": None, "reason": "no local ASR model (vosk/whisper)",
                "detail": (r or {}).get("error")}
    _wrap(client.audio, "transcribe", audio_tx)

    def voice(orig, message: str = "", *a, **kw):
        r = _llm(message, "You are RealAI speaking aloud. Answer briefly and naturally.", 256)
        if r.get("ok"):
            tts = call_ability("audio_speech", r["text"], {})
            return {"status": "success", "real": True, "response_text": r["text"], "model": r.get("model"),
                    "audio": {k: tts.get(k) for k in ("ok", "backend", "bytes", "format")} if tts else None,
                    "audio_status": "success" if tts and tts.get("ok") else "unavailable"}
        return honest(orig(message, *a, **kw))
    _wrap(client.voice, "conversation", voice)

    # ---- worldbuilding
    def world(orig, concept: str = "", **kw):
        wb = call_ability("world_brain", "region", {"region": concept})
        r = _llm(f"Build a {kw.get('scope', 'world')} for this concept: {concept}. Give name, geography, factions, rules, conflicts.",
                 "You are RealAI's worldbuilder. Be concrete and internally consistent.", 700)
        if r.get("ok"):
            return {"status": "success", "real": True, "concept": concept, "name": concept.title()[:80], "description": r["text"], "rules": [],
                    "seed": (wb or {}).get("region"), "model": r.get("model")}
        if wb and wb.get("ok"):
            return {"status": "partial", "real": True, "concept": concept, "name": concept.title()[:80], "description": None, "rules": [], "seed": wb.get("region"),
                    "reason": "procedural seed only; prose needs a local chat model"}
        return honest(orig(concept=concept, **kw))
    _wrap(client.worldbuilding, "create", world)

    # ---- plugins
    def plugin_load(orig, plugin_name: str = "", config: Optional[Dict[str, Any]] = None, **kw):
        name = plugin_name or kw.get("name", "")
        for modname in (f"realai.plugins.{name}", f"plugins.{name}"):
            try:
                mod = importlib.import_module(modname)
            except Exception:
                continue
            methods = [m for m in dir(mod) if not m.startswith("_") and callable(getattr(mod, m))]
            return {"status": "loaded", "real": True, "plugin_name": name, "module": modname, "methods": methods, "config": config}
        inv = call_ability("plugins_surface", "", {"action": "list"}) or {}
        return {"status": "unavailable", "real": False, "plugin_name": name,
                "reason": f"no plugin module named {name!r} under realai/plugins",
                "available": inv.get("counts") or inv.get("plugins")}
    _wrap(client.plugins, "load", plugin_load)
    _wrap(client.plugins, "extend", lambda orig, plugin_name="", config=None, **kw: plugin_load(orig, plugin_name, config, **kw))

    # ---- embeddings
    def embed(orig, input_text: Any = None, **kw):
        texts = input_text if isinstance(input_text, list) else [str(input_text if input_text is not None else kw.get("input", ""))]
        e = local_embeddings([str(t) for t in texts], kw.get("model"))
        return {"object": "list", "status": "success" if e["semantic"] else "fallback", "real": e["semantic"],
                "data": [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(e["vectors"])],
                "model": e.get("model"), "backend": e["backend"],
                **({} if e["semantic"] else {"reason": "deterministic hash vectors (stable, not semantic); install sentence-transformers or run llama-server --embedding"})}
    _wrap(client.embeddings, "create", embed)

    # ---- images / vision (local Pillow tiers)
    def img(orig, prompt: str = "", **kw):
        r = call_ability("image_generation", prompt, kw)
        if r and r.get("ok"):
            r.update({"status": "partial", "real": True,
                      "note": "procedural local PNG (Pillow), not a generative model; stable-diffusion.cpp tier not wired yet"})
            return r
        return {"status": "unavailable", "real": False, "data": [{"url": None, "b64_json": None}],
                "reason": (r or {}).get("error") or "Pillow not installed"}
    _wrap(client.images, "generate", img)

    def vis(orig, image_url: str = "", **kw):
        r = call_ability("image_analysis", image_url, kw)
        if r and r.get("ok"):
            r.update({"status": "partial", "real": True, "note": "pixel statistics only; semantic vision needs a multimodal GGUF"})
            r.setdefault("objects", [])
            r.setdefault("description", r.get("summary") or json.dumps({k: r.get(k) for k in ("size", "mean_rgb", "top_colors") if k in r}, default=str))
            return r
        return {"status": "unavailable", "real": False, "image_url": image_url, "description": "", "objects": [],
                "reason": (r or {}).get("error") or "image not readable or Pillow missing"}
    _wrap(client.vision, "analyze", vis)

    # ---- math / data
    def math_solve(orig, problem: str = "", **kw):
        r = call_ability("math_solver", problem, {})
        if r and r.get("ok"):
            r["real"] = True
            r.setdefault("problem", problem)
            return r
        res = orig(problem=problem, **kw)
        return honest(res, real=False, reason=(r or {}).get("error") or "symbolic solver could not parse; model narration only")
    _wrap(client.math, "solve", math_solve)

    def data_an(orig, data: Any = None, **kw):
        r = call_ability("data_analysis", "", {"data": data})
        if r and r.get("ok"):
            return r
        return honest(orig(data=data, **kw), real=False)
    _wrap(client.data, "analyze", data_an)

    # ---- web / search / browse / monitor
    def research(orig, query: str = "", depth: str = "standard", **kw):
        n = {"quick": 1, "standard": 3, "deep": 5}.get(depth, 3)
        r = call_ability("web_search", query, {"max_results": n})
        if r and r.get("ok") and r.get("results"):
            return {"status": "success", "real": True, "query": query, "results": r["results"],
                    "sources": [x.get("url") for x in r["results"]], "backend": "duckduckgo"}
        return {"status": "unavailable", "real": False, "query": query, "results": [],
                "reason": (r or {}).get("error") or "web search unreachable"}
    _wrap(client.web, "research", research)

    def search_q(orig, query: str = "", search_type: str = "web", **kw):
        action = "arxiv" if search_type == "academic" else "search"
        r = call_ability("web_search", query, {"action": action, "max_results": kw.get("max_results", 5)})
        if action == "arxiv" and not (r and r.get("ok") and r.get("results")):
            r = call_ability("web_search", f"arxiv {query}", {"max_results": kw.get("max_results", 5)})  # arXiv rate-limited
        if r and r.get("ok") and r.get("results"):
            return {"status": "success", "real": True, "query": query, "search_type": search_type, "results": r["results"],
                    "result_count": len(r["results"]), "backend": r.get("source")}
        return {"status": "unavailable", "real": False, "query": query, "results": [], "result_count": 0, "reason": (r or {}).get("error")}
    _wrap(client.search, "query", search_q)
    _wrap(client.search, "academic", lambda orig, query="", **kw: search_q(orig, query, "academic", **kw))

    def browse(orig, url: str = "", action: str = "read", **kw):
        r = call_ability("web_search", url, {"action": "browse", "url": url})
        if r and r.get("ok"):
            out = {"status": "success", "real": True, "url": url, "title": r.get("title"), "text": r.get("text"),
                   "links": r.get("links", [])[:20]}
            if action == "summarize":
                s = _llm(f"Summarize in 5 bullet points:\n\n{(r.get('text') or '')[:3500]}", "You summarize web pages faithfully.", 300)
                out["summary"] = s.get("text") if s.get("ok") else ""
                out["summary_status"] = "success" if s.get("ok") else "unavailable"
            return out
        return {"status": "unavailable", "real": False, "url": url, "summary": "", "reason": (r or {}).get("error")}
    _wrap(client.browse, "page", browse)

    def monitor(orig, topics: Optional[List[str]] = None, **kw):
        r = call_ability("web_search", "", {"action": "monitor", "topics": topics or [], "feeds": kw.get("feeds") or [],
                                             "academic": "technical" in (kw.get("event_types") or [])})
        if r and r.get("ok"):
            return {"status": "success", "real": True, "topics": topics, "items": r.get("items"), "current_events": r.get("items"), "next_update": None, "note": "one-shot poll; schedule it for continuous monitoring"}
        return {"status": "unavailable", "real": False, "topics": topics, "items": [], "current_events": [], "next_update": None, "reason": "feeds/search unreachable"}
    _wrap(client.monitor, "events", monitor)

    # ---- web3 (Solana-first, read-only/simulate, sends blocked)
    def w3(orig, operation: str = "query", blockchain: str = "solana", params: Optional[Dict[str, Any]] = None, **kw):
        ctx = dict(params or {})
        ctx.update(kw)
        ctx.setdefault("chain", blockchain)
        ctx.setdefault("method", operation)
        return call_ability("web3_integration", operation, ctx) or {"status": "unavailable", "real": False}
    _wrap(client.web3, "execute", w3)

    def contract(orig, blockchain: str = "solana", params: Optional[Dict[str, Any]] = None, **kw):
        return {"status": "blocked", "real": False, "blockchain": blockchain, "params": params,
                "reason": "contract deployment moves value and needs a signer; RealAI never loads keys. Build/deploy with anchor/solana CLI yourself, then use web3.execute for read/simulate."}
    _wrap(client.web3, "smart_contract", contract)

    # ---- track whether legacy methods actually reached a model
    orig_cc = model.chat_completion

    @functools.wraps(orig_cc)
    def tracked_cc(*a: Any, **k: Any) -> Any:
        res = orig_cc(*a, **k)
        try:
            model._last_chat_source = (res.get("realai_meta") or {}).get("source")
        except Exception:
            model._last_chat_source = None
        return res

    model.chat_completion = tracked_cc

    def llm_backed(o: Any, names: List[str]) -> None:
        for n in names:
            f = getattr(o, n, None)
            if f is None:
                continue

            def make(f: Callable[..., Any]) -> Callable[..., Any]:
                @functools.wraps(f)
                def w(*a: Any, **k: Any) -> Any:
                    model._last_chat_source = None
                    res = f(*a, **k)
                    src = getattr(model, "_last_chat_source", None)
                    if isinstance(res, dict):
                        if src in (None, "placeholder", "error"):
                            res = honest(res, real=False, reason="no model reached; structured template output")
                        else:
                            res["real"] = True
                            res["model_source"] = src
                    return res
                return w

            setattr(o, n, make(f))

    # ---- everything else that is LLM-or-template: label honestly
    for ns, names in {
        "code": ["debug", "optimize", "interpret"], "science": ["explain", "analyze"], "logic": ["debug", "analyze"],
        "architecture": ["design", "plan"], "creative": ["write", "story", "poetry"], "humor": ["generate", "joke"],
        "reflection": ["analyze", "improve"], "business": ["plan"], "tasks": [],
    }.items():
        o = getattr(client, ns, None)
        if o is not None:
            llm_backed(o, names)
    llm_backed(client.multimodal, ["analyze", "relationships"])
    llm_backed(client.agents, ["coordinate"])
    orig_run = client.agents.run

    @functools.wraps(orig_run)
    def agents_run(*a: Any, **k: Any) -> Any:
        model._last_chat_source = None
        res = orig_run(*a, **k)
        if isinstance(res, dict) and "hive_error" in res:  # fell back to in-process coordinator
            if getattr(model, "_last_chat_source", None) in (None, "placeholder", "error"):
                res = honest(res, real=False, reason="hive orchestrator offline and no model reached")
            else:
                res["real"] = True
        elif isinstance(res, dict):
            res.setdefault("real", True)
        return res

    client.agents.run = agents_run
    return client
