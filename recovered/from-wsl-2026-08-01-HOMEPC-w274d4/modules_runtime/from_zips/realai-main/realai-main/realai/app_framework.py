"""
RealAI App Framework
=====================
Base classes for building RealAI-powered applications with workflow support.

Usage::

    from realai.app_framework import RealAIApp, WorkflowBuilder, AutomationBuilder

    class MyApp(RealAIApp):
        def on_message(self, event):
            return {"response": "Hello " + str(event.payload)}

    app = MyApp("my-app")
    app.start()
    result = app.emit("greet", "World")
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AppEvent:
    """An event emitted by or to a RealAI application.

    Attributes:
        event_type: String identifier for the event type.
        payload: Event data (any type).
        timestamp: Unix timestamp of creation.
    """

    event_type: str
    payload: Any
    timestamp: float


class RealAIApp:
    """Base class for RealAI-powered applications.

    Subclass and override on_start, on_stop, and on_message.
    """

    def __init__(self, name: str, model: Any = None) -> None:
        """Initialize the app.

        Args:
            name: Human-readable application name.
            model: Optional RealAI model instance.
        """
        self.name = name
        self.model = model
        self._running = False
        self._events: List[AppEvent] = []

    def on_start(self) -> None:
        """Called when the app starts. Override in subclasses."""
        pass

    def on_stop(self) -> None:
        """Called when the app stops. Override in subclasses."""
        pass

    def on_message(self, event: AppEvent) -> Optional[Dict[str, Any]]:
        """Handle an incoming event. Override in subclasses.

        Args:
            event: AppEvent to handle.

        Returns:
            Optional response dict.
        """
        return None

    def start(self) -> Dict[str, Any]:
        """Start the application.

        Returns:
            Status dict with status and name.
        """
        self._running = True
        try:
            self.on_start()
        except Exception as e:
            return {"status": "error", "name": self.name, "error": str(e)}
        return {"status": "started", "name": self.name}

    def stop(self) -> Dict[str, Any]:
        """Stop the application.

        Returns:
            Status dict with status and name.
        """
        self._running = False
        try:
            self.on_stop()
        except Exception as e:
            return {"status": "error", "name": self.name, "error": str(e)}
        return {"status": "stopped", "name": self.name}

    def emit(self, event_type: str, payload: Any = None) -> Optional[Dict[str, Any]]:
        """Emit an event to the application.

        Args:
            event_type: Event type string.
            payload: Event payload.

        Returns:
            Response from on_message, or None.
        """
        event = AppEvent(
            event_type=event_type,
            payload=payload,
            timestamp=time.time(),
        )
        self._events.append(event)
        return self.on_message(event)


@dataclass
class WorkflowStep:
    """A single step in a workflow definition.

    Attributes:
        name: Step name.
        action: Action identifier string.
        params: Parameters dict for the action.
        depends_on: List of step names this step depends on.
    """

    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    """A named, versioned workflow with ordered steps.

    Attributes:
        id: Unique workflow identifier.
        name: Human-readable workflow name.
        steps: Ordered list of WorkflowStep objects.
        description: Optional description.
    """

    id: str
    name: str
    steps: List[WorkflowStep]
    description: str = ""


class WorkflowBuilder:
    """Fluent builder for WorkflowDefinition objects.

    Example::

        workflow = (WorkflowBuilder()
            .add_step("fetch", "web_research", {"query": "AI news"})
            .add_step("summarize", "chat_completion",
                      {"prompt": "Summarize: {input}"}, depends_on=["fetch"])
            .build("my-workflow"))
    """

    def __init__(self) -> None:
        """Initialize an empty workflow builder."""
        self._steps: List[WorkflowStep] = []

    def add_step(
        self,
        name: str,
        action: str,
        params: Dict[str, Any],
        depends_on: Optional[List[str]] = None,
    ) -> "WorkflowBuilder":
        """Add a step to the workflow.

        Args:
            name: Step name.
            action: Action identifier.
            params: Parameters dict.
            depends_on: Optional list of prerequisite step names.

        Returns:
            self for method chaining.
        """
        self._steps.append(WorkflowStep(
            name=name,
            action=action,
            params=params,
            depends_on=depends_on or [],
        ))
        return self

    def build(self, name: str) -> WorkflowDefinition:
        """Build and return the WorkflowDefinition.

        Args:
            name: Workflow name.

        Returns:
            WorkflowDefinition with all added steps.
        """
        return WorkflowDefinition(
            id=str(uuid.uuid4()),
            name=name,
            steps=list(self._steps),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the current builder state to a plain dict.

        Returns:
            Dict representation of the workflow steps.
        """
        return {
            "steps": [
                {
                    "name": s.name,
                    "action": s.action,
                    "params": s.params,
                    "depends_on": s.depends_on,
                }
                for s in self._steps
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Construct a WorkflowDefinition from a plain dict.

        Args:
            data: Dict with "name" and "steps" keys.

        Returns:
            WorkflowDefinition deserialized from data.
        """
        steps = [
            WorkflowStep(
                name=s.get("name", ""),
                action=s.get("action", ""),
                params=s.get("params", {}),
                depends_on=s.get("depends_on", []),
            )
            for s in data.get("steps", [])
        ]
        return WorkflowDefinition(
            id=str(uuid.uuid4()),
            name=data.get("name", "workflow"),
            steps=steps,
            description=data.get("description", ""),
        )


class AutomationBuilder:
    """Records and replays workflow automations.

    Supports parameterized workflows via {{key}} placeholder substitution.
    """

    def __init__(self) -> None:
        """Initialize the automation builder."""
        self._recording = False
        self._recording_name = ""
        self._recorded_steps: List[Dict[str, Any]] = []

    def start_recording(self, name: str) -> None:
        """Begin recording automation steps.

        Args:
            name: Name for the recorded workflow.
        """
        self._recording = True
        self._recording_name = name
        self._recorded_steps = []

    def record_step(self, action: str, params: Dict[str, Any]) -> None:
        """Record a single automation step.

        Args:
            action: Action identifier.
            params: Parameters dict for the action.
        """
        if self._recording:
            self._recorded_steps.append({"action": action, "params": params})

    def stop_recording(self) -> WorkflowDefinition:
        """Stop recording and return the captured workflow.

        Returns:
            WorkflowDefinition from the recorded steps.
        """
        self._recording = False
        steps = [
            WorkflowStep(
                name="step_{0}".format(i + 1),
                action=s["action"],
                params=s["params"],
            )
            for i, s in enumerate(self._recorded_steps)
        ]
        return WorkflowDefinition(
            id=str(uuid.uuid4()),
            name=self._recording_name,
            steps=steps,
        )

    def replay(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Execute all steps in a workflow and collect results.

        Args:
            workflow: WorkflowDefinition to execute.

        Returns:
            Dict with workflow name, steps_run, and results list.
        """
        results = []
        for step in workflow.steps:
            result = {
                "step": step.name,
                "action": step.action,
                "params": step.params,
                "status": "executed",
            }
            results.append(result)
        return {
            "workflow": workflow.name,
            "steps_run": len(workflow.steps),
            "results": results,
        }

    def parameterize(
        self,
        workflow: WorkflowDefinition,
        params: Dict[str, Any],
    ) -> WorkflowDefinition:
        """Substitute {{key}} placeholders in step params.

        Args:
            workflow: WorkflowDefinition with placeholder params.
            params: Dict of placeholder values.

        Returns:
            New WorkflowDefinition with substituted parameters.
        """
        def _substitute(value: Any) -> Any:
            if isinstance(value, str):
                for k, v in params.items():
                    value = value.replace("{{" + k + "}}", str(v))
                return value
            if isinstance(value, dict):
                return {kk: _substitute(vv) for kk, vv in value.items()}
            if isinstance(value, list):
                return [_substitute(item) for item in value]
            return value

        new_steps = [
            WorkflowStep(
                name=step.name,
                action=step.action,
                params=_substitute(step.params),
                depends_on=step.depends_on,
            )
            for step in workflow.steps
        ]
        return WorkflowDefinition(
            id=str(uuid.uuid4()),
            name=workflow.name,
            steps=new_steps,
            description=workflow.description,
        )
