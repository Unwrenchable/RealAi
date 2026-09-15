# Git-learn packets

Offline, static pipeline: scan a git tree **on every branch** → learning packet → optional coach plugin stub.

**Source is a local folder OR a git URL.** A path that exists on disk is always `kind: local` (no clone). A GitHub `owner/repo` or HTTPS URL is cloned into a disposable cache (`kind: remote`).

| Entry | Starts heal / GPU / orch? |
|-------|---------------------------|
| `python -m realai.learn_git <local-folder-OR-git-URL> [--write] [--refresh] [--all-branches] [--max-branches N] [--max-files N]` | **No** |
| Craft `/learn <local-folder-OR-git-URL> [--write] [--all-branches] [--max-branches N] [--max-files N]` | **No** |
| Hive `realai learn <local-folder-OR-git-URL> [--write] [--all-branches] [--max-branches N] [--max-files N]` | **No** |

Examples:

```text
python -m realai.learn_git C:\path\to\folder
python -m realai.learn_git "C:\path with spaces\repo"
/learn C:\path\to\folder
/learn ./my-repo
/learn https://github.com/org/repo
realai learn C:\path\to\folder
```

`--all-branches` is **on by default** (Travis default). Use `--no-all-branches` to scan only the current checkout.

Packets land in `realai/catalog/learned/<slug>/packet.json` (canonical) and a copy at `docs/learning/<slug>.json`.

Plugin stubs (only with `--write`) mirror `atomicfizz_coach` / `rackup_coach`:

`realai/plugins/<slug>_coach/` — `manifest.yaml` + `invoke` + stub abilities.

## What gets scanned

- **Remote clone / refresh** uses `git clone --no-single-branch` (plus `--depth 1` for branch *tips*, not a single-branch clone). Cache reuse always `git fetch --all --tags` and expands old `--single-branch` refspecs so every remote head is present.
- **Multi-branch scan** walks `refs/heads` and remotes (cap `--max-branches`, default 40) with `git ls-tree` / `git show` — it does **not** check out each branch into the working tree.
- Identical content is deduplicated; fingerprints keep `seen_on_branches`. The packet `summary` records `branches_seen`, `branch_counts`, `truncated`, and `branches_truncated`.
- **File cap** default is 5000 unique fingerprints (`--max-files`). Noise is still skipped: `node_modules`, venv, binaries, lockfiles, `dist` / `build`, etc. Normal source directories are not skipped.
- Clone cache: `realai/.learn_cache/` (gitignored, disposable). Never deletes user data.

Local paths that are real git repos get the same multi-branch walk (`kind: local`). A non-git folder is scanned as the working tree only (`kind: local` still).
