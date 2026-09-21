"""Plugins package for RealAI.

Local plugins placed in this package should expose a `register(model, config)`
callable which receives the `RealAI` instance and an optional config dict and
returns a metadata dict describing the plugin.
"""

__all__ = ["sample_plugin"]
