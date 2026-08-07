#!/usr/bin/env bash
# The 2x2 that answers the whole tuck-program question: firmware x cart-executor.
#
#                     exec=drop (today's cart)      exec=tuck (a DRTUCK=1 cart)
#   s20b  (e970e9ab)  A: the shipped champion       C: enable the executor, v1 firmware
#   s20t3 (5d010f62)  B: ship tier-3 today          D: the full tuck program
#
#   B - A  = value of shipping tier-3 onto TODAY's cart.  Expected <= 0: the cart has no
#            tuck executor, so a tier-3 tuck that wins the root argmax overwrites
#            best_col/best_orient (tuck_v3.py:644-645) and is then PLAIN-DROPPED, landing
#            shallower than the cell the search scored.
#   C - A  = value of enabling the executor with the firmware we already ship. Expected
#            <= 0 too, but for a different reason: 15 of 26 measured tuck-v1 descriptors
#            are UNPERFORMABLE (descriptor_audit.py) because v1 picks its target column
#            independently of best_col.
#   D - A  = value of the FULL program (cart rebuild + tier-3). The number that decides
#            whether months of tuck work ship.
#   D - B  = value of the executor itself, holding firmware fixed. Nobody has measured it.
#
# All four arms play the SAME seeds, so every delta is within-seed paired.
# Pressure defaults to bursty: the champion has ~0 failures on a clean L11 stream
# (1,474-game census), so a clean arm can only measure speed, not survival.
#
# Usage: run_2x2.sh [seed_start] [seed_count] [workers_per_arm] [pressure]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}"
FW=/mnt/data/drmario_cosim/fw
RES=/mnt/data/drmario_cosim/results
LOG=/mnt/data/drmario_cosim/logs

START="${1:-0}"; COUNT="${2:-120}"; W="${3:-2}"; PRESS="${4:-bursty}"
OUT="$RES/tuck2x2_${PRESS}.jsonl"
mkdir -p "$RES" "$LOG"

launch() {  # arm_label fw_dir exec_mode
  nohup "$PY" -u "$HERE/run_farm.py" \
      --arm "$1" --fw "$FW/$2" --out "$OUT" \
      --seed-start "$START" --seed-count "$COUNT" \
      --workers "$W" --exec-mode "$3" --pressure "$PRESS" \
      > "$LOG/2x2_${PRESS}_$1.log" 2>&1 < /dev/null &
  disown
  echo "  launched $1  (fw=$2, exec=$3, pressure=$PRESS)"
}

echo "2x2 tuck study -> $OUT   seeds $START..$((START+COUNT-1))  ${W} workers/arm"
launch s20b_drop  s20b  drop     # A: shipped champion
launch s20t3_drop s20t3 drop     # B: ship tier-3 today
launch s20b_tuck  s20b  tuck     # C: executor on, v1 firmware
launch s20t3_tuck s20t3 tuck     # D: full program
sleep 3
pgrep -af "[r]un_farm.py" | sed 's/.*--arm /  --arm /' | cut -c1-90

cat <<EOF

harvest (each delta is a separate paired comparison):
  $PY $HERE/analyze.py $OUT --a s20b_drop  --b s20t3_drop   # ship tier-3 today
  $PY $HERE/analyze.py $OUT --a s20b_drop  --b s20b_tuck    # executor alone, v1 fw
  $PY $HERE/analyze.py $OUT --a s20b_drop  --b s20t3_tuck   # FULL program
  $PY $HERE/analyze.py $OUT --a s20t3_drop --b s20t3_tuck   # executor value, fw fixed
EOF
