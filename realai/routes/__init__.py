"""API route modules.

Canonical FastAPI routers for RealAI. Live chat still goes through
workspace api_server.py (/v1/* + /fusion-ui/). This package exports the
split routers so a FastAPI app can include them in one call:

    from realai.routes import include_all
    include_all(app)
"""

from .audio import router as audio_router
from .chat import router as chat_router
from .embeddings import router as embeddings_router
from .health import router as health_router
from .metrics import router as metrics_router
from .models import router as models_router
from .tasks import router as tasks_router
from .voice_ws import router as voice_ws_router
from .web3 import router as web3_router

ROUTERS = (
    health_router,
    models_router,
    chat_router,
    embeddings_router,
    audio_router,
    tasks_router,
    voice_ws_router,
    web3_router,
    metrics_router,
)

__all__ = [
    "ROUTERS",
    "include_all",
    "audio_router",
    "chat_router",
    "embeddings_router",
    "health_router",
    "metrics_router",
    "models_router",
    "tasks_router",
    "voice_ws_router",
    "web3_router",
]


def include_all(app):
    """Attach every RealAI APIRouter to a FastAPI *app*."""
    for router in ROUTERS:
        app.include_router(router)
    return app
