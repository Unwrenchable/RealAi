# RealAI Hive: learning from the bot team

> **SECURITY REVIEW REQUIRED:** `realai/hive_records/redact.py` must be reviewed by Security
> **before this PR is merged and before the first ingest.** The scanner is a heuristic safety net.
> Bots must still keep secrets out of records at the source.

## Status and scope

- Hive rows are for **v3 training only**. They are **not used in v2**. The v2 inputs stay pinned:
  `training/data/ability_surface.jsonl` SHA256
  `41D31FEE78AD299FAE359409805D2C5ECC2C4101342978270E04212CD6A12CE0` and
  `scripts/train_lora_local.py`. Nothing here modifies either file.
- No PEFT run, no weights, no external API keys. Everything is local files plus Python stdlib.
- Package is `realai/hive_records/` (not `realai/hive/`: `realai/hive.py` already exists and a
  package of the same name would shadow it and break `from realai.hive import ...`).

## Flow

```
bots (Chief, QA Lead, Release & DevOps)
   |  one hive.v1 JSONL line per completed task
   v
Chief's shared bot store:   hive/inbox/YYYY-MM-DD/<bot>.jsonl      (raw, never in git, 90-day retention)
   |  scripts/hive_ingest.py <inbox>   (scheduled; validate -> redact -> dedupe -> map)
   v
training/data/_staging/hive_candidates_<date>.jsonl                (ability_surface-shaped rows)
training/data/_staging/hive_candidates_<date>.manifest.jsonl       (id, content_hash, bot, category, source)
training/data/_staging/hive_rejects_<date>.json                    (reasons only, never content)
   |  QA Lead reviews staging, opens a PR, travis gives the final OK
   v
training/data/hive_ops.jsonl                                        (promoted rows; CI must pass; v3 only)
```

Promotion is never automatic. `hive_ingest.py` never writes `hive_ops.jsonl` or `ability_surface.jsonl`.
`training/data/_staging/` is git-ignored: raw-derived candidates are not committed.

## Record schema: `hive.v1`

One JSON object per line:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | str | exactly `"hive.v1"` |
| `id` | str | UUID |
| `ts` | str | ISO-8601 **with** UTC offset (`Z` ok) |
| `bot` | obj | `{name, id}`, both non-empty strings |
| `product` | str | e.g. `RealAI` |
| `task` | obj | `{ask (<=2000 chars), category}`; category is `pr_triage\|vuln_triage\|ci_fix\|dep_update\|deploy\|data\|other` |
| `actions` | list | 1-50 of `{step (int>=1), tool_kind, summary (<=500)}`; tool_kind is `git\|gh\|npm\|pnpm\|pytest\|http\|other` |
| `verification` | obj | **required**: `{command (<=500), result pass\|fail, evidence (<=500)}` |
| `outcome` | str | `done\|partial\|blocked` |
| `blockers` | list[str] | may be empty |
| `links` | list[str] | `http(s)` URLs only |
| `reviewer`, `approval` | str or null | optional |
| `redaction` | obj | `{scanned: true, scanner_version}` |

Unknown fields are rejected (an extra field is an easy place to hide a secret). A record with no
verification is always rejected: unverified work is not training signal.

## Mapping to `ability_surface.jsonl`

Existing rows are exactly `{"messages": [{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]}`
with no other keys. Hive rows use the same shape: the user turn is
`How did the bot team handle this <category> task for <product>: <ask>` and the assistant turn
carries outcome, steps, the verification command and result, blockers, links and approval.
Provenance (id, content hash, bot, category, source file and line) goes to the manifest, not the row.

## Redaction policy: reject, never rewrite

Any record that matches is dropped whole, and only a reason code is recorded:
token prefixes (`sk-`, `ghp_`/`gho_`/..., `github_pat_`, `xox*`, `AKIA`, `Bearer`), PEM private key
blocks, connection URLs (postgres, mysql, mongodb, mongodb+srv, redis, or any `user:pass@host`),
`.env`-style `KEY=VALUE` secret lines, high-entropy strings, base58 64-byte Solana keys (also
64-number byte arrays and key-context 64-hex strings), and 12/24-word seed-phrase-like runs.
Git SHAs, SHA-256 digests, UUIDs and 32-byte public keys are allowed. The mapped training row is
scanned again after mapping.

Known limits (for the Security review): the seed-phrase check is a heuristic (no wordlist bundled);
the entropy check can false-positive on long random-looking identifiers, which is the safe direction.

## Ingest CLI

```
python scripts/hive_ingest.py <inbox> [--date YYYY-MM-DD] [--out-dir DIR] [--allow-bot NAME ...] [--dry-run]
python scripts/hive_ingest.py <inbox> --prune-older-than-days 90            # lists only
python scripts/hive_ingest.py <inbox> --prune-older-than-days 90 --apply    # deletes raw inbox files older than 90 days
```

- Allowlist defaults to Chief, QA Lead, and Release & DevOps (file stem and `bot.name` must both match).
- Dedupe is by `id` and by content hash (ignores id, ts, bot.id), also across earlier staging runs, so re-runs are idempotent.
- `--dry-run` validates and prints counts; it writes nothing.
- Pruning never deletes unless `--apply` is passed. Get travis's GO before the first `--apply`.

## Tests

`python -m pytest -q tests/test_hive_schema.py tests/test_hive_redact.py tests/test_hive_ingest.py`

Fixtures are synthetic; fake secrets are assembled at runtime and must be rejected.
