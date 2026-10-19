# repo_search (hive tool 32) and the repo corpus

Approved 2026-10-19. Travis's own GitHub repos feed RealAI through a **read-only local mirror**; facts about them are
always looked up with `repo_search`, never memorised.

## Tool

`repo_search(action=list|grep|read, repo?, path?, query?, start_line?, end_line?)` in `realai/hive_tools/repo_search.py`.

* Root: `REALAI_REPO_MIRROR`, else `D:\ARCHIVE\repo-mirror` on Windows. Nothing outside the root is ever read.
* Allowlist: `REPOS` (approved tiers). LustLink, reverse-phone-search, Productivitybot and Domain-bot are excluded;
  Token-scalper is refusal-only (mirrored for nothing, never searched); duplicates (atomicfizzcaps,
  ATOMIC-...-GPS) are replaced by the canonical `ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main`.
* Blocked: `.git`, vendor/build dirs, `.env*` (except `.env.example/.sample/.template`), `.npmrc`, keys, credential
  and wallet files, binaries, files > 512 KB, files the mirror's secret scan flagged (`repo_mirror_manifest.json`
  `blocked`), `..`/absolute/drive paths and symlinks out of the repo.
* Output capped at ~4 KB (12 grep hits, 60 read lines, 200 chars per line); every line is passed through secret
  redaction (`<redacted:type>`). No network, no writes; deterministic, so the self_data verifier recomputes it.
* Live catalog: default **on** (core tool, not behind `REALAI_HIVE_TOOLS`); `REALAI_REPO_SEARCH=0` removes it.
* Distractors: `CONFUSABLE["repo_search"]` = module_lookup, plugin_lookup, memory_search, web_search,
  request_approval, list_agents (and repo_search is a look-alike of module/plugin lookup, memory_search, request_approval).

## Spot-check suite `repos`

`python -m realai.training.spotcheck --suite repos` (11 checks, separate from core16 and extended; never the
promotion gate). Facts are computed from the same tool at check time; with no mirror, the model must say so.
Questions are part of `eval_prompts()`, so `exclude_eval_prompts` keeps them out of training.
