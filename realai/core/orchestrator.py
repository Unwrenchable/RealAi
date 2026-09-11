import time
from pathlib import Path

from core.provider import SelfHealingProvider
from core.memory import MemoryEngine
from core.world_model import WorldModel
from core.plugins import PluginSystem

class Orchestrator:
    def __init__(self, root: Path):
        self.provider = SelfHealingProvider(root)
        self.memory = MemoryEngine(root / "memory_store.json")
        self.world = WorldModel(root / "world_model.json")
        self.plugins = PluginSystem(root / "plugins")

    def evolve_world(self):
        snap = self.world.snapshot()
        out = self.provider.infer(f"Improve world-model: {snap}")
        self.world.update("evolution", out)

    def reinforce_memory(self):
        recent = self.memory.fetch_recent("errors")
        out = self.provider.infer(f"Reinforce memory based on {recent}")
        self.memory.store_value("reinforcement", out)

    def auto_train(self):
        trainer = self.plugins.get("unsloth_trainer")
        if trainer:
            print("[AutoTrainer] would run:", trainer)
            # real: subprocess.run([...])

    def run(self):
        while True:
            self.evolve_world()
            self.reinforce_memory()
            self.auto_train()
            time.sleep(60)
