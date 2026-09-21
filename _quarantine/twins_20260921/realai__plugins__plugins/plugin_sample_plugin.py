"""Sample plugin for RealAI demonstrating the plugin API.

This plugin registers a simple `sample_action` method on the model which can
be invoked by clients. It returns metadata describing the plugin.
"""

def register(model, config=None):
    """Register plugin with the RealAI `model`.

    Args:
        model: RealAI instance
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

    # Attach a friendly method onto the model instance
    setattr(model, "sample_action", sample_action)

    metadata = {
        "name": "sample_plugin",
        "version": "0.1",
        "capabilities": ["sample_action"],
        "methods": ["sample_action"],
    }

    return metadata
