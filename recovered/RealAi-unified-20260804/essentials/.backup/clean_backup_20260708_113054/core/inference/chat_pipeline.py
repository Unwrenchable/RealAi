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
    latest_user = next((msg for msg in reversed(messages) if msg.get("role") == "user"), {"content": ""})
    query = str(latest_user.get("content", ""))
    query_embedding = _message_embedding(embed_backend, query)
    retrieved = _MEMORY.search(user_id, query, k=5)
    augmented_messages = _augment_messages(messages, retrieved)
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
    _MEMORY.add(user_id, [
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
    summary_item = _SUMMARIZER.summarize_if_needed(user_id, augmented_messages, chat_backend)
    if summary_item is not None:
        _MEMORY.add(user_id, [summary_item])

    return response
