#!/usr/bin/env bash
# STEER12 identity gate (lat0 / q00 must equal FAIR's banked rows) + one smoke game per arm (seed 36734, outside the blocks).
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer12
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$CVX" || exit 2
mkdir -p steer12/gate "$TMP"
for a in lat0 q00; do
  NUMBA_CACHE_DIR="$TMP/nb_gate_$a" nice -n 19 $PY steer12_run.py race $a 2.84 lulu202610b 39134 4 2 steer12/gate/lulu12_$a.jsonl &
  NUMBA_CACHE_DIR="$TMP/nb_gate_${a}r" nice -n 19 $PY steer12_run.py race $a 2.36 hartford 39134 3 2 steer12/gate/rc12_$a.jsonl &
  NUMBA_CACHE_DIR="$TMP/nb_gate_${a}g" nice -n 19 $PY steer12_run.py gb $a owner202610 39134 3 2 steer12/gate/gb12_$a.jsonl &
done
wait
for a in lat_m2 lat_m4 lat_m6 lat_ceil ex_perfect ex_q02 ex_q03 ex_q05; do
  NUMBA_CACHE_DIR="$TMP/nb_smoke_$a" nice -n 19 $PY steer12_run.py race $a 2.84 lulu202610b 36734 1 2 steer12/gate/smoke_lulu12_$a.jsonl &
  NUMBA_CACHE_DIR="$TMP/nb_smoke_${a}g" nice -n 19 $PY steer12_run.py gb $a owner202610 36734 1 2 steer12/gate/smoke_gb12_$a.jsonl &
done
wait
echo "gate done"
