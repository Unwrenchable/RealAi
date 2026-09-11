"""Specialist tool suite for hierarchical agents (promoted from hierarchical_agent_gold).

Import-safe: langchain / RealAIClient are optional. Plain callables always available
for hive / craft / MESSAGE_BUS wiring.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

TOOL_NAMES = (
    "web_research",
    "code_execution",
    "math_solver",
    "creative_writer",
    "data_analyzer",
    "image_processor",
    "task_automator",
    "knowledge_synthesizer",
    "self_reflector",
    "pyramid",
    "roc",
    "glicko2",
    "money_audit",
)


def _hive_base() -> str:
    return (
        os.environ.get("REALAI_API_URL")
        or os.environ.get("REALAI_API_BASE")
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def _hive_chat(prompt: str, system: str = "") -> str:
    """Best-effort local hive completion; returns error string on failure."""
    payload = {
        "model": os.environ.get("REALAI_DEFAULT_MODEL") or "realai-default-coder",
        "messages": [],
        "temperature": 0.2,
    }
    if system:
        payload["messages"].append({"role": "system", "content": system})
    payload["messages"].append({"role": "user", "content": prompt})
    try:
        req = urllib.request.Request(
            f"{_hive_base()}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            or json.dumps(data)[:2000]
        )
    except Exception as e:
        return f"hive_unavailable:{type(e).__name__}:{e}"


def _try_realai_client() -> Any:
    try:
        from realai import RealAIClient  # type: ignore

        return RealAIClient()
    except Exception:
        try:
            from sdk.python.realai_client import RealAIClient  # type: ignore

            return RealAIClient()
        except Exception:
            return None


_client = None


def _client_or_none() -> Any:
    global _client
    if _client is False:
        return None
    if _client is None:
        c = _try_realai_client()
        _client = c if c is not None else False
    return None if _client is False else _client


def _plain(name: str, impl: Callable[..., str]) -> Callable[..., str]:
    impl.__name__ = name
    impl.__doc__ = impl.__doc__ or name
    return impl


def web_research(query: str, depth: str = "comprehensive") -> str:
    """Advanced web research with multiple sources and analysis."""
    c = _client_or_none()
    if c is not None:
        try:
            web = getattr(c, "web", None)
            if web is not None and hasattr(web, "research"):
                return json.dumps(web.research(query=query, depth=depth), indent=2)
        except Exception as e:
            return f"Research failed: {e}"
    # Prefer hive tool path
    try:
        from realai.v3_runtime_bridge import execute_registry_tool

        r = execute_registry_tool("web_research", {"query": query, "max_results": 5})
        return json.dumps(r, indent=2, default=str)
    except Exception:
        return _hive_chat(
            f"Research query ({depth}): {query}\nSummarize findings with sources if known.",
            system="You are a research specialist.",
        )


def code_execution(code: str, language: str = "python") -> str:
    """Execute code with safety and analysis."""
    c = _client_or_none()
    if c is not None:
        try:
            model = getattr(c, "model", None)
            if model is not None and hasattr(model, "execute_code"):
                return json.dumps(model.execute_code(code=code, language=language), indent=2)
        except Exception as e:
            return f"Code execution failed: {e}"
    try:
        from realai.v3_runtime_bridge import execute_registry_tool

        r = execute_registry_tool("execute_code", {"code": code, "language": language})
        return json.dumps(r, indent=2, default=str)
    except Exception as e:
        return f"Code execution unavailable: {e}"


def math_solver(problem: str, domain: str = "general") -> str:
    """Solve mathematical and physics problems."""
    c = _client_or_none()
    if c is not None:
        try:
            math = getattr(c, "math", None)
            if math is not None and hasattr(math, "solve"):
                return json.dumps(math.solve(problem=problem, domain=domain), indent=2)
        except Exception as e:
            return f"Math solving failed: {e}"
    return _hive_chat(
        f"Solve ({domain}): {problem}",
        system="You are a careful math/physics solver. Show steps briefly.",
    )


def creative_writer(prompt: str, style: str = "narrative") -> str:
    """Generate creative content."""
    c = _client_or_none()
    if c is not None:
        try:
            creative = getattr(c, "creative", None)
            if creative is not None and hasattr(creative, "write"):
                return json.dumps(creative.write(prompt=prompt, style=style), indent=2)
        except Exception as e:
            return f"Creative writing failed: {e}"
    return _hive_chat(prompt, system=f"Creative writer style={style}.")


def data_analyzer(data: str, analysis_type: str = "statistical") -> str:
    """Analyze data with advanced methods."""
    c = _client_or_none()
    if c is not None:
        try:
            parsed = json.loads(data) if data[:1] in "{[" else data
            da = getattr(c, "data", None)
            if da is not None and hasattr(da, "analyze"):
                return json.dumps(da.analyze(data=parsed, analysis_type=analysis_type), indent=2)
        except Exception as e:
            return f"Data analysis failed: {e}"
    return _hive_chat(
        f"Analyze ({analysis_type}):\n{data[:6000]}",
        system="You are a data analyst. Be concise and numeric when possible.",
    )


def image_processor(image_url: str, action: str = "analyze") -> str:
    """Process and analyze images."""
    c = _client_or_none()
    if c is not None:
        try:
            if action == "analyze" and hasattr(getattr(c, "vision", None) or object(), "analyze"):
                return json.dumps(c.vision.analyze(image_url=image_url), indent=2)
            if action == "edit" and hasattr(getattr(c, "image_edit", None) or object(), "modify"):
                return json.dumps(
                    c.image_edit.modify(image_url=image_url, edit_request="enhance quality"),
                    indent=2,
                )
        except Exception as e:
            return f"Image processing failed: {e}"
    return json.dumps(
        {
            "ok": False,
            "action": action,
            "image_url": image_url,
            "hint": "image_analysis ability still CODE/empty — describe via chat if needed",
        }
    )


def task_automator(task_type: str, details: str) -> str:
    """Automate real-world tasks."""
    c = _client_or_none()
    if c is not None:
        try:
            parsed = json.loads(details) if details[:1] == "{" else {"description": details}
            tasks = getattr(c, "tasks", None)
            if tasks is not None and hasattr(tasks, "automate"):
                return json.dumps(
                    tasks.automate(task_type=task_type, task_details=parsed), indent=2
                )
        except Exception as e:
            return f"Task automation failed: {e}"
    return _hive_chat(
        f"Automate task_type={task_type}\nDetails: {details}",
        system="You are a task automation planner. Produce concrete steps.",
    )


def knowledge_synthesizer(topics: str) -> str:
    """Synthesize knowledge across domains."""
    c = _client_or_none()
    if c is not None:
        try:
            topic_list = json.loads(topics) if topics[:1] == "[" else [topics]
            syn = getattr(c, "synthesis", None)
            if syn is not None and hasattr(syn, "combine"):
                return json.dumps(syn.combine(topics=topic_list), indent=2)
        except Exception as e:
            return f"Knowledge synthesis failed: {e}"
    return _hive_chat(
        f"Synthesize knowledge across: {topics}",
        system="You synthesize cross-domain knowledge clearly.",
    )


def self_reflector(interaction_history: str) -> str:
    """Self-reflection and improvement analysis."""
    c = _client_or_none()
    if c is not None:
        try:
            history = json.loads(interaction_history) if interaction_history[:1] == "[" else []
            ref = getattr(c, "reflection", None)
            if ref is not None and hasattr(ref, "analyze"):
                return json.dumps(ref.analyze(interaction_history=history), indent=2)
        except Exception as e:
            return f"Self-reflection failed: {e}"
    return _hive_chat(
        f"Reflect on this interaction history and suggest improvements:\n{interaction_history[:6000]}",
        system="You are a critic/reflector. Be specific and actionable.",
    )


# Plain registry (always importable)
def _rackup_tool(name: str) -> Callable[..., str]:
    def _fn(**kwargs: Any) -> str:
        try:
            import importlib

            mod = importlib.import_module(f"abilities.rackup.{name}")
            result = mod.run(context=kwargs, **kwargs)
            return json.dumps(result, default=str)[:8000]
        except Exception as e:
            return f"rackup_{name}_error:{e}"

    _fn.__name__ = name
    _fn.__doc__ = f"Specialist-callable RackUp domain tool: {name}"
    return _fn


# Plain registry (always importable)
TOOL_REGISTRY: Dict[str, Callable[..., str]] = {
    "web_research": web_research,
    "code_execution": code_execution,
    "math_solver": math_solver,
    "creative_writer": creative_writer,
    "data_analyzer": data_analyzer,
    "image_processor": image_processor,
    "task_automator": task_automator,
    "knowledge_synthesizer": knowledge_synthesizer,
    "self_reflector": self_reflector,
    "pyramid": _rackup_tool("pyramid"),
    "roc": _rackup_tool("roc"),
    "glicko2": _rackup_tool("glicko2"),
    "money_audit": _rackup_tool("money_audit"),
}

# Optional langchain @tool wrappers when available
try:
    from langchain_core.tools import tool as _lc_tool  # type: ignore

    TOOL_REGISTRY = {name: _lc_tool(fn) for name, fn in TOOL_REGISTRY.items()}  # type: ignore[misc]
except Exception:
    pass


def get_tools_for_agent(agent_type: str) -> List[Any]:
    """Get appropriate tools for different agent types."""
    tool_mappings = {
        "researcher": ["web_research", "data_analyzer", "knowledge_synthesizer"],
        "coder": ["code_execution", "math_solver"],
        "creative": ["creative_writer", "image_processor"],
        "executor": ["task_automator", "code_execution"],
        "critic": ["self_reflector", "data_analyzer"],
        "supervisor": ["web_research", "self_reflector"],
    }
    key = (agent_type or "").lower()
    # SpecialistAgent passes display names like "Researcher"
    aliases = {
        "researcher": "researcher",
        "coder": "coder",
        "creative": "creative",
        "executor": "executor",
        "critic": "critic",
        "supervisor": "supervisor",
    }
    mapped = aliases.get(key, key)
    tool_names = tool_mappings.get(mapped, ["web_research"])
    return [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]


def list_tools() -> Dict[str, str]:
    return {name: (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else name for name, fn in TOOL_REGISTRY.items()}
