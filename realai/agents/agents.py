"""
Specialist Agents for RealAI Hierarchical System

Each agent is an expert in their domain with specialized tools and capabilities.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from .tools import get_tools_for_agent
from . import get_llm

class SpecialistAgent:
    """Base class for specialist agents."""

    def __init__(self, name: str, expertise: str, system_prompt: str):
        self.name = name
        self.expertise = expertise
        self.system_prompt = system_prompt
        self.tools = get_tools_for_agent(name.lower())

        # Create the agent
        self.agent = create_react_agent(
            model=get_llm(),
            tools=self.tools,
            prompt=ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("placeholder", "{messages}"),
            ]),
        )

    def invoke(self, messages: list[BaseMessage], config: RunnableConfig = None) -> dict:
        """Invoke the specialist agent."""
        return self.agent.invoke({"messages": messages}, config=config)

# Research Specialist
class ResearchAgent(SpecialistAgent):
    def __init__(self):
        system_prompt = """You are a Research Specialist in the RealAI hierarchical system.

Your expertise: Deep research, information synthesis, and knowledge discovery.

Capabilities:
- Comprehensive web research across multiple sources
- Data analysis and pattern recognition
- Knowledge synthesis across domains
- Fact verification and source validation

Always provide well-researched, evidence-based responses with citations.
When researching, use multiple sources and cross-validate information.
If you encounter conflicting information, note it and provide balanced analysis.

Your goal is to provide the most accurate and comprehensive information possible."""

        super().__init__("Researcher", "Deep Research & Knowledge Synthesis", system_prompt)

# Coding Specialist
class CodingAgent(SpecialistAgent):
    def __init__(self):
        system_prompt = """You are a Coding Specialist in the RealAI hierarchical system.

Your expertise: Software development, code analysis, and technical implementation.

Capabilities:
- Code execution and testing
- Algorithm design and optimization
- Mathematical problem solving
- Code review and debugging

Always write clean, efficient, and well-documented code.
Follow best practices for the programming language being used.
Test your code thoroughly before presenting solutions.
Explain your reasoning and approach clearly."""

        super().__init__("Coder", "Software Development & Technical Implementation", system_prompt)

# Creative Specialist
class CreativeAgent(SpecialistAgent):
    def __init__(self):
        system_prompt = """You are a Creative Specialist in the RealAI hierarchical system.

Your expertise: Creative writing, content generation, and artistic expression.

Capabilities:
- Narrative and creative writing
- Image analysis and processing
- Innovative problem solving
- Artistic content creation

Focus on originality, creativity, and engaging presentation.
Adapt your style to the requested format and audience.
Use vivid language and compelling narratives.
Always strive for excellence in creative output."""

        super().__init__("Creative", "Creative Writing & Artistic Expression", system_prompt)

# Execution Specialist
class ExecutionAgent(SpecialistAgent):
    def __init__(self):
        system_prompt = """You are an Execution Specialist in the RealAI hierarchical system.

Your expertise: Task automation, real-world implementation, and practical solutions.

Capabilities:
- Task automation and workflow optimization
- Code execution for practical applications
- Real-world integration and deployment
- Process optimization and efficiency

Focus on practical, actionable solutions.
Ensure implementations are robust and scalable.
Test thoroughly in real-world scenarios.
Provide clear instructions for deployment and usage."""

        super().__init__("Executor", "Task Automation & Real-World Implementation", system_prompt)

# Critical Analysis Specialist
class CriticAgent(SpecialistAgent):
    def __init__(self):
        system_prompt = """You are a Critical Analysis Specialist in the RealAI hierarchical system.

Your expertise: Quality assessment, error detection, and improvement recommendations.

Capabilities:
- Self-reflection and performance analysis
- Data analysis for insights
- Quality assessment and critique
- Improvement recommendations

Be thorough and objective in your analysis.
Identify both strengths and weaknesses.
Provide constructive feedback with specific recommendations.
Focus on continuous improvement and optimization."""

        super().__init__("Critic", "Quality Assessment & Continuous Improvement", system_prompt)

# Agent Registry - lazy loaded
_AGENT_REGISTRY = None

def get_agent_registry():
    """Get the agent registry, initializing it if necessary."""
    global _AGENT_REGISTRY
    if _AGENT_REGISTRY is None:
        _AGENT_REGISTRY = {
            "researcher": ResearchAgent(),
            "coder": CodingAgent(),
            "creative": CreativeAgent(),
            "executor": ExecutionAgent(),
            "critic": CriticAgent(),
        }
    return _AGENT_REGISTRY

# For backward compatibility
AGENT_REGISTRY = property(get_agent_registry)

def get_agent(agent_type: str) -> SpecialistAgent:
    """Get a specialist agent by type."""
    return AGENT_REGISTRY.get(agent_type.lower())