"""In-process hive event stream (feeds SSE GET /v1/hive/events and the agents-ui viewer).

Events are small dicts: {"seq", "ts", "type", "run", ...}. Types:
  run.started, plan.created, step.started, handoff, tool.call, grounding.flag,
  step.finished, review, qa.finding, run.finished, run.error
Tool events carry tool name + path/pattern/glob only, never file contents.
"""
from __future__ import annotations

import itertools
import queue
import threading
import time
from collections import deque
from typing import Any, Callable

_LOCK = threading.Lock()
_SEQ = itertools.count(1)
_RING: deque[dict[str, Any]] = deque(maxlen=500)
_SUBS: list[queue.Queue] = []

Emit = Callable[..., None]


def emit(type_: str, **data: Any) -> dict[str, Any]:
    ev = {"seq": next(_SEQ), "ts": time.time(), "type": type_, **data}
    with _LOCK:
        _RING.append(ev)
        subs = list(_SUBS)
    for q in subs:
        try:
            q.put_nowait(ev)
        except queue.Full:
            pass
    return ev


def noop(*_a: Any, **_k: Any) -> None:
    return None


def recent(n: int = 200, after: int = 0) -> list[dict[str, Any]]:
    with _LOCK:
        return [e for e in list(_RING)[-n:] if e["seq"] > after]


def subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=1000)
    with _LOCK:
        _SUBS.append(q)
    return q


def unsubscribe(q: queue.Queue) -> None:
    with _LOCK:
        if q in _SUBS:
            _SUBS.remove(q)


def tool_args_public(args: Any) -> dict[str, Any]:
    a = args if isinstance(args, dict) else {}
    return {k: str(a[k])[:200] for k in ("path", "pattern", "query", "glob") if k in a}


def _reset_for_tests() -> None:
    with _LOCK:
        _RING.clear()
        _SUBS.clear()
