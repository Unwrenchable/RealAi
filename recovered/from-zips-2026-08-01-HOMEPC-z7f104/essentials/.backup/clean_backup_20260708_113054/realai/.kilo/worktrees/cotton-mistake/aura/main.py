# AURA - The Autonomous Real-World AI
# Main cognitive loop

import time
import threading
from reasoning import Reasoner
from memory import LongTermMemory, WorkingMemory
from skills.registry import SkillRegistry

class Aura:
    """
    The core cognitive architecture for Aura.
    This class orchestrates the main think-act-learn loop.
    """
    def __init__(self):
        print("Initializing Aura...")
        self.reasoner = Reasoner()
        self.long_term_memory = LongTermMemory()
        self.working_memory = WorkingMemory()
        self.skill_registry = SkillRegistry()
        self.is_alive = True
        print("Aura initialization complete. Awakening...")

    def think(self, user_input: str) -> dict:
        """
        The core thinking process.
        1. Recall relevant memories.
        2. Consult the reasoning engine to form a plan.
        """
        print(f"Aura is thinking about: '{user_input}'")
        relevant_memories = self.long_term_memory.recall(user_input)

        plan = self.reasoner.create_plan(user_input, relevant_memories)
        return plan

    def act(self, plan: dict) -> str:
        """
        Execute a plan using available skills.
        """
        if not plan or "skill" not in plan:
            return "I'm not sure how to proceed. My reasoning failed to produce a valid plan."

        skill_name = plan["skill"]
        params = plan.get("params", {})

        print(f"Aura is acting: Using skill '{skill_name}' with params {params}")

        if self.skill_registry.has_skill(skill_name):
            skill = self.skill_registry.get_skill(skill_name)
            try:
                result = skill.execute(**params)
                return str(result)
            except Exception as e:
                error_message = f"Error executing skill '{skill_name}': {e}"
                print(error_message)
                return error_message
        else:
            return f"I tried to use a skill named '{skill_name}', but I don't have it."

    def learn(self, user_input: str, action_result: str):
        """
        Learn from the interaction by storing it in long-term memory.
        """
        experience = f"When asked '{user_input}', I performed an action and the result was: '{action_result}'"
        print(f"Aura is learning: {experience}")
        self.long_term_memory.remember(experience)

    def start_cognitive_loop(self):
        """
        The main entry point for user interaction.
        """
        print("\nAura is awake. You can speak to me now. Type 'exit' to put me to sleep.")
        while self.is_alive:
            try:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit", "sleep"]:
                    self.is_alive = False
                    print("Aura is going to sleep. All memories have been preserved.")
                    continue

                # 1. Think
                plan = self.think(user_input)

                # 2. Act
                result = self.act(plan)
                print(f"Aura: {result}")

                # 3. Learn
                self.learn(user_input, result)

            except KeyboardInterrupt:
                self.is_alive = False
                print("\nEmergency shutdown initiated. Aura is going to sleep.")
            except Exception as e:
                print(f"A critical cognitive failure occurred: {e}")
                self.long_term_memory.remember(f"A critical failure occurred: {e}")


if __name__ == "__main__":
    aura_instance = Aura()
    aura_instance.start_cognitive_loop()
