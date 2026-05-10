"""Task route for multi-agent execution."""

from fastapi import APIRouter

from apps.api.state import inference_registry, tool_registry
from core.agents.critic import CriticAgent
from core.agents.executor import TaskExecutor
from core.agents.planner import PlannerAgent
from core.agents.synthesizer import SynthesizerAgent
from core.agents.worker import WorkerAgent
from core.api.schemas.tasks import TaskRequest, TaskResponse

router = APIRouter()


@router.post("/v1/tasks", response_model=TaskResponse)
def run_task(req: TaskRequest):
    planner = PlannerAgent(inference_registry)
    worker = WorkerAgent(inference_registry, tool_registry)
    critic = CriticAgent(inference_registry)
    synthesizer = SynthesizerAgent(inference_registry)
    executor = TaskExecutor(planner, worker, critic, synthesizer)
    result = executor.run(req.messages, {"model": req.model, **dict(req.context or {})})
    return {"result": result}

