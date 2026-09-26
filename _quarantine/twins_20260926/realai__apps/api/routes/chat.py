"""Chat routes — RealAI Bot local-only completions."""

from fastapi import APIRouter, HTTPException

from apps.api.state import inference_registry
from core.api.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from core.inference.chat_pipeline import run_chat_pipeline

router = APIRouter()


def _resolve_chat_backend(model: str):
    try:
        from realai.bot.boot import coerce_local_model, local_only_enabled

        if local_only_enabled():
            model = coerce_local_model(model)
    except Exception:
        pass
    try:
        return inference_registry.get_chat(model), model
    except Exception:
        # Fail closed for RealAI Bot — never hop to cloud.
        raise HTTPException(status_code=503, detail="local model offline")


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(req: ChatCompletionRequest):
    try:
        from realai.bot.boot import ensure_bot_registered

        ensure_bot_registered()
    except Exception:
        pass

    chat_backend, model = _resolve_chat_backend(getattr(req, "model", None) or "realai-default")
    if chat_backend is None:
        raise HTTPException(status_code=503, detail="local model offline")

    try:
        embed_backend = inference_registry.get_embed("realai-embed-default")
    except Exception:
        embed_backend = None
        try:
            # Some registries expose a default embed under alternate ids.
            for embed_id in ("realai-embed", "realai-default"):
                try:
                    embed_backend = inference_registry.get_embed(embed_id)
                    break
                except Exception:
                    continue
        except Exception:
            embed_backend = None
    if embed_backend is None:
        # Deterministic tiny stub so pipeline memory embeddings still run offline.
        class _EmbedStub(object):
            def embed(self, texts):
                data = []
                for i, _t in enumerate(texts or [""]):
                    data.append({"embedding": [float((i + 1) % 7)] * 10})
                return {"data": data}

        embed_backend = _EmbedStub()

    return run_chat_pipeline(
        user_id=req.user_id or "default-user",
        messages=[message.dict() for message in req.messages],
        chat_backend=chat_backend,
        embed_backend=embed_backend,
    )
