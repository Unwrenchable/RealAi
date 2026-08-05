import json
import os
import sqlite3
from typing import Optional, Dict, Any, List

DB_PATH = os.environ.get("REALAI_MEMORY_DB", "realai_memory.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          external_id TEXT UNIQUE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          profile_json TEXT
        );

        CREATE TABLE IF NOT EXISTS interactions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          session_id TEXT,
          input_text TEXT,
          output_text TEXT,
          models_used_json TEXT,
          tools_used_json TEXT,
          meta_json TEXT,
          FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          interaction_id INTEGER NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          rating INTEGER,
          comment TEXT,
          FOREIGN KEY (interaction_id) REFERENCES interactions(id)
        );
        """
    )
    conn.commit()
    conn.close()


def get_or_create_user(external_id: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE external_id = ?", (external_id,))
    row = cur.fetchone()
    if row:
        conn.close()
        return row["id"]

    cur.execute(
        "INSERT INTO users (external_id, profile_json) VALUES (?, ?)",
        (external_id, json.dumps({})),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def update_user_profile(user_id: int, profile_updates: Dict[str, Any]):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT profile_json FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    current = json.loads(row["profile_json"] or "{}")
    current.update(profile_updates)
    cur.execute(
        "UPDATE users SET profile_json = ? WHERE id = ?",
        (json.dumps(current), user_id),
    )
    conn.commit()
    conn.close()


def log_interaction(
    user_id: int,
    session_id: str,
    input_text: str,
    output_text: str,
    models_used: List[str],
    tools_used: List[str],
    meta: Optional[Dict[str, Any]] = None,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO interactions (
          user_id, session_id, input_text, output_text,
          models_used_json, tools_used_json, meta_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            session_id,
            input_text,
            output_text,
            json.dumps(models_used or []),
            json.dumps(tools_used or []),
            json.dumps(meta or {}),
        ),
    )
    conn.commit()
    interaction_id = cur.lastrowid
    conn.close()
    return interaction_id


def add_feedback(interaction_id: int, rating: int, comment: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO feedback (interaction_id, rating, comment) VALUES (?, ?, ?)",
        (interaction_id, rating, comment),
    )
    conn.commit()
    conn.close()


def get_user_profile(user_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT profile_json FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    return json.loads(row["profile_json"] or "{}")
