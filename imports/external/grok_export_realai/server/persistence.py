"""SQLite-backed persistence shared by structured server components."""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager


_INIT_LOCK = threading.Lock()
_INITIALIZED_PATH = None


def get_db_path():
    data_dir = os.environ.get('REALAI_DATA_DIR', os.path.expanduser('~/.realai'))
    return os.environ.get('REALAI_SERVER_DB_PATH', os.path.join(data_dir, 'server.sqlite3'))


def _ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def init_db():
    global _INITIALIZED_PATH

    db_path = get_db_path()
    with _INIT_LOCK:
        if _INITIALIZED_PATH == db_path and os.path.exists(db_path):
            return db_path

        _ensure_parent_dir(db_path)
        con = sqlite3.connect(db_path)
        try:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_records (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL,
                    agent_id    TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    summary     TEXT NOT NULL,
                    metadata    TEXT NOT NULL DEFAULT '{}',
                    created_at  INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memory_scope_created
                    ON memory_records(user_id, agent_id, created_at, id);

                CREATE TABLE IF NOT EXISTS tasks (
                    id            TEXT PRIMARY KEY,
                    task          TEXT NOT NULL,
                    context       TEXT NOT NULL DEFAULT '',
                    status        TEXT NOT NULL,
                    result        TEXT,
                    created_at    INTEGER NOT NULL,
                    completed_at  INTEGER
                );

                CREATE TABLE IF NOT EXISTS task_steps (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id     TEXT NOT NULL,
                    role        TEXT NOT NULL,
                    output      TEXT NOT NULL,
                    timestamp   INTEGER NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_task_steps_task
                    ON task_steps(task_id, id);
                """
            )
            con.commit()
        finally:
            con.close()

        _INITIALIZED_PATH = db_path
        return db_path


@contextmanager
def connect():
    init_db()
    con = sqlite3.connect(get_db_path())
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def json_dumps(value):
    return json.dumps(value if value is not None else {}, sort_keys=True)


def json_loads(value, default=None):
    if value in (None, ''):
        return {} if default is None else default
    try:
        return json.loads(value)
    except Exception:
        return {} if default is None else default
