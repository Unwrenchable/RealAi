"""RealAI Local Inference Server - OpenAI-compatible API backed by llama.cpp

This server exposes OpenAI-compatible endpoints that RealAI can talk to,
while internally using your local llama.cpp build for inference.

Usage:
    python realai_local_server.py

Then configure RealAI:
    API Base URL: http://127.0.0.1:8000/v1
    API Key: local (or any value)
"""

import subprocess
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import time

# Configure your paths here
LLAMA_CLI_PATH = r"C:\llama.cpp\build\bin\Release\llama-simple.exe"
DEFAULT_MODEL_PATH = r"C:\Users\tsmit\OneDrive\Apps\realai\models\llama3.2-1b\Llama-3.2-1B-Instruct-Q4_K_M.gguf"

app = FastAPI(title="RealAI Local Inference Server")

# Enable CORS so web clients can access this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "llama-3.2-1b"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    top_k: Optional[int] = 40


class CompletionRequest(BaseModel):
    model: str = "llama-3.2-1b"
    prompt: str
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7


class Model(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "local"


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "backend": "llama.cpp"}


@app.get("/v1/models")
def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "llama-3.2-1b",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local"
            }
        ]
    }


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    """OpenAI-compatible chat completions endpoint"""
    try:
        # Format messages into a prompt
        prompt = ""
        for msg in req.messages:
            if msg.role == "system":
                prompt += f"System: {msg.content}\n"
            elif msg.role == "user":
                prompt += f"User: {msg.content}\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n"

        prompt += "Assistant:"

        # Call llama-simple.exe
        cmd = [
            LLAMA_CLI_PATH,
            "-m", DEFAULT_MODEL_PATH,
            "-p", prompt,
            "-n", str(req.max_tokens)
        ]

        print(f"Calling llama-simple: {' '.join(cmd[:4])}...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"llama-cli failed: {result.stderr}"
            )

        # Extract the generated text
        output = result.stdout.strip()

        # Remove the prompt echo if present
        if output.startswith(prompt):
            output = output[len(prompt):].strip()

        # Return OpenAI-compatible response
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": output
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(output.split()),
                "total_tokens": len(prompt.split()) + len(output.split())
            }
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Request timed out after 5 minutes"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


@app.post("/v1/completions")
def completions(req: CompletionRequest):
    """OpenAI-compatible completions endpoint"""
    try:
        # Call llama-simple.exe
        cmd = [
            LLAMA_CLI_PATH,
            "-m", DEFAULT_MODEL_PATH,
            "-p", req.prompt,
            "-n", str(req.max_tokens)
        ]

        print(f"Calling llama-simple: {' '.join(cmd[:4])}...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"llama-cli failed: {result.stderr}"
            )

        output = result.stdout.strip()

        # Remove prompt echo
        if output.startswith(req.prompt):
            output = output[len(req.prompt):].strip()

        return {
            "id": f"cmpl-{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "text": output,
                    "index": 0,
                    "finish_reason": "stop"
                }
            ]
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Request timed out after 5 minutes"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


if __name__ == "__main__":
    print("=" * 70)
    print("RealAI Local Inference Server")
    print("=" * 70)
    print(f"Backend: llama.cpp")
    print(f"Binary: {LLAMA_CLI_PATH}")
    print(f"Model: {DEFAULT_MODEL_PATH}")
    print(f"")
    print(f"Server starting on http://127.0.0.1:8000")
    print(f"")
    print(f"Configure RealAI:")
    print(f"  API Base URL: http://127.0.0.1:8000/v1")
    print(f"  API Key: local (or any value)")
    print(f"")
    print("=" * 70)

    uvicorn.run(app, host="127.0.0.1", port=8000)
