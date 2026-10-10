"""Plugin-based tool router heuristics (promoted from RealAi-unified 763a4c2,
realai/server/router_plug.py). Status: PARTIAL, opt-in plugin. Pure scoring, no I/O."""

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


#: Keyword hints per tool (from RealAi-unified handle_tool_route).
KEYWORD_MAP: Dict[str, List[str]] = {
    'web_search': ['search', 'web', 'news', 'latest', 'find', 'browse'],
    'file_read': ['file', 'read', 'open', 'inspect', 'directory'],
    'web3_solana_rpc': ['solana', 'wallet', 'blockchain', 'rpc', 'transaction'],
}


def route(text: str, allowed_tools: Optional[List[str]] = None, provider: Optional[str] = 'local') -> Dict[str, Any]:
    """Rank allowed tools for ``text``. Provider defaults to local (Vulkan first)."""
    lowered = (text or '').lower()
    tools = [t for t in (allowed_tools or list(KEYWORD_MAP)) if isinstance(t, str)]
    scored = []
    for name in tools:
        base = sum(1.0 for kw in KEYWORD_MAP.get(name, []) if kw in lowered)
        if base <= 0:
            continue
        scored.append({'tool': name, 'score': round(base + ROUTER_PLUGINS.evaluate(name, text, provider=provider), 3)})
    scored.sort(key=lambda item: (-item['score'], item['tool']))
    return {'ok': True, 'provider': provider, 'selected': scored[0]['tool'] if scored else None, 'candidates': scored}


def register(model: Any = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if model is not None:
        setattr(model, 'route_tool', route)
    return {'name': 'tool_router', 'ok': True, 'status': 'PARTIAL', 'methods': ['route_tool']}


def invoke(ability: str, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if ability == 'health':
        return {'plugin': 'tool-router', 'result': {'status': 'ok'}}
    if ability == 'route':
        return {'plugin': 'tool-router', 'result': route(str(payload.get('text', '')), payload.get('allowed_tools'), payload.get('provider', 'local'))}
    return {'plugin': 'tool-router', 'error': 'unknown ability: {0}'.format(ability)}
