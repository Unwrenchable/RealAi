---
name: realai-tools
description: Create manage and extend tool skills for RealAI hive operators and abilities that deliver complete repo-wide capabilities. Covers file system navigation code search git operations testing builds multi-agent orchestration scanners providers and RealAI domain tools. Trigger on tool skills, repo tools, realai tools, complete tools, repo-wide abilities, or /tool commands.
---

# RealAI Tools

## Overview

This skill equips RealAI hive operators and abilities with a complete toolkit for operating across the RealAI monorepo. It standardizes how tools are defined, discovered, invoked, and composed so agents can navigate, modify, test, and orchestrate any part of the tree without fragmentation.

**Authority root:** `C:\RealAI-clean` (`REALAI_HOME`). Skills and tools live under `agent_tools/`, `abilities/`, `realai/agent_tools_gold/`, and `realai/plugins/` — not under `.blackbox/`.

## Core Principles

- Tools are first-class, discoverable capabilities registered under `agent_tools/`, `abilities/`, or `realai/plugins/`.
- Every tool must declare its name, description, parameters, and side-effect level (read-only / write / destructive).
- Prefer progressive disclosure: expose metadata first, load full implementation only when needed.
- Repo-wide tools must work from any working directory and respect `.gitignore` / ignore lists.
- Compose tools into workflows rather than creating monolithic tools.
- RackUp (`Rack_em_up`) stays an HTTP consumer (`POST .../rackup-coach`). Do not vendor hive tools into Nest.

## Tool Skill Structure

Create each tool skill as:

```
agent_tools/<tool-name>/
  SKILL.md          # Frontmatter + usage instructions
  scripts/          # Executable implementations (Python, JS, shell)
  references/       # Detailed schemas, examples, error catalogs
  assets/           # Templates, configs, fixtures
```

Or, for hive abilities:

```
abilities/<ability-name>/
  ...
```

Frontmatter rules (strict):

```yaml
---
name: kebab-case-name
description: What the tool does and when an agent should invoke it. Plain scalar only. No colon-space, no angle brackets.
---
```

## Standard Repo-Wide Tool Categories

Implement or extend tools in these categories for full coverage:

### 1. Navigation & Discovery
- `list_dir` / `tree` - recursive directory listing with ignore filters
- `find_files` - glob + regex search by name or content
- `repo_map` - high-level structural summary (modules, entry points, dependencies)
- `locate_symbol` - jump to definition / references across languages

### 2. File & Content Operations
- `read_file` / `read_range` - safe partial reads for large files
- `write_file` / `edit_file` - atomic writes with backup and diff preview
- `search_replace` - multi-file search-and-replace with dry-run
- `diff_files` - unified or side-by-side diffs

### 3. Git & Version Control
- `git_status` / `git_log` / `git_diff`
- `git_branch` / `git_checkout` / `git_commit` (with conventional message helper)
- `git_stash` / `git_worktree`
- Safe guards against force-push or hard-reset unless explicitly confirmed

### 4. Build, Test & CI
- `run_tests` - pytest / jest / vitest with filtering and coverage
- `build` - pnpm / pip / docker build targets
- `lint` / `typecheck` - aggregate results across packages
- `ci_status` - query GitHub Actions or local CI

### 5. Agent & Orchestration
- `spawn_agent` - launch specialist hive operators (coder, devops, fullstack, scanner)
- `agent_status` / `agent_result`
- `tool_registry` / `ability_catalog` - list available tools/abilities and schemas
- `compose_workflow` - chain tools into a named pipeline

### 6. RealAI / Domain Specific (hive abilities)
- `cavity_scan` - run full / alt / tri cavity searches
- `model_manifest` - inspect realai-1.0, overseer, embed models (do not treat vision/escrow as LIVE)
- `provider_list` / `provider_switch`
- `memory_store` / `knowledge_query`
- `rating_update` - Glicko-2 / ladder updates for RackUp via coach HTTP
- `phase_tools` - phase4 / phase5 merge and preview helpers

### 7. Safety & Observability
- `dry_run` - preview any mutating tool
- `audit_log` - record tool invocations
- `sandbox_exec` - run untrusted code in isolated environment
- `resource_usage` - track token, CPU, disk consumption

## Creating a New Tool Skill

1. Scaffold under `C:\RealAI-clean\agent_tools\<tool-name>\` or `C:\RealAI-clean\abilities\<ability-name>\` (ordinary directories — no Blackbox CLI required).
2. Fill SKILL.md with clear trigger phrases and parameter schema.
3. Place deterministic logic in `scripts/` (prefer Python or Node for cross-platform).
4. Document edge cases and error codes in `references/`.
5. Register so `tool_registry` / `ability_catalog` discovers it automatically.
6. Validate frontmatter and scripts (lint + a dry-run sample).
7. Test with a real hive operator session before promoting.

## Invocation Patterns for Agents

When a hive operator needs repo-wide capability:

- Prefer named tools over ad-hoc shell: use tool find_files with pattern and content args
- Always request dry-run for write operations first.
- For multi-step tasks, use `compose_workflow` or spawn a specialist operator.
- After any write, re-run `git_status` and relevant tests.
- Surface progress and intermediate artifacts so the human or parent agent can intervene.

## Example Tool Skills to Implement First

1. **repo-map** - generate a clean structural overview excluding node_modules, .venv, archives, checkpoints.
2. **safe-edit** - edit with automatic backup, diff, and rollback on test failure.
3. **cross-package-test** - discover and run tests that touch a given module across the monorepo.
4. **agent-router** - decide which specialist operator (coder, devops, scanner, fullstack) is best for a task.
5. **ability-sync** - keep `abilities/` and `agent_tools/` discovery in sync.

## Integration with Live RealAI Layout

- Product home: `C:\RealAI-clean` (`REALAI_HOME`).
- Place new skills under `agent_tools/` or abilities under `abilities/`.
- Gold/reference copies may live under `realai/agent_tools_gold/` and plugins under `realai/plugins/` or `plugins/`.
- Do **not** put skills under `C:\realai\.blackbox` or any `.blackbox/` root.
- Update registry / AGENTS docs when adding or changing tools.
- Keep scanners and phase tools under their existing packages; expose thin skill wrappers.
- RackUp consumes RealAI over HTTP only — never copy hive trees into Nest.

## Validation Checklist

Before considering a tool skill complete:

- [ ] Frontmatter validates (no forbidden characters)
- [ ] Scripts are executable and idempotent where possible
- [ ] Dry-run mode exists for any write path
- [ ] Errors return structured messages agents can parse
- [ ] Works from any subdirectory of the repo root
- [ ] Documented in tool_registry / ability_catalog
- [ ] Tested against at least one real hive operator workflow
- [ ] No secrets copied into the skill pack

## Next Actions

When the user asks for a specific tool:

1. Confirm the exact capability and safety level required.
2. Scaffold the skill directory under agent_tools/ or abilities/.
3. Implement the core script.
4. Write references and examples.
5. Validate and demonstrate with a sample invocation.
