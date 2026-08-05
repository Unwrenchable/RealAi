# Branch → recovered snapshot map

| Branch | Slug path | Role | Batch |
|--------|-----------|------|-------|
| local/nested-realai-202607 | recovered/nested-realai-202607 | primary nested snapshot | 1 |
| local/desktop-realai-202605 | recovered/desktop-realai-202605 | desktop shell | 1 |
| local/desktop-realai-agent-202604 | recovered/desktop-realai-agent-202604 | agent surface | 1 |
| local/desktop-realai-api-202604 | recovered/desktop-realai-api-202604 | API surface | 1 |
| local/desktop-realai-orchestration-202604 | recovered/desktop-realai-orchestration-202604 | orchestration | 1 |
| local/desktop-realai-design-system-202604 | recovered/desktop-realai-design-system-202604 | design system | 1 |
| local/desktop-realai-cli-202604 | recovered/desktop-realai-cli-202604 | CLI | 1 |
| local/desktop-realai-sdk-js-202604 | recovered/desktop-realai-sdk-js-202604 | JS SDK | 1 |
| local/RealAIProject-clean-20260612 | recovered/RealAIProject-clean-20260612 | project clean | 1 |
| local/real-fin-realai-source-only | recovered/real-fin-realai-source-only | real-fin source | 1 |

## Guarantee
- Snapshots under `recovered/<slug>/` are never deleted.
- Giants/junk (>100MB, gguf, node_modules, venv) may be moved to `C:\realai_giant_hold\unification-snapshots\` (not deleted).
- Living system = `core/` + `modules/` + `adapters/` + `registry/` on `unification/ultimate-all`.
