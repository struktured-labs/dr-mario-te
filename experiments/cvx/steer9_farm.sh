#!/usr/bin/env bash
# STEER9 (PREREG_STEER9.md). Launch DETACHED under the steer9- unit prefix (the steer9-throttle PAUSE/cap switch targets
# python processes in steer9-*.service cgroups):
#   systemd-run --user --unit steer9-farm -p MemoryMax=24G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer9_farm.sh
# PAUSE: touch /home/struktured/projects/dr_mario_rl/tmp/steer9/PAUSE  (or the shared .../tmp/PAUSE_ALL)
# 8 workers (shared box). 156 jobs x 50 = 7,800 games; audit; analyze_steer9.py -> steer9/analysis.txt
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer9
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER9_WORKERS:-8}
cd "$CVX" || exit 2
mkdir -p "$TMP" steer9
LOG="$TMP/farm9.log"; JB="$TMP/jobs9.txt"
echo "[$(date -u +%FT%TZ)] steer9 farm start, workers $W, git $(git rev-parse --short=8 HEAD)" >> "$LOG"
GBLO_BANK=$(for i in $(seq 0 11); do echo $(( 39134 + 100 * i )); done)               # 39134-40332 (banked FAIR rows)
GBLO_NEW="40334 40434 40534 40634 40734 40834 33000 33100 33200 33300 33400 33500"    # 40334-40932 + 33000-33598
{
  for lo in $GBLO_NEW; do echo "s9_base steer9_run.py gb s9_base owner202610 $lo 50 2 steer9/gb10_s9_base_${lo}.jsonl"; done
  for lo in $GBLO_BANK $GBLO_NEW; do
    for a in s9_V150 s9_VVETO s9_CVETO; do
      echo "$a steer9_run.py gb $a owner202610 $lo 50 2 steer9/gb10_${a}_${lo}.jsonl"
    done
  done
  for lo in $GBLO_BANK; do
    for a in s9_V150 s9_VVETO s9_CVETO; do
      echo "$a steer9_run.py race $a 2.36 $lo 50 2 steer9/rc10_${a}_${lo}.jsonl"
      echo "$a steer9_run.py race $a 2.56 $lo 50 2 steer9/lulu10_${a}_${lo}.jsonl"
    done
  done
} > "$JB"
N=$(wc -l < "$JB")
[ "$N" -eq 156 ] || { echo "[$(date -u +%FT%TZ)] FATAL job list $N, expected 156" >> "$LOG"; exit 3; }
[ "${STEER9_DRYRUN:-0}" = 1 ] && { echo "dry run: $N jobs"; exit 0; }
run_one() {
  local tag=$1; shift
  local out=${@: -1}
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/numba9_$tag" nice -n 19 "$PY" "$@" 2>> "$TMP/err9_$(basename "$out" .jsonl).log"
  echo "[$(date -u +%FT%TZ)] done $out rc=$? rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
short=0; total=0
while read -r line; do out=${line##* }; n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
  [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }; done < "$JB"
if [ "$short" -ne 0 ] || [ "$total" -ne 7800 ]; then echo "[$(date -u +%FT%TZ)] FATAL audit $short short, $total/7800" >> "$LOG"; exit 4; fi
echo "[$(date -u +%FT%TZ)] 9 audit OK 7800 rows; analysis" >> "$LOG"
nice -n 19 "$PY" analyze_steer9.py > steer9/analysis.txt 2>> "$LOG"
echo "[$(date -u +%FT%TZ)] 9 DONE (steer9/analysis.txt)" >> "$LOG"
