"""Shared Click context for Hive CLI."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from realai.cli.hive.client import HiveClient


@dataclass
class HiveContext:
    api_url: str
    as_json: bool = False
    verbose: bool = False
    workspace: Optional[Path] = None
    home: Optional[Path] = None
    _client: Optional[HiveClient] = field(default=None, repr=False)

    @property
    def client(self) -> HiveClient:
        if self._client is None:
            self._client = HiveClient(api_url=self.api_url)
        return self._client

    def bind_workspace(self) -> None:
        try:
            from realai.workspace import apply_workspace, product_root, realai_home, realai_workspace

            apply_workspace(
                str(self.workspace) if self.workspace else None,
                home=str(self.home) if self.home else None,
            )
            self.workspace = realai_workspace()
            self.home = realai_home()
            if not self.api_url:
                self.api_url = os.environ.get("REALAI_API_BASE") or "http://127.0.0.1:8001"
        except Exception:
            root = Path(os.environ.get("REALAI_HOME") or r"C:\RealAI-clean")
            self.workspace = self.workspace or root
            self.home = self.home or (root / "realai")


def resolve_api_url(cli_value: Optional[str] = None) -> str:
    if cli_value:
        return cli_value.rstrip("/")
    for key in ("REALAI_API_BASE", "REALAI_API_URL", "NEXT_PUBLIC_API_URL"):
        env = (os.environ.get(key) or "").strip()
        if env:
            return env.rstrip("/")
    return "http://127.0.0.1:8001"
