"""In-memory provider-grade memory abstractions."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List


def _tokenize(text: str):
    return [token for token in (text or '').lower().split() if token]


def _jaccard(a_tokens, b_tokens):
    a = set(a_tokens)
    b = set(b_tokens)
    if not a and not b:
        return 0.0
    return float(len(a & b)) / float(len(a | b))


@dataclass
class MemoryRecord:
    content: str
    summary: str = ''
    metadata: Dict[str, str] = field(default_factory=dict)


class MemoryStore(object):
    """Per-user/per-agent memory store with simple retrieval."""

    SUMMARY_WORD_LIMIT = 24

    def __init__(self):
        self._store = defaultdict(list)

    def _key(self, user_id: str, agent_id: str):
        return '{0}:{1}'.format(user_id or 'anonymous', agent_id or 'default')

    def add(self, user_id: str, agent_id: str, content: str, metadata=None):
        summary = ' '.join((content or '').split()[:self.SUMMARY_WORD_LIMIT])
        record = MemoryRecord(content=content or '', summary=summary, metadata=metadata or {})
        key = self._key(user_id, agent_id)
        self._store[key].append(record)
        return {
            'user_id': user_id or 'anonymous',
            'agent_id': agent_id or 'default',
            'index': len(self._store[key]) - 1,
            'summary': summary,
        }

    def list(self, user_id: str, agent_id: str):
        key = self._key(user_id, agent_id)
        return [
            {
                'index': index,
                'summary': record.summary,
                'content': record.content,
                'metadata': record.metadata,
            }
            for index, record in enumerate(self._store.get(key, []))
        ]

    def clear(self, user_id: str, agent_id: str):
        key = self._key(user_id, agent_id)
        count = len(self._store.get(key, []))
        if key in self._store:
            del self._store[key]
        return count

    def retrieve(self, user_id: str, agent_id: str, query: str, top_k: int = 3):
        key = self._key(user_id, agent_id)
        query_tokens = _tokenize(query)
        ranked = []
        for index, record in enumerate(self._store.get(key, [])):
            score = _jaccard(query_tokens, _tokenize(record.content))
            ranked.append((score, index, record))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                'index': index,
                'score': score,
                'summary': record.summary,
                'content': record.content,
                'metadata': record.metadata,
            }
            for score, index, record in ranked[:max(1, int(top_k))]
            if score > 0.0
        ]


MEMORY = MemoryStore()
