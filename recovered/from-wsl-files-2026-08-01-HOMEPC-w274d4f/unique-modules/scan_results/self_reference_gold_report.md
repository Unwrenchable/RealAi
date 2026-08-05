# Self-reference / capability gold — scanner truth vs recovery

## Honest answer

**No — not every self-reference from every cavity dump was curated into clean RealAI.**  
The scanners *did* run and *did* produce huge maps; we **indexed** them and ran a **scoped deep gold pass**, but we did **not** open multi‑GB cavity JSON as the primary source of truth (those were mostly `repo_tree*.txt` noise).

What we *did* capture:

| Pass | Self-related signal | Status |
|------|---------------------|--------|
| Root cavity (`realai_full_cavity_*`) | Group **`self_logic`: 42,837 hits** | Summarized only; raw dump too noisy |
| Root cavity | **`autonomous_behavior`: 131,639** | Same |
| Root cavity | **`training_evolution`: 13,311** | Same |
| Deep gold map | **`self_improve_training`: 905** keyword hits | `dds3_deep_gold_map_summary.json` |
| Ability inventory | `training` / `train` multi-era | Partial tokens |
| Live code inventory | **~209 unique files** matching self/hive/autonomy patterns | See below |
| Clean package modules | `realai/self_improvement.py`, training stubs, CAPABILITIES self_reflect | **Present** |

## Keywords the scanners were built to find (self stack)

From `scanners/fs1_full_spectrum_scan.py` and root cavity groups:

- `self_improve`, `self_improvement`, `meta_learn`, `evolver`, `bootstrap`, `continual`, `lifelong`
- `autonomy`, `self-heal`, `self-repair`, `self-upgrade`, `self-correct`, `self-align`, `self-evaluate`
- `watchdog`, `supervisor`, `fallback`, `resilience`
- `realai_hivemind`, `hive_mind`
- training / LoRA / evolution

## Clean-tree modules that implement the “amplify” spine

| Path | Role |
|------|------|
| `realai/self_improvement.py` | Training data gen, eval, finetune orchestration (`REALAI_SELF_IMPROVE=true`) |
| `realai/__init__.py` | `self_reflect`, hive/agent orchestration hooks |
| `realai/training/*` | Dataset build / finetune stubs |
| `docs/CAPABILITIES.md` | Documents self-reflection API |
| `REALAI_3.0.md` | Operator-grade vision (not chatty junk) |
| `agents/*` + recovered `agents/agentx/*` | Multi-agent capability surface |
| Downloads finetune jsonl / manifests | **Training gold outside repo** |

## Archive/OG/backup

Most self-keyword hits live as **copies** of the same modules under `.backup/`, `realai_og_mess/`, worktrees — not unique new self-engines. Deduping is the right merge policy: **one self_improvement + one training pipeline + agentx**, not 40 copies.

## Gap (still open)

1. **Cavity raw hits never fully distilled** into a clean “self_logic file list” artifact (multi‑GB + tree-dump pollution).  
2. **Self-improve not wired into HTTP UI** by default (gated env flag).  
3. **Python `:8000` UI** is the junky built-in server page — **not** RealAI 3.0 Next frontend.  
4. **v3 Next UI** needs deps + point at **Vulkan `:8080`**, not Python `:8000`.

## Recommendation

Treat **RealAI 3.0 Next** (`apps/frontend`) + **Vulkan llama-server** as the “dope” stack; keep Python `api_server` only as optional orchestrator later once self_improve/tools/agents route through it.
