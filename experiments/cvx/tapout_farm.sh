#!/usr/bin/env bash
# TAPOUT farm. Usage: tapout_farm.sh JOBFILE NAME [WORKERS]. JOBFILE lines: "ARGS... OUT" for tapout_run.py (OUT = the
# rows file, the 6th/8th arg). Launch: systemd-run --user --unit tapout-NAME -p Nice=19 -p MemoryMax=24G tapout_farm.sh ...
# Waits (does not start new jobs) while ~/projects/dr_mario_rl/tmp/PAUSE_ALL or tmp/tapout/PAUSE exists. Restartable:
# a job whose OUT already has the expected rows (EXPECT field, first token) is skipped.
set -uo pipefail
JB=$1; NAME=$2; W=${3:-12}
CVX=$(cd "$(dirname "$0")" && pwd); TMP=$CVX/../../tmp/tapout; mkdir -p "$TMP"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
NB="$TMP/nb_${NAME}_$(date -u +%Y%m%dT%H%M%SZ)"; LOG="$TMP/farm_$NAME.log"; STATUS="$TMP/STATUS_$NAME.txt"
cd "$CVX" || exit 2
echo "RUNNING $$ $(wc -l < "$JB") jobs since $(date -u +%FT%TZ)" > "$STATUS"
run_one() {
  local n=$1; shift; local out=$1; shift
  while [ -e /home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL ] || [ -e "$TMP/PAUSE" ]; do sleep 60; done
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge "$n" ]; then echo "skip $out" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$NB/$(basename "$out" .jsonl)" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 \
    nice -n 19 "$PY" tapout_run.py "$@" 2>> "$TMP/err_$(basename "$out" .jsonl).log"
  echo "[$(date -u +%FT%TZ)] done $out rc=$? rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY NB
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
echo "DONE $(date -u +%FT%TZ)" > "$STATUS"
