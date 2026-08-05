"""Solana JSON-RPC backend."""

from typing import Any, Dict, List

from core.logging.logger import log
from core.tracing.tracer import tracer

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


class SolanaBackend:
    name = "solana"

    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com", timeout: int = 10):
        self.rpc = rpc_url
        self.timeout = timeout

    def _rpc(self, method: str, params: List[Any]) -> Dict[str, Any]:
        if requests is None:
            raise RuntimeError("requests dependency is unavailable for Solana backend")
        with tracer.start_as_current_span("web3.call"):
            log("web3.call", {"backend": self.name, "method": method, "params": params})
            response = requests.post(
                self.rpc,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

    def get_account(self, address: str) -> Dict[str, Any]:
        return self._rpc("getAccountInfo", [address, {"encoding": "jsonParsed"}])

    def simulate(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        payload = tx.get("transaction", tx)
        result = self._rpc("simulateTransaction", [payload])
        log("web3.tx_simulated", {"backend": self.name, "tx": payload, "result": result})
        return result

    def send(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        payload = tx.get("transaction", tx)
        result = self._rpc("sendTransaction", [payload])
        log("web3.tx_sent", {"backend": self.name, "tx": payload, "signature": result})
        return result

    def call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(params, dict):
            rpc_params = params.get("params", [])
            if not isinstance(rpc_params, list):
                rpc_params = [rpc_params]
            return self._rpc(method, rpc_params)
        if isinstance(params, list):
            return self._rpc(method, params)
        return self._rpc(method, [params])
