#!/usr/bin/env bash
# STEER14 disk-based progress + automatic pre-registered analyses (no in-session monitor needed). Launch:
#   systemd-run --user --unit steer14-desk-autoreport -p Nice=19 -p MemoryMax=8G .../steer14_autoreport.sh
# Every 600 s: tmp/steer14/progress.txt <- UTC time, STATUS_main, PAUSE state, BLIND row counts (analyze --status).
# Part R complete (and steer14/analysis_R.txt absent) -> analyze_steer14.py --rederive (PREREG sec. 4: part R is analysed
# as soon as it is complete). STATUS_main DONE -> the full analysis -> steer14/analysis.txt, then exit. FATAL -> exit.
# The unit name carries the steer14-desk- prefix, so steer14-throttle pauses it under PAUSE_STEER14 / PAUSE_ALL and gives
# its short python runs priority over a farm worker.
set -uo pipefail
CVX=/home/struktured/projects/dr-mario-h16-wt/experiments/cvx
TMP=/home/struktured/projects/dr-mario-h16-wt/tmp/steer14
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
export NUMBA_CACHE_DIR=$TMP/nb_desk_autoreport OMP_NUM_THREADS=1
cd "$CVX" || exit 2
while true; do
  st=$(cat "$TMP/STATUS_main.txt" 2>/dev/null)
  pa=$([ -e /home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL ] && echo "PAUSE_ALL held" || echo "PAUSE_ALL clear")
  cnt=$(nice -n 19 "$PY" analyze_steer14.py --status 2>&1)
  { echo "$(date -u +%FT%TZ)"; echo "$st"; echo "$pa"; echo "$cnt"; } > "$TMP/progress.txt.new" && mv "$TMP/progress.txt.new" "$TMP/progress.txt"
  if [ ! -s steer14/analysis_R.txt ] && echo "$cnt" | head -1 | command grep -a -q "complete$"; then
    nice -n 19 "$PY" analyze_steer14.py --rederive > "$TMP/analysis_R.log" 2>&1
    echo "$(date -u +%FT%TZ) part R analysed rc=$?" >> "$TMP/autoreport.log"
  fi
  case "$st" in
    *"STATUS: DONE"*)
      nice -n 19 "$PY" analyze_steer14.py > "$TMP/analysis.log" 2>&1
      echo "$(date -u +%FT%TZ) full analysis rc=$?" >> "$TMP/autoreport.log"; exit 0;;
    *"STATUS: FATAL"*)
      echo "$(date -u +%FT%TZ) farm FATAL: $st" >> "$TMP/autoreport.log"; exit 1;;
  esac
  sleep 600
done
