"""Safety policy for Web3 operations."""

from typing import Any, Dict


class Web3Policy:
    def __init__(self, max_spend: float = 0.1):
        self.max_spend = float(max_spend)

    def _tx_value(self, tx: Dict[str, Any]) -> float:
        value = tx.get("value", 0)
        try:
            return float(value)
        except Exception:
            return 0.0

    def require_approval(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        if self._tx_value(tx) > 0 and not bool(tx.get("approved", False)):
            return {
                "requires_approval": True,
                "tx_summary": {
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "value": self._tx_value(tx),
                    "nonce": tx.get("nonce"),
                },
            }
        return {"requires_approval": False}

    def validate_tx(self, tx: Dict[str, Any], context: Dict[str, Any] = None):
        context = context if isinstance(context, dict) else {}
        max_spend = float(context.get("max_spend", self.max_spend))
        value = self._tx_value(tx)
        if value > max_spend:
            raise ValueError("Transaction exceeds allowed spend limit.")
        approval = self.require_approval(tx)
        if approval.get("requires_approval"):
            raise PermissionError("Transaction requires human approval.")
        return {"ok": True, "value": value, "max_spend": max_spend}
