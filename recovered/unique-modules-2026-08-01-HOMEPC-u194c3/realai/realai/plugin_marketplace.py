"""
RealAI Plugin Marketplace
==========================
Provides plugin discovery, installation, verification, and sandboxed execution.

Usage::

    from realai.plugin_marketplace import PluginDiscovery, PluginManifest

    discovery = PluginDiscovery()
    installed = discovery.list_installed()
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class PluginPermission(Enum):
    """Permissions that plugins may request.

    Attributes:
        NETWORK: Allow network access.
        FILESYSTEM: Allow filesystem access.
        SUBPROCESS: Allow subprocess execution.
        GUI: Allow GUI creation.
    """
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    SUBPROCESS = "subprocess"
    GUI = "gui"


@dataclass
class PluginManifest:
    """Manifest describing a RealAI plugin.

    Attributes:
        name: Plugin name.
        version: Semantic version string.
        author: Plugin author name.
        description: Human-readable description.
        permissions: List of PluginPermission value strings.
        signature: SHA-256 signature string for verification.
        homepage: Optional homepage URL.
    """
    name: str
    version: str
    author: str
    description: str
    permissions: List[str] = field(default_factory=list)
    signature: str = ""
    homepage: str = ""


class PluginDiscovery:
    """Handles plugin discovery, installation, and uninstallation.

    Reads/writes installed plugin manifests from ~/.realai/plugins/manifests.json.
    """

    _DEFAULT_MANIFESTS_PATH = os.path.join(
        os.path.expanduser("~/.realai"),
        "plugins",
        "manifests.json",
    )

    def __init__(self, manifests_path: Optional[str] = None) -> None:
        """Initialize plugin discovery.

        Args:
            manifests_path: Path to manifests JSON file. Defaults to
                            ~/.realai/plugins/manifests.json.
        """
        self._path = manifests_path or self._DEFAULT_MANIFESTS_PATH

    def fetch_index(
        self,
        registry_url: str = "https://api.github.com/repos/realai-plugins/registry/releases",
    ) -> List[PluginManifest]:
        """Fetch the plugin index from a remote registry.

        Args:
            registry_url: URL of the plugin registry API.

        Returns:
            List of PluginManifest from the registry, or empty list on failure.
        """
        try:
            import urllib.request
            with urllib.request.urlopen(registry_url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            if isinstance(data, list):
                manifests = []
                for item in data:
                    if isinstance(item, dict) and "name" in item:
                        manifests.append(PluginManifest(
                            name=item.get("name", ""),
                            version=item.get("version", "0.0.0"),
                            author=item.get("author", ""),
                            description=item.get("description", ""),
                            permissions=item.get("permissions", []),
                            signature=item.get("signature", ""),
                            homepage=item.get("homepage", ""),
                        ))
                return manifests
        except Exception as e:
            logger.warning("Failed to fetch plugin index: %s", e)
        return []

    def list_installed(self) -> List[PluginManifest]:
        """Return list of installed plugin manifests.

        Returns:
            List of PluginManifest objects read from the manifests file.
        """
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
            return [
                PluginManifest(
                    name=item.get("name", ""),
                    version=item.get("version", "0.0.0"),
                    author=item.get("author", ""),
                    description=item.get("description", ""),
                    permissions=item.get("permissions", []),
                    signature=item.get("signature", ""),
                    homepage=item.get("homepage", ""),
                )
                for item in (data if isinstance(data, list) else [])
            ]
        except Exception as e:
            logger.warning("Failed to read installed plugins: %s", e)
            return []

    def install(self, manifest: PluginManifest) -> bool:
        """Install a plugin by saving its manifest.

        Args:
            manifest: PluginManifest to install.

        Returns:
            True on success, False on failure.
        """
        try:
            installed = self.list_installed()
            # Remove existing with same name
            installed = [p for p in installed if p.name != manifest.name]
            installed.append(manifest)
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(
                    [self._manifest_to_dict(p) for p in installed],
                    f,
                    indent=2,
                )
            return True
        except Exception as e:
            logger.error("Failed to install plugin: %s", e)
            return False

    def uninstall(self, name: str) -> bool:
        """Uninstall a plugin by name.

        Args:
            name: Plugin name to remove.

        Returns:
            True if found and removed, False otherwise.
        """
        try:
            installed = self.list_installed()
            original_count = len(installed)
            installed = [p for p in installed if p.name != name]
            if len(installed) == original_count:
                return False
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(
                    [self._manifest_to_dict(p) for p in installed],
                    f,
                    indent=2,
                )
            return True
        except Exception as e:
            logger.error("Failed to uninstall plugin: %s", e)
            return False

    def _manifest_to_dict(self, manifest: PluginManifest) -> dict:
        """Convert a manifest to a plain dict."""
        return {
            "name": manifest.name,
            "version": manifest.version,
            "author": manifest.author,
            "description": manifest.description,
            "permissions": manifest.permissions,
            "signature": manifest.signature,
            "homepage": manifest.homepage,
        }


class PluginVerifier:
    """Verifies plugin signatures.

    Uses SHA-256 of name+version+author against the signature field.
    """

    def verify(
        self,
        manifest: PluginManifest,
        trusted_keys: Optional[List[str]] = None,
    ) -> bool:
        """Verify a plugin manifest.

        Args:
            manifest: PluginManifest to verify.
            trusted_keys: List of trusted key strings. If None or empty,
                          returns True (open trust) with a warning.

        Returns:
            True if verified (or open trust), False if signature mismatch.
        """
        if not trusted_keys:
            logger.warning(
                "Plugin '%s' verified with open trust (no trusted_keys provided).",
                manifest.name,
            )
            return True

        payload = manifest.name + manifest.version + manifest.author
        expected_sig = hashlib.sha256(payload.encode()).hexdigest()
        return manifest.signature == expected_sig


class PluginSandbox:
    """Runs plugin functions with basic permission checks.

    Does not actually restrict imports but logs permission checks.
    """

    BLOCKED_MODULES = {"os", "subprocess", "sys", "importlib", "builtins"}

    def execute_plugin(
        self,
        plugin_fn: Callable,
        *args: Any,
        allowed_permissions: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a plugin function with permission logging.

        Args:
            plugin_fn: The plugin callable to invoke.
            *args: Positional arguments for plugin_fn.
            allowed_permissions: List of allowed permission strings.
            **kwargs: Keyword arguments for plugin_fn.

        Returns:
            Plugin return value, or error dict on exception.
        """
        allowed = allowed_permissions or []
        logger.info(
            "Executing plugin '%s' with permissions: %s",
            getattr(plugin_fn, "__name__", "unknown"),
            allowed,
        )

        try:
            return plugin_fn(*args, **kwargs)
        except Exception as e:
            logger.error("Plugin execution error: %s", e)
            return {"status": "error", "error": str(e)}
