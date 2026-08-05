"""Typed config models for week-1 foundation."""

from dataclasses import dataclass


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class PathsConfig:
    models: str = "models.yaml"
    providers: str = "providers.yaml"

