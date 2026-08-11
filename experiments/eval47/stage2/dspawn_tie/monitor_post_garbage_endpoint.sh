#!/usr/bin/env bash
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=${1:-"$HERE/out/post_garbage_endpoint/evaluation"}

printf 'endpoint_out %s\n' "$OUT"
if [[ ! -d "$OUT" ]]; then
  printf 'state NOT_STARTED (directory absent)\n'
  pgrep -af '[r]un_post_garbage_v8_endpoint.py' || true
  exit 0
fi

segments=$(find "$OUT" -maxdepth 1 -type f -name 'seg_*.jsonl' | wc -l)
rows=$(find "$OUT" -maxdepth 1 -type f -name 'seg_*.jsonl' -exec wc -l {} + \
  | awk '$2 != "total" {n+=$1} END {print n+0}')
summaries=$(find "$OUT" -maxdepth 1 -type f -name 'seg_*.summary.json' | wc -l)
printf 'progress rows=%s/9000 segments=%s summaries=%s\n' "$rows" "$segments" "$summaries"

if [[ -f "$OUT/META.json" ]]; then
  printf 'meta_sha256 '
  sha256sum "$OUT/META.json" | awk '{print $1}'
else
  printf 'meta MISSING\n'
fi

latest=$(find "$OUT" -maxdepth 1 -type f -name 'seg_*.summary.json' \
  -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)
if [[ -n "$latest" ]]; then
  printf 'latest_summary %s\n' "$latest"
  sed -n '1,120p' "$latest"
fi

printf 'processes\n'
pgrep -af '[r]un_post_garbage_v8_endpoint.py' || true
printf 'storage\n'
du -sh "$OUT"
df -h "$OUT" | sed -n '1,2p'
