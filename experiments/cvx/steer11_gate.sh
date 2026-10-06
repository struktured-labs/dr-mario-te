#!/usr/bin/env bash
# STEER11 identity gate on the LEGACY clock (patched vs_race / stuck_probe + steer11_run wrapper) vs the banked STEER10 /
# STEER8 FAIR rows: lulu10b s10_base (steer10/), rc10 + gb10 fD_bdepD (steer8/). Seeds 39134.. step 2.
# Launch: systemd-run --user --unit steer11-gate -p Nice=19 -p MemoryMax=8G .../steer11_gate.sh
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer11
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$CVX" || exit 2
mkdir -p steer11/gate "$TMP"
NUMBA_CACHE_DIR="$TMP/nb_gate_lb" nice -n 19 $PY steer11_run.py race s10_base 2.84 lulu202610b legacy 39134 6 2 steer11/gate/lulu10b_s10_base_legacy.jsonl &
NUMBA_CACHE_DIR="$TMP/nb_gate_a16" nice -n 19 $PY steer11_run.py race s10_A16 2.84 lulu202610b legacy 39134 4 2 steer11/gate/lulu10b_s10_A16_legacy.jsonl &
NUMBA_CACHE_DIR="$TMP/nb_gate_rc" nice -n 19 $PY steer11_run.py race s10_base 2.36 hartford legacy 39134 4 2 steer11/gate/rc10_s10_base_legacy.jsonl &
NUMBA_CACHE_DIR="$TMP/nb_gate_gb" nice -n 19 $PY steer11_run.py gb s10_base owner202610 39134 3 2 steer11/gate/gb10_s10_base.jsonl &
wait
echo "gate done"
