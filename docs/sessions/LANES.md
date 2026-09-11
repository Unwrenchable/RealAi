# Session lanes (what is / isn’t RealAI)

Encoded roots under `C:\Users\tsmit\.grok\sessions\`:

| Lane | Encoded folder | Working dir | RealAI product? | Notes |
|------|----------------|-------------|-----------------|-------|
| `realai-core` | `C%3A%5Crealai` | `C:\realai` | **Yes (legacy)** | Pre-clean mega-repo / DDS / unification. Historical. |
| `realai-core` | `C%3A%5CRealAI-clean` | `C:\RealAI-clean` | **Yes (current)** | Living product. Most development after 2026-08-08. |
| `realai-voice` | `C%3A%5CRealAI-clean%5Crealai%5Cvoice` | `C:\RealAI-clean\realai\voice` | **Yes (subsystem)** | Local Voice Lab / hive voice rewrite. |
| `realai-tooling` | `C%3A%5CUsers%5Ctsmit%5C.grok%5Cbin` | `C:\Users\tsmit\.grok\bin` | **Yes (tooling)** | Getting bare `realai` CLI on PATH. |
| `adjacent-other-repo` | `...ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS` | `C:\Users\tsmit\ATOMIC-FIZZ-...` | **No (other repo)** | Vault-77 / Omniverse game work. Title mentions RealAI conceptually; **not** the RealAI-clean product tree. |
| `unrelated` | `...Rack_em_up` | `C:\Users\tsmit\Rack_em_up` | **No** | NestJS Express typings on Render. Ignore for RealAI phases. |

## Stub / noise sessions

Empty or near-empty sessions (usually 2 chat messages, no title). Safe to ignore when reading phases:

- `019fdbaa-9d6a-7050-99e9-db6a34beca6f` — Rack_em_up stub
- `019fe166-e5ce-7dd2-bc26-5e9e0eb0a89f` — RealAI-clean stub
- `01a038fb-8b0e-7911-8019-e0c544bee4d7` — RealAI-clean stub
- `01a038fb-4305-7583-a098-16a110d7be98` — RealAI-clean stub
- `01a04992-91a0-7820-a8a2-942e207cba9f` — grok-bin stub
- `01a05400-dbe6-7502-b1a0-a4406017e50b` — RealAI-clean stub
- `01a05407-a259-7133-9456-b7d408c0a720` — RealAI-clean stub

## Counts (as of catalog refresh)

| Lane | Sessions |
|------|----------|
| realai-core | 37 |
| realai-voice | 1 |
| realai-tooling | 2 |
| adjacent-other-repo | 1 |
| unrelated | 2 |
| **Total** | **43** |
