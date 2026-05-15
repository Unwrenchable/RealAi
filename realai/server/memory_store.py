"""SQLite-backed provider-grade memory abstractions."""

import time
from typing import Dict, List

from .persistence import connect, json_dumps, json_loads


def _tokenize(text: str):
    return [token for token in (text or '').lower().split() if token]


def _jaccard(a_tokens, b_tokens):
    a = set(a_tokens)
    b = set(b_tokens)
    if not a and not b:
        return 0.0
    return float(len(a & b)) / float(len(a | b))


class MemoryStore(object):
    """Per-user/per-agent memory store with durable retrieval."""

    SUMMARY_WORD_LIMIT = 24

    def _scope(self, user_id: str, agent_id: str):
        return user_id or 'anonymous', agent_id or 'default'

    def add(self, user_id: str, agent_id: str, content: str, metadata=None):
        scoped_user, scoped_agent = self._scope(user_id, agent_id)
        summary = ' '.join((content or '').split()[:self.SUMMARY_WORD_LIMIT])
        created_at = int(time.time())
        with connect() as con:
            cur = con.execute(
                """
                INSERT INTO memory_records (user_id, agent_id, content, summary, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    scoped_user,
                    scoped_agent,
                    content or '',
                    summary,
                    json_dumps(metadata or {}),
                    created_at,
                ),
            )
        return {
            'id': cur.lastrowid,
            'user_id': scoped_user,
            'agent_id': scoped_agent,
            'summary': summary,
            'created_at': created_at,
        }

    def list(self, user_id: str, agent_id: str):
        scoped_user, scoped_agent = self._scope(user_id, agent_id)
        with connect() as con:
            rows = con.execute(
                """
                SELECT id, summary, content, metadata, created_at
                FROM memory_records
                WHERE user_id = ? AND agent_id = ?
                ORDER BY id ASC
                """,
                (scoped_user, scoped_agent),
            ).fetchall()
        return [
            {
                'id': row['id'],
                'index': index,
                'summary': row['summary'],
                'content': row['content'],
                'metadata': json_loads(row['metadata']),
                'created_at': row['created_at'],
            }
            for index, row in enumerate(rows)
        ]

    def clear(self, user_id: str, agent_id: str):
        scoped_user, scoped_agent = self._scope(user_id, agent_id)
        with connect() as con:
            cur = con.execute(
                'DELETE FROM memory_records WHERE user_id = ? AND agent_id = ?',
                (scoped_user, scoped_agent),
            )
        return cur.rowcount

    def retrieve(self, user_id: str, agent_id: str, query: str, top_k: int = 3):
        query_tokens = _tokenize(query)
        ranked = []
        for item in self.list(user_id, agent_id):
            haystack = '{0} {1}'.format(item.get('summary', ''), item.get('content', ''))
            score = _jaccard(query_tokens, _tokenize(haystack))
            ranked.append((score, item))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                'id': item['id'],
                'index': item['index'],
                'score': score,
                'summary': item['summary'],
                'content': item['content'],
                'metadata': item['metadata'],
                'created_at': item['created_at'],
            }
            for score, item in ranked[:max(1, int(top_k))]
            if score > 0.0
        ]


MEMORY = MemoryStore()
