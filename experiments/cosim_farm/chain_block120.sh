#!/usr/bin/env bash
# Wait for the current fixed-firmware arms to finish, then extend all THREE arms into
# seeds 135-234.
#
# WHY. The fast-sim lane split its 400 seeds at 120 (a boundary THIS lane specified, not
# one they chose) and found their arm-D effect lives entirely above it: seeds 0-119 are a
# wash with the wrong sign (+0.033 [-0.050,+0.117], p=0.57), seeds 120-399 carry the whole
# effect (-0.089 [-0.146,-0.032], p=0.0026), and a permutation test on the block labels
# puts a split that extreme at p=0.023.
#
# My fixed-arm re-run inherited arm A's seed set, which is 40/55 inside 0-119. So if
# D_fixed - A comes back null on it, "the fix does not help" and "these are the seeds where
# nothing happens for anyone" are INDISTINGUISHABLE. This extension buys seeds in the block
# where a second, independent method says an effect exists.
#
# Arm A must be extended too: it only has rows up to seed 134, so there is nothing to pair
# against above that. Running all three keeps every comparison paired on identical seeds.
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT=/mnt/data/drmario_cosim/results/tuck2x2_bursty.jsonl
LOGS=/mnt/data/drmario_cosim/logs

while pgrep -f "run_farm.py --arm s20t3fix_" >/dev/null 2>&1; do sleep 60; done
echo "$(date -Is) current fixed arms finished; starting block-120+ extension" >&2

launch() {  # launch <arm> <fwdir> <exec-mode> <workers>
  nohup "$PY" -u "$HERE/run_farm.py" --arm "$1" --fw "$2" --out "$OUT" \
    --seed-start 135 --seed-count 100 --workers "$4" \
    --exec-mode "$3" --pressure bursty \
    > "$LOGS/blk120_$1.log" 2>&1 &
}

launch s20b_drop      /mnt/data/drmario_cosim/fw/s20b         drop 8
launch s20t3fix_tuck  /mnt/data/drmario_cosim/fw/fixslot_ctl  tuck 8
launch s20t3fix_drop  /mnt/data/drmario_cosim/fw/fixslot_ctl  drop 8
sleep 30
echo "$(date -Is) launched: $(pgrep -fc 'run_farm.py --arm') runners, $(pgrep -xc farm_vsim) co-sims" >&2
