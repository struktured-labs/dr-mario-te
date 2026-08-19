#!/usr/bin/env bash
# Launch the paired s20b-vs-s20t3 A/B. Arms run CONCURRENTLY over the SAME seed range so
# pairs complete together and a partial harvest is still balanced -- an A/B that finishes
# arm A first and arm B later would, if interrupted, leave an unpaired and biased sample.
#
# Resumable: run_farm.py skips (arm, seed) rows already in the JSONL, so re-running this
# extends the sample rather than redoing it.
#
# Usage: run_ab.sh [seed_start] [seed_count] [workers_per_arm] [exec_mode]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}"
FW=/mnt/data/drmario_cosim/fw
RES=/mnt/data/drmario_cosim/results
LOG=/mnt/data/drmario_cosim/logs

START="${1:-0}"
COUNT="${2:-150}"
W="${3:-3}"
EXEC="${4:-drop}"
OUT="$RES/ab_${EXEC}.jsonl"

mkdir -p "$RES" "$LOG"
for arm in s20b s20t3; do
  nohup nice -n 12 "$PY" -u "$HERE/run_farm.py" \
      --arm "$arm" --fw "$FW/$arm" --out "$OUT" \
      --seed-start "$START" --seed-count "$COUNT" \
      --workers "$W" --exec-mode "$EXEC" \
      > "$LOG/ab_${EXEC}_${arm}.log" 2>&1 < /dev/null &
  disown
  echo "launched $arm -> $OUT (log $LOG/ab_${EXEC}_${arm}.log)"
done
sleep 2
pgrep -af "[r]un_farm.py" | sed 's/^/  /'
cat <<EOF

harvest with:
  $PY $HERE/analyze.py $OUT --a s20b --b s20t3
EOF
