"""Web3 tool adapter for agents."""

from typing import Any, Dict

from core.tools.base import Tool
from core.tools.permissions import Permissions
from core.web3.policy import Web3Policy
from core.web3.registry import Web3Registry


class Web3Tool(Tool):
    name = "web3"
    description = "Execute blockchain operations"
    params_schema = {
        "backend": {"type": "string"},
        "method": {"type": "string"},
        "params": {"type": "object"},
    }
    permissions = [Permissions.WEB3]

    def __init__(self, registry: Web3Registry, policy: Web3Policy = None):
        self.registry = registry
        self.policy = policy or Web3Policy()

    def __call__(self, **kwargs: Any):
        backend_name = str(kwargs.get("backend", "")).strip()
        method = str(kwargs.get("method", "")).strip()
        params = kwargs.get("params", {})
        context = kwargs.get("_context") if isinstance(kwargs.get("_context"), dict) else {}
        if not backend_name:
            raise ValueError("backend is required")
        if not method:
            raise ValueError("method is required")
        if not isinstance(params, dict):
            raise ValueError("params must be an object")

        backend = self.registry.get(backend_name)
        if method == "get_account":
            return backend.get_account(str(params.get("address", "")))
        if method == "simulate":
            return backend.simulate(params)
        if method == "send":
            approval = self.policy.require_approval(params)
            if approval.get("requires_approval"):
                return approval
            self.policy.validate_tx(params, context=context)
            return backend.send(params)
        return backend.call(method, params)

