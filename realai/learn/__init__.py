"""Git-learn: scan a git tree, emit a packet, optionally scaffold a coach stub."""
from __future__ import annotations

from realai.learn.packet import PACKET_SCHEMA, validate_packet
from realai.learn.pipeline import run_learn
from realai.learn.scout import handle_learn_queue_request, scout, scout_and_queue
from realai.learn.scaffold import plugin_package_name, scaffold_plugin
from realai.learn.skip import (
    SKIP_DIR_NAMES,
    SKIP_FILE_NAMES,
    SKIP_SUFFIXES,
    should_skip_dir,
    should_skip_file,
    should_skip_filename,
    should_skip_rel,
)

__all__ = [
    "PACKET_SCHEMA",
    "SKIP_DIR_NAMES",
    "SKIP_FILE_NAMES",
    "SKIP_SUFFIXES",
    "plugin_package_name",
    "handle_learn_queue_request",
    "run_learn",
    "scout",
    "scout_and_queue",
    "scaffold_plugin",
    "should_skip_dir",
    "should_skip_file",
    "should_skip_filename",
    "should_skip_rel",
    "validate_packet",
]
