"""Self-evolving capability scaffolding (promoted from RealAi-unified 763a4c2,
realai/server/self_evolving.py). Status: PARTIAL, opt-in plugin.

Default OFF / dry-run: nothing is written unless REALAI_SELF_EVOLVING=1 (or
``dry_run=False``). When enabled, state lives only under
REALAI_HOME/.realai/self_evolving_state.json. "Generated plugins" are proposals
recorded in state; no code is written. No network.

This module provides lightweight, runtime-based mechanisms for:
- self-diagnosis of recurring failures
- generation of new capability plugins
- shadow-critic suggestions
- memory-backed evolution state
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def enabled() -> bool:
    """True only when REALAI_SELF_EVOLVING is explicitly on."""
    return os.environ.get('REALAI_SELF_EVOLVING', '').strip().lower() in {'1', 'true', 'yes', 'on'}


class SelfEvolvingRuntime(object):
    """Store lightweight evolution state and propose new capabilities."""

    def __init__(self, state_path: Optional[Path] = None, dry_run: Optional[bool] = None):
        from modules.organs.synthetic_organs import realai_home, within_home

        home = realai_home()
        self.state_path = (state_path or home / '.realai' / 'self_evolving_state.json').resolve()
        if not within_home(self.state_path, home):
            raise ValueError('self_evolving state_path must be inside REALAI_HOME')
        if dry_run is None:
            dry_run = not enabled()
        self.dry_run = bool(dry_run)
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding='utf-8'))
                if isinstance(data, dict) and 'diagnoses' in data:
                    return data
            except Exception:
                pass
        return {
            'version': 1,
            'cycles': 0,
            'diagnoses': [],
            'generated_plugins': [],
            'shadow_suggestions': [],
        }

    def _save_state(self):
        if self.dry_run:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
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
            'dry_run': self.dry_run,
            'cycles': self._state['cycles'],
            'diagnoses': list(self._state['diagnoses'][-5:]),
            'generated_plugins': list(self._state['generated_plugins'][-5:]),
            'shadow_suggestions': list(self._state['shadow_suggestions'][-5:]),
        }


def evolve(text: str, tool_name: Optional[str] = None, runtime: Optional[SelfEvolvingRuntime] = None) -> Dict[str, Any]:
    """One diagnose -> critic -> proposal cycle (dry-run unless enabled)."""
    rt = runtime or SelfEvolvingRuntime()
    diagnosis = rt.diagnose(text, tool_name=tool_name)
    return {
        'diagnosis': diagnosis,
        'shadow_critic': rt.shadow_critic(text),
        'generated_plugin': rt.generate_plugin(diagnosis),
        'state': rt.state(),
    }


def register(model: Any = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Opt-in registration; attaches ``self_evolve`` (dry-run by default)."""
    if model is not None:
        setattr(model, 'self_evolve', evolve)
    return {'name': 'self_evolving', 'ok': True, 'status': 'PARTIAL', 'dry_run': not enabled(), 'methods': ['self_evolve']}


def invoke(ability: str, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if ability == 'health':
        return {'plugin': 'self-evolving', 'result': {'status': 'ok', 'dry_run': not enabled()}}
    if ability == 'evolve':
        return {'plugin': 'self-evolving', 'result': evolve(str(payload.get('text', '')), payload.get('tool_name'))}
    return {'plugin': 'self-evolving', 'error': 'unknown ability: {0}'.format(ability)}
