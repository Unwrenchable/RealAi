"""Robust tool execution engine with retries and dependency handling."""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.logging.logger import log
from core.security.python_sandbox import PythonSandbox
from core.tracing.tracer import tracer
from core.tools.credentials import ToolCredentialManager


@dataclass
class ToolExecutionRequest:
    """A single tool execution request."""

    tool_name: str
    arguments: Dict[str, Any]
    request_id: str = ""
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = str(uuid.uuid4())


@dataclass
class ToolExecutionResult:
    """Structured result for a tool execution."""

    request_id: str
    tool_name: str
    status: str
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    attempts: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0
    duration_ms: float = 0.0
    rolled_back: bool = False
    dependencies: List[str] = field(default_factory=list)
    sandboxed: bool = False
    sandbox_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the execution result."""
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "output": dict(self.output),
            "error": self.error,
            "attempts": self.attempts,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "rolled_back": self.rolled_back,
            "dependencies": list(self.dependencies),
            "sandboxed": self.sandboxed,
            "sandbox_type": self.sandbox_type,
        }


@dataclass
class ToolExecutionAuditRecord:
    """Audit record for a tool execution attempt."""

    request_id: str
    tool_name: str
    status: str
    started_at: float
    duration_ms: float
    attempts: int
    rolled_back: bool = False
    error: Optional[str] = None
    input_summary: str = ""
    output_summary: str = ""
    credentials: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    sandboxed: bool = False
    sandbox_type: str = ""


class ToolExecutionEngine:
    """Execute tools with permission checks, retries, rollback, and DAG scheduling."""

    def __init__(
        self,
        timeout_seconds: int = 5,
        max_retries: int = 2,
        max_parallel: int = 4,
        credential_manager: ToolCredentialManager = None,
    ) -> None:
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.max_retries = max(0, int(max_retries))
        self.max_parallel = max(1, int(max_parallel))
        self.credential_manager = credential_manager or ToolCredentialManager()
        self._audit_log: List[ToolExecutionAuditRecord] = []

    def get_audit_log(self) -> List[ToolExecutionAuditRecord]:
        """Return recorded execution audit events."""
        return list(self._audit_log)

    def _safe_dict_copy(self, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Return a defensive copy of a dictionary-like value."""
        return dict(value or {})

    def execute_tool(
        self,
        tool_name: str,
        tool: Any,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> ToolExecutionResult:
        """Execute one tool request."""
        with tracer.start_as_current_span("tool.execute.{0}".format(tool_name)):
            request = ToolExecutionRequest(
                tool_name=tool_name,
                arguments=self._safe_dict_copy(arguments),
                request_id=request_id or "",
                depends_on=list(dependencies or []),
                timeout_seconds=self._tool_timeout(tool),
                max_retries=self._tool_retries(tool),
            )
            runtime_context = self._prepare_context(tool_name, context)
            self._validate_permissions(tool, runtime_context)
            return self._run_request(request, tool, runtime_context)

    def execute_plan(
        self,
        requests: List[ToolExecutionRequest],
        tools: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, ToolExecutionResult]:
        """Execute a dependency-aware batch of tool requests."""
        pending = {request.request_id: request for request in requests}
        results: Dict[str, ToolExecutionResult] = {}
        shared_context = self._safe_dict_copy(context)

        while pending:
            ready: List[ToolExecutionRequest] = []
            for request_id, request in list(pending.items()):
                dependency_results = [results.get(dep) for dep in request.depends_on]
                if any(dep_result is None for dep_result in dependency_results):
                    continue
                failed_dep = next(
                    (dep_result for dep_result in dependency_results if dep_result.status != "success"),
                    None,
                )
                if failed_dep is not None:
                    result = self._dependency_failure_result(request, failed_dep)
                    results[request_id] = result
                    pending.pop(request_id, None)
                    self._record_audit(result, request.arguments, [])
                    continue
                ready.append(request)

            if not ready:
                for request_id, request in list(pending.items()):
                    result = ToolExecutionResult(
                        request_id=request.request_id,
                        tool_name=request.tool_name,
                        status="dependency_failed",
                        error="Unresolved tool dependencies",
                        attempts=0,
                        started_at=time.time(),
                        finished_at=time.time(),
                        duration_ms=0.0,
                        dependencies=list(request.depends_on),
                    )
                    results[request_id] = result
                    pending.pop(request_id, None)
                    self._record_audit(result, request.arguments, [])
                break

            with ThreadPoolExecutor(max_workers=min(self.max_parallel, len(ready))) as pool:
                futures = {}
                for request in ready:
                    tool = tools[request.tool_name]
                    dependency_outputs = {
                        dep: results[dep].output
                        for dep in request.depends_on
                        if dep in results
                    }
                    runtime_context = self._safe_dict_copy(shared_context)
                    runtime_context["dependency_results"] = dependency_outputs
                    runtime_context["tool_request_id"] = request.request_id
                    futures[pool.submit(
                        self.execute_tool,
                        request.tool_name,
                        tool,
                        request.arguments,
                        runtime_context,
                        request.request_id,
                        request.depends_on,
                    )] = request

                for future in as_completed(futures):
                    request = futures[future]
                    results[request.request_id] = future.result()
                    pending.pop(request.request_id, None)

        return results

    def _run_request(
        self,
        request: ToolExecutionRequest,
        tool: Any,
        runtime_context: Dict[str, Any],
    ) -> ToolExecutionResult:
        started_at = time.time()
        attempts = 0
        result_payload: Dict[str, Any] = {}
        error_message: Optional[str] = None
        status = "error"
        rolled_back = False
        audit_credentials = self._audit_credentials(request.tool_name, runtime_context)
        retry_count = int(request.max_retries if request.max_retries is not None else self.max_retries)
        total_attempts = retry_count + 1
        sandboxed = self._uses_sandbox(tool)
        default_sandbox_type = "python" if sandboxed else ""
        sandbox_type = str(getattr(tool, "sandbox_type", default_sandbox_type))

        log("tool.execution.start", {
            "tool": request.tool_name,
            "request_id": request.request_id,
            "dependencies": request.depends_on,
            "credentials": audit_credentials,
            "sandboxed": sandboxed,
            "sandbox_type": sandbox_type,
        })

        for attempt in range(1, total_attempts + 1):
            attempts = attempt
            try:
                result_payload = self._invoke_with_timeout(
                    tool,
                    request.arguments,
                    runtime_context,
                    int(request.timeout_seconds or self.timeout_seconds),
                )
                if not isinstance(result_payload, dict):
                    result_payload = {"result": result_payload}
                status = "success"
                error_message = None
                break
            except TimeoutError as exc:
                error_message = str(exc)
                status = "timeout"
            except Exception as exc:
                error_message = str(exc)
                status = "error"
                rolled_back = self._rollback(tool, request.arguments, runtime_context, error_message) or rolled_back
                if not self._should_retry(exc, attempt, total_attempts):
                    break
            if attempt < total_attempts:
                time.sleep(0.1 * attempt)

        finished_at = time.time()
        result = ToolExecutionResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            status=status,
            output=result_payload,
            error=error_message,
            attempts=attempts,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(finished_at - started_at) * 1000.0,
            rolled_back=rolled_back,
            dependencies=list(request.depends_on),
            sandboxed=sandboxed,
            sandbox_type=sandbox_type,
        )
        self._record_audit(result, request.arguments, audit_credentials)
        log("tool.execution.finish", {
            "tool": request.tool_name,
            "request_id": request.request_id,
            "status": result.status,
            "attempts": result.attempts,
            "rolled_back": result.rolled_back,
            "error": result.error,
            "sandboxed": result.sandboxed,
            "sandbox_type": result.sandbox_type,
        })
        return result

    def _prepare_context(
        self,
        tool_name: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        runtime_context = self._safe_dict_copy(context)
        requested_scopes = self._requested_scopes(tool_name, runtime_context)
        return self.credential_manager.inject_into_context(
            tool_name,
            runtime_context,
            requested_scopes=requested_scopes,
        )

    def _requested_scopes(self, tool_name: str, context: Dict[str, Any]) -> List[str]:
        scope_spec = context.get("requested_scopes", [])
        if isinstance(scope_spec, dict):
            scopes = scope_spec.get(tool_name, [])
        else:
            scopes = scope_spec
        if not isinstance(scopes, list):
            return []
        return [str(scope) for scope in scopes if str(scope).strip()]

    def _audit_credentials(self, tool_name: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.credential_manager.describe_for_audit(
            tool_name,
            requested_scopes=self._requested_scopes(tool_name, context),
        )

    def _validate_permissions(self, tool: Any, context: Dict[str, Any]) -> None:
        allowed = set(context.get("allowed_permissions", []))
        for permission in list(getattr(tool, "permissions", []) or []):
            if permission not in allowed:
                raise PermissionError("Permission denied: {0}".format(permission))

    def _tool_timeout(self, tool: Any) -> int:
        return max(1, int(getattr(tool, "timeout_seconds", self.timeout_seconds)))

    def _tool_retries(self, tool: Any) -> int:
        return max(0, int(getattr(tool, "max_retries", self.max_retries)))

    def _invoke_with_timeout(
        self,
        tool: Any,
        arguments: Dict[str, Any],
        runtime_context: Dict[str, Any],
        timeout_seconds: int,
    ) -> Any:
        if self._uses_sandbox(tool):
            return self._invoke_in_sandbox(tool, arguments, runtime_context, timeout_seconds)

        outcome: Dict[str, Any] = {}
        error_holder: List[Exception] = []

        def _run() -> None:
            try:
                payload = dict(arguments or {})
                payload = self._safe_dict_copy(payload)
                payload["_context"] = runtime_context
                outcome["result"] = tool(**payload)
            except Exception as exc:
                error_holder.append(exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)
        if thread.is_alive():
            raise TimeoutError("Execution timed out after {0}s".format(timeout_seconds))
        if error_holder:
            raise error_holder[0]
        return outcome.get("result")

    def _should_retry(self, exc: Exception, attempt: int, total_attempts: int) -> bool:
        if isinstance(exc, (PermissionError, ValueError)):
            return False
        return attempt < total_attempts

    def _uses_sandbox(self, tool: Any) -> bool:
        return bool(getattr(tool, "requires_sandbox", False))

    def _invoke_in_sandbox(
        self,
        tool: Any,
        arguments: Dict[str, Any],
        runtime_context: Dict[str, Any],
        timeout_seconds: int,
    ) -> Any:
        sandbox = getattr(tool, "sandbox", None)
        if sandbox is None or not hasattr(sandbox, "run"):
            sandbox = PythonSandbox(
                timeout_seconds=timeout_seconds,
                allowed_imports=getattr(tool, "allowed_imports", ()),
            )
        if hasattr(sandbox, "timeout_seconds"):
            sandbox.timeout_seconds = max(1, int(timeout_seconds))
        build_script = getattr(tool, "build_sandbox_script", None)
        if callable(build_script):
            code = build_script(
                arguments=self._safe_dict_copy(arguments),
                context=self._safe_dict_copy(runtime_context),
            )
        else:
            code = arguments.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Sandboxed tool requires executable code")
        parse_result = getattr(tool, "parse_sandbox_result", None)
        sandbox_result = sandbox.run(code)
        if callable(parse_result):
            return parse_result(sandbox_result)
        return sandbox_result

    def _rollback(
        self,
        tool: Any,
        arguments: Dict[str, Any],
        runtime_context: Dict[str, Any],
        error_message: Optional[str],
    ) -> bool:
        rollback_fn = getattr(tool, "rollback", None)
        if not callable(rollback_fn):
            return False
        try:
            rollback_fn(arguments=dict(arguments or {}), context=dict(runtime_context), error=error_message)
            return True
        except Exception as rollback_exc:
            log("tool.execution.rollback_error", {
                "tool": getattr(tool, "name", "unknown"),
                "error": str(rollback_exc),
            })
            return False

    def _dependency_failure_result(
        self,
        request: ToolExecutionRequest,
        failed_dependency: ToolExecutionResult,
    ) -> ToolExecutionResult:
        started_at = time.time()
        return ToolExecutionResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            status="dependency_failed",
            error="Dependency {0} failed".format(failed_dependency.request_id),
            attempts=0,
            started_at=started_at,
            finished_at=started_at,
            duration_ms=0.0,
            dependencies=list(request.depends_on),
        )

    def _record_audit(
        self,
        result: ToolExecutionResult,
        arguments: Dict[str, Any],
        credentials: List[Dict[str, Any]],
    ) -> None:
        self._audit_log.append(ToolExecutionAuditRecord(
            request_id=result.request_id,
            tool_name=result.tool_name,
            status=result.status,
            started_at=result.started_at,
            duration_ms=result.duration_ms,
            attempts=result.attempts,
            rolled_back=result.rolled_back,
            error=result.error,
            input_summary=str(arguments)[:200],
            output_summary=str(result.output)[:200],
            credentials=list(credentials),
            dependencies=list(result.dependencies),
            sandboxed=result.sandboxed,
            sandbox_type=result.sandbox_type,
        ))
