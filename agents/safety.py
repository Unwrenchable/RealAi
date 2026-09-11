"""Agent safety rules and validations."""


class AgentSafety:
    MAX_STEPS = 10

    def __init__(self, max_steps: int = None):
        self.max_steps = int(max_steps or self.MAX_STEPS)

    def validate_step(self, step_count: int):
        if int(step_count) > self.max_steps:
            raise RuntimeError("Agent exceeded maximum step count: {0} > {1}".format(step_count, self.max_steps))

    def validate_tool_call(self, tool_call, allowed_tools):
        if not isinstance(tool_call, dict):
            raise ValueError("Invalid tool call payload.")
        name = tool_call.get("name")
        if name not in set(allowed_tools or []):
            raise PermissionError("Tool not allowed")
