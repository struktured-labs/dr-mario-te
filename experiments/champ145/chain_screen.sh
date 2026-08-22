#!/bin/bash
# champion-145 screening chain: bank home-regime states, then analyze.
# Every stage gates on the previous stage's success MARKER (not shell fate),
# per the gw-price masked-crash lesson.
set -eo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
export NUMBA_CACHE_DIR=/home/struktured/projects/dr-mario-champ145-wt/tmp/numba-cache
mkdir -p "$NUMBA_CACHE_DIR"
export PYTHONPATH="$PWD/../eval47/stage2/oracle/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments"

W=${1:-12}

"$PY" screen_home_states.py --workers "$W" 2>&1 | tee out/bank_run.log
command grep -aq 'SCREEN_BANK_OK' out/bank_run.log || {
  echo 'CHAIN FAIL: bank stage marker missing' >&2; exit 1; }

"$PY" analyze_screen.py 2>&1 | tee out/analyze_run.log
command grep -aq 'ANALYZE_SCREEN_OK' out/analyze_run.log || {
  echo 'CHAIN FAIL: analyze stage marker missing' >&2; exit 1; }

echo CHAIN_OK
