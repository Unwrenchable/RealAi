"""Chat pipeline with memory retrieval and tool execution loop."""

import json
import time
from typing import Any, Dict, List

from core.memory.sqlite_store import SQLiteMemoryStore
from core.memory.summarizer import ConversationSummarizer
from core.tools.code import CodeExecutionTool
from core.tools.file import FileTool
from core.tools.permissions import Permissions
from core.tools.registry import ToolRegistry
from core.tools.web import WebSearchTool

_MEMORY = SQLiteMemoryStore("realai_memory.sqlite3")
_SUMMARIZER = ConversationSummarizer(trigger_every=4)
_TOOLS = ToolRegistry()
_TOOLS.register(WebSearchTool())
_TOOLS.register(CodeExecutionTool())
_TOOLS.register(FileTool("."))


def _message_embedding(embed_backend, text: str):
    payload = embed_backend.embed([text])
    data = payload.get("data", [])
    if not data:
        return [0.0] * 10
    return data[0].get("embedding", [0.0] * 10)


def _augment_messages(messages: List[Dict[str, Any]], retrieved: List[Dict[str, Any]]):
    if not retrieved:
        return list(messages)
    snippets = [item.get("content", "") for item in retrieved[:3]]
    context = "\n".join("- {0}".format(snippet) for snippet in snippets if snippet)
    augmented = list(messages)
    augmented.insert(0, {"role": "system", "content": "Relevant memory:\n{0}".format(context)})
    return augmented


def _ensure_realai_system(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure RealAI Bot system prompt is present (does not overwrite an existing system)."""
    try:
        from realai.bot.boot import inject_system

        return inject_system(messages)
    except Exception:
        try:
            from realai.bot.boot import DEFAULT_REALAI_PROMPT
        except Exception:
            DEFAULT_REALAI_PROMPT = (
                "You are RealAI, a chat bot and operator built by the RealAI project.\n"
                "You are the provider. Inference runs on the local RealAI stack."
            )
        for item in messages or []:
            if isinstance(item, dict) and str(item.get("role") or "").lower() == "system":
                return list(messages or [])
        out = [{"role": "system", "content": DEFAULT_REALAI_PROMPT}]
        out.extend(list(messages or []))
        return out


def _memory_user_id(user_id: str) -> str:
    """Prefer persona memory namespace when RealAI Bot is active.

    SQLiteMemoryStore currently keys rows by user_id only (no first-class
    namespace column). We encode the active persona namespace into user_id
    as ``{namespace}:{user_id}`` when available so RealAI Bot memory stays
    isolated without a store schema rewrite.
    """
    try:
        from realai.identity import PERSONA_SWITCHER

        active = getattr(PERSONA_SWITCHER, "active", None)
        ns = getattr(active, "memory_namespace", "") if active else ""
        if ns:
            return "{0}:{1}".format(ns, user_id)
    except Exception:
        pass
    return user_id


def _extract_tool_call(response: Dict[str, Any]):
    choices = response.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message", {})
    return message.get("tool_call")


def _execute_tool_call(tool_call: Dict[str, Any], context: Dict[str, Any]):
    name = tool_call.get("name")
    args = tool_call.get("arguments", {})
    if not isinstance(args, dict):
        args = {}
    result = _TOOLS.execute_tool(name, args, context=context)
    return {"name": name, "result": result}


def run_chat_pipeline(
    user_id: str,
    messages: List[Dict[str, Any]],
    chat_backend,
    embed_backend,
    max_tool_steps: int = 2,
):
    memory_uid = _memory_user_id(user_id)
    latest_user = next((msg for msg in reversed(messages) if msg.get("role") == "user"), {"content": ""})
    query = str(latest_user.get("content", ""))
    query_embedding = _message_embedding(embed_backend, query)
    retrieved = _MEMORY.search(memory_uid, query, k=5)
    augmented_messages = _augment_messages(messages, retrieved)
    augmented_messages = _ensure_realai_system(augmented_messages)
    if chat_backend is None:
        raise RuntimeError("local model offline")
    response = chat_backend.generate(augmented_messages)

    tool_steps = 0
    while tool_steps < max_tool_steps:
        tool_call = _extract_tool_call(response)
        if not tool_call:
            break
        tool_steps += 1
        execution = _execute_tool_call(
            tool_call,
            context={
                "allowed_permissions": [
                    Permissions.NETWORK,
                    Permissions.CODE_EXEC,
                    Permissions.FILESYSTEM,
                ]
            },
        )
        augmented_messages.append({"role": "assistant", "content": json.dumps({"tool_call": tool_call})})
        augmented_messages.append({"role": "tool", "content": json.dumps(execution["result"]), "name": execution["name"]})
        response = chat_backend.generate(augmented_messages)

    assistant_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    _MEMORY.add(memory_uid, [
        {
            "type": "message",
            "content": query,
            "embedding": query_embedding,
            "timestamp": int(time.time()),
        },
        {
            "type": "message",
            "content": assistant_content,
            "embedding": _message_embedding(embed_backend, assistant_content),
            "timestamp": int(time.time()),
        },
    ])
    summary_item = _SUMMARIZER.summarize_if_needed(memory_uid, augmented_messages, chat_backend)
    if summary_item is not None:
        _MEMORY.add(memory_uid, [summary_item])

    # Opt-in RealAI Bot voice metadata from agent-tools tts-stack (no forced TTS).
    try:
        from realai.bot.boot import maybe_voice_route, voice_enabled

        if voice_enabled():
            voice = maybe_voice_route(assistant_content, intent="chat", synthesize=False)
            if isinstance(response, dict):
                meta = dict(response.get("realai_meta") or {})
                meta["voice"] = {
                    "speak": voice.get("speak"),
                    "spoken_text": voice.get("spoken_text"),
                    "enabled": True,
                }
                response["realai_meta"] = meta
    except Exception:
        pass

    return response
