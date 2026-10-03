#!/usr/bin/env bash
# STEER7 farm (PREREG_STEER7.md sec. 8). Launch DETACHED as a transient user service:
#   systemd-run --user --unit steer7-farm -p MemoryMax=20G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer7_farm.sh
# Resume-safe: a job whose output already has 50 rows is skipped. Completion audit: 264 files x 50 rows, short = FATAL.
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer7
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER7_WORKERS:-12}
ARM=s6_dist_target60
cd "$CVX" || exit 2
mkdir -p steer7/A steer7/B "$TMP"
LOG="$TMP/farm.log"; JOBS="$TMP/jobs.txt"
echo "[$(date -u +%FT%TZ)] steer7 farm start, workers $W, git $(git rev-parse --short=8 HEAD)" >> "$LOG"

shiftval() { case "$1" in sp1) echo 1;; s0) echo 0;; sm1) echo -1;; sm2) echo -2;; sm4) echo -4;; ceil) echo ceil;; esac; }
emit() {  # blk lo0 arm cell
  local blk=$1 lo0=$2 a=$3 cell=$4 i lo
  for i in $(seq 0 11); do
    lo=$(( lo0 + 100 * i ))
    case "$cell" in
      gb)   echo "$a gb $ARM owner0804 $lo 50 2 steer7/$blk/gb_${a}_${i}.jsonl $(shiftval "$a")";;
      rc6)  echo "$a race $ARM 6 $lo 50 2 steer7/$blk/rc6_${a}_${i}.jsonl $(shiftval "$a")";;
      rc47) echo "$a race $ARM 4.7 $lo 50 2 steer7/$blk/rc47_${a}_${i}.jsonl $(shiftval "$a")";;
    esac
  done
}
{
  for a in s0 sm1; do for cell in gb rc6; do emit A 37934 $a $cell; emit B 39134 $a $cell; done; done
  for a in s0 sm1; do emit A 37934 $a rc47; done
  for a in sm2 sm4 ceil sp1; do for cell in gb rc6 rc47; do emit A 37934 $a $cell; done; done
} > "$JOBS"
N=$(wc -l < "$JOBS")
[ "$N" -eq 264 ] || { echo "[$(date -u +%FT%TZ)] FATAL job list has $N lines, expected 264" >> "$LOG"; exit 3; }
[ "${STEER7_DRYRUN:-0}" = 1 ] && { echo "dry run: $N jobs in $JOBS"; exit 0; }

run_one() {
  local a=$1; shift
  local out=${@: -2:1}
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/numba_$a" nice -n 19 "$PY" steer7_dlat.py "$@" 2>> "$TMP/err_$(basename "$out" .jsonl).log"
  local rc=$?
  echo "[$(date -u +%FT%TZ)] done $out rc=$rc rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JOBS"

# completion audit (rows per file, and total)
short=0; total=0
while read -r a mode arm x lo cnt step out sh; do
  n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
  [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }
done < "$JOBS"
if [ "$short" -ne 0 ] || [ "$total" -ne 13200 ]; then
  echo "[$(date -u +%FT%TZ)] FATAL completion audit: $short short files, $total / 13200 rows" >> "$LOG"; exit 4
fi
echo "[$(date -u +%FT%TZ)] audit OK 13200 rows; running analysis" >> "$LOG"
nice -n 19 "$PY" analyze_steer7.py > steer7/analysis.txt 2>> "$LOG"
echo "[$(date -u +%FT%TZ)] DONE rc=$? (steer7/analysis.txt)" >> "$LOG"
