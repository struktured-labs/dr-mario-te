#!/usr/bin/env bash
# Validate the tuck-isolating control IN THE REGIME THAT MATTERS: 125 near-death boards.
#
# WHY, and it is this lane's own finding turned back on its own control. The mid-game
# validation came back 0/50 placement differences -- but `dr-mario-cosim-farm` records
# that agreement here is REGIME-DEPENDENT: 100% mid-game, 88% near death, p=0.0065, and
# explicitly NOT a last-ply collapse but a regime-wide ~12% divergence. A mid-game corpus
# therefore does not certify near-death equivalence.
#
# And the quantity being attributed is a near-death one: the survival cost is the 3-vs-0
# one-directional discordance, i.e. games that ended. If noscan and base diverge near
# death, "noscan == base" would hold exactly where it does not matter and fail exactly
# where it does.
#
# EITHER OUTCOME IS WORTH THE 40 MINUTES:
#   matches 125/125 -> the control is validated where it counts, and the staged full-game
#                      noscan arm may be unnecessary -- two firmwares making identical
#                      decisions produce identical games.
#   diverges        -> the tier-3 image behaves differently near death for NON-TUCK
#                      reasons, which would make both the -32.8 pills and the 3-vs-0
#                      partly attributable to something unidentified. That is the more
#                      important outcome and it is invisible to a mid-game corpus.
#
# SEQUENCING (team lead): after the n=55 arms, never before -- they answer whether there
# is a survival cost to attribute at all, and if there is not, neither this validation nor
# the noscan arm is needed. Waits for the wave-1 fixed arms specifically, then takes just
# 2 co-sim slots alongside whatever wave is running.
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
HERE="$(cd "$(dirname "$0")" && pwd)"

while pgrep -f "run_farm.py --arm s20t3fix_" >/dev/null 2>&1; do sleep 60; done
echo "$(date -Is) wave-1 fixed arms done; validating control on 125 near-death boards" >&2

"$PY" -u "$HERE/decide_compare.py" \
  /mnt/data/drmario_cosim/gate/death_hostdata.txt \
  --arms base=/mnt/data/drmario_cosim/fw/s20b \
         noscan=/mnt/data/drmario_cosim/fw/t3_noscan \
  --out /mnt/data/drmario_cosim/results/control_noscan_death125.json
echo "$(date -Is) near-death control validation finished" >&2
