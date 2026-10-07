#!/usr/bin/env bash
# STEER14 farm (PREREG_STEER14.md). PHASE = main. Launch DETACHED under the steer14- unit prefix (the steer14-throttle
# PAUSE/cap switch SIGSTOPs python processes in steer14-*.service cgroups):
#   systemd-run --user --unit steer14-farm-main -p MemoryMax=24G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer14_farm.sh main
# PAUSE: touch /home/struktured/projects/dr_mario_rl/tmp/PAUSE_STEER14  (or the shared .../tmp/PAUSE_ALL)
# 10 workers (shared box; the throttle caps runnable at 10). Jobs of 50 games; complete files are skipped (restartable);
# no wall-clock timeouts anywhere (a SIGSTOP is safe). FRESH numba cache per LAUNCH (nb14_<launch time>/<tag>): a
# relaunch never reads an older cache. Every job runs steer14_run.jit_guard() first; a guard failure (rc 5) writes
# $TMP/GUARD_FAIL and every later job is skipped, so the audit fails loudly. Audit: every job file has exactly 50 rows.
# STATUS file (rule 10): $TMP/STATUS_<phase>.txt = RUNNING <pid> <artifact> | DONE <artifact> <rows> | FATAL <why>.
set -uo pipefail
PHASE=${1:?phase}
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer14
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER14_WORKERS:-10}
cd "$CVX" || exit 2
if [ "${STEER14_DRYRUN:-0}" = 1 ]; then
  N=$($PY steer14_jobs.py "$PHASE" | wc -l); echo "dry run: $N jobs ($(( N * 50 )) games)"
  $PY steer14_jobs.py "$PHASE" | head -3; $PY steer14_jobs.py "$PHASE" | tail -2; exit 0
fi
mkdir -p "$TMP" steer14/$PHASE
LOG="$TMP/farm14_$PHASE.log"; JB="$TMP/jobs14_$PHASE.txt"; STATUS="$TMP/STATUS_$PHASE.txt"
NB="$TMP/nb14_$(date -u +%Y%m%dT%H%M%SZ)"
[ -e "$NB" ] && { echo "FATAL numba dir $NB exists" > "$STATUS"; exit 2; }
rm -f "$TMP/GUARD_FAIL"
echo "[$(date -u +%FT%TZ)] steer14 farm $PHASE start, workers $W, git $(git rev-parse --short=8 HEAD), numba $NB" >> "$LOG"
$PY steer14_jobs.py "$PHASE" > "$JB" || { echo "[$(date -u +%FT%TZ)] FATAL job list" >> "$LOG"; echo "FATAL job list" > "$STATUS"; exit 3; }
N=$(wc -l < "$JB")
echo "[$(date -u +%FT%TZ)] $N jobs ($(( N * 50 )) games)" >> "$LOG"
echo "STATUS: RUNNING $$ steer14/$PHASE ($N jobs, $(( N * 50 )) rows expected) since $(date -u +%FT%TZ)" > "$STATUS"
run_one() {
  local tag=$1; shift
  local out=${@: -1}
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  if [ -e "$TMP/GUARD_FAIL" ]; then echo "[$(date -u +%FT%TZ)] SKIP $out (GUARD_FAIL)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$NB/$tag" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 \
    nice -n 19 "$PY" "$@" 2>> "$TMP/err14_$(basename "$out" .jsonl).log"
  local rc=$?
  [ "$rc" -eq 5 ] && { echo "$out" >> "$TMP/GUARD_FAIL"; echo "[$(date -u +%FT%TZ)] GUARD FAIL $out" >> "$LOG"; }
  echo "[$(date -u +%FT%TZ)] done $out rc=$rc rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY NB
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
short=0; total=0
while read -r line; do out=${line##* }; n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
  [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }; done < "$JB"
if [ "$short" -ne 0 ] || [ "$total" -ne $(( N * 50 )) ] || [ -e "$TMP/GUARD_FAIL" ]; then
  echo "[$(date -u +%FT%TZ)] FATAL audit $short short, $total/$(( N * 50 )), guard_fail=$([ -e "$TMP/GUARD_FAIL" ] && echo yes || echo no)" >> "$LOG"
  echo "STATUS: FATAL audit $short short, $total/$(( N * 50 )) rows ($(date -u +%FT%TZ))" > "$STATUS"
  exit 4
fi
echo "[$(date -u +%FT%TZ)] $PHASE audit OK $total rows" >> "$LOG"
echo "[$(date -u +%FT%TZ)] $PHASE DONE" >> "$LOG"
echo "STATUS: DONE steer14/$PHASE $total rows, audit OK ($(date -u +%FT%TZ))" > "$STATUS"
