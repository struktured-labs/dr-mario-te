#!/usr/bin/env bash
# Wave 3: cross the ONE real boundary in the seed space.
#
# WHY THIS AND NOT MORE SUB-256 SEEDS. The fast-sim lane retracted its seed-120 split --
# the wobble within its "effect" block is ~3x the gap that defined the block, so it was a
# gradient, not a cliff. What survives that retraction is a mechanism-backed coverage
# fact, not a fitted one: NesPillSource takes s0 = (seed>>8)&0xFF, so EVERY seed below
# 256 has s0=0. Waves 1 and 2 are seeds 0-234, which means the entire experiment so far
# sits inside a single LFSR state region with a measurably different pill_switch_rate
# (0.833 vs 0.867). That lane measured their effect as FLAT across this boundary
# (p=0.92), so this is external validity rather than effect-hunting -- but as it stands
# nothing measured here generalises past seed 255, and that is worth 60 seeds.
#
# Waits for BOTH earlier waves. The guard is "no run_farm at all AND wave 2 has actually
# produced rows", so this cannot fire during the gap before chain_block120 launches.
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT=/mnt/data/drmario_cosim/results/tuck2x2_bursty.jsonl
LOGS=/mnt/data/drmario_cosim/logs

wave2_started() {
  "$PY" - "$OUT" <<'EOF'
import json, sys
n = 0
for line in open(sys.argv[1]):
    r = json.loads(line)
    if r.get("seed", 0) >= 135 and r.get("arm", "").startswith("s20t3fix"):
        n += 1
sys.exit(0 if n > 0 else 1)
EOF
}

while true; do
  if ! pgrep -f "run_farm.py --arm" >/dev/null 2>&1 && wave2_started; then break; fi
  sleep 120
done
echo "$(date -Is) waves 1+2 done; starting s0-crossing wave (seeds 256-315)" >&2

launch() {  # launch <arm> <fwdir> <exec-mode> <workers>
  nohup "$PY" -u "$HERE/run_farm.py" --arm "$1" --fw "$2" --out "$OUT" \
    --seed-start 256 --seed-count 60 --workers "$4" \
    --exec-mode "$3" --pressure bursty \
    > "$LOGS/s0cross_$1.log" 2>&1 &
}

launch s20b_drop      /mnt/data/drmario_cosim/fw/s20b         drop 8
launch s20t3fix_tuck  /mnt/data/drmario_cosim/fw/fixslot_ctl  tuck 8
launch s20t3fix_drop  /mnt/data/drmario_cosim/fw/fixslot_ctl  drop 8
sleep 30
echo "$(date -Is) launched: $(pgrep -fc 'run_farm.py --arm') runners, $(pgrep -xc farm_vsim) co-sims" >&2
