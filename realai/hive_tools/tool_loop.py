"""Tool loop: let a model route to hive tools and answer from their output.

Works with any OpenAI-compatible endpoint (llama-server --jinja parses Qwen <tool_call> into
``message.tool_calls``). When a model writes its call as plain text instead (Qwen2.5-Coder, Llama 3.x
without a parser, small fine-tunes), parse_tool_calls falls back to the content: ``<tool_call>``,
``<function_call>``, ```json / ```xml fences, ``<|python_tag|>``, bare JSON objects or lists with
"name" + "arguments"/"parameters", and doubled ``{{ }}`` braces. Text fallbacks only accept names of
tools that were actually offered, so prose that happens to contain JSON is not executed.
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


_TEXT_TAGS = re.compile(r"<(tool_call|function_call|tool_use|functioncall)>\s*(.*?)\s*</\1>", re.S | re.I)
_FENCE = re.compile(r"```[a-zA-Z]*\s*(.*?)```", re.S)
_PY_TAG = "<|python_tag|>"
_APPROVAL_ACTIONS = {"search_replace", "write_file", "run_terminal_command", "run_script", "auto_wire",
                     "self_heal_promote", "self_extend", "self_repair"}


def _norm_call(d: Any, known: Optional[set]) -> Optional[Dict[str, Any]]:
    if not isinstance(d, dict):
        return None
    if isinstance(d.get("function"), dict):  # {"type": "function", "function": {...}}
        d = d["function"]
    name = d.get("name") or d.get("tool") or d.get("tool_name")
    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip()
    args = d.get("arguments", d.get("parameters", d.get("args", d.get("input"))))
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except json.JSONDecodeError:
            args = {"_raw": args}
    if args is None and set(d) - {"name", "tool", "tool_name", "type", "id"}:
        return None  # a JSON object that merely has a "name" field, not a call
    args = args if isinstance(args, dict) else {}
    if name in _APPROVAL_ACTIONS and (known is None or "request_approval" in known) and name not in (known or ()):
        # models often "call" the gated action itself (run_terminal_command, write_file ...): that is a
        # request_approval with action=<name>; it only files a pending request, nothing runs.
        name, args = "request_approval", {"action": name, **{k: v for k, v in args.items() if k != "action"}}
    if known is not None and name not in known:
        return None
    return {"name": name, "arguments": args, "id": None}


def _json_values(text: str) -> List[Any]:
    """Every top-level JSON object/array that decodes inside text (left to right, non-overlapping)."""
    out, i, dec = [], 0, json.JSONDecoder()
    while True:
        m = re.search(r"[\[{]", text[i:])
        if not m:
            return out
        start = i + m.start()
        try:
            val, n = dec.raw_decode(text[start:])
        except json.JSONDecodeError:
            i = start + 1
            continue
        out.append(val)
        i = start + n


def _calls_from_text(text: str, known: Optional[set]) -> List[Dict[str, Any]]:
    t = _THINK.sub("", text or "")
    if "{{" in t and "}}" in t:
        t = t.replace("{{", "{").replace("}}", "}")
    t = t.replace(_PY_TAG, " ")
    chunks = [m.group(2) for m in _TEXT_TAGS.finditer(t)] + [m.group(1) for m in _FENCE.finditer(t)]
    for src in chunks + [t]:  # tagged/fenced first; whole text last
        calls = []
        for v in _json_values(src):
            for d in v if isinstance(v, list) else [v]:
                c = _norm_call(d, known)
                if c:
                    calls.append(c)
        if calls:
            return calls
    return []


def parse_tool_calls(msg: Dict[str, Any], known: Optional[set] = None) -> List[Dict[str, Any]]:
    """Structured ``tool_calls`` first; otherwise tool calls written as text (see module doc).

    ``known``: names of the offered tools. Text fallbacks other than ``<tool_call>`` require it (when None,
    hive_tools.SPECS is used), so arbitrary JSON in an answer is never mistaken for a call."""
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
    if out:
        return out
    content = str(msg.get("content") or "")
    for m in _TC.finditer(content):
        try:
            d = json.loads(m.group(1))
            out.append({"name": d.get("name"), "arguments": d.get("arguments") or {}, "id": None})
        except json.JSONDecodeError:
            continue
    if out or not content.strip():
        return out
    return _calls_from_text(content, set(known) if known is not None else set(hive_tools.SPECS))


def run(chat: ChatFn, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, max_rounds: int = 4,
        offline: bool = False, ctx: Optional[Dict[str, Any]] = None, project: str = "realai") -> Dict[str, Any]:
    """Returns {"answer", "messages" (full transcript), "calls": [{name, arguments, result}], "rounds"}."""
    tools = tools if tools is not None else hive_tools.specs()
    known = {str((t.get("function") or t).get("name")) for t in tools} if tools else set()
    msgs = [dict(m) for m in messages]
    calls: List[Dict[str, Any]] = []
    answer = ""
    for rnd in range(max_rounds + 1):
        reply = chat(msgs, tools)
        tcs = parse_tool_calls(reply, known) if rnd < max_rounds else []
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
