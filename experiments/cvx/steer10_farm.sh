#!/usr/bin/env bash
# STEER10 (PREREG_STEER10.md). Launch DETACHED under the steer10- unit prefix (the steer10-throttle PAUSE/cap switch
# targets python processes in steer10-*.service cgroups):
#   systemd-run --user --unit steer10-farm -p MemoryMax=24G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer10_farm.sh
# PAUSE: touch /home/struktured/projects/dr_mario_rl/tmp/steer10/PAUSE  (or the shared .../tmp/PAUSE_ALL)
# 8 workers (shared box). Jobs of 50 games; audit; analyze_steer10.py -> steer10/analysis.txt
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer10
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER10_WORKERS:-8}
ARMS="s10_A16 s10_R60 s10_R120 s10_A16R120"                                           # PRE-REGISTERED (PREREG_STEER10.md)
cd "$CVX" || exit 2
mkdir -p "$TMP" steer10
LOG="$TMP/farm10.log"; JB="$TMP/jobs10.txt"
echo "[$(date -u +%FT%TZ)] steer10 farm start, workers $W, git $(git rev-parse --short=8 HEAD), arms: $ARMS" >> "$LOG"
LO24="$(for i in $(seq 0 11); do echo -n "$(( 39134 + 100 * i )) "; done)40334 40434 40534 40634 40734 40834 33000 33100 33200 33300 33400 33500"
LO12="$(for i in $(seq 0 11); do echo -n "$(( 39134 + 100 * i )) "; done)"
{
  for lo in $LO24; do echo "s10_base steer10_run.py race s10_base 2.84 lulu202610b $lo 50 2 steer10/lulu10b_s10_base_${lo}.jsonl"; done
  for a in $ARMS; do
    for lo in $LO24; do
      echo "$a steer10_run.py race $a 2.84 lulu202610b $lo 50 2 steer10/lulu10b_${a}_${lo}.jsonl"
      echo "$a steer10_run.py gb $a owner202610 $lo 50 2 steer10/gb10_${a}_${lo}.jsonl"
    done
    for lo in $LO12; do echo "$a steer10_run.py race $a 2.36 hartford $lo 50 2 steer10/rc10_${a}_${lo}.jsonl"; done
  done
} > "$JB"
NA=$(echo $ARMS | wc -w); N=$(wc -l < "$JB"); NX=$(( 24 + NA * 60 ))
[ "$N" -eq "$NX" ] || { echo "[$(date -u +%FT%TZ)] FATAL job list $N, expected $NX" >> "$LOG"; exit 3; }
[ "${STEER10_DRYRUN:-0}" = 1 ] && { echo "dry run: $N jobs ($(( N * 50 )) games)"; exit 0; }
run_one() {
  local tag=$1; shift
  local out=${@: -1}
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/numba10_$tag" nice -n 19 "$PY" "$@" 2>> "$TMP/err10_$(basename "$out" .jsonl).log"
  echo "[$(date -u +%FT%TZ)] done $out rc=$? rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
short=0; total=0
while read -r line; do out=${line##* }; n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
  [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }; done < "$JB"
if [ "$short" -ne 0 ] || [ "$total" -ne $(( N * 50 )) ]; then echo "[$(date -u +%FT%TZ)] FATAL audit $short short, $total/$(( N * 50 ))" >> "$LOG"; exit 4; fi
echo "[$(date -u +%FT%TZ)] 10 audit OK $total rows; analysis" >> "$LOG"
nice -n 19 "$PY" analyze_steer10.py > /dev/null 2>> "$LOG"
echo "[$(date -u +%FT%TZ)] 10 DONE (steer10/analysis.txt)" >> "$LOG"
