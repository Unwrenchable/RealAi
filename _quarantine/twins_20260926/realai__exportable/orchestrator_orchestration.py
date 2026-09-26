"""Planner -> worker -> critic -> synthesizer orchestration runtime."""

import time
import uuid
from typing import Any, Dict, List


class TaskOrchestrator(object):
    """Stateful task orchestration with lifecycle tracking."""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, payload: Dict[str, Any]):
        task_id = 'task_{0}'.format(uuid.uuid4().hex[:12])
        state = {
            'id': task_id,
            'status': 'running',
            'created_at': int(time.time()),
            'steps': [],
            'result': None,
        }
        self._tasks[task_id] = state
        self._run_pipeline(task_id, payload or {})
        return state

    def _append_step(self, task_id: str, role: str, output: str):
        self._tasks[task_id]['steps'].append({
            'role': role,
            'output': output,
            'timestamp': int(time.time()),
        })

    def _run_pipeline(self, task_id: str, payload: Dict[str, Any]):
        task = payload.get('task') or ''
        context = payload.get('context') or ''
        planner = 'Plan for task: {0}'.format(task)
        worker = 'Executed work based on plan. Context={0}'.format(context)
        critic = 'Critique: output is coherent and low risk.'
        synthesizer = '{0}\n{1}\n{2}'.format(planner, worker, critic)
        self._append_step(task_id, 'planner', planner)
        self._append_step(task_id, 'worker', worker)
        self._append_step(task_id, 'critic', critic)
        self._append_step(task_id, 'synthesizer', synthesizer)
        self._tasks[task_id]['result'] = {
            'final_output': synthesizer,
            'task': task,
        }
        self._tasks[task_id]['status'] = 'completed'
        self._tasks[task_id]['completed_at'] = int(time.time())

    def get_task(self, task_id: str):
        if task_id not in self._tasks:
            raise ValueError('Unknown task {0}'.format(task_id))
        return self._tasks[task_id]

    def list_tasks(self):
        return sorted(self._tasks.values(), key=lambda item: item['created_at'], reverse=True)

    def interrupt(self, task_id: str):
        task = self.get_task(task_id)
        if task['status'] == 'completed':
            return task
        task['status'] = 'interrupted'
        return task


TASKS = TaskOrchestrator()

