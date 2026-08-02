"""Plugins package for RealAI.

Local plugins placed in this package should expose a `register(model, config)`
callable which receives the `RealAI` instance and an optional config dict and
returns a metadata dict describing the plugin.
"""


def list_plugins():
    return [
        {
            "name": "sample_plugin",
            "module": "plugins.sample_plugin",
            "description": "Sample plugin demonstrating registration and execution",
        },
        {
            "name": "workspace_info_plugin",
            "module": "plugins.workspace_info_plugin",
            "description": "Inspect a workspace path and return basic metadata",
        },
    ]


__all__ = ["sample_plugin", "workspace_info_plugin", "list_plugins"]
