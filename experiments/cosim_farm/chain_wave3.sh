#!/usr/bin/env bash
# Wave 3: seeds 400-459 -- OUTSIDE the fast-sim lane's entire studied range.
#
# SUPERSEDES an earlier wave-3 aimed at seeds 256-315, which I armed on the belief that
# s0 = (seed>>8)&0xFF made seed 256 a regime boundary. That lane checked its own claim
# three ways and retracted it: the pill_switch_rate anomaly lives INSIDE s0=0 --
#     0-119 (s0=0, lo s1) 0.8326  vs  120-255 (s0=0, hi s1) 0.8690   p=0.0000
#     120-255 (s0=0)      0.8690  vs  256-399 (s0=1)        0.8648   p=0.44
# so it is a LOW-SEED property, not an LFSR-high-byte one, and seed 256 is inert on the
# input side (p=0.44) as well as on their outcome side (p=0.92). Crossing it buys a
# confirmation they can already hand over for free.
#
# WHAT THE EXISTING WAVES ALREADY COVER, at no extra cost: wave 1 (0-134) sits largely
# inside the anomalous low-seed region and wave 2 (135-234) sits outside it, and those
# are already reported separately. That contrast IS the external-validity check for the
# one real input-side anomaly in this range.
#
# WHAT IS STILL GENUINELY UNCOVERED: seeds 400+ leave that lane's studied range
# altogether, so nothing either rig has measured speaks to them. Same 60 seeds, strictly
# more information than 256-315.
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
echo "$(date -Is) waves 1+2 done; starting wave 3 (seeds 400-459, outside both studied ranges)" >&2

launch() {  # launch <arm> <fwdir> <exec-mode> <workers>
  nohup "$PY" -u "$HERE/run_farm.py" --arm "$1" --fw "$2" --out "$OUT" \
    --seed-start 400 --seed-count 60 --workers "$4" \
    --exec-mode "$3" --pressure bursty \
    > "$LOGS/wave3_$1.log" 2>&1 &
}

launch s20b_drop      /mnt/data/drmario_cosim/fw/s20b         drop 8
launch s20t3fix_tuck  /mnt/data/drmario_cosim/fw/fixslot_ctl  tuck 8
launch s20t3fix_drop  /mnt/data/drmario_cosim/fw/fixslot_ctl  drop 8
sleep 30
echo "$(date -Is) launched: $(pgrep -fc 'run_farm.py --arm') runners, $(pgrep -xc farm_vsim) co-sims" >&2
