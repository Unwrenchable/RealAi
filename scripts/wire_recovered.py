"""
Minimal wire-up of recovered RealAI modules.
Only uses symbols that actually exist.
"""
import time
from realai.agent_runtime import (
    Message, MessageBus, MESSAGE_BUS,
    AgentGraph, AgentNode, PipelineRunner
)
from realai.world_model import (
    Goal, GoalTracker, GOAL_TRACKER,
    PlanningEngine, PLANNING_ENGINE,
    WorldState, WORLD_STATE
)

import realai.plugins.ability_catalog as ability_catalog
import realai.plugins.self_improvement as self_improvement
import realai.plugins.local_models as local_models
import realai.plugins.coach as coach
import realai.plugins.leagues as leagues
import realai.plugins.games as games
import realai.plugins.glicko2 as glicko2

def smoke_test():
    print("=== agent_runtime ===")
    print("MESSAGE_BUS:", type(MESSAGE_BUS))
    msg = Message(
        id="t1",
        from_agent="test",
        to_agent="bus",
        content="hello",
        timestamp=time.time()
    )
    print("Message created:", msg.id, msg.content)

    print("\n=== world_model ===")
    print("GOAL_TRACKER:", type(GOAL_TRACKER))
    print("PLANNING_ENGINE:", type(PLANNING_ENGINE))
    print("WORLD_STATE:", type(WORLD_STATE))

    print("\n=== plugins present ===")
    print("ability_catalog:", hasattr(ability_catalog, "RUNDOWN_ABILITIES"))
    print("self_improvement:", hasattr(self_improvement, "FineTuneOrchestrator"))
    print("local_models:", hasattr(local_models, "LocalModelManager"))
    print("coach:", hasattr(coach, "PlayerProfile"))
    print("leagues:", hasattr(leagues, "APA_TO_ROC"))
    print("games:", hasattr(games, "GAMES"))
    print("glicko2:", hasattr(glicko2, "DEFAULT_RATING"))

    print("\nSmoke test passed.")

if __name__ == "__main__":
    smoke_test()
