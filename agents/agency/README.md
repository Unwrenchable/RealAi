# The Agency @ RealAI

**The Agency: AI specialists ready to transform your workflow** — vendored into this repo under `agents/agency/` and wired for Hive / hierarchical use.

Upstream inspiration: [agency-agents](https://github.com/msitarzewski/agency-agents) (specialist personality packs). Here they are first-class RealAI agents, not a separate chat product.

## Why this helps RealAI

| Benefit | In this repo |
|---------|----------------|
| Specialist depth | Division folders (engineering, design, marketing, testing, …) with personality + mission + deliverables |
| Hive Console / Agents UI | Imported into `agents/agentx/agents.json` with `agency` + division tags — filter **Agency** in `/agents-ui/` |
| Hierarchical / RISE | `agents.hierarchical` can resolve Agency specialists by id and load their system prompts from these `.md` files |
| Craft / learn / finetune | Manifests feed `training/data/agent_manifests_for_finetuning.json` and AgentX packs |
| Local-first | Runs against Hive (`:8001`) + Vulkan — no cloud agency subscription required |

## Roster (this checkout)

Specialists live as markdown under division folders:

```text
agents/agency/
  academic/  design/  engineering/  finance/  game-development/
  marketing/ paid-media/ product/ project-management/ sales/
  spatial-computing/ specialized/ support/ testing/
```

Counts change as packs are re-imported. Re-sync anytime:

```powershell
cd C:\RealAI-clean
$env:PYTHONPATH="C:\RealAI-clean"
py -3 scripts\sync_agency_registry.py
```

## How RealAI uses them

1. **Agents UI** — open `http://127.0.0.1:8001/agents-ui/`, tab **Agency** (tags include `agency`).
2. **Hierarchical** — `from agents.hierarchical import get_agency_specialist, list_agency_divisions`
3. **Hive chat** — natural language / multi-agent runs can route to tagged specialists via the shared registry (`REALAI_AGENTS_PATH` → `agents/agentx/agents.json`).
4. **Persona files** — each `.md` is the system prompt source; registry entries point at `source_path` under `agents/agency/…`.

## Related packages

| Path | Role |
|------|------|
| `agents/agency/*.md` | Persona / SOP source of truth |
| `agents/agentx/agents.json` | Live Hive registry (merged) |
| `agents/agentx/agency_import.json` | Agency-only import snapshot |
| `agents/hierarchical/` | RISE / supervisor + Agency helpers |
| `agents/orchestration/` | Orchestration package surface |

## Contributing new specialists

1. Add `agents/agency/<division>/<slug>.md` with YAML frontmatter (`name`, `description`) and personality sections.
2. Run `scripts/sync_agency_registry.py`.
3. Confirm the agent appears under Agents UI → **Agency**.

MIT-licensed specialist content follows upstream Agency licensing where applicable; RealAI wiring and registry are part of this product tree.
