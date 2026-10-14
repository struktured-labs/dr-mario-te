#!/usr/bin/env bash
# pocketclk lane: STEER14 arms at the Pocket copro clock (steer14_pocket.py), paired by seed with the banked MiSTer rows
# (dr-mario-h16-wt experiments/cvx/steer14/main). Jobs of 50 LULU races, W workers, restartable (complete files skipped).
# A job is not started while dr_mario_rl/tmp/PAUSE_ALL exists; the companion unit grok-pocketclk-pause SIGSTOPs this unit.
set -uo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
O=/home/struktured/projects/dr_mario_rl/tmp/pocketclk/steer14; mkdir -p $O
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${W:-6}; N=${N:-2000}; NB=$O/nb_$(date -u +%Y%m%dT%H%M%SZ)
JB=$O/jobs.txt; : > $JB
echo "K1 S14_d4_k32 44300 $O/ctl_K1_S14_d4_k32_44300.jsonl" >> $JB          # identity control (K = 1)
for arm in ${ARMS:-S14_d4_k32 S14_d16_k32 S14_d4_u8}; do
  for ((i = 0; i < N / 50; i++)); do lo=$((44300 + 100 * i)); echo "PK $arm $lo $O/pk_${arm}_$lo.jsonl" >> $JB; done; done
run_one() {
  local mode=$1 arm=$2 lo=$3 out=$4
  [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ] && return 0
  while [ -e /home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL ]; do sleep 10; done
  local k=""; [ "$mode" = K1 ] && k=1.0
  POCKET_K=${k:-$(python3 -c 'print(85.909088/(601.362942/11))')} NUMBA_CACHE_DIR="$NB/${arm}_$lo" OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 nice -n 19 $PY "$R/tools/pocketclk/steer14_pocket.py" race "$arm" 2.84 \
    lulu202610b "$lo" 50 2 "$out.part" 2>> "$O/err_$(basename "$out" .jsonl).log" && mv "$out.part" "$out"
  echo "$(date -u +%FT%TZ) $mode $arm $lo rc=$? rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> $O/farm.log
}
export -f run_one; export O PY NB R
echo "$(date -u +%FT%TZ) start $(wc -l < $JB) jobs W=$W git $(git -C "$R" rev-parse --short=8 HEAD)" >> $O/farm.log
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < $JB
echo "$(date -u +%FT%TZ) FARM DONE" >> $O/farm.log
