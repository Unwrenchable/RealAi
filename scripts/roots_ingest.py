"""
Canonical roots_ingest
======================
No roots_ingest.py in recovered trees. The ingest root list is recovered
from scanners/scan_desktop_missing_gold.py::DEFAULT_ROOTS.
This module only exposes that list. It does not walk disks on import.
"""
from __future__ import annotations

from typing import Any, Dict, List

STATUS = "reconstructed_from_recovered_list"
CANONICAL_NAME = "roots_ingest"
RECOVERED_FROM = "scanners/scan_desktop_missing_gold.py::DEFAULT_ROOTS"

# Recovered DEFAULT_ROOTS (Linux-mount form) plus the Windows labels
# from the reconstruction request. Stored as data, not walked.
DEFAULT_ROOTS: List[str] = [
    r"C:\\RealAI-clean",
    r"C:\\RealAI-clean\\realai",
    r"C:\\RealAI-clean\\scripts",
    r"C:\\RealAI-clean\\providers",
    r"C:\\RealAI-clean\\packages",
    r"C:\\RealAI-clean\\agents",
    r"C:\\RealAI-clean\\memory",
    r"C:\\RealAI-clean\\models",
    r"C:\\RealAI-clean\\training",
    r"C:\\RealAI-clean\\archive",
    r"C:\\RealAI-clean\\.kilo",
    r"C:\\RealAI-clean\\_quarantine",
    r"C:\\Users\\tsmit\\realai_historical_backups",
    r"C:\\Users\\tsmit\\backups",
    r"D:\\RealAI-archive",
    r"D:\\realai_archives",
]


def roots() -> List[str]:
    return list(DEFAULT_ROOTS)


def describe() -> Dict[str, Any]:
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "recovered_from": RECOVERED_FROM,
        "root_count": len(DEFAULT_ROOTS),
        "walks_on_import": False,
    }
