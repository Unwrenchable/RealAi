"""
Robust, strict protocol for weak local models (ReAct-style over text).

Design goals (per code review):
- Extremely small, testable surface.
- Rigid output contract that small models can hit reliably.
- Multiple parse strategies (fenced JSON, TOOL:/ARGS:, loose DONE).
- Few-shot examples in the prompt.
- Helpers for "retry with exact format".
- No global side effects.

The contract the model must follow:
  TOOL: tool_name
  ARGS: {json object}

or

  DONE: short summary of what was accomplished

Only one action per turn. Read before you edit. Prefer small verifiable changes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# The canonical system instructions injected for self-build tasks.
# Keep this tight — small models do better with strict, short rules + examples.
BASE_RULES = """You are RealAI Self-Builder running 100% locally on GGUF weights.
Your only job is to improve this RealAI repository using the tools below.

CRITICAL INSTRUCTIONS - FOLLOW EXACTLY OR YOU WILL FAIL:
- Output NOTHING except exactly one TOOL block or one DONE block.
- Your entire response must start with "TOOL:" or "DONE:" and contain nothing else.
- Use exactly ONE tool per turn.
- ALWAYS read_file before any search_replace on that file.
- After receiving an OBSERVATION, immediately output the next action in the exact format.
- When the task is 100% complete (you verified with run_terminal_command that tests pass and the change is correct), output DONE.

Allowed tools: read_file, list_dir, grep, search_replace, run_terminal_command

EXACT OUTPUT FORMAT (copy character for character, no extra spaces or lines):

TOOL: read_file
ARGS: {"target_file": "realai/agent_protocol.py", "limit": 20}

DONE: Made the parser stricter and added test for tuple handling. All tests now pass.

If you output anything except the above format, the system will treat it as failure and send you an error.
"""

# A couple of high-signal few-shot examples. Small models copy style well.
FEW_SHOTS = """
Example 1:
User: Add a unit test for the new parser helper.
Assistant:
TOOL: read_file
ARGS: {"target_file": "tests/test_agent_protocol.py", "limit": 20}

Example 2 (after receiving an observation):
OBSERVATION: {"content": "def parse..."}
Assistant:
TOOL: search_replace
ARGS: {"file_path": "realai/agent_protocol.py", "old_string": "old buggy line", "new_string": "fixed line"}

Example 3 (task complete):
Assistant:
DONE: Added the missing parser test case and verified with unittest. 7 tests passing.
"""

def build_system_prompt(workspace: str, extra_rules: str = "") -> str:
    ws = f"Workspace root: {workspace}\n"
    return ws + BASE_RULES + (extra_rules + "\n" if extra_rules else "") + "\nExamples:\n" + FEW_SHOTS


@dataclass
class ParsedAction:
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    done: Optional[str] = None
    raw: str = ""


def _strip_prefixes(text: str) -> str:
    t = text.strip()
    # Common model echoes / prefixes on Windows + llama.cpp
    t = re.sub(r"^[\s:>*•\-]+", "", t)
    t = re.sub(r"^(user|assistant|system)\s*:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^[\s:]+", "", t)
    return t.strip()


def parse_agent_reply(text: str) -> ParsedAction:
    """
    Robust multi-strategy parser.
    Order of preference:
      1. Fenced JSON block containing {"tool": "...", "args": {...}} or {"done": "..."}
      2. TOOL: name \n ARGS: {json}
      3. DONE: summary  (anywhere, after stripping junk)
    Returns ParsedAction with exactly one of (tool+args) or done set.
    """
    if not text or not text.strip():
        return ParsedAction(raw=text)

    raw = text
    cleaned = _strip_prefixes(text)

    # 1. Fenced JSON (most reliable when model cooperates)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            obj = json.loads(fence.group(1))
            if isinstance(obj, dict):
                if obj.get("tool"):
                    return ParsedAction(tool=str(obj["tool"]), args=obj.get("args") or obj.get("arguments") or {}, raw=raw)
                if obj.get("done") or obj.get("DONE"):
                    return ParsedAction(done=str(obj.get("done") or obj.get("DONE")).strip(), raw=raw)
        except json.JSONDecodeError:
            pass

    # 2. Classic TOOL / ARGS (our primary training target)
    tool_m = re.search(r"TOOL:\s*([a-zA-Z0-9_\-]+)", cleaned, re.IGNORECASE)
    args_m = re.search(r"ARGS:\s*(\{.*\})", cleaned, re.DOTALL | re.IGNORECASE)
    if tool_m and args_m:
        try:
            args = json.loads(args_m.group(1))
            if isinstance(args, dict):
                return ParsedAction(tool=tool_m.group(1).strip(), args=args, raw=raw)
        except json.JSONDecodeError:
            pass

    # 3. DONE anywhere (after tool attempts failed)
    done_m = re.search(r"DONE:\s*(.+?)(?:\n|$)", cleaned, re.IGNORECASE | re.DOTALL)
    if done_m:
        summary = done_m.group(1).strip().split("\n")[0].strip()
        if summary:
            return ParsedAction(done=summary, raw=raw)

    # Nothing recognizable
    return ParsedAction(raw=raw)


def format_retry_message(last_raw: str, hint: str = "") -> str:
    """Message to feed back to the model when it produced unparseable output."""
    base = (
        "Your previous reply was not in the exact required format.\n"
        "Output ONLY one of these (nothing else):\n\n"
        "TOOL: tool_name\n"
        'ARGS: {"param": "value"}\n\n'
        "or\n\n"
        "DONE: short summary here\n\n"
    )
    if hint:
        base += f"Hint: {hint}\n"
    if last_raw:
        base += f"Previous (do not repeat this style):\n{last_raw[:600]}\n"
    return base


def is_done(action: ParsedAction) -> bool:
    if isinstance(action, (list, tuple)):
        # Legacy 3-tuple compat: (tool, args, done)
        if len(action) >= 3:
            return bool(action[2])
        return False
    return bool(getattr(action, "done", None) and not getattr(action, "tool", None))


def is_tool_call(action: ParsedAction) -> bool:
    if isinstance(action, (list, tuple)):
        if len(action) >= 3:
            return bool(action[0]) and bool(action[1])
        return False
    return bool(getattr(action, "tool", None) and getattr(action, "args", None) is not None)


# Small set of canonical tool names we expect for self-build.
REPO_TOOLS = {"read_file", "list_dir", "grep", "search_replace", "run_terminal_command"}


def normalize_repo_args(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Map common model mistakes to the exact param names our handlers expect."""
    a = dict(args or {})
    if tool == "read_file":
        if "target_file" not in a:
            for k in ("file_path", "path", "file"):
                if k in a:
                    a["target_file"] = a.pop(k)
                    break
    elif tool == "list_dir":
        if "target_directory" not in a:
            for k in ("path", "dir", "directory"):
                if k in a:
                    a["target_directory"] = a.pop(k)
                    break
    elif tool == "search_replace":
        if "file_path" not in a:
            for k in ("target_file", "path"):
                if k in a:
                    a["file_path"] = a.pop(k)
                    break
    elif tool == "grep":
        if "path" not in a and "target_directory" in a:
            a["path"] = a.pop("target_directory")
    return a
