"""Package-root import shim for Self-improving agent.

Gold lives at ``agents.self_improving_agent`` (product-root).
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from agents.self_improving_agent import *  # noqa: F403
