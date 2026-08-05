"""Code execution tool with local sandbox limits."""

from typing import Any, Dict

from core.security.python_sandbox import PythonSandbox
from core.tools.base import Tool
from core.tools.permissions import Permissions


class CodeExecutionTool(Tool):
    name = "code_exec"
    description = "Run Python code in a constrained local sandbox"
    params_schema = {"code": {"type": "string"}}
    permissions = [Permissions.CODE_EXEC]

    def __init__(self, sandbox: PythonSandbox = None):
        self.sandbox = sandbox or PythonSandbox()

    def __call__(self, **kwargs: Any) -> Dict[str, Any]:
        code = str(kwargs.get("code", ""))
        return self.sandbox.run(code)
