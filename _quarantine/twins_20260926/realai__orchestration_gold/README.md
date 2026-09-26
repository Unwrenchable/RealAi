# RealAI Orchestration

Multi-agent coordination layer for the [RealAI](https://github.com/realai/realai) project.

## Overview

`realai-orchestration` provides composable primitives for building multi-agent
workflows on top of RealAI:

| Class | Purpose |
|-------|---------|
| `BaseAgent` | Single agent backed by a RealAI client |
| `Orchestrator` | Manages a pool of agents; supports sequential, parallel, and auto-routing execution |
| `SharedMemory` | Thread-safe key/value store shared across agents |
| `ToolRegistry` / `Tool` | Register and invoke named capabilities that agents can call |
| `Pipeline` | Fixed-sequence chain where each step's output seeds the next task |

## Installation

```bash
# From the repo root
pip install -e .
```

## Quick Start

```python
from realai import RealAIClient
from realai_orchestration import BaseAgent, Orchestrator, SharedMemory

client = RealAIClient()

researcher = BaseAgent(
    name="researcher",
    role="You are an expert research analyst. Provide detailed findings.",
    realai_client=client,
)
writer = BaseAgent(
    name="writer",
    role="You are a professional content writer. Create engaging content.",
    realai_client=client,
)

orch = Orchestrator(client)
orch.add_agent(researcher)
orch.add_agent(writer)

# Sequential pipeline — writer receives researcher output as context
result = orch.run_pipeline("Write a blog post about the future of AI agents.")
print(result["final_output"])
```

## Parallel Execution

```python
tasks = [
    "Summarise recent OpenAI announcements",
    "Summarise recent Anthropic announcements",
    "Summarise recent Google DeepMind announcements",
]
results = orch.run_parallel(tasks)
for r in results:
    print(r["agent"], r["output"][:80])
```

## Auto-Routing

```python
# The orchestrator picks the best agent based on keyword matching
result = orch.route("Research the history of neural networks")
print(f"Routed to: {result['routed_to']}")
print(result["output"])
```

## Pipelines

```python
from realai_orchestration import Pipeline

pipe = Pipeline([
    (researcher, lambda _: "Research the latest advances in LLMs"),
    (writer, lambda prev: f"Write a summary article based on: {prev}"),
])
result = pipe.run(None)
print(result["final_output"])
```

## Tools

```python
from realai_orchestration import ToolRegistry, BaseAgent

registry = ToolRegistry()

@registry.register("get_weather", "Get the current weather for a city")
def get_weather(city: str) -> str:
    return f"Sunny, 22°C in {city}"  # replace with real API call

agent = BaseAgent(
    name="assistant",
    role="You are a helpful assistant.",
    realai_client=client,
    tools=registry,
)
```

## Shared Memory

```python
from realai_orchestration import SharedMemory

mem = SharedMemory()
mem.store("research_topic", "quantum computing")
print(mem.get_context())   # {"research_topic": "quantum computing"}
mem.delete("research_topic")
mem.clear()
```

## API Reference

### `BaseAgent(name, role, realai_client, tools=None, model=None, temperature=0.7, max_tokens=1024)`

- `run(task, context=None) -> dict` — Execute a task and return `{agent, task, output, success, error}`.

### `Orchestrator(realai_client, memory=None)`

- `add_agent(agent)` — Register an agent.
- `run_pipeline(task, agents=None) -> dict` — Sequential execution.
- `run_parallel(tasks, agents=None) -> list` — Parallel execution.
- `route(task, context=None) -> dict` — Auto-route to best agent.
- `reset_memory()` — Clear shared memory.

### `SharedMemory()`

- `store(key, value)` / `retrieve(key, default=None)` / `delete(key)`
- `get_context() -> dict` / `clear()` / `keys() -> list`

### `Pipeline(steps, memory=None, stop_on_failure=True)`

- `run(initial_input) -> dict` — Execute all steps sequentially.
- `add_step(agent, task_fn)` — Append a step.

### `ToolRegistry()`

- `add(tool)` / `register(name, description)` decorator
- `call(name, *args, **kwargs)` / `list_tools() -> list`
