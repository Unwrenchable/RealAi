"""Orchestrator glue (opt-in, default OFF so live chat is unchanged).

* Tool loop: REALAI_TOOL_LOOP=1, header ``X-RealAI-Tool-Loop: 1`` or body ``realai_tool_loop: true`` makes
  /v1/chat/completions run realai.hive_tools.tool_loop (model routes -> hive tools execute -> grounded answer).
  Backend: body ``realai_tool_loop_base`` / env REALAI_TOOL_LOOP_BASE (e.g. http://127.0.0.1:8081 for the
  trained 1.5B) else the orchestrator's Vulkan base (:8080).
* Capture: REALAI_CAPTURE=1 logs chats and /v1/tools/execute calls (tagged by project via header
  ``X-RealAI-Project`` / body ``realai_project`` / inference) for the learning loop. See SELF_DATA.md.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional


def _on(v: Any) -> bool:
    return str(v or "").lower() in ("1", "true", "on", "yes")


def _hdr(headers: Dict[str, Any], name: str) -> Optional[str]:
    for k, v in (headers or {}).items():
        if str(k).lower() == name.lower():
            return v
    return None


def project_of(body: Dict[str, Any], headers: Dict[str, Any]) -> Optional[str]:
    return body.get("realai_project") or _hdr(headers, "X-RealAI-Project")


def wants_tool_loop(body: Dict[str, Any], headers: Dict[str, Any]) -> bool:
    return _on(body.get("realai_tool_loop")) or _on(_hdr(headers, "X-RealAI-Tool-Loop")) or _on(os.environ.get("REALAI_TOOL_LOOP"))


def maybe_tool_loop(body: Dict[str, Any], headers: Dict[str, Any], default_base: str) -> Optional[Dict[str, Any]]:
    if not wants_tool_loop(body, headers) or not body.get("messages"):
        return None
    import realai.hive_tools as hive_tools
    from realai.hive_tools import tool_loop

    base = body.get("realai_tool_loop_base") or os.environ.get("REALAI_TOOL_LOOP_BASE") or default_base
    chat = tool_loop.http_chat(base, str(body.get("model") or "local"), temperature=float(body.get("temperature", 0.2)),
                               max_tokens=int(body.get("max_tokens") or 600))
    msgs = [m for m in body["messages"] if m.get("role") in ("system", "user", "assistant", "tool")]
    if not any(m.get("role") == "system" for m in msgs):
        from realai.training.dataset_builder.adapters_tools import TOOL_SYSTEM

        msgs = [{"role": "system", "content": TOOL_SYSTEM}] + msgs
    res = tool_loop.run(chat, msgs, tools=hive_tools.specs(), offline=False, project=project_of(body, headers) or "realai")
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex[:12], "object": "chat.completion", "created": int(time.time()),
        "model": str(body.get("model") or "realai"),
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": res["answer"]}}],
        "realai_meta": {"orchestrator": "v3", "tool_loop": True, "tool_loop_base": base,
                        "tool_calls": [{"name": c["name"], "arguments": c["arguments"], "ok": bool((c["result"] or {}).get("ok"))}
                                       for c in res["calls"]]},
    }


def capture_chat(body: Dict[str, Any], headers: Dict[str, Any], response: Any) -> None:
    try:
        from realai.training.self_data.capture import capture, enabled

        if not enabled() or not isinstance(response, dict):
            return
        msg = ((response.get("choices") or [{}])[0].get("message") or {})
        msgs = [m for m in body.get("messages") or [] if isinstance(m, dict)] + [{"role": "assistant", "content": msg.get("content") or ""}]
        capture(msgs, project=project_of(body, headers), channel="chat")
    except Exception:
        pass


def capture_tool(name: str, args: Any, result: Any, headers: Dict[str, Any]) -> None:
    try:
        from realai.training.self_data.capture import capture, enabled

        if not enabled():
            return
        capture([{"role": "user", "content": f"[tool request] {name}"}], calls=[{"name": name, "arguments": args, "result": result}],
                project=_hdr(headers, "X-RealAI-Project"), channel="tools_execute")
    except Exception:
        pass
