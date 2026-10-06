#!/bin/bash
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
until command grep -aq "TUCKMASK DONE" $S/logs/tuckmask.log 2>/dev/null; do sleep 30; done
PAIRS="m1g2:1" $S/tools/fullseed.sh
