"""RealAI-clean local inference shim — OpenAI-compatible API via llama-cli.

Prefer the full stack for day-to-day use:
    start_gpu_chat.bat
    powershell -File scripts\\run_local_chat.ps1
    → UI :3000 → orchestrator :8001 → Vulkan llama-server :8080

This script is a lightweight single-process alternative (CLI backend, no Vulkan server).

Usage:
    python realai_local_server.py

Configure clients:
    API Base URL: http://127.0.0.1:8000/v1
    API Key: local (or any value)
    Model: realai-default-coder
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parent
_MODELS = _ROOT / "models"

# Preferred public model id for this repo
DEFAULT_MODEL_ID = os.environ.get("REALAI_DEFAULT_MODEL", "realai-default-coder")

# GGUF preference order (repo models/)
_GGUF_CANDIDATES = [
    "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
    "realai-1.0-instruct-Q4_K_M.gguf",
    "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
    "llama-3.2-1b.gguf",
    "llama-local-1b-Q4_K_M.gguf",
]

_LLAMA_CANDIDATES = [
    Path(os.environ["REALAI_LLAMA_CLI"]) if os.environ.get("REALAI_LLAMA_CLI") else None,
    Path(r"C:\llama-vulkan\llama-cli.exe"),
    Path(r"C:\llama-vulkan\llama-completion.exe"),
    Path(r"C:\llama.cpp\build\bin\Release\llama-cli.exe"),
    Path(r"C:\llama.cpp\build\bin\Release\llama-simple.exe"),
    Path(r"C:\llama.cpp\llama-cli.exe"),
]


def _find_llama_cli() -> Path:
    for name in ("llama-cli", "llama-cli.exe", "llama-completion", "llama-completion.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for p in _LLAMA_CANDIDATES:
        if p and p.is_file():
            return p
    raise FileNotFoundError(
        "No llama-cli found. Install C:\\llama-vulkan\\llama-cli.exe "
        "or set REALAI_LLAMA_CLI."
    )


def _find_default_gguf() -> Path:
    env = os.environ.get("REALAI_MODEL_PATH") or os.environ.get("REALAI_BACKEND_MODEL")
    if env:
        p = Path(env)
        if not p.is_file() and not p.is_absolute():
            p = _MODELS / Path(env).name
        if p.is_file():
            return p
    for name in _GGUF_CANDIDATES:
        p = _MODELS / name
        if p.is_file():
            return p
    ggufs = sorted(_MODELS.glob("*.gguf")) if _MODELS.is_dir() else []
    if ggufs:
        return ggufs[0]
    raise FileNotFoundError(f"No GGUF under {_MODELS}")


try:
    LLAMA_CLI_PATH = str(_find_llama_cli())
except FileNotFoundError:
    LLAMA_CLI_PATH = r"C:\llama-vulkan\llama-cli.exe"

try:
    DEFAULT_MODEL_PATH = str(_find_default_gguf())
except FileNotFoundError:
    DEFAULT_MODEL_PATH = str(_MODELS / _GGUF_CANDIDATES[0])

app = FastAPI(title="RealAI-clean Local Inference Server")

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
    model: str = DEFAULT_MODEL_ID
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    top_k: Optional[int] = 40


class CompletionRequest(BaseModel):
    model: str = DEFAULT_MODEL_ID
    prompt: str
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7


def _run_llama(prompt: str, max_tokens: int) -> str:
    cli = Path(LLAMA_CLI_PATH)
    model = Path(DEFAULT_MODEL_PATH)
    if not cli.is_file():
        raise HTTPException(status_code=500, detail=f"llama binary missing: {cli}")
    if not model.is_file():
        raise HTTPException(status_code=500, detail=f"GGUF missing: {model}")

    cmd = [
        str(cli),
        "-m",
        str(model),
        "-p",
        prompt,
        "-n",
        str(max_tokens or 512),
    ]
    print(f"Calling {cli.name}: model={model.name} n={max_tokens}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"llama-cli failed: {result.stderr or result.stdout}",
        )
    output = (result.stdout or "").strip()
    if output.startswith(prompt):
        output = output[len(prompt) :].strip()
    return output


@app.get("/health")
def health():
    return {
        "status": "ok",
        "backend": "llama-cli",
        "repo": str(_ROOT),
        "model_path": DEFAULT_MODEL_PATH,
        "llama_cli": LLAMA_CLI_PATH,
        "default_model": DEFAULT_MODEL_ID,
    }


@app.get("/v1/models")
def list_models():
    data = []
    if _MODELS.is_dir():
        for gguf in sorted(_MODELS.glob("*.gguf")):
            mid = (
                DEFAULT_MODEL_ID
                if gguf.name == Path(DEFAULT_MODEL_PATH).name
                else gguf.stem.lower().replace(".", "-")
            )
            data.append(
                {
                    "id": mid,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "realai",
                    "realai": {"gguf_filename": gguf.name, "gguf_path": str(gguf)},
                }
            )
    if not data:
        data = [
            {
                "id": DEFAULT_MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "realai",
            }
        ]
    # Always expose canonical id first
    ids = {m["id"] for m in data}
    if DEFAULT_MODEL_ID not in ids:
        data.insert(
            0,
            {
                "id": DEFAULT_MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "realai",
            },
        )
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    try:
        prompt = ""
        for msg in req.messages:
            if msg.role == "system":
                prompt += f"System: {msg.content}\n"
            elif msg.role == "user":
                prompt += f"User: {msg.content}\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n"
        prompt += "Assistant:"

        output = _run_llama(prompt, req.max_tokens or 512)
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model or DEFAULT_MODEL_ID,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": output},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(output.split()),
                "total_tokens": len(prompt.split()) + len(output.split()),
            },
        }
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Request timed out after 5 minutes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@app.post("/v1/completions")
def completions(req: CompletionRequest):
    try:
        output = _run_llama(req.prompt, req.max_tokens or 512)
        return {
            "id": f"cmpl-{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": req.model or DEFAULT_MODEL_ID,
            "choices": [{"text": output, "index": 0, "finish_reason": "stop"}],
        }
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Request timed out after 5 minutes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("RealAI-clean Local Inference Server (llama-cli shim)")
    print("=" * 70)
    print(f"Repo:   {_ROOT}")
    print(f"Binary: {LLAMA_CLI_PATH}")
    print(f"Model:  {DEFAULT_MODEL_PATH}")
    print(f"ID:     {DEFAULT_MODEL_ID}")
    print()
    print("Server: http://127.0.0.1:8000")
    print("  API Base: http://127.0.0.1:8000/v1")
    print("  API Key:  local")
    print()
    print("Prefer full stack: start_gpu_chat.bat  (orchestrator :8001 + Vulkan :8080)")
    print("=" * 70)

    uvicorn.run(app, host="127.0.0.1", port=8000)
