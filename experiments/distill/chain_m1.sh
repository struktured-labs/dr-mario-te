#!/bin/bash
# chain_m1.sh — M1 label campaign launch (REGISTRATION_M1_LABELS.md sec 8).
# Usage: bash chain_m1.sh launch|status
# Preconditions enforced at launch: smoke PASS line in out/smoke.log, and the
# seed block present in tools/seed_registry.py CONSUMED (grep for the owner
# tag) — the block is registered at launch, not before.
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
REG=/home/struktured/projects/dr-mario-rl/tools/seed_registry.py

launch() {
  grep -q '^\[m1-smoke\] verdict=PASS' "$HERE/out/smoke.log" || {
    echo "refusing: no smoke PASS in out/smoke.log"; exit 1; }
  grep -q 'distill-coproc M1 labels' "$REG" || {
    echo "refusing: seed block not registered in CONSUMED"; exit 1; }
  systemd-run --user --collect --unit drm-m1-l20 \
    -p MemoryMax=20G -p MemorySwapMax=0 -p Nice=10 \
    -p WorkingDirectory="$HERE" \
    bash -c "$PY -u m1_run.py l20 --workers 8"
  systemd-run --user --collect --unit drm-m1-l11m \
    -p MemoryMax=12G -p MemorySwapMax=0 -p Nice=10 \
    -p WorkingDirectory="$HERE" \
    bash -c "$PY -u m1_run.py l11m --workers 4"
  echo "launched drm-m1-l20 (8w) + drm-m1-l11m (4w)"
}

status() {
  systemctl --user --no-pager status drm-m1-l20 drm-m1-l11m 2>&1 |
    grep -E 'drm-m1|Active:' || true
  for s in L20 L11M; do
    n=$(ls "$HERE/out/labels_m1/$s" 2>/dev/null | grep -c '^seed_' || true)
    echo "$s segments: $n"
  done
  cat "$HERE/out/STATUS" 2>/dev/null || true
}

case "${1:-status}" in
  launch) launch ;;
  status) status ;;
  *) echo "usage: $0 launch|status"; exit 2 ;;
esac
