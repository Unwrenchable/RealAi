"""Web3 ability surface — policy-gated wrappers over core.web3.

Unique Solana/EVM backends already live in ``core/web3/``. External
``C:\\tools\\realai`` ``web3.js`` / ``solana.js`` stubs are empty (0 bytes) and
are NOT source of truth.

Secrets policy: never copy wallet keys/tokens from CLI or recovered trees.
Optional EVM private key is read only from env ``REALAI_EVM_PRIVATE_KEY``.
"""

from __future__ import annotations

import os
from typing import Any

ABILITY = {
    "id": "web3_integration",
    "name": "web3_integration",
    "type": "ability",
    "status": "CODE",
    "source": "core.web3 + core.tools.web3.Web3Tool",
    "dest": "abilities/web3_integration.py",
    "capabilities": ["solana_rpc", "evm_rpc", "policy_gated_tx"],
    "secrets_policy": "env-only; never promote wallet keys from CLI/recovered trees",
}


def get_web3_tool() -> Any:
    """Build a policy-gated Web3Tool from in-tree backends (no secret files)."""
    from core.tools.web3 import Web3Tool
    from core.web3.evm_backend import EVMBackend
    from core.web3.policy import Web3Policy
    from core.web3.registry import Web3Registry
    from core.web3.solana_backend import SolanaBackend

    registry = Web3Registry()
    registry.register(SolanaBackend())
    evm_rpc = (os.getenv("REALAI_EVM_RPC_URL") or "").strip()
    if evm_rpc:
        try:
            registry.register(
                EVMBackend(evm_rpc, private_key=os.getenv("REALAI_EVM_PRIVATE_KEY"))
            )
        except Exception:
            pass
    return Web3Tool(registry, policy=Web3Policy())
