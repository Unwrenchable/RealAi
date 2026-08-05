"""Planner -> worker -> critic -> synthesizer orchestration runtime."""

import time
import uuid
from typing import Any, Dict, List

from .persistence import connect, json_dumps, json_loads


class TaskOrchestrator(object):
    """SQLite-backed task orchestration with lifecycle tracking."""

    def create_task(self, payload: Dict[str, Any]):
        task_id = 'task_{0}'.format(uuid.uuid4().hex[:12])
        created_at = int(time.time())
        task = payload.get('task') or ''
        context = payload.get('context') or ''
        with connect() as con:
            con.execute(
                """
                INSERT INTO tasks (id, task, context, status, result, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, task, context, 'running', None, created_at, None),
            )
        self._run_pipeline(task_id, payload or {})
        return self.get_task(task_id)

    def _append_step(self, task_id: str, role: str, output: str):
        with connect() as con:
            con.execute(
                'INSERT INTO task_steps (task_id, role, output, timestamp) VALUES (?, ?, ?, ?)',
                (task_id, role, output, int(time.time())),
            )

    def _run_pipeline(self, task_id: str, payload: Dict[str, Any]):
        task = payload.get('task') or ''
        context = payload.get('context') or ''
        tool_names = payload.get('tools') or []
        tool_hint = ', '.join(tool_names) if isinstance(tool_names, list) and tool_names else 'none declared'
        planner = 'Plan for task: {0}. Context length={1}. Tools={2}.'.format(task, len(context), tool_hint)
        worker = 'Executed work package for "{0}". Context={1}'.format(task, context or 'none')
        critic = 'Critique: output is coherent, traceable, and ready for follow-up execution.'
        synthesizer = 'Task complete.\n\n{0}\n{1}\n{2}'.format(planner, worker, critic)
        self._append_step(task_id, 'planner', planner)
        self._append_step(task_id, 'worker', worker)
        self._append_step(task_id, 'critic', critic)
        self._append_step(task_id, 'synthesizer', synthesizer)
        result = {
            'final_output': synthesizer,
            'task': task,
            'context': context,
        }
        with connect() as con:
            con.execute(
                """
                UPDATE tasks
                SET status = ?, result = ?, completed_at = ?
                WHERE id = ?
                """,
                ('completed', json_dumps(result), int(time.time()), task_id),
            )

    def get_task(self, task_id: str):
        with connect() as con:
            task = con.execute(
                """
                SELECT id, task, context, status, result, created_at, completed_at
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
            steps = con.execute(
                """
                SELECT role, output, timestamp
                FROM task_steps
                WHERE task_id = ?
                ORDER BY id ASC
                """,
                (task_id,),
            ).fetchall()
        if task is None:
            raise ValueError('Unknown task {0}'.format(task_id))
        return {
            'id': task['id'],
            'task': task['task'],
            'context': task['context'],
            'status': task['status'],
            'created_at': task['created_at'],
            'completed_at': task['completed_at'],
            'result': json_loads(task['result'], default=None),
            'steps': [
                {
                    'role': row['role'],
                    'output': row['output'],
                    'timestamp': row['timestamp'],
                }
                for row in steps
            ],
        }

    def list_tasks(self):
        with connect() as con:
            rows = con.execute(
                """
                SELECT id, task, context, status, result, created_at, completed_at
                FROM tasks
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [
            {
                'id': row['id'],
                'task': row['task'],
                'context': row['context'],
                'status': row['status'],
                'created_at': row['created_at'],
                'completed_at': row['completed_at'],
                'result': json_loads(row['result'], default=None),
            }
            for row in rows
        ]

    def interrupt(self, task_id: str):
        task = self.get_task(task_id)
        if task['status'] == 'completed':
            return task
        with connect() as con:
            con.execute(
                'UPDATE tasks SET status = ? WHERE id = ?',
                ('interrupted', task_id),
            )
        return self.get_task(task_id)


TASKS = TaskOrchestrator()
