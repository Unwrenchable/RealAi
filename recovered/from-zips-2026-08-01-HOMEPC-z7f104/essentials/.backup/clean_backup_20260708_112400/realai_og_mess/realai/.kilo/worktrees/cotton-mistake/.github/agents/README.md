# RealAI — Copilot Agent Pack

This directory contains repo-local context files that help GitHub Copilot and
AI coding assistants give accurate, project-aware suggestions as RealAI evolves.

## Files

| File | Purpose |
|------|---------|
| `agent.md` | Repo-specific guidance: structure, toolchain, conventions |
| `memory.md` | Persistent notes updated over time (decisions, gotchas, commands) |
| `bootstrap.md` | Step-by-step local setup guide |
| `fullstack-dev.md` | Full-stack RealAI developer agent — general code, API, GUI |
| `provider-specialist.md` | AI provider integration specialist — routing, API keys, new providers |
| `capability-dev.md` | Capability implementation agent — turning stub methods into real integrations |

## Safety rules — please read before editing

1. **Never store secrets.** No API keys, private keys, passwords, RPC
   credentials, or any other sensitive values may appear in any file here.
2. **Use environment variables for secrets.** The `.gitignore` already excludes
   `.env` files. Use environment variables or `~/.realai/config.json` (managed
   by the GUI) for runtime credentials.
3. **Human review required.** All additions to `memory.md` must be reviewed in
   a pull request before merging to `main`.
4. **No executable code.** These are documentation files only; they must not
   contain runnable scripts that could be auto-executed by tools.
5. **Keep it factual.** Record only what is true of the repository right now.
   Outdated notes should be removed or corrected promptly.

## How the memory loop works

```
Code change ──► agent proposes memory.md update ──► PR review ──► merge
                                                        │
                                              Human verifies no secrets
                                              and content is accurate
```

Over time `memory.md` accumulates decisions, tested commands, and architecture
notes that make every subsequent AI interaction faster and more accurate.
