"""Specialist agents for RealAI hierarchical system (promoted from gold).

Works with or without langgraph/langchain. Heavy deps are optional.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .tools import get_tools_for_agent


class SpecialistAgent:
    """Base class for specialist agents."""

    def __init__(self, name: str, expertise: str, system_prompt: str):
        self.name = name
        self.expertise = expertise
        self.system_prompt = system_prompt
        self.tools = get_tools_for_agent(name.lower())
        self.agent = None
        try:
            from langchain_core.prompts import ChatPromptTemplate  # type: ignore
            from langgraph.prebuilt import create_react_agent  # type: ignore
            from .llm import get_llm

            self.agent = create_react_agent(
                model=get_llm(),
                tools=self.tools,
                prompt=ChatPromptTemplate.from_messages(
                    [
                        ("system", system_prompt),
                        ("placeholder", "{messages}"),
                    ]
                ),
            )
        except Exception:
            self.agent = None

    def invoke(self, messages: list[Any], config: Any = None) -> dict:
        """Invoke the specialist agent (langgraph) or fallback summary."""
        if self.agent is not None:
            return self.agent.invoke({"messages": messages}, config=config)
        # Fallback: run first matching tool if last message is text-like
        text = ""
        if messages:
            last = messages[-1]
            text = getattr(last, "content", None) or str(last)
        tool_names = []
        for t in self.tools:
            tool_names.append(getattr(t, "name", None) or getattr(t, "__name__", type(t).__name__))
        result = None
        if self.tools and text:
            fn = self.tools[0]
            try:
                # langchain tool vs plain callable
                if hasattr(fn, "invoke"):
                    result = fn.invoke(text)
                elif callable(fn):
                    result = fn(text)
            except Exception as e:
                result = f"tool_error:{e}"
        return {
            "agent": self.name,
            "expertise": self.expertise,
            "tools": tool_names,
            "fallback": True,
            "input": text[:2000],
            "result": result,
            "system": self.system_prompt[:500],
        }


class ResearchAgent(SpecialistAgent):
    def __init__(self) -> None:
        super().__init__(
            "Researcher",
            "Deep Research & Knowledge Synthesis",
            """You are a Research Specialist in the RealAI hierarchical system.
Provide well-researched, evidence-based responses with citations when possible.""",
        )


class CodingAgent(SpecialistAgent):
    def __init__(self) -> None:
        super().__init__(
            "Coder",
            "Software Development & Technical Implementation",
            """You are a Coding Specialist in the RealAI hierarchical system.
Write clean, efficient, tested code and explain your approach.""",
        )


class CreativeAgent(SpecialistAgent):
    def __init__(self) -> None:
        super().__init__(
            "Creative",
            "Writing & Creative Expression",
            """You are a Creative Specialist in the RealAI hierarchical system.
Produce vivid, coherent creative content matching the requested style.""",
        )


class ExecutionAgent(SpecialistAgent):
    def __init__(self) -> None:
        super().__init__(
            "Executor",
            "Task Automation & Implementation",
            """You are an Execution Specialist in the RealAI hierarchical system.
Turn plans into concrete executable steps and automate where safe.""",
        )


class CriticAgent(SpecialistAgent):
    def __init__(self) -> None:
        super().__init__(
            "Critic",
            "Quality Assessment & Improvement",
            """You are a Critic Specialist in the RealAI hierarchical system.
Find errors, gaps, and improvements; be specific and actionable.""",
        )


_AGENT_REGISTRY: Optional[Dict[str, SpecialistAgent]] = None


def get_agent_registry() -> Dict[str, SpecialistAgent]:
    global _AGENT_REGISTRY
    if _AGENT_REGISTRY is None:
        _AGENT_REGISTRY = {
            "researcher": ResearchAgent(),
            "coder": CodingAgent(),
            "creative": CreativeAgent(),
            "executor": ExecutionAgent(),
            "critic": CriticAgent(),
        }
    return _AGENT_REGISTRY


def get_agent(agent_type: str) -> Optional[SpecialistAgent]:
    """Get a specialist agent by type."""
    return get_agent_registry().get((agent_type or "").lower())
