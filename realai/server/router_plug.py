"""Plugin-based router module for intelligent tool selection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class RouterPlugin(object):
    """Simple plugin interface for router heuristics."""

    name = 'base'

    def score(self, tool_name: str, text: str, provider: Optional[str] = None, **kwargs) -> float:
        return 0.0


class ProviderAwarePlugin(RouterPlugin):
    """Prefer tools that match provider context."""

    name = 'provider-aware'

    def score(self, tool_name: str, text: str, provider: Optional[str] = None, **kwargs) -> float:
        provider = (provider or '').lower()
        if provider == 'local' and tool_name in {'file_read', 'web_search'}:
            return 0.3
        if provider in {'openai', 'remote'} and tool_name == 'web_search':
            return 0.3
        return 0.0


class CostLatencyPlugin(RouterPlugin):
    """Prefer cheaper and faster tools when otherwise equivalent."""

    name = 'cost-latency'

    def score(self, tool_name: str, text: str, provider: Optional[str] = None, **kwargs) -> float:
        cost_map = {'web_search': 0.2, 'file_read': -0.1, 'web3_solana_rpc': 0.4}
        latency_map = {'web_search': 0.2, 'file_read': -0.1, 'web3_solana_rpc': 0.3}
        return cost_map.get(tool_name, 0.0) + latency_map.get(tool_name, 0.0)


class RouterPluginRegistry(object):
    """Registry of router plugins used for selection."""

    def __init__(self):
        self._plugins: List[RouterPlugin] = [ProviderAwarePlugin(), CostLatencyPlugin()]

    def register(self, plugin: RouterPlugin):
        self._plugins.append(plugin)

    def evaluate(self, tool_name: str, text: str, provider: Optional[str] = None, **kwargs) -> float:
        total = 0.0
        for plugin in self._plugins:
            total += plugin.score(tool_name, text, provider=provider, **kwargs)
        return total


ROUTER_PLUGINS = RouterPluginRegistry()
