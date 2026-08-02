"""Self-evolving capability scaffolding for RealAI.

This module provides lightweight, runtime-based mechanisms for:
- self-diagnosis of recurring failures
- generation of new capability plugins
- shadow-critic suggestions
- memory-backed evolution state
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class SelfEvolvingRuntime(object):
    """Store lightweight evolution state and propose new capabilities."""

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path(__file__).resolve().parents[2] / 'realai_evolution_state.json'
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding='utf-8'))
            except Exception:
                return {}
        return {
            'version': 1,
            'cycles': 0,
            'diagnoses': [],
            'generated_plugins': [],
            'shadow_suggestions': [],
        }

    def _save_state(self):
        self.state_path.write_text(json.dumps(self._state, indent=2), encoding='utf-8')

    def diagnose(self, text: str, tool_name: Optional[str] = None) -> Dict[str, Any]:
        lowered = (text or '').lower()
        concerns = []
        if 'search' in lowered or 'web' in lowered:
            concerns.append('web_lookup_gap')
        if 'file' in lowered or 'read' in lowered:
            concerns.append('local_context_gap')
        if 'solve' in lowered or 'plan' in lowered:
            concerns.append('planning_gap')
        diagnosis = {
            'timestamp': int(time.time()),
            'text': text,
            'tool': tool_name,
            'concerns': concerns,
            'summary': 'Self-diagnosis found {0}'.format(', '.join(concerns) if concerns else 'no clear gaps'),
        }
        self._state['diagnoses'].append(diagnosis)
        self._state['cycles'] += 1
        self._save_state()
        return diagnosis

    def shadow_critic(self, text: str) -> Dict[str, Any]:
        lowered = (text or '').lower()
        suggestions = []
        if 'search' in lowered or 'web' in lowered:
            suggestions.append('create_web_research_plugin')
        if 'file' in lowered or 'read' in lowered:
            suggestions.append('create_workspace_memory_plugin')
        if 'plan' in lowered or 'task' in lowered:
            suggestions.append('create_task_graph_plugin')
        suggestion = {
            'timestamp': int(time.time()),
            'text': text,
            'suggestions': suggestions,
            'summary': 'Shadow critic recommends {0}'.format(', '.join(suggestions) if suggestions else 'no new plugin'),
        }
        self._state['shadow_suggestions'].append(suggestion)
        self._save_state()
        return suggestion

    def generate_plugin(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        concerns = diagnosis.get('concerns', [])
        plugin_name = 'generated_plugin'
        if 'web_lookup_gap' in concerns:
            plugin_name = 'web_research_plugin'
        elif 'local_context_gap' in concerns:
            plugin_name = 'workspace_memory_plugin'
        elif 'planning_gap' in concerns:
            plugin_name = 'task_graph_plugin'
        plugin = {
            'name': plugin_name,
            'created_at': int(time.time()),
            'source': diagnosis.get('summary', 'self-evolution'),
            'capabilities': concerns or ['adaptive_reasoning'],
        }
        self._state['generated_plugins'].append(plugin)
        self._save_state()
        return plugin

    def state(self) -> Dict[str, Any]:
        return {
            'cycles': self._state['cycles'],
            'diagnoses': list(self._state['diagnoses'][-5:]),
            'generated_plugins': list(self._state['generated_plugins'][-5:]),
            'shadow_suggestions': list(self._state['shadow_suggestions'][-5:]),
        }


SELF_EVOLVING = SelfEvolvingRuntime()
