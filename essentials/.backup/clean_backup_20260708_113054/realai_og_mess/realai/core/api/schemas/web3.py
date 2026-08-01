"""Web3 API schemas."""

from typing import Any, Dict

from pydantic import BaseModel


class Web3Request(BaseModel):
    backend: str
    method: str
    params: Dict[str, Any] = {}
    context: Dict[str, Any] = {}


class Web3Response(BaseModel):
    result: Dict[str, Any]

