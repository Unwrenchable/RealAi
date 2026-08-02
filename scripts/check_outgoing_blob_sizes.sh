#!/usr/bin/env bash
set -euo pipefail

# Fail if any blob larger than 100 MB exists in commits ahead of the upstream branch.
limit_bytes=100000000

upstream="${1:-@{upstream}}"

if ! git rev-parse --verify "$upstream" >/dev/null 2>&1; then
  echo "ERROR: Upstream '$upstream' not found. Pass an explicit ref, e.g. origin/analysis-clean." >&2
  exit 2
fi

large_blobs=$(git rev-list --objects "$upstream"..HEAD \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk -v limit="$limit_bytes" '$1=="blob" && $3>limit {printf "%.2f MB\t%s\n",$3/1048576,$4}')

if [[ -n "$large_blobs" ]]; then
  echo "Push blocked: found blobs larger than 100 MB in outgoing commits:" >&2
  echo "$large_blobs" >&2
  exit 1
fi

echo "OK: no outgoing blobs larger than 100 MB."
