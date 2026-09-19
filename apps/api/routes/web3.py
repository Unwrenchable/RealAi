"""Web3 route."""

from fastapi import APIRouter

from apps.api.main import web3_policy, web3_registry
from core.api.schemas.web3 import Web3Request
from core.logging.logger import log
from core.tracing.tracer import tracer

router = APIRouter()


@router.post("/v1/web3")
def web3_call(req: Web3Request):
    with tracer.start_as_current_span("web3.route"):
        backend = web3_registry.get(req.backend)
        params = dict(req.params or {})
        context = dict(req.context or {})
        method = req.method
        log("web3.call", {"backend": req.backend, "method": method, "params": params})
        if method == "get_account":
            result = backend.get_account(str(params.get("address", "")))
            return {"result": result}
        if method == "simulate":
            result = backend.simulate(params)
            return {"result": result}
        if method == "send":
            approval = web3_policy.require_approval(params)
            if approval.get("requires_approval"):
                return {"result": approval}
            web3_policy.validate_tx(params, context=context)
            result = backend.send(params)
            return {"result": result}
        result = backend.call(method, params)
        return {"result": result}
