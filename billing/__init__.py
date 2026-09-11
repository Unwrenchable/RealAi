"""
Billing and usage tracking system
Tracks API usage for metering, quotas, and future monetization
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class Provider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    REALAI = "realai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


@dataclass
class UsageEvent:
    """Single API usage event"""
    id: str
    user_id: str
    api_key_id: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "api_key_id": self.api_key_id,
            "provider": self.provider,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "timestamp": self.timestamp.isoformat(),
        }


class UsageTracker:
    """Track API usage for billing and analytics"""

    def __init__(self):
        self.events: List[UsageEvent] = []

    def log_usage(self, event: UsageEvent) -> None:
        """Log a usage event"""
        self.events.append(event)

    def get_usage_summary(
        self, user_id: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Get usage summary for a user in a time range"""
        filtered = [
            e for e in self.events
            if e.user_id == user_id
            and start_time <= e.timestamp <= end_time
        ]

        total_tokens_in = sum(e.tokens_in for e in filtered)
        total_tokens_out = sum(e.tokens_out for e in filtered)

        usage_by_provider = {}
        for event in filtered:
            if event.provider not in usage_by_provider:
                usage_by_provider[event.provider] = {
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "requests": 0,
                }
            usage_by_provider[event.provider]["tokens_in"] += event.tokens_in
            usage_by_provider[event.provider]["tokens_out"] += event.tokens_out
            usage_by_provider[event.provider]["requests"] += 1

        return {
            "user_id": user_id,
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_requests": len(filtered),
            "usage_by_provider": usage_by_provider,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }


# Global tracker instance
tracker = UsageTracker()
