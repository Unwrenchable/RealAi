"""Tool registry for RealAI agents.

Tools are callable objects registered by name.  Agents discover available
tools at runtime and the Orchestrator may attach a shared tool registry to
every agent in a pipeline.
"""

from typing import Any, Callable, Dict, List, Optional


class Tool:
    """A named, callable capability that an agent can invoke.

    Args:
        name: Short identifier used to look up the tool.
        description: Human-readable summary of what the tool does.
        func: The callable to execute when the tool is invoked.
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
    ) -> None:
        self.name = name
        self.description = description
        self._func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool.

        Args:
            *args: Positional arguments forwarded to the underlying callable.
            **kwargs: Keyword arguments forwarded to the underlying callable.

        Returns:
            Whatever the underlying callable returns.
        """
        return self._func(*args, **kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Tool(name={self.name!r})"


class ToolRegistry:
    """Central registry that maps tool names to :class:`Tool` instances.

    Example::

        registry = ToolRegistry()

        @registry.register("add", "Add two numbers")
        def add(a, b):
            return a + b

        result = registry.call("add", 1, 2)   # 3
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        """Register a :class:`Tool` instance directly.

        Args:
            tool: Tool to add to the registry.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def register(
        self, name: str, description: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that wraps a function as a :class:`Tool` and registers it.

        Args:
            name: Tool name.
            description: Short description of the tool.

        Returns:
            Decorator function.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add(Tool(name=name, description=description, func=func))
            return func

        return decorator

    def get(self, name: str) -> Optional[Tool]:
        """Look up a tool by name.

        Args:
            name: Tool name to look up.

        Returns:
            The :class:`Tool`, or None if not found.
        """
        return self._tools.get(name)

    def call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Look up and invoke a tool by name.

        Args:
            name: Tool name.
            *args: Positional arguments forwarded to the tool.
            **kwargs: Keyword arguments forwarded to the tool.

        Returns:
            The tool's return value.

        Raises:
            KeyError: If no tool with *name* is registered.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' is not registered.")
        return tool(*args, **kwargs)

    def list_tools(self) -> List[Dict[str, str]]:
        """Return a list of all registered tools with their descriptions.

        Returns:
            List of dicts with 'name' and 'description' keys.
        """
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ToolRegistry(tools={list(self._tools.keys())})"
