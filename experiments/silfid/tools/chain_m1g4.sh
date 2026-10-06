#!/bin/bash
# silfid H1: whole-game CHAINED co-sim of M1 G4 in ONE copro process (fw 1488e158), GOs on the FAIR-cart Mesen schedule
# (ctl_m1g4_D: 0 preemptions -> WAIT mode, the upload waits for the previous DONE, as cart D does). wgap 18.
cd /home/struktured/projects/dr_mario_rl/tmp/silfid/an
nice -n 19 /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python chain_run.py \
  /home/struktured/projects/dr_mario_rl/tmp/silfid/cosim/fw1488/copro_rom.hex \
  /home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics/pubtrace_m1g4_lulu_20261005.jsonl \
  /home/struktured/projects/dr_mario_rl/tmp/silfid/cosim/chain_wait_m1g4.jsonl \
  /home/struktured/projects/dr_mario_rl/tmp/silfid/mesen/runs/ctl_m1g4_D/lateflip_ctl_m1g4_D.log
echo "$(date +%T) CHAIN DONE rc=$?"
