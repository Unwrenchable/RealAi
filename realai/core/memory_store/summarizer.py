"""Conversation summarizer for periodic memory compression."""

import time
from typing import Any, Dict, List, Optional


class ConversationSummarizer:
    """Generate compact summary items every N messages."""

    def __init__(self, trigger_every: int = 6):
        self.trigger_every = max(1, int(trigger_every))
        self._counts: Dict[str, int] = {}

    def summarize_if_needed(self, user_id: str, messages: List[Dict[str, Any]], chat_backend) -> Optional[Dict[str, Any]]:
        self._counts[user_id] = self._counts.get(user_id, 0) + 1
        if self._counts[user_id] % self.trigger_every != 0:
            return None
        clipped = messages[-6:]
        text = " | ".join(str(msg.get("content", "")) for msg in clipped if isinstance(msg, dict))
        summary_prompt = [{"role": "system", "content": "Summarize briefly."}, {"role": "user", "content": text}]
        response = chat_backend.generate(summary_prompt)
        summary_text = response["choices"][0]["message"].get("content", "")[:400]
        return {
            "type": "summary",
            "content": summary_text,
            "timestamp": int(time.time()),
            "embedding": [],
        }
