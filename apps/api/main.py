"""Week-1/2 FastAPI provider app entrypoint."""

import json
import time
from collections import defaultdict, deque

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from apps.api.middleware.logging import RequestLogger
from apps.api.state import (
    inference_registry,
    model_cache,
    tool_registry,
    voice_registry,
    web3_policy,
    web3_registry,
)
from core.logging.logger import log

app = FastAPI(title="RealAI API")
app.add_middleware(RequestLogger)

MAX_REQUESTS_PER_SECOND = 10
MAX_REQUESTS_PER_MINUTE = 100
MAX_PAYLOAD_BYTES = 1 * 1024 * 1024
_RATE_WINDOWS = defaultdict(deque)

@app.middleware("http")
async def security_middleware(request, call_next):
    try:
        now = time.monotonic()
        identifier = request.client.host if request.client and request.client.host else "unknown"
        window = _RATE_WINDOWS[identifier]
        while window and now - window[0] > 60:
            window.popleft()
        one_second_count = 0
        for ts in reversed(window):
            if now - ts <= 1:
                one_second_count += 1
            else:
                break
        if one_second_count >= MAX_REQUESTS_PER_SECOND or len(window) >= MAX_REQUESTS_PER_MINUTE:
            return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
        window.append(now)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_PAYLOAD_BYTES:
                    return JSONResponse(status_code=413, content={"error": "Payload too large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"error": "Invalid content-length header"})

        if request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.body()
                if len(body) > MAX_PAYLOAD_BYTES:
                    return JSONResponse(status_code=413, content={"error": "Payload too large"})
                if body:
                    try:
                        json.loads(body.decode("utf-8"))
                    except Exception:
                        return JSONResponse(status_code=400, content={"error": "Malformed JSON"})
                request._body = body
        return await call_next(request)
    except Exception as exc:
        log("error.exception", {"path": request.url.path, "error": str(exc)})
        raise


from apps.api.routes import audio, chat, embeddings, health, metrics, models, tasks, voice_ws, web3  # noqa: E402

app.include_router(chat.router)
app.include_router(embeddings.router)
app.include_router(models.router)
app.include_router(metrics.router)
app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(audio.router)
app.include_router(voice_ws.router)
app.include_router(web3.router)
