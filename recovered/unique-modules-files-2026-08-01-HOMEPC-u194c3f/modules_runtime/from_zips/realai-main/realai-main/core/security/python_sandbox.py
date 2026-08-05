"""Hardened local Python sandbox with resource and capability limits."""

import os
import subprocess
import tempfile
from typing import Any, Dict, Iterable, Set

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None


class PythonSandbox:
    def __init__(
        self,
        cpu_seconds: int = 2,
        memory_bytes: int = 256 * 1024 * 1024,
        timeout_seconds: int = 2,
        allowed_imports: Iterable[str] = (),
    ):
        self.cpu_seconds = max(1, int(cpu_seconds))
        self.memory_bytes = max(16 * 1024 * 1024, int(memory_bytes))
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.allowed_imports: Set[str] = {name.strip() for name in allowed_imports if str(name).strip()}

    def _limits(self):
        if resource is None:  # pragma: no cover
            return
        resource.setrlimit(resource.RLIMIT_CPU, (self.cpu_seconds, self.cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (self.memory_bytes, self.memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1 * 1024 * 1024, 1 * 1024 * 1024))

    def _sandbox_prelude(self) -> str:
        allowed = repr(sorted(self.allowed_imports))
        prelude = """
import builtins
import socket

_ALLOWED_IMPORTS = set(__ALLOWED_IMPORTS__)
_ORIG_IMPORT = builtins.__import__

def _blocked(*args, **kwargs):
    raise PermissionError("Operation blocked by sandbox policy")

def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = str(name).split(".")[0]
    if root not in _ALLOWED_IMPORTS:
        raise PermissionError("Import not allowed in sandbox: {0}".format(root))
    return _ORIG_IMPORT(name, globals, locals, fromlist, level)

builtins.open = _blocked
builtins.__import__ = _safe_import
socket.socket = _blocked
socket.create_connection = _blocked
"""
        return prelude.replace("__ALLOWED_IMPORTS__", allowed)

    def run(self, code: str) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            script_path = os.path.join(tmp_dir, "sandbox_script.py")
            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(self._sandbox_prelude())
                handle.write("\n")
                handle.write(str(code))
            try:
                proc = subprocess.run(
                    ["python3", "-I", script_path],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    preexec_fn=self._limits if resource is not None else None,
                )
                return {
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "returncode": proc.returncode,
                    "sandboxed": True,
                }
            except subprocess.TimeoutExpired:
                return {"error": "Execution timed out", "sandboxed": True}
