"""
Advanced Tool Suite for RealAI Hierarchical Agent

Implements the expert-level tool ecosystem for the ultimate AI framework.
"""

from langchain_core.tools import tool
from realai import RealAIClient
import json
import time
from typing import List

# Initialize RealAI client for tool backing
realai_client = RealAIClient()

@tool
def web_research(query: str, depth: str = "comprehensive") -> str:
    """Advanced web research with multiple sources and analysis."""
    try:
        result = realai_client.web.research(query=query, depth=depth)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Research failed: {e}"

@tool
def code_execution(code: str, language: str = "python") -> str:
    """Execute code with safety and analysis."""
    try:
        result = realai_client.model.execute_code(code=code, language=language)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Code execution failed: {e}"

@tool
def math_solver(problem: str, domain: str = "general") -> str:
    """Solve mathematical and physics problems."""
    try:
        result = realai_client.math.solve(problem=problem, domain=domain)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Math solving failed: {e}"

@tool
def creative_writer(prompt: str, style: str = "narrative") -> str:
    """Generate creative content."""
    try:
        result = realai_client.creative.write(prompt=prompt, style=style)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Creative writing failed: {e}"

@tool
def data_analyzer(data: str, analysis_type: str = "statistical") -> str:
    """Analyze data with advanced methods."""
    try:
        # Parse data if it's JSON string
        parsed_data = json.loads(data) if data.startswith('{') or data.startswith('[') else data
        result = realai_client.data.analyze(data=parsed_data, analysis_type=analysis_type)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Data analysis failed: {e}"

@tool
def image_processor(image_url: str, action: str = "analyze") -> str:
    """Process and analyze images."""
    try:
        if action == "analyze":
            result = realai_client.vision.analyze(image_url=image_url)
        elif action == "edit":
            result = realai_client.image_edit.modify(image_url=image_url, edit_request="enhance quality")
        else:
            result = {"error": f"Unknown action: {action}"}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Image processing failed: {e}"

@tool
def task_automator(task_type: str, details: str) -> str:
    """Automate real-world tasks."""
    try:
        parsed_details = json.loads(details) if details.startswith('{') else {"description": details}
        result = realai_client.tasks.automate(task_type=task_type, task_details=parsed_details)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Task automation failed: {e}"

@tool
def knowledge_synthesizer(topics: str) -> str:
    """Synthesize knowledge across domains."""
    try:
        topic_list = json.loads(topics) if topics.startswith('[') else [topics]
        result = realai_client.synthesis.combine(topics=topic_list)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Knowledge synthesis failed: {e}"

@tool
def self_reflector(interaction_history: str) -> str:
    """Self-reflection and improvement analysis."""
    try:
        history = json.loads(interaction_history) if interaction_history.startswith('[') else []
        result = realai_client.reflection.analyze(interaction_history=history)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Self-reflection failed: {e}"

# Tool registry for easy access
TOOL_REGISTRY = {
    "web_research": web_research,
    "code_execution": code_execution,
    "math_solver": math_solver,
    "creative_writer": creative_writer,
    "data_analyzer": data_analyzer,
    "image_processor": image_processor,
    "task_automator": task_automator,
    "knowledge_synthesizer": knowledge_synthesizer,
    "self_reflector": self_reflector,
}

def get_tools_for_agent(agent_type: str) -> List:
    """Get appropriate tools for different agent types."""
    tool_mappings = {
        "researcher": ["web_research", "data_analyzer", "knowledge_synthesizer"],
        "coder": ["code_execution", "math_solver"],
        "creative": ["creative_writer", "image_processor"],
        "executor": ["task_automator", "code_execution"],
        "critic": ["self_reflector", "data_analyzer"],
        "supervisor": ["web_research", "self_reflector"],  # Limited tools for oversight
    }

    tool_names = tool_mappings.get(agent_type, ["web_research"])
    return [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]