#!/usr/bin/env bash
# STEER12 miss-dose calibration (BEFORE the prereg): pills-to-clear overhead vs ex_perfect on 60 seeds OUTSIDE the
# STEER10/12 blocks (36734-36852 step 2; declared reuse, champion-search lane block). LULU race couch11. Read: pills only.
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer12
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$CVX" || exit 2
mkdir -p steer12/qcal
for a in ex_perfect q00 ex_q01 ex_q02 ex_q03 ex_q04 ex_q06 ex_q08; do
  NUMBA_CACHE_DIR="$TMP/nb_qcal_$a" nice -n 19 $PY steer12_run.py race $a 2.84 lulu202610b 36734 60 2 steer12/qcal/lulu12_$a.jsonl &
done
wait
echo "qcal done"
