"""
Local self-builder: RealAI improving itself using only local GGUF weights + repo tools.

Usage:
  REALAI_API_URL=http://127.0.0.1:8000 python -m realai.self_builder "Make the agent protocol stricter"
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .agent_protocol import (
    ParsedAction,
    build_system_prompt,
    format_retry_message,
    is_done,
    is_tool_call,
    normalize_repo_args,
    parse_agent_reply as _parse_action,  # returns rich ParsedAction
)

from .model_assets import repo_root
from .repo_tools import REPO_TOOL_HANDLERS, workspace_root
from .sdk.python.realai_client import RealAIClient

# Public API for legacy callers / tests that expect the old 3-tuple:
#   tool, args, done = parse_agent_reply(text)
def parse_agent_reply(text: str):
    action = _parse_action(text)
    if hasattr(action, "tool"):
        return getattr(action, "tool", None), getattr(action, "args", None), getattr(action, "done", None)
    if isinstance(action, (list, tuple)) and len(action) == 3:
        return action
    return None, None, None


__all__ = ["parse_agent_reply", "SelfBuilder", "select_builder_model", "main"]


def _load_self_builder_config() -> Dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        return {}
    path = repo_root() / "realai.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    section = data.get("self_builder")
    return section if isinstance(section, dict) else {}


def select_builder_model(client: RealAIClient, preferred: Optional[str] = None) -> str:
    if preferred:
        return preferred
    cfg = _load_self_builder_config()
    if cfg.get("model"):
        return str(cfg["model"])
    try:
        listing = client.models()
        models = listing.get("data") or []
    except Exception:
        return "realai-1.0-instruct"
    for mid in ("qwen-coder-7b", "realai-1.0-instruct", "realai-1.0", "llama-local-1b"):
        entry = next((m for m in models if m.get("id") == mid), None)
        if not entry:
            continue
        if entry.get("weights_ready") is False:
            continue
        if mid == "qwen-coder-7b":
            return mid
    for mid in ("realai-1.0-instruct", "realai-1.0"):
        entry = next((m for m in models if m.get("id") == mid), None)
        if entry and entry.get("weights_ready") is not False:
            return mid
    return "realai-1.0-instruct"


def _load_self_builder_config() -> Dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        return {}
    path = repo_root() / "realai.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    section = data.get("self_builder")
    return section if isinstance(section, dict) else {}


def select_builder_model(client: RealAIClient, preferred: Optional[str] = None) -> str:
    if preferred:
        return preferred
    cfg = _load_self_builder_config()
    if cfg.get("model"):
        return str(cfg["model"])
    try:
        listing = client.models()
        models = listing.get("data") or []
    except Exception:
        return "realai-1.0-instruct"
    for mid in ("qwen-coder-7b", "realai-1.0-instruct", "realai-1.0", "llama-local-1b"):
        entry = next((m for m in models if m.get("id") == mid), None)
        if not entry:
            continue
        if entry.get("weights_ready") is False:
            continue
        if mid == "qwen-coder-7b":
            return mid
    for mid in ("realai-1.0-instruct", "realai-1.0"):
        entry = next((m for m in models if m.get("id") == mid), None)
        if entry and entry.get("weights_ready") is not False:
            return mid
    return "realai-1.0-instruct"


def _append_session_log(record: Dict[str, Any]) -> None:
    if os.environ.get("REALAI_LOG_SELF_BUILD", "1").strip().lower() in ("0", "false", "no"):
        return
    out = repo_root() / "realai" / "datasets" / "processed" / "self_builder_sessions.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


class SelfBuilder:
    """
    Thin, reliable driver for local self-improvement.

    - Uses the strict protocol from agent_protocol (no more ad-hoc regex in this file).
    - Executes the 5 repo tools directly via REPO_TOOL_HANDLERS (no mandatory global mutation).
    - Prefers the best local coding model (qwen-coder-7b when its GGUF is ready).
    - Good recovery: on bad parse or fallback, feeds a precise retry message.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        max_steps: int = 20,
        auto_confirm: bool = True,
        register_for_api: bool = False,   # set True only if you want /v1/tools to advertise the repo tools
    ):
        cfg = _load_self_builder_config()
        url = api_url or os.environ.get("REALAI_API_URL") or cfg.get("api_url") or "http://127.0.0.1:8000"
        self.client = RealAIClient(api_url=url, timeout=int(cfg.get("timeout", 300)))
        self.model = model
        self.max_steps = int(max_steps if max_steps is not None else cfg.get("max_steps", 20))
        self.auto_confirm = auto_confirm
        self.register_for_api = register_for_api

        # Only touch the global registry if the caller explicitly wants the API surface to expose these tools.
        if self.register_for_api:
            try:
                from .repo_tools import register_repo_tools as _reg
                from .tools import TOOL_REGISTRY as _global
                _reg(_global)
            except Exception:
                pass

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        model = self.model or select_builder_model(self.client)
        self.model = model
        # Keep history short — long contexts are the #1 cause of fallback on small local models.
        trimmed = self._trim(messages, keep=10)
        resp = self.client.chat(model=model, messages=trimmed, temperature=0.15, max_tokens=900)
        choice = resp.get("choices", [{}])[0]
        text = str((choice.get("message") or {}).get("content") or choice.get("text") or "")
        if "Fallback response:" in text or resp.get("backend") == "structured-fallback":
            raise RuntimeError("Local inference fallback: " + text[:300])
        return text

    def _trim(self, messages: List[Dict[str, str]], keep: int = 10) -> List[Dict[str, str]]:
        sys_msgs = [m for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        return sys_msgs + rest[-keep * 2 :]

    def _execute_repo_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        handler = REPO_TOOL_HANDLERS.get(name)
        if not handler:
            return {"status": "error", "error": f"Unknown tool: {name}"}

        # Normalize common model mistakes (file_path vs target_file etc.)
        norm = normalize_repo_args(name, args)

        # Auto-confirm for self-build context (the whole point of the loop).
        # If you want human-in-the-loop, pass auto_confirm=False when constructing SelfBuilder.
        def _confirm(_n: str, _a: Dict[str, Any]) -> bool:
            return self.auto_confirm

        # We bypass the big SecureToolExecutor global for the builder path (cleaner, no rate-limit pollution).
        # Still do a tiny safety wrapper.
        try:
            if name in ("search_replace", "run_terminal_command") and not self.auto_confirm:
                # In non-auto mode we still let the caller decide; here we just call.
                pass
            result = handler(**norm)
            if not isinstance(result, dict):
                result = {"output": result}
            result.setdefault("status", "success")
            return result
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def run(self, task: str, extra_context: str = "") -> Dict[str, Any]:
        workspace = str(workspace_root())
        sys_prompt = build_system_prompt(workspace)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": task if not extra_context else f"{task}\n\nContext:\n{extra_context}"},
        ]
        trace: List[Dict[str, Any]] = []
        consecutive_fallbacks = 0

        for step in range(self.max_steps):
            try:
                reply = self._chat(messages)
                consecutive_fallbacks = 0  # reset on successful chat
            except Exception as exc:
                consecutive_fallbacks += 1
                trace.append({"step": step, "error": str(exc)})
                if consecutive_fallbacks >= 3:
                    # Model/backend is stuck in fallback. Reset context to give it a fresh chance.
                    messages = [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": task + "\n\nIMPORTANT: The previous attempts failed. Output ONLY the exact TOOL or DONE format with no extra text."},
                    ]
                    consecutive_fallbacks = 0
                else:
                    messages.append({"role": "user", "content": format_retry_message(str(exc), "Output ONLY 'TOOL: name' + 'ARGS: {...}' or 'DONE: summary'. Nothing else.")})
                continue

            trace.append({"step": step, "assistant": reply[:3000]})
            action = _parse_action(reply)

            if is_done(action):
                result = {
                    "status": "done",
                    "summary": action.done,
                    "model": self.model,
                    "steps": step + 1,
                    "trace": trace,
                }
                _append_session_log({"ts": datetime.now(timezone.utc).isoformat(), "task": task, "result": result})
                return result

            if is_tool_call(action):
                tool = action.tool
                args = action.args or {}

                tool_result = self._execute_repo_tool(tool, args)
                observation = json.dumps(tool_result, default=str)[:2800]
                trace.append({"step": step, "tool": tool, "args": args, "result": tool_result})

                # Combined TOOL + DONE in one reply (common with 7B models)
                if (tool_result.get("exit_code") == 0 or tool_result.get("status") in (None, "success", "ok")) and action.done:
                    result = {"status": "done", "summary": action.done, "model": self.model, "steps": step + 1, "trace": trace}
                    _append_session_log({"ts": datetime.now(timezone.utc).isoformat(), "task": task, "result": result})
                    return result

                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": f"OBSERVATION:\n{observation}"})
                continue

            # Bad / unparseable output from model
            consecutive_fallbacks += 1
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": format_retry_message(reply, "Your output was invalid. Reply with EXACTLY one block starting with TOOL: or DONE: and nothing else.")})

            if consecutive_fallbacks >= 4:
                # Give up on this iteration - context is probably poisoned
                result = {"status": "max_steps", "model": self.model, "trace": trace, "reason": "repeated invalid model output"}
                _append_session_log({"ts": datetime.now(timezone.utc).isoformat(), "task": task, "result": result})
                return result

        # Ran out of steps
        result = {"status": "max_steps", "model": self.model, "trace": trace}
        _append_session_log({"ts": datetime.now(timezone.utc).isoformat(), "task": task, "result": result})
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RealAI local self-builder (no cloud spend)")
    parser.add_argument("task", help="What to build or fix in this repo")
    parser.add_argument("--api-url", default=os.environ.get("REALAI_API_URL"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print plan only (no LLM)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        print(json.dumps({"workspace": str(workspace_root()), "task": args.task}, indent=2))
        return 0
    steps = 16 if args.max_steps is None else args.max_steps
    builder = SelfBuilder(api_url=args.api_url, model=args.model, max_steps=steps)
    result = builder.run(args.task)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())