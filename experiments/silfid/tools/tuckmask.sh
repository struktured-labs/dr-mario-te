#!/bin/bash
# silfid: does the tie-break seed's high nibble leak into the tuck extension (tuck_cell_prep loads S_CA/S_CB unmasked)?
# Same seed (0x99: both nibbles -> $D, i.e. VIRUS-coded tuck halves) on fw 1488e158 vs the masked rebuild, tuck pills.
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
until command grep -aq "SWEEP DONE" $S/logs/seedcls.log; do sleep 30; done
cd $S/an
SEED=153 J=5 /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python cosim.py $S/cosim/tuck_none153.jsonl $(cat $S/cases/tuck_pills.txt); echo "$(date +%T) none done"
SEED=153 J=5 FWDIR=$S/fw/mask_dir /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python cosim.py $S/cosim/tuck_mask153.jsonl $(cat $S/cases/tuck_pills.txt); echo "$(date +%T) mask done"
echo "$(date +%T) TUCKMASK DONE"
