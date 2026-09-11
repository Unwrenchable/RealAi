"""FastAPI health router for root ``main.py`` / docker entry.

Reports honest subsystem status (never claims Redis/Postgres ok without a probe).
Shape aligns with the RealAI hive blueprint::

    { realai, redis, postgres, vulkan }
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter

router = APIRouter(tags=["health"])


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _probe_tcp(host: str, port: int, timeout: float = 1.5) -> Tuple[str, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "ok", f"tcp://{host}:{port}"
    except OSError as e:
        return "error", str(e)


def _probe_redis() -> Dict[str, Any]:
    url = _env("REDIS_URL") or _env("REALAI_REDIS_URL")
    host = _env("REDIS_HOST") or _env("REALAI_REDIS_HOST")
    port_s = _env("REDIS_PORT") or _env("REALAI_REDIS_PORT") or "6379"
    if not url and not host:
        # default local probe only if explicitly enabled
        if _env("REALAI_HEALTH_PROBE_LOCAL", "1") not in ("1", "true", "True", "yes"):
            return {"status": "missing", "detail": "REDIS_URL not set"}
        host, port_s = "127.0.0.1", "6379"
    try:
        port = int(port_s)
    except ValueError:
        return {"status": "error", "detail": f"bad redis port: {port_s}"}

    if url.startswith("redis://") and not host:
        # redis://[:password@]host:port/db
        rest = url[len("redis://") :]
        if "@" in rest:
            rest = rest.split("@", 1)[1]
        hostport = rest.split("/", 1)[0]
        if ":" in hostport:
            host, port_s = hostport.rsplit(":", 1)
            try:
                port = int(port_s)
            except ValueError:
                port = 6379
        else:
            host = hostport or "127.0.0.1"

    # Prefer redis-py if installed
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(url) if url.startswith("redis://") else redis.Redis(host=host, port=port, socket_timeout=1.5)
        client.ping()
        return {"status": "ok", "detail": url or f"{host}:{port}"}
    except ImportError:
        status, detail = _probe_tcp(host or "127.0.0.1", port)
        return {
            "status": status if status == "ok" else ("missing" if "refused" in detail.lower() or "10061" in detail else status),
            "detail": detail if status == "ok" else f"redis package missing; tcp={detail}",
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _probe_postgres() -> Dict[str, Any]:
    host = _env("POSTGRES_HOST") or _env("REALAI_POSTGRES_HOST")
    port_s = _env("POSTGRES_PORT") or _env("REALAI_POSTGRES_PORT") or "5432"
    db = _env("POSTGRES_DB") or _env("REALAI_POSTGRES_DB") or "realai_core"
    user = _env("POSTGRES_USER") or _env("REALAI_POSTGRES_USER")
    password = _env("POSTGRES_PASSWORD") or _env("REALAI_POSTGRES_PASSWORD")
    dsn = _env("DATABASE_URL") or _env("REALAI_DATABASE_URL")

    if not dsn and not host and not user:
        if _env("REALAI_HEALTH_PROBE_LOCAL", "1") not in ("1", "true", "True", "yes"):
            return {"status": "missing", "detail": "POSTGRES_* / DATABASE_URL not set"}
        host = "127.0.0.1"

    try:
        port = int(port_s)
    except ValueError:
        return {"status": "error", "detail": f"bad postgres port: {port_s}"}

    try:
        import psycopg2  # type: ignore

        if dsn:
            conn = psycopg2.connect(dsn, connect_timeout=2)
        else:
            conn = psycopg2.connect(
                host=host or "127.0.0.1",
                port=port,
                dbname=db,
                user=user or "realai",
                password=password or "",
                connect_timeout=2,
            )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            conn.close()
        return {"status": "ok", "detail": f"{host or 'dsn'}:{port}/{db}"}
    except ImportError:
        status, detail = _probe_tcp(host or "127.0.0.1", port)
        return {
            "status": status if status == "ok" else ("missing" if "refused" in detail.lower() or "10061" in detail else status),
            "detail": detail if status == "ok" else f"psycopg2 missing; tcp={detail}",
        }
    except Exception as e:
        # Never echo password
        msg = str(e)
        if password and password in msg:
            msg = msg.replace(password, "***")
        return {"status": "error", "detail": msg}


def _probe_vulkan() -> Dict[str, Any]:
    base = (_env("REALAI_VULKAN_BASE") or _env("VULKAN_URL") or "http://127.0.0.1:8080").rstrip("/")
    url = f"{base}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body: Any = json.loads(raw)
            except Exception:
                body = raw[:200]
            ok = 200 <= getattr(resp, "status", 200) < 300
            return {
                "status": "ok" if ok else "degraded",
                "base": base,
                "body": body,
            }
    except Exception as e:
        return {"status": "error", "base": base, "detail": str(e)}


def build_health() -> Dict[str, Any]:
    redis = _probe_redis()
    postgres = _probe_postgres()
    vulkan = _probe_vulkan()

    # Top-level flat fields for blueprint consumers
    flat = {
        "realai": "ok",
        "redis": redis.get("status") or "missing",
        "postgres": postgres.get("status") or "missing",
        "vulkan": vulkan.get("status") or "error",
    }

    # Overall: degraded if vulkan bad; error if realai somehow broken (never here)
    overall = "ok"
    if flat["vulkan"] in ("error", "degraded"):
        overall = "degraded"
    if flat["redis"] == "error" or flat["postgres"] == "error":
        overall = "degraded"

    return {
        **flat,
        "status": overall,
        "service": "realai-fastapi",
        "details": {
            "redis": redis,
            "postgres": postgres,
            "vulkan": vulkan,
        },
    }


@router.get("/health")
def health() -> Dict[str, Any]:
    return build_health()


@router.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"status": "ok"}
