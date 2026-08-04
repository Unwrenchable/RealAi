from fastapi import Depends, FastAPI

from .auth import require_api_key
from .config import DEFAULT_MODEL_ID, DEFAULT_MODEL_OWNER
from .providers import MockProvider, ProviderRouter
from .schemas import ChatCompletionRequest

app = FastAPI(
    title="RealAI API",
    version="0.1.0",
    description="OpenAI-compatible RealAI API skeleton with pluggable agents.",
)

provider_router = ProviderRouter(
    default_provider=MockProvider(model_id=DEFAULT_MODEL_ID, owned_by=DEFAULT_MODEL_OWNER)
)


@app.get("/v1/models")
def list_models(api_key: str = Depends(require_api_key)):
    models = provider_router.list_models()
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest, api_key: str = Depends(require_api_key)):
    response = provider_router.route_chat(request)
    return response
