# RealAI Git Contribution Policy

**Document version:** 1.0.0  
**Date:** 2026-09-15  
**Audience:** Cloud / Craft agents, Copilot, human maintainers  
**Status:** LOCKED — default integration branch for this repo  
**Related:** `CONTRIBUTING.md`, `README.md` (live branch), foreign product repos (Rack_em_up, Atomic Fizz)

---

## 0. Default integration branch

| Repo | Default integration branch | Treat as |
|------|----------------------------|----------|
| **RealAI** (`Unwrenchable/RealAi`) | `live/realai-clean-20260911` | **main** for merges |
| Foreign product repos (Rack_em_up, Atomic Fizz, Caps, …) | **That repo’s GitHub default** (usually `main`) | Same rule, their default |

RealAI PRs **must** open against `live/realai-clean-20260911`.  
Do not open RealAI work against `main` unless the task is an **explicit** `main` ↔ live sync.

---

## 1. Cloud / Craft PRs

1. Branch from `live/realai-clean-20260911` (or the foreign repo’s default).
2. Open the PR **against that same default**.
3. After merge, **delete the head branch**.
4. Do not leave `cursor/*` (or other agent) branches after close, hold, or merge.

Orphan head branches break the “always contribute into live” contract. Close or merge, then delete.

---

## 2. `main` is legacy here

On RealAI, `main` is **legacy** unless a task explicitly syncs it with live.

| Do | Do not |
|----|--------|
| Merge features into `live/realai-clean-20260911` | Treat `main` as the daily integration branch |
| Sync `main` only when asked | Open Cloud/Craft PRs at `main` “because that’s usual” |
| Prefer live in docs, CI, and agent base-branch settings | Leave work sitting on `cursor/*` after the PR is done |

---

## 3. Foreign product repos

Rack_em_up, Atomic Fizz, and other product trees use **their** default branch the same way RealAI uses live:

- Open PRs against **that repo’s** default (`main` unless the remote says otherwise).
- Delete the head branch after merge.
- Do not leave `cursor/*` orphans after close/hold.
- Learned knowledge / plugin stubs from those repos are written **back into RealAI** (`realai/catalog/learned/`, `realai/plugins/<slug>_coach/`) — they do not rewrite the foreign default branch unless the task is a PR **in that foreign repo**.

---

## 4. Git-learn (offline)

`python -m realai.learn_git` / Craft `/learn` scans a git source (local path, `owner/repo`, or HTTPS URL) **across all branches** (default; `--max-branches` cap, `--max-files` cap), writes a learning packet, and optionally scaffolds a plugin stub. It **must not** start heal, GPU, or the orchestrator. Clone cache under `realai/.learn_cache/` is disposable; never delete user data. Clones use `--no-single-branch` (not default-tip-only).

See `docs/learning/README.md`.
