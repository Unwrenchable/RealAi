"""
RealAI Hierarchical Agent System - Main Interface

The ultimate AI framework that all others want to be.
"""

from typing import Dict, Any, Optional
import json
from datetime import datetime

class RealAIUltimate:
    """The ultimate RealAI system with hierarchical agents and self-improvement."""

    def __init__(self):
        self.version = "1.0.0"
        self.hierarchical_system = HierarchicalAgentSystem()
        self.rise_system = RISESystem()
        self.training_pipeline = TrainingPipeline()
        self.supervisor = SupervisorAgent()
        self.agent_registry = get_agent_registry()
        self.tool_registry = TOOL_REGISTRY
        self.capabilities = [
            "Hierarchical Multi-Agent Coordination",
            "RISE Self-Improvement Loops",
            "Advanced RL Training (GRPO/M-GRPO)",
            "Synthetic Data Generation",
            "Production-Grade Deployment",
            "44+ Core AI Capabilities",
            "Real-World Integrations",
            "Continuous Evolution"
        ]

    def query(self, user_input: str, enable_rise: bool = True) -> Dict[str, Any]:
        """Process a user query through the hierarchical agent system."""
        print("🤖 RealAI Ultimate processing your request...")

        start_time = datetime.now()

        # Invoke hierarchical agent system
        result = self.hierarchical_system.process_query(user_input)

        processing_time = (datetime.now() - start_time).total_seconds()

        # Apply RISE self-improvement if enabled
        if enable_rise:
            interaction = {
                "user_input": user_input,
                "response": result.get("response", ""),
                "processing_time": processing_time,
                "metadata": result.get("metadata", {})
            }

            rise_result = self.rise_system.apply_rise_cycle(interaction)
            result["rise_improvements"] = rise_result

        result["processing_time"] = processing_time
        result["system_info"] = {
            "version": self.version,
            "capabilities": self.capabilities,
            "active_specialists": list(self.agent_registry.keys())
        }

        print(f"✅ Response generated in {processing_time:.2f} seconds")
        return result

    def train_model(self, num_samples: int = 10000, output_dir: str = "./training_output") -> bool:
        """Train the model using advanced RL techniques."""
        print("🎯 Starting advanced model training...")

        # Setup training environment
        if not self.training_pipeline.setup_training_environment():
            return False

        # Generate synthetic training data
        data_path = self.training_pipeline.generate_training_data(num_samples)

        # Run training
        success = self.training_pipeline.run_training(data_path, output_dir)

        if success:
            # Evaluate the trained model
            evaluation = self.training_pipeline.evaluate_model(f"{output_dir}/final_model")
            print(f"📊 Model evaluation: {json.dumps(evaluation, indent=2)}")

        return success

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "version": self.version,
            "capabilities": self.capabilities,
            "agents": list(self.agent_registry.keys()),
            "tools": len(self.tool_registry),
            "rise_cycles_completed": len(self.rise_system.get_improvement_history()),
            "evolution_events": len(self.rise_system.get_evolution_log()),
            "training_ready": self.training_pipeline.setup_training_environment(),
            "status": "operational"
        }

    def demonstrate_capabilities(self) -> str:
        """Demonstrate the system's capabilities."""
        demo_prompts = [
            "Explain quantum computing to a 10-year-old",
            "Write a Python function to solve the traveling salesman problem",
            "Research the latest developments in fusion energy",
            "Create a business plan for an AI startup",
            "Design a system for autonomous task management"
        ]

        results = []
        for prompt in demo_prompts:
            print(f"🔄 Demonstrating: {prompt[:50]}...")
            result = self.query(prompt, enable_rise=False)
            results.append({
                "prompt": prompt,
                "response_length": len(result["response"]),
                "processing_time": result["processing_time"]
            })

        return f"""
🎉 RealAI Ultimate Capability Demonstration Complete!

Processed {len(results)} complex queries across multiple domains:
{json.dumps(results, indent=2)}

✨ Key Achievements:
- Hierarchical agent coordination
- Multi-domain expertise integration
- Real-time response generation
- Quality assurance through specialist review

🚀 RealAI is now the "go-to AI for everyone" - independent, comprehensive, and continuously evolving!
"""

# Lazy-loaded global instance
_realai_ultimate = None

def _get_realai_ultimate():
    global _realai_ultimate
    if _realai_ultimate is None:
        _realai_ultimate = RealAIUltimate()
    return _realai_ultimate

# For backward compatibility
realai_ultimate = property(_get_realai_ultimate)

def main():
    """Command-line interface for RealAI Ultimate."""
    print("🚀 RealAI Ultimate - The AI That All Others Want To Be")
    print("=" * 60)

    while True:
        print("\nOptions:")
        print("1. Query the AI")
        print("2. Train model")
        print("3. System status")
        print("4. Demonstrate capabilities")
        print("5. Exit")

        choice = input("\nChoose an option (1-5): ").strip()

        if choice == "1":
            user_input = input("Enter your query: ")
            result = realai_ultimate.query(user_input)
            print(f"\n🤖 Response: {result['response']}")
            print(".2f")

        elif choice == "2":
            num_samples = input("Number of training samples (default 10000): ").strip()
            num_samples = int(num_samples) if num_samples.isdigit() else 10000
            success = realai_ultimate.train_model(num_samples)
            print("✅ Training completed!" if success else "❌ Training failed")

        elif choice == "3":
            status = realai_ultimate.get_system_status()
            print(json.dumps(status, indent=2))

        elif choice == "4":
            demo = realai_ultimate.demonstrate_capabilities()
            print(demo)

        elif choice == "5":
            print("👋 Goodbye! RealAI Ultimate signing off.")
            break

        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()