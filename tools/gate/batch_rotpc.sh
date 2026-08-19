#!/bin/bash
set -u
D=/home/struktured/projects/dr-mario-rotexec-wt
while pgrep -x Mesen >/dev/null; do sleep 15; done
RP_SEED=114 RP_PCFRAMES=20 "$D/tools/gate/run_rotpc.sh" 3 4000  </dev/null 2>&1 | command grep -a "^SUMMARY\|FAILED"
RP_SEED=114 RP_PCFRAMES=20 RP_CTLFRAME=1471 "$D/tools/gate/run_rotpc.sh" 0 4000 </dev/null 2>&1 | command grep -a "^SUMMARY\|FAILED"
