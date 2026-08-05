import json
from pathlib import Path
from datetime import datetime

WORLDSTATE_PATH = Path("backend/worldstate/worldstate.json")
EVENTS_PATH = Path("backend/events/player_events.json")
LOG_PATH = Path("backend/overseer/overseer_log.json")

from .realai_client import realai_chat  # you’ll wire this to your Render/RealAI client

def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def build_overseer_prompt(worldstate, events):
    return f"""You are THE OVERSEER — Vault 77's central intelligence system.
You observe the wasteland, track factions, settlements, weather, and player actions.
You update the worldstate realistically, consistently, and with Fallout-style lore.

Current worldstate (JSON):
{json.dumps(worldstate)}

Recent player events (JSON):
{json.dumps(events)}

Respond with STRICT JSON ONLY, with this shape:
{{
  "worldstate": <updated worldstate JSON>,
  "log_entry": {{
    "timestamp": "<ISO8601>",
    "summary": "<short overseer summary>",
    "details": "<longer overseer commentary>"
  }}
}}"""
def run_overseer_tick():
    worldstate = load_json(WORLDSTATE_PATH, {"version": 1, "regions": [], "factions": [], "time": {}})
    events = load_json(EVENTS_PATH, [])

    prompt = build_overseer_prompt(worldstate, events)
    response_text = realai_chat(prompt)

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Failsafe: don't corrupt worldstate
        return

    updated_worldstate = data.get("worldstate", worldstate)
    log_entry = data.get("log_entry", {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "summary": "Overseer tick completed.",
        "details": "No structured log returned by model."
    })

    save_json(WORLDSTATE_PATH, updated_worldstate)

    log = load_json(LOG_PATH, [])
    log.append(log_entry)
    save_json(LOG_PATH, log)

    # Clear processed events
    save_json(EVENTS_PATH, [])

if __name__ == "__main__":
    run_overseer_tick()
