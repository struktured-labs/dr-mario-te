#!/bin/bash
# silfid: when the 20-class sweep's replays finish, write the final 32-class per-game verdict into h16 experiments/silfid.
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
until command grep -aq "SEEDREPLAY_GEN DONE" $S/logs/seedrep20.log; do sleep 60; done
cd $S/an && /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python seed32.py
cp $S/cosim/seedcls.jsonl /home/struktured/projects/dr-mario-h16-wt/experiments/silfid/seedcls_20261006.jsonl
echo "$(date +%T) SEED32 FINAL DONE"
