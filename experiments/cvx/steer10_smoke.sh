#!/usr/bin/env bash
# STEER10 arm smoke (NOT analysed): every arm runs in both instruments and its rule is active. Seed 36734 (outside the
# STEER10 analysis blocks). Launch: systemd-run --user --unit steer10-smoke -p Nice=19 -p MemoryMax=12G .../steer10_smoke.sh
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer10
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$CVX" || exit 2
for a in s10_A16 s10_R60 s10_R120 s10_A16R120; do
  NUMBA_CACHE_DIR="$TMP/numba10_smoke_${a}_r" nice -n 19 $PY steer10_run.py race $a 2.84 lulu202610b 36734 2 2 steer10/gate/smoke_lulu10b_${a}.jsonl &
  NUMBA_CACHE_DIR="$TMP/numba10_smoke_${a}_g" nice -n 19 $PY steer10_run.py gb $a owner202610 36734 2 2 steer10/gate/smoke_gb10_${a}.jsonl &
done
wait
echo "smoke done"
