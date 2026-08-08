#!/usr/bin/env bash
# THREE arms, not four. Supersedes run_2x2.sh for the tuck study.
#
#   A  s20b_drop   e970e9ab  descriptor ignored   = the shipped champion
#   B  s20t3_drop  5d010f62  descriptor ignored   = ship tier-3 onto today's cart
#   D  s20t3_tuck  5d010f62  descriptor honoured  = the full program
#
# ARM C (s20b_tuck: executor ON with v1 firmware) IS DELIBERATELY DROPPED. It is the only
# arm whose answer cannot change a decision: v1's descriptors measured 62% coherent and 8%
# productive, and "never ship DRTUCK=1 with v1 firmware" is already settled on mechanism.
# Putting a confidence interval on a configuration nobody will ship costs 25% of
# throughput for nothing. Dropping it moves ~3.5 -> ~4.7 paired seeds/hour.
#
# PRIMARY ENDPOINT: bad-end rate (topout or stall) via McNemar on paired seeds.
# Pills-to-clear is DESCRIPTIVE ONLY -- measured paired SD is 81.65 under bursty v1.1
# (bimodal: clear ~70 pills, or run to the 300 cap), so even a ship-sized effect does not
# reach significance at n=120. See POWER.txt; the model is calibrated against #47, whose
# real -13.51 pills gives t=1.81 while its -22.5-point bad-end effect is p~3e-5.
#
# TARGET n >= 56, which detects 21.4 points and so covers the reference effect (#47 moved
# bad-end 22.5 points). n~37 by morning detects only 26.1 and would MISS it -- so this run
# is meant to continue past morning, not stop there. Nothing tuck-related can ship without
# a Quartus fit + seed sweep anyway, so there is no 9am decision waiting on it.
#
# Usage: run_abd.sh [seed_start] [seed_count] [workers_per_arm] [pressure]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}"
FW=/mnt/data/drmario_cosim/fw
RES=/mnt/data/drmario_cosim/results
LOG=/mnt/data/drmario_cosim/logs

START="${1:-0}"; COUNT="${2:-120}"; W="${3:-4}"; PRESS="${4:-bursty}"
OUT="$RES/tuck2x2_${PRESS}.jsonl"          # same file: existing A/B/D rows are RESUMED
mkdir -p "$RES" "$LOG"

launch() {
  nohup "$PY" -u "$HERE/run_farm.py" \
      --arm "$1" --fw "$FW/$2" --out "$OUT" \
      --seed-start "$START" --seed-count "$COUNT" \
      --workers "$W" --exec-mode "$3" --pressure "$PRESS" \
      > "$LOG/2x2_${PRESS}_$1.log" 2>&1 < /dev/null &
  disown
  echo "  launched $1  (fw=$2, exec=$3, pressure=$PRESS, workers=$W)"
}

echo "A/B/D tuck study -> $OUT   seeds $START..$((START+COUNT-1))  ${W} workers/arm"
launch s20b_drop  s20b  drop
launch s20t3_drop s20t3 drop
launch s20t3_tuck s20t3 tuck
sleep 3
pgrep -af "[r]un_farm.py" | sed 's/.*--arm /  --arm /' | cut -c1-70

cat <<EOF

harvest (bad-end rate is primary; pills descriptive only):
  $PY $HERE/analyze.py $OUT --a s20b_drop  --b s20t3_tuck   # D-A  full program
  $PY $HERE/analyze.py $OUT --a s20t3_drop --b s20t3_tuck   # D-B  executor ROI, fw fixed
  $PY $HERE/analyze.py $OUT --a s20b_drop  --b s20t3_drop   # B-A  ship tier-3 today
EOF
