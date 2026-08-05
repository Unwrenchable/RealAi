"""
RealAI Main Server - Clean FastAPI Version with Plugins
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Our recovered plugins
from plugins.core.local_models import get_model_manager, get_llm_engine
from plugins.tools.device_selector import get_device_name
from aura.memory.engine import get_memory
from aura.reasoning.core import get_reasoner

app = FastAPI(title="RealAI", version="3.0-dev")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "RealAI is running", "version": "3.0-dev"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "device": get_device_name(),
        "plugins": ["local_models", "device_selector", "memory", "reasoning"]
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
    print("🚀 RealAI Main Server starting on http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)