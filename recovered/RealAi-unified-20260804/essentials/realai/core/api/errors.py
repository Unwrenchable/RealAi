"""Core API errors."""


class RealAIAPIError(Exception):
    """Base error for core API modules."""


class ConfigError(RealAIAPIError):
    """Configuration loading or validation error."""


class RegistryError(RealAIAPIError):
    """Model registry loading or validation error."""

