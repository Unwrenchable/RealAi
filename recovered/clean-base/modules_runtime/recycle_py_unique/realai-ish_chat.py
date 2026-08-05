"""Chat routes."""

from fastapi import APIRouter

from apps.api.main import inference_registry
from core.api.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from core.inference.chat_pipeline import run_chat_pipeline

router = APIRouter()


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(req: ChatCompletionRequest):
    chat_backend = inference_registry.get_chat(req.model)
    embed_backend = inference_registry.get_embed("realai-embed-default")
    return run_chat_pipeline(
        user_id=req.user_id or "default-user",
        messages=[message.dict() for message in req.messages],
        chat_backend=chat_backend,
        embed_backend=embed_backend,
    )
