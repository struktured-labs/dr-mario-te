#!/usr/bin/env bash
# STEER7 declared secondary (PREREG_STEER7 addendum) + STEER6r (PREREG_STEER6r.md), queued BEHIND the STEER7 primary farm.
# Launch DETACHED:
#   systemd-run --user --unit steer7b-farm -p MemoryMax=20G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer7b_farm.sh
# Waits until steer7-farm.service is no longer active (the 12-worker budget is shared), then runs 216 jobs x 50 games.
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer7
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER7_WORKERS:-12}
cd "$CVX" || exit 2
LOG="$TMP/farm_b.log"; JOBS="$TMP/jobs_b.txt"
echo "[$(date -u +%FT%TZ)] steer7b farm armed, waiting for steer7-farm" >> "$LOG"
[ "${STEER7_DRYRUN:-0}" = 1 ] || while [ "$(systemctl --user is-active steer7-farm 2>/dev/null)" = "active" ]; do sleep 60; done
echo "[$(date -u +%FT%TZ)] steer7b farm start, workers $W, git $(git rev-parse --short=8 HEAD)" >> "$LOG"
mkdir -p steer7/A10 steer6r

shiftval() { case "$1" in s0) echo 0;; sm1) echo -1;; sm2) echo -2;; esac; }
{
  # STEER7 secondary (block A, 12 chunks of 50): gate (b) owner202610 + LULU race lam 2.56
  for a in s0 sm1 sm2; do
    for i in $(seq 0 11); do lo=$(( 37934 + 100 * i ))
      echo "s7_$a steer7_refit.py gb s6_dist_target60 owner202610 $lo 50 2 steer7/A10/gb10_${a}_${i}.jsonl $(shiftval $a)"
      echo "s7_$a steer7_refit.py race s6_dist_target60 2.56 $lo 50 2 steer7/A10/rcL10_${a}_${i}.jsonl $(shiftval $a)"
    done
  done
  # STEER6r: gb10 DIST60 + ANTIBODY on the 1,500-seed confirm block (18 chunks from 39134, 12 from 33000)
  for k in dist anti; do
    case $k in dist) arm=s6_dist_target60;; anti) arm=s5b_hsv512;; esac
    for i in $(seq 0 17); do echo "r6_$k steer6r_run.py gb $arm owner202610 $(( 39134 + 100 * i )) 50 2 steer6r/gb10_${k}_${i}.jsonl"; done
    for i in $(seq 0 11); do echo "r6_$k steer6r_run.py gb $arm owner202610 $(( 33000 + 100 * i )) 50 2 steer6r/gb10_${k}_$(( 18 + i )).jsonl"; done
  done
  for i in $(seq 0 11); do echo "r6_tap steer6r_run.py gb s4_base owner202610 $(( 39134 + 100 * i )) 50 2 steer6r/gb10_tap_${i}.jsonl"; done
  for k in dist anti tap; do
    case $k in dist) arm=s6_dist_target60;; anti) arm=s5b_hsv512;; tap) arm=s4_base;; esac
    for i in $(seq 0 11); do lo=$(( 39134 + 100 * i ))
      echo "r6_$k steer6r_run.py race $arm 2.36 $lo 50 2 steer6r/rc10_${k}_${i}.jsonl"
      echo "r6_$k steer6r_run.py race $arm 2.56 $lo 50 2 steer6r/lulu10_${k}_${i}.jsonl"
    done
  done
} > "$JOBS"
N=$(wc -l < "$JOBS")
[ "$N" -eq 216 ] || { echo "[$(date -u +%FT%TZ)] FATAL job list has $N lines, expected 216" >> "$LOG"; exit 3; }
[ "${STEER7_DRYRUN:-0}" = 1 ] && { echo "dry run: $N jobs in $JOBS"; exit 0; }

run_one() {
  local tag=$1; shift
  local out
  case "$1" in steer7_refit.py) out=${@: -2:1};; *) out=${@: -1};; esac
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/numba_$tag" nice -n 19 "$PY" "$@" 2>> "$TMP/errb_$(basename "$out" .jsonl).log"
  local rc=$?
  echo "[$(date -u +%FT%TZ)] done $out rc=$rc rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JOBS"

short=0; total=0
while read -r line; do
  set -- $line; shift
  case "$1" in steer7_refit.py) out=${@: -2:1};; *) out=${@: -1};; esac
  n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
  [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }
done < "$JOBS"
if [ "$short" -ne 0 ] || [ "$total" -ne 10800 ]; then
  echo "[$(date -u +%FT%TZ)] FATAL completion audit: $short short files, $total / 10800 rows" >> "$LOG"; exit 4
fi
echo "[$(date -u +%FT%TZ)] audit OK 10800 rows; running analyses" >> "$LOG"
nice -n 19 "$PY" analyze_steer7.py --refit > steer7/analysis_refit.txt 2>> "$LOG"
nice -n 19 "$PY" analyze_steer6r.py > steer6r/analysis.txt 2>> "$LOG"
echo "[$(date -u +%FT%TZ)] DONE (steer7/analysis_refit.txt, steer6r/analysis.txt)" >> "$LOG"
