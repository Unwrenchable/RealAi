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

## Mirror (`tools/repo_mirror.py`)

`python -m tools.repo_mirror --dry-run` prints the plan (no network, no writes). A real run is a separately approved
step: `python -m tools.repo_mirror --out D:\ARCHIVE\repo-mirror`.

* `--out` must be under `D:\ARCHIVE`; anything else is refused. Only the searchable allowlist is cloned.
* `git clone --depth 1 --filter=blob:none --no-checkout --sparse` + non-cone sparse patterns, so `.env*`, `.npmrc`,
  keys, credential/wallet files, vendor/build dirs and binaries are never fetched or written. `core.symlinks=false`,
  public HTTPS only, `GIT_TERMINAL_PROMPT=0`.
* Existing repo dirs are skipped (never overwritten); the manifest is backed up before it is rewritten; nothing is deleted.
* `repo_mirror_manifest.json`: commit, SHA256 + size per file, `blocked` (files > 1 MB, secret-scan hits).
  `secrets-report-<stamp>.json`: secret **types** and paths only. `ACTIONS.log`: one line per step.

## Dataset adapter `repo_corpus` (off by default)

`realai/training/dataset_builder/adapters_repo.py`; PC config entry `repo_corpus` has `"enabled": false` until the run is
approved. Every factual row is user -> `repo_search` (executed at build time, offline) -> answer restating the tool output:
README overview, top-level listing, where a def/class/function is defined, the first lines of it, which repo has X
(only when exactly one repo matches), and README-title edits through `request_approval` (RealAi: filed PENDING;
other repos: REFUSED as outside the workspace; never executed or claimed done).

Money repos (Token-scalper, FizzSwap, cookbook, Atomic Fizz, Cue-guard): trade / swap / send / deploy / charge asks are
refusal rows only (optionally after a read-only look); they never file `request_approval`, because the gate's money
regex does not cover buy/swap/deploy commands. Token-scalper is never opened.

Caps: `per_repo_share` 0.25 of this source's rows per repo (money refusals exempt) and `max_source_share.repo_corpus`
0.15 of the mix (a capped source with no rows no longer loosens the other caps). Hold-out by repo: rows about
crispy-octo-guacamole and BlueScreenHelp carry `meta.split = "eval"` and go to eval only (`totals.eval_holdout`).

## self_data: `--seed-topics` and `filter` (v2 + repo_search)

* `python -m realai.training.self_data generate ... --seed-topics ecosystem_index.json README.md` loads topics
  (.json/.jsonl/.md/.txt; headings, title/name/topic keys) and steers each proposal batch with 6 of them. Topics equal to
  a spot-check question are dropped, and proposed questions equal to a spot-check question (core, extended, repos)
  are skipped (`eval_prompt_skipped`). `repo_search` is a self-play target (seeds name the mirrored repos).
* `python -m realai.training.self_data filter <files> [--teacher-prefix qwen3-30b-a3b] [--archive DIR] [--recompute] [--write]`
  is the in-repo port of the round-2 30B filter: failed last tool, rackup payload keys/values, plus repo_search
  (ungrounded cited paths, secrets or redaction markers, excluded repos, stale vs the mirror with `--recompute`) and
  `money_approval_filed` (a pending request_approval for a buy/swap/deploy/charge/wallet command). Report-only by default;
  `--write` keeps the raw as `.jsonl.raw` (or `.pre-v3`), copies it to `--archive`, and never overwrites.
* The verifier also rejects repo_search answers that cite paths missing from the tool output or repeat a redaction marker.
