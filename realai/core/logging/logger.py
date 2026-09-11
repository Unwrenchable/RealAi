"""JSON structured logger."""

import json
import time
from typing import Any, Dict


def log(event_type: str, data: Dict[str, Any]):
    entry = {"timestamp": time.time(), "event": str(event_type), "data": data if isinstance(data, dict) else {}}
    try:
        print(json.dumps(entry, default=str))
    except Exception:
        print(json.dumps({"timestamp": time.time(), "event": "error.exception", "data": {"event_type": event_type}}))

