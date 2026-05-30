"""Scoped credential manager for tool execution."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCredential:
    """Credential issued to one or more tools."""

    alias: str
    scheme: str
    secret: str
    scopes: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[float] = None

    def is_valid_for(self, tool_name: str, requested_scopes: Optional[List[str]] = None) -> bool:
        """Return whether the credential can be used for a tool request."""
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return False
        if self.expires_at is not None and float(self.expires_at) <= time.time():
            return False
        required_scopes = set(requested_scopes or [])
        if required_scopes and not required_scopes.issubset(set(self.scopes)):
            return False
        return True

    def masked_secret(self) -> str:
        """Return a safe preview of the secret."""
        if len(self.secret) <= 4:
            return "*" * len(self.secret)
        return "{0}{1}".format("*" * (len(self.secret) - 4), self.secret[-4:])

    def to_runtime_dict(self) -> Dict[str, Any]:
        """Return the credential payload for tool runtime context."""
        return {
            "alias": self.alias,
            "scheme": self.scheme,
            "secret": self.secret,
            "scopes": list(self.scopes),
            "metadata": dict(self.metadata),
            "expires_at": self.expires_at,
        }

    def to_audit_dict(self) -> Dict[str, Any]:
        """Return a masked credential payload for audit logging."""
        return {
            "alias": self.alias,
            "scheme": self.scheme,
            "secret_preview": self.masked_secret(),
            "scopes": list(self.scopes),
            "metadata": dict(self.metadata),
            "expires_at": self.expires_at,
        }


class ToolCredentialManager:
    """Store and resolve scoped tool credentials."""

    def __init__(self) -> None:
        self._credentials: Dict[str, ToolCredential] = {}

    def register_api_key(
        self,
        alias: str,
        secret: str,
        allowed_tools: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register an API key credential."""
        self._credentials[alias] = ToolCredential(
            alias=alias,
            scheme="api_key",
            secret=str(secret),
            allowed_tools=list(allowed_tools or []),
            scopes=list(scopes or []),
            metadata=dict(metadata or {}),
        )

    def register_oauth_token(
        self,
        alias: str,
        token: str,
        allowed_tools: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register an OAuth-style bearer token."""
        self._credentials[alias] = ToolCredential(
            alias=alias,
            scheme="oauth2",
            secret=str(token),
            allowed_tools=list(allowed_tools or []),
            scopes=list(scopes or []),
            expires_at=expires_at,
            metadata=dict(metadata or {}),
        )

    def resolve(
        self,
        tool_name: str,
        requested_scopes: Optional[List[str]] = None,
    ) -> List[ToolCredential]:
        """Resolve all credentials allowed for a tool request."""
        matches: List[ToolCredential] = []
        for credential in self._credentials.values():
            if credential.is_valid_for(tool_name, requested_scopes=requested_scopes):
                matches.append(credential)
        return matches

    def inject_into_context(
        self,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None,
        requested_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return a copy of context populated with matching credentials."""
        runtime_context = dict(context or {})
        runtime_context["tool_credentials"] = [
            credential.to_runtime_dict()
            for credential in self.resolve(tool_name, requested_scopes=requested_scopes)
        ]
        return runtime_context

    def describe_for_audit(
        self,
        tool_name: str,
        requested_scopes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return masked credential metadata for logging."""
        return [
            credential.to_audit_dict()
            for credential in self.resolve(tool_name, requested_scopes=requested_scopes)
        ]
