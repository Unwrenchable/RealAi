"""Web3 ability surface: Solana-first, read-only + simulate by default.

Backends live in ``realai/core/web3`` (``core.web3`` via the compat package).

Safety rules (enforced here, not just documented):

* Default chain is **Solana** (RPC from ``REALAI_SOLANA_RPC``, else the public
  mainnet-beta endpoint). EVM is only registered when ``REALAI_EVM_RPC_URL`` is
  set, and always read-only (no private key is ever loaded).
* Allowed without approval: read RPC methods (see ``READ_METHODS``) and
  ``simulate``.
* Anything that moves value (``send``/``sendTransaction``/``eth_sendRawTransaction``...)
  is **blocked by default**. It only goes through when BOTH the environment
  flag ``REALAI_WEB3_ALLOW_SEND=1`` is set AND the call passes ``approved=True``.
  The caller must supply an already-signed transaction: this module never reads
  keypairs, wallet files or ``*_PRIVATE_KEY`` env vars.
"""

from __future__ import annotations

import os
from typing import Any

ABILITY = {
    "id": "web3_integration",
    "name": "web3_integration",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.core.web3 + realai.core.tools.web3.Web3Tool",
    "dest": "abilities/web3_integration.py",
    "capabilities": ["solana_rpc", "evm_rpc_readonly", "simulate", "policy_gated_tx"],
    "secrets_policy": "never loads keys; signed tx must be supplied by caller; send blocked by default",
}

DEFAULT_CHAIN = "solana"
DEFAULT_SOLANA_RPC = "https://api.mainnet-beta.solana.com"

READ_METHODS = {
    # Solana
    "getAccountInfo", "getBalance", "getBlockHeight", "getEpochInfo", "getHealth",
    "getLatestBlockhash", "getMultipleAccounts", "getProgramAccounts",
    "getSignaturesForAddress", "getSignatureStatuses", "getSlot", "getSupply",
    "getTokenAccountBalance", "getTokenAccountsByOwner", "getTokenLargestAccounts",
    "getTokenSupply", "getTransaction", "getVersion", "getMinimumBalanceForRentExemption",
    # EVM
    "eth_blockNumber", "eth_call", "eth_chainId", "eth_estimateGas", "eth_gasPrice",
    "eth_getBalance", "eth_getCode", "eth_getLogs", "eth_getTransactionByHash",
    "eth_getTransactionCount", "eth_getTransactionReceipt",
}
SEND_METHODS = {"send", "sendTransaction", "eth_sendRawTransaction", "eth_sendTransaction", "requestAirdrop"}


def _send_allowed(ctx: dict[str, Any]) -> bool:
    env_ok = str(os.getenv("REALAI_WEB3_ALLOW_SEND") or "").strip().lower() in {"1", "true", "yes"}
    return env_ok and ctx.get("approved") is True


def get_web3_tool() -> Any:
    from realai.core.tools.web3 import Web3Tool
    from realai.core.web3.evm_backend import EVMBackend
    from realai.core.web3.policy import Web3Policy
    from realai.core.web3.registry import Web3Registry
    from realai.core.web3.solana_backend import SolanaBackend

    registry = Web3Registry()
    registry.register(SolanaBackend(rpc_url=(os.getenv("REALAI_SOLANA_RPC") or DEFAULT_SOLANA_RPC).strip()))
    evm_rpc = (os.getenv("REALAI_EVM_RPC_URL") or "").strip()
    if evm_rpc:
        try:
            registry.register(EVMBackend(evm_rpc, private_key=None))
        except Exception:
            pass
    return Web3Tool(registry, policy=Web3Policy())


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute a policy-gated web3 operation.

    context keys: ``chain`` (solana|evm), ``method`` (RPC method, ``get_account``,
    ``simulate`` or ``send``), ``address``, ``params`` (list/dict), ``transaction``
    (signed, base64/hex), ``approved`` (bool).
    """
    ctx = dict(context or {})
    ctx.update(kwargs)
    chain = str(ctx.get("chain") or ctx.get("blockchain") or DEFAULT_CHAIN).lower()
    if chain in {"ethereum", "eth", "base", "polygon", "bsc", "arbitrum"}:
        chain = "evm"
    method = str(ctx.get("method") or ctx.get("operation") or input or "getHealth").strip()
    if method == "query":
        method = "getAccountInfo" if ctx.get("address") else "getHealth"
    base = {"ability": "web3_integration", "chain": chain, "method": method}

    if method in SEND_METHODS:
        if not _send_allowed(ctx):
            return {
                **base,
                "ok": False,
                "status": "blocked",
                "error": "value-moving transactions are blocked by default",
                "hint": "set REALAI_WEB3_ALLOW_SEND=1 and pass approved=True with a pre-signed transaction",
            }
        if not ctx.get("transaction"):
            return {**base, "ok": False, "status": "blocked", "error": "signed transaction required; keys are never loaded"}
    elif method not in READ_METHODS and method not in {"get_account", "simulate"}:
        return {**base, "ok": False, "status": "blocked", "error": f"method not in read-only allowlist: {method}"}

    try:
        tool = get_web3_tool()
    except Exception as exc:
        return {**base, "ok": False, "status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}
    if chain not in tool.registry.backends:
        return {**base, "ok": False, "status": "unavailable", "error": f"chain not configured: {chain}"}

    try:
        if method == "get_account":
            result = tool(backend=chain, method="get_account", params={"address": str(ctx.get("address") or "")})
        elif method == "simulate":
            if not ctx.get("transaction"):
                return {**base, "ok": False, "status": "error", "error": "transaction (base64) required for simulate"}
            result = tool(backend=chain, method="simulate", params={"transaction": ctx["transaction"]})
        elif method in SEND_METHODS:
            result = tool(
                backend=chain,
                method="send",
                params={"transaction": ctx["transaction"], "approved": True, "value": ctx.get("value", 0)},
                _context={"max_spend": float(ctx.get("max_spend", 0.1))},
            )
        else:
            params = ctx.get("params")
            if params is None:
                params = [ctx["address"]] if ctx.get("address") else []
            result = tool.registry.get(chain).call(method, {"params": params} if isinstance(params, list) else params)
    except Exception as exc:
        return {**base, "ok": False, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
    err = result.get("error") if isinstance(result, dict) else None
    return {**base, "ok": err is None, "status": "success" if err is None else "error", "result": result, "real": True}
