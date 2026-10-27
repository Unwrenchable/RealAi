# Tool Schema Reference

Every tool skill should expose a machine-readable schema so RealAI hive operators and abilities can discover and call it safely.

## Minimal Schema (JSON)

```json
{
  "name": "find_files",
  "description": "Search the repository for files by name glob or content pattern.",
  "parameters": {
    "type": "object",
    "properties": {
      "pattern": { "type": "string", "description": "Glob pattern relative to repo root" },
      "content": { "type": "string", "description": "Optional regex to match file contents" },
      "max_results": { "type": "integer", "default": 50 },
      "ignore": { "type": "array", "items": { "type": "string" }, "default": ["node_modules", ".git", ".venv", "checkpoints", "checkpoints_lora", "weights"] }
    },
    "required": ["pattern"]
  },
  "side_effect": "read-only",
  "returns": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "path": { "type": "string" },
        "size": { "type": "integer" },
        "matches": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

## Side-Effect Levels

| Level        | Meaning                                      | Agent Policy                          |
|--------------|----------------------------------------------|---------------------------------------|
| read-only    | No filesystem or state changes               | Always safe                           |
| write        | Creates or modifies files                    | Require confirmation or dry-run first |
| destructive  | Deletes, force-pushes, drops data            | Explicit human approval required      |
| network      | Calls external APIs or fetches remote data   | Log and rate-limit                    |
| privileged   | Requires elevated permissions or secrets     | Never auto-run                        |

## Discovery

RealAI hive operators should call `tool_registry` and/or `ability_catalog` at the start of a complex task to obtain the current list of tools/abilities and their schemas. Prefer RealAI registry surfaces under `agent_tools/`, `abilities/`, and `realai/registry` — not Blackbox agent discovery. Cache the result for the session unless skills are reloaded.
