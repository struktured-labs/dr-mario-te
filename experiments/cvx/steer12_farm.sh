#!/usr/bin/env bash
# STEER12 farm (PREREG_STEER12.md). PHASE = main. Launch DETACHED under the steer12- unit prefix (the steer12-throttle
# PAUSE/cap switch SIGSTOPs python processes in steer12-*.service cgroups):
#   systemd-run --user --unit steer12-farm-main -p MemoryMax=24G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer12_farm.sh main
# PAUSE: touch /home/struktured/projects/dr_mario_rl/tmp/steer12/PAUSE  (or the shared .../tmp/PAUSE_ALL)
# 8 workers (shared box, the throttle caps runnable at 8). Jobs of 50 games; complete files are skipped (restartable);
# no wall-clock timeouts anywhere (a SIGSTOP is safe). Audit: every job file has exactly 50 rows.
#   main     8 arms x (LULU race 1,200 + owner race 600 + gate b 600) = 19,200 games (steer12_jobs.py main)
set -uo pipefail
PHASE=${1:?phase}
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer12
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER12_WORKERS:-8}
cd "$CVX" || exit 2
mkdir -p "$TMP" steer12/$PHASE
LOG="$TMP/farm12_$PHASE.log"; JB="$TMP/jobs12_$PHASE.txt"
echo "[$(date -u +%FT%TZ)] steer12 farm $PHASE start, workers $W, git $(git rev-parse --short=8 HEAD)" >> "$LOG"
$PY steer12_jobs.py "$PHASE" > "$JB" || { echo "[$(date -u +%FT%TZ)] FATAL job list" >> "$LOG"; exit 3; }
N=$(wc -l < "$JB")
echo "[$(date -u +%FT%TZ)] $N jobs ($(( N * 50 )) games)" >> "$LOG"
[ "${STEER12_DRYRUN:-0}" = 1 ] && { echo "dry run: $N jobs ($(( N * 50 )) games)"; head -3 "$JB"; exit 0; }
run_one() {
  local tag=$1; shift
  local out=${@: -1}
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/numba12_$tag" nice -n 19 "$PY" "$@" 2>> "$TMP/err12_$(basename "$out" .jsonl).log"
  echo "[$(date -u +%FT%TZ)] done $out rc=$? rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
short=0; total=0
while read -r line; do out=${line##* }; n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
  [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }; done < "$JB"
if [ "$short" -ne 0 ] || [ "$total" -ne $(( N * 50 )) ]; then echo "[$(date -u +%FT%TZ)] FATAL audit $short short, $total/$(( N * 50 ))" >> "$LOG"; exit 4; fi
echo "[$(date -u +%FT%TZ)] $PHASE audit OK $total rows" >> "$LOG"
echo "[$(date -u +%FT%TZ)] $PHASE DONE" >> "$LOG"
