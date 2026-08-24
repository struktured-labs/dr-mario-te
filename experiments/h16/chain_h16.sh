#!/bin/bash
# chain_h16.sh — H16 endpoint chain (REGISTRATION_H16.md sec 6).
# Usage:  bash chain_h16.sh launch   (from anywhere; requires SHEET_OK)
#
# Two systemd --user units:
#   drm-h16-guard : 1,000 clean L11 pairs, 4 workers (concurrent, cheap;
#                   stopped automatically by an e1 FUTILITY_STOP)
#   drm-h16-main  : e1 (600 L20 pairs, runner-level futility) -> e2
#                   dose-matched null -> analyze
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python

launch() {
  grep -q '^SHEET_OK' "$HERE/out/gate_sheet.log" || {
    echo "refusing: no SHEET_OK in out/gate_sheet.log"; exit 1; }
  systemd-run --user --collect --unit drm-h16-guard \
    -p MemoryMax=12G -p MemorySwapMax=0 -p Nice=10 \
    -p WorkingDirectory="$HERE" \
    "$PY" -u run_h16.py guard --workers 4
  systemd-run --user --collect --unit drm-h16-main \
    -p MemoryMax=24G -p MemorySwapMax=0 -p Nice=10 \
    -p WorkingDirectory="$HERE" \
    bash -c "$PY -u run_h16.py e1 --workers 14 \
             && $PY -u run_h16.py e2 --workers 14 \
             ;  $PY -u run_h16.py analyze"
  echo "launched drm-h16-guard + drm-h16-main"
}

status() {
  systemctl --user --no-pager status drm-h16-main drm-h16-guard 2>&1 |
    grep -E 'drm-h16|Active:' || true
  ls "$HERE"/out/e1 2>/dev/null | grep -c '^pair_' | sed 's/^/e1 pairs: /'
  ls "$HERE"/out/e2 2>/dev/null | grep -c '^pair_' | sed 's/^/e2 pairs: /'
  ls "$HERE"/out/guard 2>/dev/null | grep -c '^pair_' | sed 's/^/guard pairs: /'
}

case "${1:-launch}" in
  launch) launch ;;
  status) status ;;
  *) echo "usage: $0 launch|status"; exit 2 ;;
esac
