"""Validated environment settings shared by the deployed API entrypoints."""

from pathlib import Path
from typing import Dict, List, Optional
import os

from pydantic import BaseModel, Field, ValidationError


_ROOT = Path(__file__).resolve().parents[1]


def _read_env_file(path: Path) -> Dict[str, str]:
    values = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


class ServerSettings(BaseModel):
    """Validated runtime settings for the HTTP and FastAPI servers."""

    OPENAI_API_KEY: Optional[str] = Field(default=None)
    REALAI_API_KEY: Optional[str] = Field(default=None)
    REALAI_API_BASE: Optional[str] = Field(default=None)
    REALAI_API_URL: Optional[str] = Field(default=None)
    NEXT_PUBLIC_API_URL: Optional[str] = Field(default=None)
    REALAI_MODEL: str = Field(default="realai-1.0")
    ENV: str = Field(default="production")
    CORS_ALLOWED_ORIGINS: str = Field(default="*")
    # Local default matches repo root `.env` (PORT=8001). Hosted platforms override via PORT.
    PORT: int = Field(default=8001)

    class Config:
        extra = "ignore"

    def cors_allowed_origins(self) -> List[str]:
        """Return configured CORS origins as a normalized list."""
        raw = (self.CORS_ALLOWED_ORIGINS or "*").strip()
        if not raw or raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    def api_base_url(self) -> str:
        """Single resolved API base used by clients, UIs, and SDK helpers."""
        for candidate in (self.REALAI_API_BASE, self.REALAI_API_URL, self.NEXT_PUBLIC_API_URL):
            if candidate and str(candidate).strip():
                return str(candidate).strip().rstrip("/")
        return "http://127.0.0.1:{0}".format(self.PORT)

    def public_dict(self) -> Dict[str, object]:
        """Return a sanitized settings snapshot for logs."""
        return {
            "ENV": self.ENV,
            "REALAI_MODEL": self.REALAI_MODEL,
            "PORT": self.PORT,
            "REALAI_API_BASE": self.api_base_url(),
            "CORS_ALLOWED_ORIGINS": self.cors_allowed_origins(),
            "OPENAI_API_KEY_SET": bool(self.OPENAI_API_KEY),
        }


def load_server_settings() -> ServerSettings:
    """Load validated settings from `.env` and the process environment."""
    payload = _read_env_file(_ROOT / ".env")
    payload.update(os.environ)
    try:
        return ServerSettings(**payload)
    except ValidationError as exc:
        raise RuntimeError("Invalid server environment configuration: {0}".format(exc))


settings = load_server_settings()


def default_api_base() -> str:
    """Env-driven API base shared by CLI/SDK/tools (same resolution as the server)."""
    return settings.api_base_url()