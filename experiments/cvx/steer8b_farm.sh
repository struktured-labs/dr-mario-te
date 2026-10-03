#!/usr/bin/env bash
# STEER8b AMENDED (PREREG_STEER8b.md amendment), queued BEHIND steer8a-farm. Launch DETACHED:
#   systemd-run --user --unit steer8b-farm -p MemoryMax=20G -p MemorySwapMax=0 -p Nice=19 \
#       /home/struktured/projects/dr-mario-h16-wt/experiments/cvx/steer8b_farm.sh
# 8 workers (Quartus priority). 240 jobs x 50 = 12,000 games (SECOND amendment: fix D); audit; analyze_steer8b2.py -> steer8/analysis_8b.txt
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer7
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=${STEER8_WORKERS:-8}
cd "$CVX" || exit 2
LOG="$TMP/farm8b.log"; JB="$TMP/jobs8b2.txt"
echo "[$(date -u +%FT%TZ)] steer8b farm armed, waiting for steer8a-farm" >> "$LOG"
[ "${STEER8_DRYRUN:-0}" = 1 ] || while [ "$(systemctl --user is-active steer8a-farm 2>/dev/null)" = "active" ]; do sleep 60; done
echo "[$(date -u +%FT%TZ)] steer8b farm start, workers $W, git $(git rev-parse --short=8 HEAD)" >> "$LOG"
{
  for a in fD_a2 fD_bref2 fD_bdep2 fD_c2 fD_brefD fD_bdepD; do
    for i in $(seq 0 11); do lo=$(( 39134 + 100 * i ))
      echo "$a steer8_run.py gb $a owner202610 $lo 50 2 steer8/gb10_${a}_${i}.jsonl"
      echo "$a steer8_run.py race $a 2.36 $lo 50 2 steer8/rc10_${a}_${i}.jsonl"
      echo "$a steer8_run.py race $a 2.56 $lo 50 2 steer8/lulu10_${a}_${i}.jsonl"
    done
  done
  for i in $(seq 0 11); do lo=$(( 39134 + 100 * i ))
    echo "fD_ehb0 steer8_run.py gb fD_ehb0 owner202610 $lo 50 2 steer8/gb10_fD_ehb0_${i}.jsonl"
    echo "fD_ehb0 steer8_run.py race fD_ehb0 2.36 $lo 50 2 steer8/rc10_fD_ehb0_${i}.jsonl"
  done
} > "$JB"
N=$(wc -l < "$JB")
[ "$N" -eq 240 ] || { echo "[$(date -u +%FT%TZ)] FATAL job list $N, expected 240" >> "$LOG"; exit 3; }
[ "${STEER8_DRYRUN:-0}" = 1 ] && { echo "dry run: $N jobs"; exit 0; }
mkdir -p steer8
run_one() {
  local tag=$1; shift
  local out=${@: -1}
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge 50 ]; then echo "[$(date -u +%FT%TZ)] skip $out (complete)" >> "$LOG"; return 0; fi
  NUMBA_CACHE_DIR="$TMP/numba8b_$tag" nice -n 19 "$PY" "$@" 2>> "$TMP/err8b_$(basename "$out" .jsonl).log"
  echo "[$(date -u +%FT%TZ)] done $out rc=$? rows=$(wc -l < "$out" 2>/dev/null || echo 0)" >> "$LOG"
}
export -f run_one; export LOG TMP PY
xargs -P "$W" -L 1 bash -c 'run_one "$@"' _ < "$JB"
short=0; total=0
while read -r line; do out=${line##* }; n=$(wc -l < "$out" 2>/dev/null || echo 0); total=$(( total + n ))
  [ "$n" -eq 50 ] || { short=$(( short + 1 )); echo "[$(date -u +%FT%TZ)] SHORT $out rows=$n" >> "$LOG"; }; done < "$JB"
if [ "$short" -ne 0 ] || [ "$total" -ne 12000 ]; then echo "[$(date -u +%FT%TZ)] FATAL audit $short short, $total/12000" >> "$LOG"; exit 4; fi
echo "[$(date -u +%FT%TZ)] 8b audit OK 12000 rows; analysis" >> "$LOG"
nice -n 19 "$PY" analyze_steer8b2.py > steer8/analysis_8b.txt 2>> "$LOG"
echo "[$(date -u +%FT%TZ)] 8b DONE (steer8/analysis_8b.txt)" >> "$LOG"
