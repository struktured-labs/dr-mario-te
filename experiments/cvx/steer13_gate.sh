#!/usr/bin/env bash
# STEER13 identity gate + smokes (seed 39134 block = STEER10/12 LULU block; smoke seed 36734 outside every block).
#   IDENTITY: A_fair_q00 and B_orc6_q00 (sched path + counterfactual restore) must equal FAIR's banked rows
#             (lulu = steer11 pilot couch11 rows, gb = steer8 fD_bdepD rows) on every non-stamp key.
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer13
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$CVX" || exit 2
mkdir -p steer13/gate "$TMP"
for a in A_fair_q00 B_orc6_q00_fairref; do
  NUMBA_CACHE_DIR="$TMP/nb_gate_${a}" nice -n 19 $PY steer13_run.py race $a 2.84 lulu202610b 39134 4 2 steer13/gate/lulu_$a.jsonl &
  NUMBA_CACHE_DIR="$TMP/nb_gate_${a}g" nice -n 19 $PY steer13_run.py gb $a owner202610 39134 3 2 steer13/gate/gb_$a.jsonl &
done
for a in B_14886_q00 B_14886_q03 B_v116_q00 B_v114_q00 B_v112_q00 A_a16_q04 A_r60_q04 B_orc4_q00 B_orc6_q00; do
  NUMBA_CACHE_DIR="$TMP/nb_smoke_$a" nice -n 19 $PY steer13_run.py race $a 2.84 lulu202610b 36734 2 2 steer13/gate/smoke_lulu_$a.jsonl &
done
wait
NUMBA_CACHE_DIR="$TMP/nb_smoke_gb" nice -n 19 $PY steer13_run.py gb B_v114_q00 owner202610 36734 2 2 steer13/gate/smoke_gb_B_v114_q00.jsonl
echo "gate done"
