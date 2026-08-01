"""Base agent implementation for RealAI orchestration."""

from typing import Any, Dict, List, Optional

from .tools import ToolRegistry


class BaseAgent:
    """An autonomous agent that uses a RealAI client to fulfil tasks.

    Agents are designed to be composable: the Orchestrator chains them
    together while passing a shared context dict so each agent can build
    on the results of previous ones.

    Args:
        name: Unique name for this agent (e.g. ``"researcher"``).
        role: Plain-language description of the agent's purpose used to
            build its system prompt (e.g. ``"You are a research analyst"``).
        realai_client: A :class:`~realai.RealAIClient` instance (or any
            object with a compatible ``chat.completions`` interface).
        tools: Optional :class:`~tools.ToolRegistry` the agent may call.
        model: Override the default model for this agent.
        temperature: Sampling temperature (0 = deterministic).
        max_tokens: Maximum tokens in the completion.

    Example::

        from realai import RealAIClient
        from realai_orchestration.agent import BaseAgent

        client = RealAIClient()
        agent = BaseAgent(
            name="summarizer",
            role="You are an expert summarizer. Summarize the given text concisely.",
            realai_client=client,
        )
        result = agent.run("Summarise the history of AI.")
    """

    def __init__(
        self,
        name: str,
        role: str,
        realai_client: Any,
        tools: Optional[ToolRegistry] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> None:
        self.name = name
        self.role = role
        self.realai_client = realai_client
        self.tools = tools or ToolRegistry()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute *task* and return the agent's result.

        The agent builds a conversation from the system prompt, an
        optional context summary, and the task, then calls the RealAI
        client for a completion.

        Args:
            task: The instruction or question the agent should address.
            context: Optional dict of shared state from previous agents.

        Returns:
            Dict with keys:
                - ``agent``: this agent's name.
                - ``task``: the original task string.
                - ``output``: the model's response text.
                - ``success``: True if the call succeeded.
                - ``error``: Error message string, or None on success.
        """
        messages = self._build_messages(task, context or {})
        try:
            response = self._call_model(messages)
            return {
                "agent": self.name,
                "task": task,
                "output": response,
                "success": True,
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "agent": self.name,
                "task": task,
                "output": "",
                "success": False,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """Construct the system prompt for this agent.

        Returns:
            System prompt string combining the role description and the
            list of available tools.
        """
        parts = [self.role]

        tool_list = self.tools.list_tools()
        if tool_list:
            tool_descriptions = "\n".join(
                f"  - {t['name']}: {t['description']}" for t in tool_list
            )
            parts.append(f"\nAvailable tools:\n{tool_descriptions}")

        parts.append(
            "\nBe concise, accurate, and return only what is asked for."
        )
        return "\n".join(parts)

    def _build_messages(
        self, task: str, context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Build the messages list to send to the model.

        Args:
            task: The user task.
            context: Shared memory context from previous pipeline steps.

        Returns:
            List of dicts with 'role' and 'content' keys.
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._build_system_prompt()},
        ]

        if context:
            context_lines = []
            for key, value in context.items():
                if isinstance(value, dict) and "output" in value:
                    context_lines.append(f"[{key}]: {value['output']}")
                else:
                    context_lines.append(f"[{key}]: {value}")
            if context_lines:
                messages.append(
                    {
                        "role": "user",
                        "content": "Context from previous steps:\n"
                        + "\n".join(context_lines),
                    }
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": "Understood. I have noted the context.",
                    }
                )

        messages.append({"role": "user", "content": task})
        return messages

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        """Invoke the RealAI client and extract the response text.

        Supports both the :class:`~realai.RealAIClient` interface
        (``client.chat.completions.create``) and simple callables
        that accept a list of messages.

        Args:
            messages: Chat messages to send to the model.

        Returns:
            The model's response as a string.

        Raises:
            RuntimeError: If the client call fails or returns an unexpected
                response shape.
        """
        kwargs: Dict[str, Any] = {}
        if self.model:
            kwargs["model"] = self.model
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        # Support RealAIClient (has .chat.completions.create)
        if hasattr(self.realai_client, "chat") and hasattr(
            self.realai_client.chat, "completions"
        ):
            response = self.realai_client.chat.completions.create(
                messages=messages, **kwargs
            )
            # OpenAI-compatible response object
            if hasattr(response, "choices"):
                return str(response.choices[0].message.content or "")
            # Dict response
            if isinstance(response, dict):
                choices = response.get("choices", [])
                if choices:
                    return str(
                        choices[0].get("message", {}).get("content", "")
                    )
            return str(response)

        # Fallback: treat the client itself as callable
        if callable(self.realai_client):
            result = self.realai_client(messages=messages, **kwargs)
            if isinstance(result, dict):
                choices = result.get("choices", [])
                if choices:
                    return str(
                        choices[0].get("message", {}).get("content", "")
                    )
            return str(result)

        raise RuntimeError(
            f"realai_client {type(self.realai_client)} has no usable "
            "chat.completions.create method and is not callable."
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"BaseAgent(name={self.name!r}, role={self.role[:40]!r}...)"
