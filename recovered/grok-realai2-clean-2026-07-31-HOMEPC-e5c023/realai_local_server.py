"""
RealAI Local Inference Server - OpenAI-compatible with plugins
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Our recovered plugins
from plugins.core.local_models import get_model_manager, get_llm_engine
from plugins.tools.device_selector import get_device_name
from aura.memory.engine import get_memory
from aura.reasoning.core import get_reasoner

app = FastAPI(title="RealAI Local", version="3.0-dev")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "RealAI Local Server is running", "backend": "local"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "device": get_device_name(),
        "plugins": ["local_models", "device_selector", "memory", "reasoning"],
        "llm": "ready"
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 512)

    engine = get_llm_engine()
    response_text = engine.chat_completion(messages, max_tokens=max_tokens, temperature=temperature)

    return {
        "id": "chat-" + str(hash(response_text)),
        "object": "chat.completion",
        "choices": [{"message": {"role": "assistant", "content": response_text}}],
        "usage": {"total_tokens": len(response_text.split())}
    }

if __name__ == "__main__":
    print("=" * 70)
    print("RealAI Local Server with Plugins")
    print("=" * 70)
    print("Server starting on http://127.0.0.1:8000")
    print("Configure RealAI client to use this URL")
    print("=" * 70)
    uvicorn.run(app, host="127.0.0.1", port=8000)