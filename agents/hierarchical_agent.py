"""
RealAI Hierarchical Agent System - Main Orchestrator

This is the core of the "go-to AI for everyone" - implementing frontier 2026 architecture.
"""

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from .supervisor import SupervisorAgent, AgentState
from .agents import get_agent_registry
from .rise_system import RISESystem
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Constants
MAX_STEPS = 5

class HierarchicalAgentSystem:
    """The complete hierarchical agent system."""

    def __init__(self):
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the hierarchical agent workflow graph."""

        def supervisor_node(state: AgentState) -> Dict[str, Any]:
            """Supervisor analyzes and coordinates."""
            user_query = state["messages"][-1].content

            # Analyze the task
            task_analysis = supervisor.analyze_task(user_query)

            # Coordinate specialists
            coordination_result = supervisor.coordinate_specialists(task_analysis, user_query)

            # Apply RISE self-improvement
            if len(state["self_corrections"]) > 0:
                improvements = supervisor.apply_rise_self_improvement(state["self_corrections"])
                coordination_result["improvements"] = improvements

            # Update state
            final_answer = coordination_result["final_output"]

            return {
                "messages": [AIMessage(content=final_answer)],
                "next_agent": "complete",
                "completed_tasks": ["task_analysis", "specialist_coordination", "result_synthesis"],
                "self_corrections": coordination_result.get("corrections", []),
                "metadata": {
                    "task_analysis": task_analysis,
                    "coordination_result": coordination_result,
                    "step_count": len(state["completed_tasks"]) + 1
                }
            }

        def quality_check_node(state: AgentState) -> Dict[str, Any]:
            """Final quality check and self-improvement."""
            current_output = state["messages"][-1].content

            # Apply final RISE analysis
            interaction_history = [
                {"role": "user", "content": state["messages"][0].content},
                {"role": "assistant", "content": current_output}
            ] + [{"correction": corr} for corr in state["self_corrections"]]

            improvements = supervisor.apply_rise_self_improvement(interaction_history)

            # Enhance final answer based on improvements
            enhanced_prompt = f"""Review and enhance this response based on self-improvement analysis:

Original Response: {current_output}

Self-Improvement Analysis: {json.dumps(improvements, indent=2)}

Provide an enhanced final answer that incorporates the improvements."""

            messages = [HumanMessage(content=enhanced_prompt)]
            enhanced_response = supervisor.supervisor.invoke({"messages": messages})

            return {
                "messages": [AIMessage(content=enhanced_response["messages"][-1].content)],
                "next_agent": "complete",
                "completed_tasks": state["completed_tasks"] + ["quality_enhancement"],
                "self_corrections": state["self_corrections"] + [improvements],
                "metadata": state["metadata"]
            }

        # Build the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("quality_check", quality_check_node)

        # Add edges
        workflow.add_edge(START, "supervisor")
        workflow.add_edge("supervisor", "quality_check")
        workflow.add_edge("quality_check", END)

        # Add conditional edges for complex tasks
        def should_continue(state: AgentState) -> str:
            """Determine if we need additional processing."""
            step_count = state["metadata"].get("step_count", 0)
            has_corrections = len(state["self_corrections"]) > 0

            if step_count < MAX_STEPS and has_corrections:
                return "supervisor"  # Re-process with corrections
            else:
                return "quality_check"  # Final quality check

        workflow.add_conditional_edges(
            "supervisor",
            should_continue,
            {
                "supervisor": "supervisor",
                "quality_check": "quality_check"
            }
        )

        return workflow.compile(checkpointer=self.memory)

    def invoke(self, user_query: str, thread_id: str = "default") -> Dict[str, Any]:
        """Invoke the hierarchical agent system."""
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "next_agent": "supervisor",
            "completed_tasks": [],
            "self_corrections": [],
            "metadata": {"start_time": "now", "thread_id": thread_id}
        }

        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(initial_state, config=config)

        return {
            "response": result["messages"][-1].content,
            "metadata": result["metadata"],
            "completed_tasks": result["completed_tasks"],
            "self_corrections": result["self_corrections"]
        }

    def stream(self, user_query: str, thread_id: str = "default"):
        """Stream the hierarchical agent processing."""
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "next_agent": "supervisor",
            "completed_tasks": [],
            "self_corrections": [],
            "metadata": {"start_time": "now", "thread_id": thread_id}
        }

        config = {"configurable": {"thread_id": thread_id}}
        for chunk in self.graph.stream(initial_state, config=config):
            yield chunk

# Global instance
hierarchical_agent = HierarchicalAgentSystem()