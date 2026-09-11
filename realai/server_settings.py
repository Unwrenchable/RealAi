"""Package-root import shim for Server settings.

Gold lives at ``realai.server.server_settings`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.server.server_settings import *  # noqa: F403
