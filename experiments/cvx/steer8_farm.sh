#!/usr/bin/env bash
# STEER8a (PREREG_STEER8a.md) then STEER8b (PREREG_STEER8b.md), queued BEHIND steer7b-farm. Launch DETACHED:
#   systemd-run --user --unit steer8-farm -p MemoryMax=20G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer8_farm.sh
# 8 workers (coordinator: Quartus has priority). Phase A = 8a (108 jobs), audit, analysis; phase B = 8b.
# STEER8_PHASES=A runs 8a only (8b was AMENDED before it ran; its farm is steer8b_farm.sh).
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer7
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER8_WORKERS:-8}
cd "$CVX" || exit 2
LOG="$TMP/farm8.log"; JA="$TMP/jobs8a.txt"; JB="$TMP/jobs8b.txt"
echo "[$(date -u +%FT%TZ)] steer8 farm armed, waiting for steer7b-farm" >> "$LOG"
[ "${STEER8_DRYRUN:-0}" = 1 ] || while [ "$(systemctl --user is-active steer7b-farm 2>/dev/null)" = "active" ]; do sleep 60; done
echo "[$(date -u +%FT%TZ)] steer8 farm start, workers $W, git $(git rev-parse --short=8 HEAD)" >> "$LOG"

gbjobs() {  # arm  n_chunks_kind(full|600)
  local arm=$1 kind=$2 i
  for i in $(seq 0 11); do echo "$arm steer8_run.py gb $arm owner202610 $(( 39134 + 100 * i )) 50 2 steer8/gb10_${arm}_${i}.jsonl"; done
  if [ "$kind" = full ]; then
    for i in $(seq 12 17); do echo "$arm steer8_run.py gb $arm owner202610 $(( 39134 + 100 * i )) 50 2 steer8/gb10_${arm}_${i}.jsonl"; done
    for i in $(seq 0 11); do echo "$arm steer8_run.py gb $arm owner202610 $(( 33000 + 100 * i )) 50 2 steer8/gb10_${arm}_$(( 18 + i )).jsonl"; done
  fi
}
racejobs() {  # arm  lulu(1|0)
  local arm=$1 lulu=$2 i
  for i in $(seq 0 11); do
    echo "$arm steer8_run.py race $arm 2.36 $(( 39134 + 100 * i )) 50 2 steer8/rc10_${arm}_${i}.jsonl"
    [ "$lulu" = 1 ] && echo "$arm steer8_run.py race $arm 2.56 $(( 39134 + 100 * i )) 50 2 steer8/lulu10_${arm}_${i}.jsonl"
  done
}
{ for a in fA fD; do gbjobs $a full; racejobs $a 1; done; } > "$JA"
{ for a in fD_sB_dep fD_sB_ref fD_sC; do gbjobs $a full; racejobs $a 1; done
  for a in fD_ehb0 fD_hang0; do gbjobs $a 600; racejobs $a 0; done; } > "$JB"
NA=$(wc -l < "$JA"); NB=$(wc -l < "$JB")
[ "$NA" -eq 108 ] && [ "$NB" -eq 210 ] || { echo "[$(date -u +%FT%TZ)] FATAL job lists $NA/$NB, expected 108/210" >> "$LOG"; exit 3; }
[ "${STEER8_DRYRUN:-0}" = 1 ] && { echo "dry run: $NA + $NB jobs"; exit 0; }
mkdir -p steer8

run_one() {
  local tag=$1; shift
  local out=${@: -1}
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/numba8_$tag" nice -n 19 "$PY" "$@" 2>> "$TMP/err8_$(basename "$out" .jsonl).log"
  echo "[$(date -u +%FT%TZ)] done $out rc=$? rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY

audit() {  # jobs expected_rows
  local short=0 total=0 n line out
  while read -r line; do
    out=${line##* }; n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
    [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }
  done < "$1"
  [ "$short" -eq 0 ] && [ "$total" -eq "$2" ]
}

xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JA"
if audit "$JA" 5400; then
  echo "[$(date -u +%FT%TZ)] 8a audit OK 5400 rows; analysis" >> "$LOG"
  nice -n 19 "$PY" analyze_steer8a.py > steer8/analysis_8a.txt 2>> "$LOG"
  echo "[$(date -u +%FT%TZ)] 8a DONE (steer8/analysis_8a.txt)" >> "$LOG"
else
  echo "[$(date -u +%FT%TZ)] FATAL 8a completion audit" >> "$LOG"
fi
[ "${STEER8_PHASES:-AB}" = A ] && { echo "[$(date -u +%FT%TZ)] phase A only: stop" >> "$LOG"; exit 0; }
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
if audit "$JB" 10500; then
  echo "[$(date -u +%FT%TZ)] 8b audit OK 10500 rows; analysis" >> "$LOG"
  nice -n 19 "$PY" analyze_steer8b.py > steer8/analysis_8b.txt 2>> "$LOG"
  echo "[$(date -u +%FT%TZ)] 8b DONE (steer8/analysis_8b.txt)" >> "$LOG"
else
  echo "[$(date -u +%FT%TZ)] FATAL 8b completion audit" >> "$LOG"; exit 4
fi
