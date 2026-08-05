"""
RealAI Unified Tool-Calling Protocol
=====================================
Provides ToolSchema, ToolRegistry, ToolCallValidator, and ToolCallOptimizer.

Usage::

    from realai.tools import TOOL_REGISTRY, ToolCallValidator

    tools = TOOL_REGISTRY.to_openai_format()
    result = ToolCallValidator().validate("web_research", {"query": "test"})
"""

from __future__ import annotations

import threading as _threading
import time as _time
from collections import deque as _deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSchema:
    """Schema definition for a callable tool.

    Attributes:
        name: Unique tool name.
        description: Human-readable description.
        parameters: JSON Schema object describing parameters.
        required: List of required parameter names.
        safety_level: One of "safe", "restricted", "dangerous".
        source: Origin tag — builtin | ability_catalog | plugin.
        ability_status: Catalog status when source is ability_catalog.
        live_path: Optional HTTP path associated with the ability.
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]
    safety_level: str = "safe"
    requires_confirmation: bool = False
    rate_limit_rpm: int = 60
    source: str = "builtin"
    ability_status: str = ""
    live_path: Optional[str] = None


@dataclass
class ValidationResult:
    """Result from a tool call validation.

    Attributes:
        valid: Whether the call is valid.
        errors: List of error messages.
    """
    valid: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class ToolExecutionRecord:
    """Record of a single tool execution for audit purposes.

    Attributes:
        tool_name: Name of the executed tool.
        input_summary: Truncated string representation of inputs.
        output_summary: Truncated string representation of outputs.
        started_at: Unix timestamp when execution began.
        duration_ms: Execution time in milliseconds.
        status: One of "success", "error", "timeout", "rate_limited".
        error: Optional error message if status != "success".
    """

    tool_name: str
    input_summary: str
    output_summary: str
    started_at: float
    duration_ms: float
    status: str  # "success", "error", "timeout", "rate_limited"
    error: Optional[str] = None


class ToolRegistry:
    """Singleton registry of all available tools.

    Register tools with register(), retrieve with get(), and export
    to OpenAI format with to_openai_format().
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: Dict[str, ToolSchema] = {}
        self._catalog_loaded: bool = False
        self._catalog_load_error: Optional[str] = None

    def register(self, schema: ToolSchema) -> None:
        """Register a tool schema.

        Args:
            schema: The ToolSchema to register.
        """
        self._tools[schema.name] = schema

    def get(self, name: str) -> Optional[ToolSchema]:
        """Retrieve a tool schema by name.

        Args:
            name: Tool name to look up.

        Returns:
            ToolSchema or None if not found.
        """
        self.ensure_ability_catalog_loaded()
        return self._tools.get(name)

    def list_all(self) -> List[ToolSchema]:
        """Return all registered tool schemas.

        Returns:
            List of all ToolSchema objects.
        """
        self.ensure_ability_catalog_loaded()
        return list(self._tools.values())

    def list_by_source(self, source: str) -> List[ToolSchema]:
        """Return tools matching a source tag."""
        if not self._catalog_loaded:
            self.ensure_ability_catalog_loaded()
        return [t for t in self._tools.values() if t.source == source]

    def to_openai_format(self, *, include_catalog: bool = True) -> List[Dict[str, Any]]:
        """Export tools in OpenAI tools array format.

        Args:
            include_catalog: When False, only builtin/plugin tools (not ability.*).

        Returns:
            List of tool dicts compatible with OpenAI API.
        """
        if not self._catalog_loaded:
            self.ensure_ability_catalog_loaded()
        result = []
        for schema in self._tools.values():
            if not include_catalog and schema.source == "ability_catalog":
                continue
            result.append({
                "type": "function",
                "function": {
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": schema.parameters,
                },
            })
        return result

    def ensure_ability_catalog_loaded(self, force: bool = False) -> Dict[str, Any]:
        """Load RUNDOWN abilities from ability_catalog into the registry once.

        Does not overwrite existing builtin tool names. Catalog entries are
        registered as ``ability.<id>`` so agents/tools can discover them.

        Returns:
            Status dict with counts / errors.
        """
        if self._catalog_loaded and not force:
            return {
                "loaded": True,
                "count": sum(1 for t in self._tools.values() if t.source == "ability_catalog"),
                "error": self._catalog_load_error,
            }
        return self.load_ability_catalog(force=force)

    def load_ability_catalog(self, force: bool = False) -> Dict[str, Any]:
        """Import ability_catalog.RUNDOWN_ABILITIES as discoverable tools."""
        import logging
        import os

        log = logging.getLogger("realai.tools")
        # Optional disable
        if os.environ.get("REALAI_LOAD_ABILITY_CATALOG", "1").strip() in (
            "0", "false", "False", "no",
        ):
            self._catalog_loaded = True
            self._catalog_load_error = "disabled_by_env"
            return {"loaded": False, "count": 0, "error": "disabled_by_env"}

        if self._catalog_loaded and not force:
            return {
                "loaded": True,
                "count": sum(1 for t in self._tools.values() if t.source == "ability_catalog"),
                "error": self._catalog_load_error,
            }

        registered = 0
        skipped = 0
        try:
            from realai.ability_catalog import RUNDOWN_ABILITIES

            # Prefer enriched statuses when build_catalog is cheap enough
            abilities = list(RUNDOWN_ABILITIES)
            try:
                from realai.ability_catalog import build_catalog

                cat = build_catalog()
                if cat.get("abilities"):
                    abilities = cat["abilities"]
            except Exception as enrich_err:
                log.debug("ability_catalog enrich soft-fail: %s", enrich_err)

            for entry in abilities:
                aid = str(entry.get("id") or "").strip()
                if not aid:
                    skipped += 1
                    continue
                name = f"ability.{aid}"
                # Never clobber builtins
                existing = self._tools.get(name)
                if existing and existing.source != "ability_catalog" and not force:
                    skipped += 1
                    continue
                status = str(entry.get("status") or "UNKNOWN").upper()
                # Map catalog status → safety
                if status in ("MISSING", "STUB"):
                    safety = "restricted"
                elif status in ("GOLD", "CODE"):
                    safety = "restricted"
                else:
                    safety = "safe"
                desc = (
                    f"[ability_catalog:{status}] {entry.get('name') or aid}. "
                    f"Pillar={entry.get('pillar') or 'n/a'}. "
                    f"Live={entry.get('live_path') or 'n/a'}."
                )
                schema = ToolSchema(
                    name=name,
                    description=desc[:500],
                    parameters={
                        "type": "object",
                        "properties": {
                            "input": {
                                "type": "string",
                                "description": "Natural-language input for this ability.",
                            },
                            "context": {
                                "type": "object",
                                "description": "Optional structured context from the host.",
                            },
                        },
                    },
                    required=[],
                    safety_level=safety,
                    requires_confirmation=status in ("MISSING", "STUB", "GOLD"),
                    source="ability_catalog",
                    ability_status=status,
                    live_path=entry.get("live_path"),
                )
                self.register(schema)
                registered += 1

            self._catalog_loaded = True
            self._catalog_load_error = None
            log.info(
                "ability_catalog loaded into TOOL_REGISTRY: registered=%s skipped=%s",
                registered,
                skipped,
            )
            return {
                "loaded": True,
                "registered": registered,
                "skipped": skipped,
                "total_tools": len(self._tools),
                "error": None,
            }
        except Exception as e:
            self._catalog_loaded = True  # avoid tight retry loops
            self._catalog_load_error = str(e)
            log.warning("ability_catalog load failed (soft): %s", e)
            return {
                "loaded": False,
                "registered": registered,
                "skipped": skipped,
                "error": str(e),
            }

    def catalog_status(self) -> Dict[str, Any]:
        """Return load status for diagnostics."""
        self.ensure_ability_catalog_loaded()
        catalog_tools = [t for t in self._tools.values() if t.source == "ability_catalog"]
        by_status: Dict[str, int] = {}
        for t in catalog_tools:
            by_status[t.ability_status or "UNKNOWN"] = by_status.get(t.ability_status or "UNKNOWN", 0) + 1
        return {
            "catalog_loaded": self._catalog_loaded,
            "catalog_error": self._catalog_load_error,
            "ability_tool_count": len(catalog_tools),
            "builtin_count": sum(1 for t in self._tools.values() if t.source == "builtin"),
            "total": len(self._tools),
            "by_status": by_status,
        }


class ToolCallValidator:
    """Validates tool calls against registered schemas.

    Checks tool existence, required fields, and type matching.
    """

    _TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    def validate(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ValidationResult:
        """Validate a tool call.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments dict for the call.

        Returns:
            ValidationResult with valid flag and errors list.
        """
        errors = []
        schema = TOOL_REGISTRY.get(tool_name)
        if schema is None:
            return ValidationResult(valid=False, errors=["Unknown tool: {0}".format(tool_name)])

        # Guardian policy (advisory by default; hard_block via REALAI_GUARDIAN_MODE)
        try:
            from realai.guardian import check_tool_call

            g = check_tool_call(tool_name, arguments, schema)
            if not g.get("allowed", True):
                return ValidationResult(
                    valid=False,
                    errors=g.get("errors") or ["Blocked by guardian"],
                )
            if g.get("warnings"):
                # Non-fatal — surface as errors only in hard mode (already handled)
                pass
        except Exception:
            pass

        # Check required fields
        for req in schema.required:
            if req not in arguments:
                errors.append("Missing required field: {0}".format(req))

        # Check types
        props = schema.parameters.get("properties", {})
        for arg_name, arg_value in arguments.items():
            if arg_name in props:
                expected_type = props[arg_name].get("type")
                if expected_type and expected_type in self._TYPE_MAP:
                    expected = self._TYPE_MAP[expected_type]
                    if not isinstance(arg_value, expected):
                        errors.append(
                            "Field '{0}' expected {1}, got {2}".format(
                                arg_name, expected_type, type(arg_value).__name__
                            )
                        )

        return ValidationResult(valid=len(errors) == 0, errors=errors)


class ToolCallOptimizer:
    """Optimizes batches of tool calls.

    Provides deduplication and parallel batching.
    """

    def deduplicate(self, calls: List[Dict]) -> List[Dict]:
        """Remove exact-duplicate tool calls.

        Args:
            calls: List of tool call dicts.

        Returns:
            Deduplicated list preserving order.
        """
        seen = set()
        result = []
        for call in calls:
            # Serialize to a stable string for comparison
            key = (call.get("name", ""), str(sorted(call.get("arguments", {}).items())))
            if key not in seen:
                seen.add(key)
                result.append(call)
        return result

    def batch_parallel(self, calls: List[Dict]) -> List[List[Dict]]:
        """Group independent calls into parallel batches.

        Currently groups all calls into a single batch (conservative approach
        — no dependency analysis).

        Args:
            calls: List of tool call dicts.

        Returns:
            List of batches, each batch is a list of independent calls.
        """
        if not calls:
            return []
        # Simple strategy: each unique tool name gets its own group
        groups: Dict[str, List[Dict]] = {}
        for call in calls:
            name = call.get("name", "unknown")
            if name not in groups:
                groups[name] = []
            groups[name].append(call)
        return list(groups.values())


class SecureToolExecutor:
    """Secure executor for tool calls with rate limiting, confirmation, timeout, and audit trail.

    Enforces per-tool rate limits, optional human-in-the-loop confirmation,
    execution timeouts, and retry with exponential backoff. All executions
    are recorded in an audit log accessible via get_audit_log().
    """

    def __init__(
        self,
        registry: ToolRegistry,
        timeout_secs: int = 30,
        max_retries: int = 3,
    ) -> None:
        """Initialize the executor.

        Args:
            registry: ToolRegistry to validate tools against.
            timeout_secs: Maximum seconds to wait per execution attempt.
            max_retries: Maximum retry attempts on transient errors.
        """
        self._registry = registry
        self._timeout_secs = timeout_secs
        self._max_retries = max_retries
        self._audit_log: List[ToolExecutionRecord] = []
        # Maps tool_name -> deque of timestamps (float) for sliding-window rate limit
        self._rate_limit_tracker: Dict[str, _deque] = {}

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        handler: Callable[..., Any],
        confirm_callback: Optional[Callable[[str, Dict], bool]] = None,
    ) -> Dict[str, Any]:
        """Execute a tool call with validation, rate limiting, confirmation, and retry.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments dict for the tool.
            handler: Callable that actually executes the tool. Called with **arguments.
            confirm_callback: Optional callable(tool_name, arguments) -> bool.
                If the tool requires confirmation and this is not provided or returns
                False, execution is skipped.

        Returns:
            Dict with at minimum: {"status": "success"|"error"|"timeout"|"rate_limited", ...}
        """
        started_at = _time.time()

        # --- Validate ---
        validator = ToolCallValidator()
        vr = validator.validate(tool_name, arguments)
        if not vr.valid:
            record = ToolExecutionRecord(
                tool_name=tool_name,
                input_summary=str(arguments)[:200],
                output_summary="",
                started_at=started_at,
                duration_ms=0.0,
                status="error",
                error="Validation failed: " + "; ".join(vr.errors),
            )
            self._audit_log.append(record)
            return {"status": "error", "error": record.error}

        schema = self._registry.get(tool_name)

        # --- Rate limit ---
        if schema is not None:
            limit_rpm = schema.rate_limit_rpm
            now = _time.time()
            if tool_name not in self._rate_limit_tracker:
                self._rate_limit_tracker[tool_name] = _deque()
            window = self._rate_limit_tracker[tool_name]
            # Evict timestamps older than 60 s
            cutoff = now - 60.0
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= limit_rpm:
                record = ToolExecutionRecord(
                    tool_name=tool_name,
                    input_summary=str(arguments)[:200],
                    output_summary="",
                    started_at=started_at,
                    duration_ms=(_time.time() - started_at) * 1000,
                    status="rate_limited",
                    error="Rate limit exceeded ({0} rpm)".format(limit_rpm),
                )
                self._audit_log.append(record)
                return {"status": "rate_limited", "error": record.error}

        # --- Confirmation ---
        if schema is not None and schema.requires_confirmation:
            if confirm_callback is None or not confirm_callback(tool_name, arguments):
                record = ToolExecutionRecord(
                    tool_name=tool_name,
                    input_summary=str(arguments)[:200],
                    output_summary="",
                    started_at=started_at,
                    duration_ms=(_time.time() - started_at) * 1000,
                    status="error",
                    error="Execution requires confirmation but was not confirmed.",
                )
                self._audit_log.append(record)
                return {"status": "error", "error": record.error}

        # --- Execute with retry + timeout ---
        last_error: Optional[str] = None
        result: Dict[str, Any] = {}
        timed_out = False

        for attempt in range(self._max_retries):
            timed_out = False
            outcome: Dict[str, Any] = {}
            exc_holder: List[Optional[Exception]] = [None]

            def _run() -> None:
                try:
                    outcome["result"] = handler(**arguments)
                except Exception as exc:
                    exc_holder[0] = exc

            thread = _threading.Thread(target=_run, daemon=True)
            thread.start()
            thread.join(timeout=self._timeout_secs)

            if thread.is_alive():
                timed_out = True
                last_error = "Execution timed out after {0}s".format(self._timeout_secs)
            elif exc_holder[0] is not None:
                last_error = str(exc_holder[0])
            else:
                result = outcome.get("result") or {}
                if not isinstance(result, dict):
                    result = {"output": result}
                break

            # Exponential backoff before retry (skip on last attempt)
            if attempt < self._max_retries - 1:
                _time.sleep(0.1 * (2 ** attempt))

        # --- Record outcome ---
        if timed_out:
            status = "timeout"
            error_msg: Optional[str] = last_error
        elif last_error and not result:
            status = "error"
            error_msg = last_error
        else:
            status = "success"
            error_msg = None

        duration_ms = (_time.time() - started_at) * 1000

        # Update rate-limit window on success/error (not on rate_limited)
        if schema is not None:
            self._rate_limit_tracker.setdefault(tool_name, _deque())
            self._rate_limit_tracker[tool_name].append(_time.time())

        record = ToolExecutionRecord(
            tool_name=tool_name,
            input_summary=str(arguments)[:200],
            output_summary=str(result)[:200],
            started_at=started_at,
            duration_ms=duration_ms,
            status=status,
            error=error_msg,
        )
        self._audit_log.append(record)

        if status == "success":
            result["status"] = "success"
            return result
        return {"status": status, "error": error_msg}

    def get_audit_log(self) -> List[ToolExecutionRecord]:
        """Return all execution records.

        Returns:
            List of ToolExecutionRecord objects, oldest first.
        """
        return list(self._audit_log)

    def get_rate_limit_status(self, tool_name: str) -> Dict[str, Any]:
        """Return the current rate-limit status for a tool.

        Args:
            tool_name: Tool to check.

        Returns:
            Dict with keys: tool_name, calls_this_minute, limit_rpm, available.
        """
        schema = self._registry.get(tool_name)
        limit_rpm = schema.rate_limit_rpm if schema else 60

        window = self._rate_limit_tracker.get(tool_name)
        if window:
            cutoff = _time.time() - 60.0
            calls = sum(1 for ts in window if ts >= cutoff)
        else:
            calls = 0

        return {
            "tool_name": tool_name,
            "calls_this_minute": calls,
            "limit_rpm": limit_rpm,
            "available": calls < limit_rpm,
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

TOOL_REGISTRY = ToolRegistry()

# ---------------------------------------------------------------------------
# Built-in tool registrations
# ---------------------------------------------------------------------------

TOOL_REGISTRY.register(ToolSchema(
    name="web_research",
    description="Search the web for information on a given query.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "max_results": {"type": "integer", "description": "Maximum results to return."},
        },
    },
    required=["query"],
    safety_level="safe",
))

TOOL_REGISTRY.register(ToolSchema(
    name="execute_code",
    description="Execute a code snippet in a sandboxed environment.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Code to execute."},
            "language": {"type": "string", "description": "Programming language."},
        },
    },
    required=["code"],
    safety_level="restricted",
))

TOOL_REGISTRY.register(ToolSchema(
    name="generate_image",
    description="Generate an image from a text prompt.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Image generation prompt."},
            "size": {"type": "string", "description": "Image dimensions, e.g. 1024x1024."},
        },
    },
    required=["prompt"],
    safety_level="safe",
))

TOOL_REGISTRY.register(ToolSchema(
    name="translate",
    description="Translate text to a target language.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate."},
            "target_language": {"type": "string", "description": "Target language code."},
        },
    },
    required=["text", "target_language"],
    safety_level="safe",
))

TOOL_REGISTRY.register(ToolSchema(
    name="transcribe_audio",
    description="Transcribe audio from a file path or URL.",
    parameters={
        "type": "object",
        "properties": {
            "audio_path": {"type": "string", "description": "Path or URL to audio file."},
            "language": {"type": "string", "description": "Optional language hint."},
        },
    },
    required=["audio_path"],
    safety_level="safe",
    source="builtin",
))

# Auto-load ability catalog at import (soft-fail). Does not replace builtins.
try:
    TOOL_REGISTRY.ensure_ability_catalog_loaded()
except Exception:
    pass
