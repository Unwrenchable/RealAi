from fastapi import APIRouter
from pathlib import Path
import json

WORLDSTATE_PATH = Path("backend/worldstate/worldstate.json")
EVENTS_PATH = Path("backend/events/player_events.json")

router = APIRouter(prefix="/overseer", tags=["overseer"])

def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

@router.get("/worldstate")
def get_worldstate():
    return load_json(WORLDSTATE_PATH, {})

@router.post("/event")
def push_event(event: dict):
    events = load_json(EVENTS_PATH, [])
    events.append(event)
    save_json(EVENTS_PATH, events)
    return {"status": "queued", "count": len(events)}
