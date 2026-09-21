"""Sample plugin for RealAI demonstrating the plugin API.

This plugin registers a simple `sample_action` method on the model which can
be invoked by clients. It returns metadata describing the plugin.
"""


def register(model, config=None):
    """Register plugin with the RealAI `model`.

    Args:
        model: RealAI instance (optional — None is allowed for catalog-only register_all)
        config: Optional configuration dict

    Returns:
        dict: metadata describing the plugin
    """

    def sample_action(data=None):
        return {
            "plugin": "sample_plugin",
            "ok": True,
            "received": data,
        }

    # Attach only when a real model instance is provided
    if model is not None:
        setattr(model, "sample_action", sample_action)

    return {
        "name": "sample_plugin",
        "version": "0.1",
        "capabilities": ["sample_action"],
        "methods": ["sample_action"],
        "ok": True,
        "registered": model is not None,
    }
