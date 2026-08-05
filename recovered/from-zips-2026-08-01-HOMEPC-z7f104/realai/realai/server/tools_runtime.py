"""Declarative tool manifest and runtime policy checks."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolManifest:
    name: str
    description: str
    params: Dict[str, str] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    timeout_ms: int = 8000
    safety_class: str = 'standard'

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'params': self.params,
            'permissions': self.permissions,
            'timeout_ms': self.timeout_ms,
            'safety_class': self.safety_class,
        }


class ToolRuntime(object):
    """Tool registry with simple permission policy and audit logs."""

    def __init__(self):
        self._tools: Dict[str, ToolManifest] = {}
        self._audit: List[Dict[str, Any]] = []
        self._register_defaults()

    def _register_defaults(self):
        self.register(ToolManifest(
            name='web_search',
            description='Search the web',
            params={'query': 'string'},
            permissions=['network'],
            timeout_ms=8000,
            safety_class='networked',
        ))
        self.register(ToolManifest(
            name='file_read',
            description='Read local files',
            params={'path': 'string'},
            permissions=['filesystem.read'],
            timeout_ms=5000,
            safety_class='restricted',
        ))
        self.register(ToolManifest(
            name='web3_solana_rpc',
            description='Call Solana RPC methods',
            params={'method': 'string', 'params': 'object'},
            permissions=['web3.solana'],
            timeout_ms=10000,
            safety_class='privileged',
        ))

    def register(self, manifest: ToolManifest):
        self._tools[manifest.name] = manifest

    def list_tools(self):
        return [tool.to_dict() for tool in sorted(self._tools.values(), key=lambda t: t.name)]

    def get(self, name: str):
        if name not in self._tools:
            raise ValueError('Unknown tool {0}'.format(name))
        return self._tools[name]

    def authorize(self, tool_name: str, allowed_permissions=None):
        allowed = set(allowed_permissions or [])
        manifest = self.get(tool_name)
        required = set(manifest.permissions)
        missing = sorted(required - allowed)
        return {
            'authorized': len(missing) == 0,
            'missing_permissions': missing,
            'required_permissions': sorted(required),
        }

    def audit(self, tool_name: str, actor: str, outcome: str):
        self._audit.append({
            'tool': tool_name,
            'actor': actor or 'system',
            'outcome': outcome,
            'timestamp': int(time.time()),
        })

    def list_audit(self):
        return list(self._audit[-200:])


TOOLS = ToolRuntime()
