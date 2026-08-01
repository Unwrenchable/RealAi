"""
Supervisor Agent for RealAI Hierarchical System

The supervisor coordinates specialist agents, manages workflow, and ensures quality.
Implements RISE self-improvement loops and advanced orchestration.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph_supervisor import create_supervisor
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import create_react_agent
from .agents import get_agent_registry
from .tools import TOOL_REGISTRY
from . import get_llm
from typing import TypedDict, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """State for the hierarchical agent system."""
    messages: List[BaseMessage]
    current_agent: Optional[str]
    task_analysis: Optional[Dict[str, Any]]
    specialist_results: Dict[str, Any]
    final_response: Optional[str]
    metadata: Dict[str, Any]
import json
from typing import Dict, Any, List

class SupervisorAgent:
    """Supervisor agent that orchestrates the hierarchical system."""

    def __init__(self):
        self.system_prompt = """You are the Supervisor Agent for RealAI - the ultimate AI framework.

Your role: Orchestrate specialist agents to solve complex problems with maximum quality.

Specialists available:
- Researcher: Deep research, knowledge synthesis, fact verification
- Coder: Software development, algorithms, technical implementation
- Creative: Writing, content creation, artistic expression
- Executor: Task automation, real-world implementation
- Critic: Quality assessment, error detection, improvement

Orchestration Strategy:
1. Analyze the problem and break it into components
2. Assign appropriate specialists to each component
3. Coordinate their work and integrate results
4. Apply self-improvement loops (RISE methodology)
5. Ensure final output meets highest quality standards

RISE Self-Improvement:
- Reflect: Analyze your own performance and identify improvements
- Introspect: Deep self-analysis of decision-making processes
- Self-correct: Fix errors and optimize approaches
- Evolve: Learn from experience and adapt strategies

Always provide comprehensive oversight and quality control."""

        self.agent_registry = get_agent_registry()
        self.tool_registry = TOOL_REGISTRY

        # Create supervisor with limited tools for oversight
        supervisor_tools = [self.tool_registry["web_research"], self.tool_registry["self_reflector"]]

        llm = get_llm()
        self.supervisor = create_react_agent(
            model=llm,
            tools=supervisor_tools,
            prompt=ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("placeholder", "{messages}"),
            ]),
        )

    def analyze_task(self, task_description: str) -> Dict[str, Any]:
        """Analyze a task and determine which specialists to involve."""
        analysis_prompt = f"""Analyze this task and determine the optimal specialist assignments:

Task: {task_description}

Return a JSON object with:
- specialists: array of specialist types needed (researcher, coder, creative, executor, critic)
- strategy: brief description of the approach
- priority_order: order in which specialists should be consulted
- expected_outcomes: what each specialist should deliver

Be strategic and efficient in your assignments."""

        messages = [HumanMessage(content=analysis_prompt)]
        response = self.supervisor.invoke({"messages": messages})

        try:
            # Extract JSON from response
            content = response["messages"][-1].content
            # Find JSON in the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except:
            # Fallback analysis
            return {
                "specialists": ["researcher", "coder", "critic"],
                "strategy": "General problem-solving approach",
                "priority_order": ["researcher", "coder", "critic"],
                "expected_outcomes": {
                    "researcher": "Gather information and research",
                    "coder": "Implement technical solutions",
                    "critic": "Review and improve quality"
                }
            }

    def coordinate_specialists(self, task_analysis: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Coordinate the work of multiple specialists."""
        results = {}
        corrections = []

        for specialist_type in task_analysis["priority_order"]:
            if specialist_type not in self.agent_registry:
                continue

            specialist = self.agent_registry[specialist_type]
            expected_outcome = task_analysis["expected_outcomes"].get(specialist_type, "")

            # Create specialized prompt for this specialist
            specialist_prompt = f"""Task: {user_query}

Your role: {expected_outcome}

Previous work: {json.dumps(results, indent=2)}

Provide your contribution following your expertise as a {specialist_type}."""

            messages = [HumanMessage(content=specialist_prompt)]
            response = specialist.invoke(messages)

            results[specialist_type] = response["messages"][-1].content

            # Self-improvement loop - analyze this specialist's work
            if specialist_type == "critic":
                # Critic provides feedback on all work
                critic_analysis = results.get("critic", "")
                corrections.append({
                    "stage": specialist_type,
                    "analysis": critic_analysis,
                    "timestamp": "current"
                })

        return {
            "results": results,
            "corrections": corrections,
            "final_output": self.synthesize_results(results, task_analysis)
        }

    def synthesize_results(self, results: Dict[str, Any], task_analysis: Dict[str, Any]) -> str:
        """Synthesize all specialist contributions into final output."""
        synthesis_prompt = f"""Synthesize the following specialist contributions into a comprehensive final answer:

Task Analysis: {json.dumps(task_analysis, indent=2)}

Specialist Results:
{json.dumps(results, indent=2)}

Create a cohesive, high-quality response that integrates all contributions.
Apply any corrections or improvements identified.
Ensure the final answer is complete, accurate, and well-structured."""

        messages = [HumanMessage(content=synthesis_prompt)]
        response = self.supervisor.invoke({"messages": messages})

        return response["messages"][-1].content

    def apply_rise_self_improvement(self, interaction_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply RISE methodology for self-improvement."""
        rise_prompt = f"""Apply RISE self-improvement methodology to analyze this interaction history:

History: {json.dumps(interaction_history, indent=2)}

RISE Process:
1. Reflect: What worked well and what didn't?
2. Introspect: Why did certain approaches succeed or fail?
3. Self-correct: What specific changes should be made?
4. Evolve: How can future performance be improved?

Return a JSON object with improvement recommendations."""

        messages = [HumanMessage(content=rise_prompt)]
        response = self.supervisor.invoke({"messages": messages})

        try:
            content = response["messages"][-1].content
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except:
            return {"improvements": "Self-improvement analysis completed"}