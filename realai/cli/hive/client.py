"""HTTP client for Hive CLI — extends SDK with orchestrator hive routes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from realai.sdk.python.realai_client import RealAIClient, _default_api_url


class HiveClient(RealAIClient):
    """Orchestrator-facing client used by the Hive CLI."""

    def __init__(self, api_url: Optional[str] = None, timeout: float = 60.0):
        super().__init__(api_url=api_url or _default_api_url(), timeout=timeout)

    def _request_raw(self, method: str, path: str, payload: Any = None, timeout: Optional[float] = None):
        url = "{0}{1}".format(self.api_url.rstrip("/"), path)
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                timeout=timeout if timeout is not None else self.timeout,
            )
        except requests.RequestException as e:
            raise ConnectionError("orchestrator unreachable ({0}): {1}".format(url, e)) from e
        if response.status_code >= 400:
            body = response.text[:500]
            raise RuntimeError("HTTP {0} {1}: {2}".format(response.status_code, path, body))
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    # Override base to use friendlier errors
    def _request(self, method, path, payload=None):
        return self._request_raw(method, path, payload)

    def health(self) -> Dict[str, Any]:
        return self._request_raw("GET", "/health", timeout=5.0) or {}

    def capabilities(self) -> Dict[str, Any]:
        return self._request_raw("GET", "/v1/capabilities", timeout=15.0) or {}

    def tools(self) -> Dict[str, Any]:
        return self._request_raw("GET", "/v1/tools", timeout=15.0) or {}

    def tool_execute(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request_raw(
            "POST",
            "/v1/tools/execute",
            {"name": name, "arguments": arguments or {}},
            timeout=180.0,
        ) or {}

    def multi_agent(
        self,
        task: str,
        *,
        mode: str = "pipeline",
        max_tokens: int = 384,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        return self._request_raw(
            "POST",
            "/v1/multi-agent/run",
            {
                "task": task,
                "mode": mode,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=300.0,
        ) or {}

    def self_heal_status(self) -> Dict[str, Any]:
        return self._request_raw("GET", "/v1/self-heal/status", timeout=20.0) or {}

    def self_heal_post(self, action: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request_raw(
            "POST",
            "/v1/self-heal/{0}".format(action.lstrip("/")),
            body or {},
            timeout=300.0,
        ) or {}

    def lora(self) -> Dict[str, Any]:
        return self._request_raw("GET", "/v1/lora", timeout=15.0) or {}

    def recovery(self) -> Dict[str, Any]:
        return self._request_raw("GET", "/v1/recovery", timeout=15.0) or {}

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str = "realai-default-coder",
        max_tokens: int = 512,
        temperature: float = 0.3,
        agent_id: Optional[str] = None,
        multi_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if agent_id:
            payload["agent_id"] = agent_id
        if multi_agent:
            payload["multi_agent"] = multi_agent
        return self._request_raw("POST", "/v1/chat/completions", payload, timeout=300.0) or {}
