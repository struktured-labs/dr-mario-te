#!/usr/bin/env bash
# STEER10 identity gate: s10_base == banked fD_bdepD rows (gb10 / rc10 / lulu10 old fit, 3 seeds each) + a lulu202610b
# smoke. Launch: systemd-run --user --unit steer10-gate -p Nice=19 -p MemoryMax=8G .../steer10_gate.sh
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer10
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$CVX" || exit 2
mkdir -p steer10/gate
NUMBA_CACHE_DIR="$TMP/numba10_gate_gb" nice -n 19 $PY steer10_run.py gb s10_base owner202610 39134 3 2 steer10/gate/gb10_s10_base.jsonl &
NUMBA_CACHE_DIR="$TMP/numba10_gate_rc" nice -n 19 $PY steer10_run.py race s10_base 2.36 hartford 39134 3 2 steer10/gate/rc10_s10_base.jsonl &
NUMBA_CACHE_DIR="$TMP/numba10_gate_lu" nice -n 19 $PY steer10_run.py race s10_base 2.56 hartford 39134 3 2 steer10/gate/lulu10_s10_base.jsonl &
NUMBA_CACHE_DIR="$TMP/numba10_gate_lb" nice -n 19 $PY steer10_run.py race s10_base 2.84 lulu202610b 39134 2 2 steer10/gate/smoke_lulu10b_s10_base.jsonl &
wait
echo "gate done"
