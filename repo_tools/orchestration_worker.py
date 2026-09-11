#!/usr/bin/env python3
"""Compat shim — prefer::

    python -m modules.orchestrators.orchestration_worker
"""
from __future__ import annotations

import sys

from modules.orchestrators.orchestration_worker import main_loop

if __name__ == "__main__":
    print(
        "[compat] use: python -m modules.orchestrators.orchestration_worker",
        file=sys.stderr,
    )
    main_loop()
