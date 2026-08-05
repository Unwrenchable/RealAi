# Branch → recovered snapshot map

## Batch 1
| Branch | Slug | Status |
|--------|------|--------|
| local/nested-realai-202607 | recovered/nested-realai-202607 | ok |
| local/desktop-realai-202605 | recovered/desktop-realai-202605 | ok |
| local/desktop-realai-agent-202604 | recovered/desktop-realai-agent-202604 | ok |
| local/desktop-realai-api-202604 | recovered/desktop-realai-api-202604 | ok |
| local/desktop-realai-orchestration-202604 | recovered/desktop-realai-orchestration-202604 | ok |
| local/desktop-realai-design-system-202604 | recovered/desktop-realai-design-system-202604 | ok |
| local/desktop-realai-cli-202604 | recovered/desktop-realai-cli-202604 | ok |
| local/desktop-realai-sdk-js-202604 | recovered/desktop-realai-sdk-js-202604 | ok |
| local/RealAIProject-clean-20260612 | recovered/RealAIProject-clean-20260612 | ok |
| local/real-fin-realai-source-only | recovered/real-fin-realai-source-only | ok |

## Batch 2 (expanded)
| local/recovery-primary-clean-20260731-clean | recovered/recovery-primary-clean-20260731-clean | ok files=3729 |
| recovery/primary-clean/2026-07-31/HOMEPC/p1c9e2 | recovered/primary-clean-2026-07-31-HOMEPC-p1c9e2 | ok files=1200 |
| recovery/og-mess-clean/2026-07-26/HOMEPC/9c2d11 | recovered/og-mess-clean-2026-07-26-HOMEPC-9c2d11 | ok files=276 |
| recovery/unique-modules/2026-08-01/HOMEPC/u194c3 | recovered/unique-modules-2026-08-01-HOMEPC-u194c3 | ok files=8053 |
| recovery/unique-modules-files/2026-08-01/HOMEPC/u194c3f | recovered/unique-modules-files-2026-08-01-HOMEPC-u194c3f | ok files=8739 |
| recovery/modules-runtime/2026-08-01/HOMEPC/m21f01 | recovered/modules-runtime-2026-08-01-HOMEPC-m21f01 | ok files=7150 |
| recovery/plugin-system/2026-08-01/HOMEPC/p26b2 | recovered/plugin-system-2026-08-01-HOMEPC-p26b2 | ok files=8053 |
| recovery/agents-skills/2026-08-01/HOMEPC/s137e5 | recovered/agents-skills-2026-08-01-HOMEPC-s137e5 | ok files=8198 |
| recovery/unique-plugins-orchestrators-agenttools/2026-07-31/HOMEPC/u9f2a1 | recovered/unique-plugins-orchestrators-agenttools-2026-07-31-HOMEPC-u9f2a1 | ok files=228 |
| local/realai-clean-20260726-source-only | recovered/realai-clean-20260726-source-only | ok files=1221 |
| recovery/from-wsl/2026-08-01/HOMEPC/w274d4 | recovered/from-wsl-2026-08-01-HOMEPC-w274d4 | ok files=8053 |
| recovery/from-wsl-files/2026-08-01/HOMEPC/w274d4f | recovered/from-wsl-files-2026-08-01-HOMEPC-w274d4f | ok files=8739 |
| recovery/wsl-RealAi/2026-07-31/HOMEPC/w4a8c2 | recovered/wsl-RealAi-2026-07-31-HOMEPC-w4a8c2 | ok files=328 |
| recovery/grok-realai2-clean/2026-07-31/HOMEPC/e5c023 | recovered/grok-realai2-clean-2026-07-31-HOMEPC-e5c023 | ok files=433 |
| recovery/grok-export/2026-07-31/HOMEPC/e1a2b3 | recovered/grok-export-2026-07-31-HOMEPC-e1a2b3 | ok files=550 |
| recovery/essentials/2026-07-26/HOMEPC/snapshot1 | recovered/essentials-2026-07-26-HOMEPC-snapshot1 | ok files=4720 |
| recovery/users-tsmit-realai-clean/2026-07-31/HOMEPC/d4b912 | recovered/users-tsmit-realai-clean-2026-07-31-HOMEPC-d4b912 | ok files=290 |
| recovery/users-tsmit-realai/2026-07-31/HOMEPC/c3a801 | recovered/users-tsmit-realai-2026-07-31-HOMEPC-c3a801 | ok files=316 |
| realai-3.0-update | recovered/realai-3.0-update | ok files=328 |
| realai-3.0-clean | recovered/realai-3.0-clean | ok files=420 |
| grok_snapshot | recovered/grok_snapshot | ok files=550 |
| restored-from-history | recovered/restored-from-history | ok files=328 |

## Living (promoted — not ghosted)
| Module | Path | Source |
|--------|------|--------|
| training | core/training | unique-modules trainers + living finetune |
| datasets | modules/training/datasets | agents-skills finetune jsonl |
| memory | core/memory (+ long_term_engine) | primary-clean engine |
| agents | core/agents (+ self_heal, agent_runtime) | agents-skills + unique-modules |
| orchestration | core/orchestration | v3 + gold |
| agents pack | modules/agents_skills | agents-skills |
| orchestrators pack | modules/orchestrators | unique-plugins |

## Guarantee
Snapshots under recovered/ are never deleted. Giants/junk moved to C:\realai_giant_hold\unification-snapshots\.
