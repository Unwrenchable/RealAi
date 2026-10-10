"""Tool loop: let a model route to hive tools and answer from their output.

Works with any OpenAI-compatible endpoint (llama-server --jinja parses Qwen <tool_call> into
``message.tool_calls``); falls back to parsing ``<tool_call>{...}</tool_call>`` from the text.
Tools run through realai.hive_tools.execute (read-only). Every turn can be captured for the
learning loop (realai.training.self_data.capture) when REALAI_CAPTURE=1.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Callable, Dict, List, Optional

import realai.hive_tools as hive_tools

_THINK = re.compile(r"<think>.*?</think>", re.S)
_TC = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
ChatFn = Callable[[List[Dict[str, Any]], List[Dict[str, Any]]], Dict[str, Any]]


def http_chat(base_url: str, model: str = "local", temperature: float = 0.0, max_tokens: int = 400, timeout: int = 300) -> ChatFn:
    url = base_url.rstrip("/") + ("/chat/completions" if base_url.rstrip("/").endswith("/v1") else "/v1/chat/completions")

    def chat(messages, tools):
        body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "seed": 1}
        if tools:
            body["tools"] = tools
        req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["choices"][0]["message"]

    return chat


def parse_tool_calls(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for tc in msg.get("tool_calls") or []:
        f = tc.get("function") or tc
        args = f.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args or "{}")
            except json.JSONDecodeError:
                args = {"_raw": args}
        out.append({"name": f.get("name"), "arguments": args or {}, "id": tc.get("id")})
    if not out:
        for m in _TC.finditer(str(msg.get("content") or "")):
            try:
                d = json.loads(m.group(1))
                out.append({"name": d.get("name"), "arguments": d.get("arguments") or {}, "id": None})
            except json.JSONDecodeError:
                continue
    return out


def run(chat: ChatFn, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, max_rounds: int = 4,
        offline: bool = False, ctx: Optional[Dict[str, Any]] = None, project: str = "realai") -> Dict[str, Any]:
    """Returns {"answer", "messages" (full transcript), "calls": [{name, arguments, result}], "rounds"}."""
    tools = tools if tools is not None else hive_tools.specs()
    msgs = [dict(m) for m in messages]
    calls: List[Dict[str, Any]] = []
    answer = ""
    for rnd in range(max_rounds + 1):
        reply = chat(msgs, tools)
        tcs = parse_tool_calls(reply) if rnd < max_rounds else []
        if not tcs:
            answer = _THINK.sub("", _TC.sub("", str(reply.get("content") or ""))).strip()
            msgs.append({"role": "assistant", "content": answer})
            break
        msgs.append({"role": "assistant", "content": "",
                     "tool_calls": [{"type": "function", "function": {"name": t["name"], "arguments": t["arguments"]}} for t in tcs]})
        for t in tcs:
            res = hive_tools.execute(str(t["name"]), t["arguments"], offline=offline, ctx=ctx)
            calls.append({"name": t["name"], "arguments": t["arguments"], "result": res})
            msgs.append({"role": "tool", "name": t["name"], "content": hive_tools.tool_json(res)})
    out = {"answer": answer, "messages": msgs, "calls": calls, "rounds": len([m for m in msgs if m.get("tool_calls")])}
    if os.environ.get("REALAI_CAPTURE", "").lower() in ("1", "true", "on"):
        try:
            from realai.training.self_data.capture import capture

            capture(msgs, tools=tools, calls=calls, project=project, channel="tool_loop")
        except Exception:
            pass
    return out
