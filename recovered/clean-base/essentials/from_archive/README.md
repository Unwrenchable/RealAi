# Recovered from archive/ (curated)

This tree holds **unique GOLD** found in `archive/` that was at risk of being
treated as disposable. Recovery policy:

1. **Never overwrite** superior clean-runtime clients (frontend `realai.ts`,
   VS Code streaming `realaiClient.ts`).
2. **Wire** unique modules into `packages/sdk-ts` where they belong.
3. **Preserve** memory snapshots under `memory_snapshots/` with an INDEX —
   do **not** auto-swap live DBs.
4. **Restore** agentx capability profiles under `agents/agentx/`.

## What was recovered

| Item | Destination | Notes |
|------|-------------|-------|
| `registryClient.ts` | `packages/sdk-ts/src/registryClient.ts` | Was only in archive |
| env-driven chat client | `packages/sdk-ts/src/envChatClient.ts` | Archive `realaiClient.ts` renamed |
| Historical frontend client | `recovered/from_archive/ui/*historical*` | Superseded by clean frontend |
| AgentX agents/profiles | `agents/agentx/` | Multi-agent capability defs |
| Unique memory blobs | `recovered/from_archive/memory_snapshots/` | See INDEX.json |

## What was NOT bulk-merged

- Duplicate lockfiles, `.next` builds, empty SDK shells
- Multi-GB cavity manifests
- Live `data/realai_memory*` (left as active store)

See `RECOVERY_LOG.json` for full provenance.
