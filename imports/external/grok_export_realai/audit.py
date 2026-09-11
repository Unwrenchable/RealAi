"""
RealAI Audit, Compliance, and Observability
=============================================
Provides thread-safe audit logging, AES-256 data encryption, per-user consent
management, sliding-window rate limiting, and system observability metrics.

Usage::

    from realai.audit import AUDIT_LOGGER, CONSENT_MANAGER, RATE_LIMITER, OBSERVABILITY
    from realai.audit import AuditEvent, DataEncryption

    # Log an event
    event = AuditEvent(
        event_id="evt-1", timestamp=time.time(), user_id="alice",
        action_type="chat", resource="/v1/chat/completions",
        input_hash=DataEncryption.hash_data("hello"),
        output_hash=DataEncryption.hash_data("world"),
        status="success", duration_ms=120.0,
    )
    AUDIT_LOGGER.log(event)

    # Check consent
    CONSENT_MANAGER.grant_consent("alice", "memory")
    assert CONSENT_MANAGER.has_consent("alice", "memory")
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AuditEvent:
    """A single immutable audit log event.

    Attributes:
        event_id: Unique event identifier (UUID recommended).
        timestamp: Unix timestamp of the event.
        user_id: Identifier of the user who triggered the event.
        action_type: Category of the action (e.g. "chat", "tool_call").
        resource: Resource path or name being acted on.
        input_hash: SHA-256 hash of the input data.
        output_hash: SHA-256 hash of the output data.
        status: Outcome — "success", "error", "timeout", "rate_limited".
        duration_ms: Wall-clock execution time in milliseconds.
        metadata: Optional dict of additional key-value metadata.
    """

    event_id: str
    timestamp: float
    user_id: str
    action_type: str
    resource: str
    input_hash: str
    output_hash: str
    status: str
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the event to a plain dict.

        Returns:
            Dict representation of the event.
        """
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "resource": self.resource,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Deserialize an event from a plain dict.

        Args:
            data: Dict previously returned by to_dict().

        Returns:
            AuditEvent instance.
        """
        return cls(
            event_id=data.get("event_id", ""),
            timestamp=float(data.get("timestamp", 0.0)),
            user_id=data.get("user_id", ""),
            action_type=data.get("action_type", ""),
            resource=data.get("resource", ""),
            input_hash=data.get("input_hash", ""),
            output_hash=data.get("output_hash", ""),
            status=data.get("status", ""),
            duration_ms=float(data.get("duration_ms", 0.0)),
            metadata=data.get("metadata", {}),
        )


class AuditLogger:
    """Thread-safe JSONL audit logger with automatic file rotation.

    Each event is written as a single JSON line. The log is rotated when
    the file exceeds max_bytes by renaming it with a `.N` suffix.
    """

    def __init__(
        self,
        log_path: str = "realai/audit_log.jsonl",
        max_bytes: int = 10_000_000,
    ) -> None:
        """Initialize the logger.

        Args:
            log_path: Path to the JSONL log file. Parent dirs are created
                automatically.
            max_bytes: Maximum file size in bytes before rotation (default 10 MB).
        """
        self._log_path = log_path
        self._max_bytes = max_bytes
        self._lock = threading.Lock()
        try:
            os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        except Exception:
            pass

    def log(self, event: AuditEvent) -> None:
        """Append an event to the log file.

        No-ops silently on any I/O error.

        Args:
            event: AuditEvent to log.
        """
        with self._lock:
            try:
                self._rotate_if_needed()
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event.to_dict()) + "\n")
            except Exception:
                pass

    def read_events(self, limit: int = 100) -> List[AuditEvent]:
        """Read the most recent events from the log.

        Args:
            limit: Maximum number of events to return (newest last).

        Returns:
            List of AuditEvent objects. Empty list if file absent or unreadable.
        """
        with self._lock:
            events: List[AuditEvent] = []
            try:
                if not os.path.isfile(self._log_path):
                    return events
                with open(self._log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for line in lines[-limit:]:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            events.append(AuditEvent.from_dict(data))
                        except Exception:
                            pass
            except Exception:
                pass
            return events

    def _rotate_if_needed(self) -> None:
        """Rotate the log file if it exceeds max_bytes.

        The current file is renamed to ``<path>.1``; existing ``.1`` is
        renamed to ``.2``, and so on up to ``.5`` (oldest discarded).
        """
        try:
            if not os.path.isfile(self._log_path):
                return
            size = os.path.getsize(self._log_path)
            if size < self._max_bytes:
                return
            # Rotate: .4 -> .5, .3 -> .4, ..., current -> .1
            for i in range(4, 0, -1):
                src = "{0}.{1}".format(self._log_path, i)
                dst = "{0}.{1}".format(self._log_path, i + 1)
                if os.path.isfile(src):
                    try:
                        os.rename(src, dst)
                    except Exception:
                        pass
            try:
                os.rename(self._log_path, self._log_path + ".1")
            except Exception:
                pass
        except Exception:
            pass


class DataEncryption:
    """AES-256 encryption with base64 fallback when cryptography is unavailable.

    When the ``cryptography`` package is installed, uses AES-256-CBC with a
    random IV. Falls back to base64 encoding (obfuscation only) when not
    available, so callers never need to handle ImportError.
    """

    def __init__(self, key: Optional[bytes] = None) -> None:
        """Initialize with an optional encryption key.

        Args:
            key: 32-byte AES key. If None, a random key is generated.
        """
        if key is None:
            key = os.urandom(32)
        self._key = key[:32].ljust(32, b"\x00")  # Ensure exactly 32 bytes

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string.

        Args:
            plaintext: UTF-8 string to encrypt.

        Returns:
            Encrypted string (AES-CBC + base64 when cryptography available,
            plain base64 fallback otherwise).
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            import base64

            iv = os.urandom(16)
            # Pad to block boundary
            data = plaintext.encode("utf-8")
            pad_len = 16 - len(data) % 16
            data += bytes([pad_len] * pad_len)

            cipher = Cipher(
                algorithms.AES(self._key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            enc = cipher.encryptor()
            ct = enc.update(data) + enc.finalize()
            return base64.b64encode(iv + ct).decode("ascii")
        except ImportError:
            import base64
            return base64.b64encode(plaintext.encode("utf-8")).decode("ascii")
        except Exception:
            import base64
            return base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string previously encrypted by encrypt().

        Args:
            ciphertext: Encrypted string from encrypt().

        Returns:
            Decrypted UTF-8 string, or the ciphertext on any error.
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            import base64

            raw = base64.b64decode(ciphertext.encode("ascii"))
            iv = raw[:16]
            ct = raw[16:]

            cipher = Cipher(
                algorithms.AES(self._key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            dec = cipher.decryptor()
            padded = dec.update(ct) + dec.finalize()
            pad_len = padded[-1]
            return padded[:-pad_len].decode("utf-8")
        except ImportError:
            import base64
            try:
                return base64.b64decode(ciphertext.encode("ascii")).decode("utf-8")
            except Exception:
                return ciphertext
        except Exception:
            return ciphertext

    @staticmethod
    def hash_data(data: str) -> str:
        """Return the SHA-256 hex digest of a string.

        Args:
            data: Input string.

        Returns:
            64-character hex string.
        """
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


class ConsentManager:
    """Tracks per-user consent for memory, tools, and data retention.

    Consent state is persisted to a JSON file. Changes are written
    immediately after every grant/revoke operation.
    """

    def __init__(self, storage_path: str = "realai/consent_store.json") -> None:
        """Initialize and load existing consent data.

        Args:
            storage_path: Path to the JSON persistence file.
                Parent directories are created automatically.
        """
        self._storage_path = storage_path
        self._lock = threading.Lock()
        # consent_store: {user_id: set of scope strings}
        self._store: Dict[str, List[str]] = {}
        self._load()

    def grant_consent(self, user_id: str, scope: str) -> None:
        """Grant consent for a user+scope pair.

        Args:
            user_id: User identifier.
            scope: Consent scope (e.g. "memory", "tools", "data_retention").
        """
        with self._lock:
            if user_id not in self._store:
                self._store[user_id] = []
            if scope not in self._store[user_id]:
                self._store[user_id].append(scope)
            self._save()

    def revoke_consent(self, user_id: str, scope: str) -> None:
        """Revoke consent for a user+scope pair.

        Args:
            user_id: User identifier.
            scope: Consent scope to revoke.
        """
        with self._lock:
            if user_id in self._store:
                self._store[user_id] = [
                    s for s in self._store[user_id] if s != scope
                ]
            self._save()

    def has_consent(self, user_id: str, scope: str) -> bool:
        """Check whether a user has granted consent for a scope.

        Args:
            user_id: User identifier.
            scope: Consent scope to check.

        Returns:
            True if consent is granted, False otherwise.
        """
        return scope in self._store.get(user_id, [])

    def get_user_consents(self, user_id: str) -> List[str]:
        """Return all consented scopes for a user.

        Args:
            user_id: User identifier.

        Returns:
            List of granted scope strings.
        """
        return list(self._store.get(user_id, []))

    def _save(self) -> None:
        """Persist consent data to disk. No-ops on any error."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self._storage_path)), exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(self._store, f)
        except Exception:
            pass

    def _load(self) -> None:
        """Load consent data from disk. No-ops if file absent or invalid."""
        try:
            if not os.path.isfile(self._storage_path):
                return
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._store = {k: list(v) for k, v in data.items()}
        except Exception:
            pass


class RateLimiter:
    """Sliding-window rate limiter tracking requests and tokens per user.

    Uses separate deques for requests-per-minute (RPM) and tokens-per-minute
    (TPM) tracking. Limits are configurable per user; unspecified users share
    the default limits.
    """

    def __init__(
        self,
        default_rpm: int = 60,
        default_tpm: int = 100_000,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            default_rpm: Default requests per minute limit.
            default_tpm: Default tokens per minute limit.
        """
        self._default_rpm = default_rpm
        self._default_tpm = default_tpm
        self._request_times: Dict[str, Any] = {}
        self._token_counts: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _get_deque(self, mapping: Dict[str, Any], key: str) -> Any:
        """Get or create a deque for the given key."""
        from collections import deque
        if key not in mapping:
            mapping[key] = deque()
        return mapping[key]

    def check_rate_limit(self, user_id: str, tokens: int = 0) -> bool:
        """Check whether a request is within the rate limits.

        Args:
            user_id: User identifier.
            tokens: Number of tokens in this request (0 = no token check).

        Returns:
            True if the request is allowed, False if rate-limited.
        """
        with self._lock:
            now = time.time()
            cutoff = now - 60.0

            req_deque = self._get_deque(self._request_times, user_id)
            while req_deque and req_deque[0] < cutoff:
                req_deque.popleft()

            if len(req_deque) >= self._default_rpm:
                return False

            if tokens > 0:
                tok_deque = self._get_deque(self._token_counts, user_id)
                # Evict old token entries (stored as (timestamp, count) tuples)
                while tok_deque and tok_deque[0][0] < cutoff:
                    tok_deque.popleft()
                total_tokens = sum(t for _, t in tok_deque)
                if total_tokens + tokens > self._default_tpm:
                    return False

            return True

    def record_request(self, user_id: str, tokens: int = 0) -> None:
        """Record a completed request for rate tracking.

        Args:
            user_id: User identifier.
            tokens: Number of tokens consumed (0 = not tracking tokens).
        """
        with self._lock:
            now = time.time()
            req_deque = self._get_deque(self._request_times, user_id)
            req_deque.append(now)

            if tokens > 0:
                tok_deque = self._get_deque(self._token_counts, user_id)
                tok_deque.append((now, tokens))

    def get_status(self, user_id: str) -> Dict[str, Any]:
        """Return the current rate-limit status for a user.

        Args:
            user_id: User identifier.

        Returns:
            Dict with keys: user_id, requests_this_minute, rpm_limit, allowed.
        """
        with self._lock:
            now = time.time()
            cutoff = now - 60.0
            req_deque = self._get_deque(self._request_times, user_id)
            requests_this_minute = sum(1 for t in req_deque if t >= cutoff)
            return {
                "user_id": user_id,
                "requests_this_minute": requests_this_minute,
                "rpm_limit": self._default_rpm,
                "allowed": requests_this_minute < self._default_rpm,
            }


class ObservabilityDashboard:
    """Collects and reports system observability metrics.

    Thread-safe. Tracks per-provider request counts, latencies, token usage,
    and estimated costs.
    """

    def __init__(self) -> None:
        """Initialize with empty metrics."""
        self._requests: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_request(
        self,
        provider: str,
        duration_ms: float,
        tokens: int,
        cost: float,
        success: bool,
    ) -> None:
        """Record a completed request.

        Args:
            provider: Provider name.
            duration_ms: Latency in milliseconds.
            tokens: Number of tokens consumed.
            cost: Estimated cost in USD.
            success: Whether the request succeeded.
        """
        with self._lock:
            self._requests.append({
                "provider": provider,
                "duration_ms": duration_ms,
                "tokens": tokens,
                "cost": cost,
                "success": success,
                "timestamp": time.time(),
            })

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregated observability statistics.

        Returns:
            Dict with keys:
              - total_requests (int)
              - error_rate (float)
              - avg_latency_ms (float)
              - token_usage (int)
              - cost_estimate (float)
              - top_providers (Dict[str, int])
        """
        with self._lock:
            if not self._requests:
                return {
                    "total_requests": 0,
                    "error_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "token_usage": 0,
                    "cost_estimate": 0.0,
                    "top_providers": {},
                }

            total = len(self._requests)
            errors = sum(1 for r in self._requests if not r["success"])
            avg_latency = sum(r["duration_ms"] for r in self._requests) / total
            token_usage = sum(r["tokens"] for r in self._requests)
            cost_estimate = sum(r["cost"] for r in self._requests)

            provider_counts: Dict[str, int] = {}
            for r in self._requests:
                p = r["provider"]
                provider_counts[p] = provider_counts.get(p, 0) + 1

            # Sort top providers by count descending
            top_providers = dict(
                sorted(provider_counts.items(), key=lambda x: x[1], reverse=True)
            )

            return {
                "total_requests": total,
                "error_rate": round(errors / total, 4),
                "avg_latency_ms": round(avg_latency, 2),
                "token_usage": token_usage,
                "cost_estimate": round(cost_estimate, 6),
                "top_providers": top_providers,
            }


# ---------------------------------------------------------------------------
# Global singletons
# ---------------------------------------------------------------------------

AUDIT_LOGGER = AuditLogger()
CONSENT_MANAGER = ConsentManager()
RATE_LIMITER = RateLimiter()
OBSERVABILITY = ObservabilityDashboard()
