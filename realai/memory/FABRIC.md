# Memory Fabric (Orchestrator 2.0)

Scoped durable memory for RealAI meta-router hooks. Stdlib-only JSONL backend.

## Store path

Default: `C:\RealAI-clean\state\memory\fabric.jsonl`

Override with env:

```
REALAI_MEMORY_FABRIC=<absolute path to .jsonl>
```

`REALAI_WORKSPACE` (default `C:\RealAI-clean`) is used when the override is unset.

## Record schema

| Field | Values / notes |
|-------|----------------|
| `id` | hex uuid |
| `text` | memory body |
| `scope` | `episodic` \| `semantic` \| `procedural` \| `world` \| `agent` |
| `owner` | agent / target id |
| `ttl` | e.g. `30d`, `7d`, `forever` |
| `sensitivity` | `normal` \| `high` \| `secret` |
| `created_at` | ISO-8601 UTC |
| `expires_at` | ISO-8601 UTC or null if forever |
| `tags` | string list |
| `meta` | free-form object |

## APIs

- `write_memory(text, *, scope, owner, ttl, sensitivity, tags, meta)`
- `read_memory(query, *, scopes, owner, limit=8, include_expired=False, privacy=None, redact_high=None)`
- `memory_fabric_status()`
- `purge_expired()` — callable sweep, not a daemon

High/secret text is redacted (`[REDACTED]`) when `privacy` is cloud-bound or `redact_high=True`.

Universe `memory_bridge` remains a status reporter only; fabric is the durable write/read path for meta_router hooks.
