#!/usr/bin/env bash
# STEER14 identity gate + consistency + positive control + smokes (PREREG_STEER14.md sec. 2). Seeds: STEER13's block
# 41100.. for the identity (compared against STEER13's banked rows) and the positive control; smoke seed 36734 (2 games).
# No STEER14 main-block seed. Launch as a steer14- unit (throttle: PAUSE_STEER14 / PAUSE_ALL, cap 10):
#   systemd-run --user --unit steer14-gate -p MemoryMax=16G -p MemorySwapMax=0 -p Nice=19 .../steer14_gate.sh
# Then: python steer14_identity.py  (exit 0 = PASS) -> steer14/gate/identity.txt
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer14
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
NB="$TMP/nb14gate_$(date -u +%Y%m%dT%H%M%SZ)"
cd "$CVX" || exit 2
mkdir -p steer14/gate "$TMP"
rm -f steer14/gate/*.jsonl
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1
run() { local n=$1; shift; NUMBA_CACHE_DIR="$NB/$n" nice -n 19 "$PY" steer14_run.py "$@" 2>> "$TMP/gate_err_$n.log"; echo "$n rc=$?"; }
# IDENTITY (slam OFF) vs STEER13 B_v116_qb
run id_l  race S14_id_v116 2.84 lulu202610b 41100 50 2 steer14/gate/id_lulu_S14_id_v116.jsonl &
run id_r  race S14_id_v116 2.36 hartford    41100 25 2 steer14/gate/id_rc_S14_id_v116.jsonl &
run id_g  gb   S14_id_v116 owner202610      41100 25 2 steer14/gate/id_gb_S14_id_v116.jsonl &
# CONSISTENCY: C13_14886 IS the tempo reference (tempo 0 on every pill); DETERMINISM: the same arm twice is identical
run c0    race C13_14886   2.84 lulu202610b 41100 10 2 steer14/gate/cons_lulu_C13_14886.jsonl &
run dt1   race S14_d4_k32  2.84 lulu202610b 41100 10 2 steer14/gate/det1_lulu_S14_d4_k32.jsonl &
run dt2   race S14_d4_k32  2.84 lulu202610b 41100 10 2 steer14/gate/det2_lulu_S14_d4_k32.jsonl &
# POSITIVE CONTROL: the A16 arm must differ from the DIST4 rows on the same seeds
run pc    race S14_d16_k32 2.84 lulu202610b 41100 10 2 steer14/gate/pc_lulu_S14_d16_k32.jsonl &
wait
# SMOKES (every arm family / cell active)
run sm_k8  race S14_d16_k8      2.84 lulu202610b 36734 2 2 steer14/gate/smoke_lulu_S14_d16_k8.jsonl &
run sm_q4  race S14_d4_k32_q02  2.84 lulu202610b 36734 2 2 steer14/gate/smoke_lulu_S14_d4_k32_q02.jsonl &
run sm_q16 race S14_d16_k16_q02 2.84 lulu202610b 36734 2 2 steer14/gate/smoke_lulu_S14_d16_k16_q02.jsonl &
run sm_g   gb   S14_d16_k16     owner202610      36734 2 2 steer14/gate/smoke_gb_S14_d16_k16.jsonl &
run sm_r   race S14_d16_k16     2.36 hartford    36734 2 2 steer14/gate/smoke_rc_S14_d16_k16.jsonl &
run sm_v   race C13_v116        2.84 lulu202610b 36734 2 2 steer14/gate/smoke_lulu_C13_v116.jsonl &
wait
echo "gate done"
