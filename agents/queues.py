# realai/agents/queues.py
import json
import redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

r = redis.Redis.from_url(REDIS_URL)


def enqueue(queue_name: str, message: dict):
    r.lpush(queue_name, json.dumps(message))


def dequeue(queue_name: str, timeout: int = 5):
    item = r.brpop(queue_name, timeout=timeout)
    if item is None:
        return None
    _, raw = item
    return json.loads(raw)
