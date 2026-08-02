import os
import re
from typing import Iterable, List

RELEVANT_EXTENSIONS = {'.py', '.ts', '.js', '.md', '.json', '.yaml', '.yml', '.toml'}
IGNORED_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.next', '.backup', 'archive', 'build', 'dist', '.eggs', 'tmp'}
IGNORED_FILES = {'package-lock.json', 'SOURCES.txt', 'PKG-INFO', 'requires.txt', 'dependency_links.txt', 'top_level.txt', 'entry_points.txt', '.gitkeep'}


def filter_relevant_files(paths: Iterable[str]) -> List[str]:
    relevant = []
    for path in paths:
        if not path:
            continue
        if os.path.splitext(path)[1].lower() not in RELEVANT_EXTENSIONS:
            continue
        parts = path.split('/')
        if any(part in IGNORED_DIRS for part in parts[:2]):
            continue
        if os.path.basename(path) in IGNORED_FILES:
            continue
        if '/.backup/' in path or '/archive/' in path or '/backup/' in path:
            continue
        if parts and parts[0].startswith('.'):
            continue
        relevant.append(path)
    return sorted(relevant)
