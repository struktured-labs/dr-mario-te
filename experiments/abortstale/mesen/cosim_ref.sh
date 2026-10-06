#!/bin/bash
# fresh references (one process per decision = the banked method), all three games, both fw; then the banked check
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
D=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/chain_cosim.py
TL=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
for g in G2 G3 G4; do
  for fw in 1488e158 a1ef31c8; do
    case $fw in 1488e158) T=$TL/pubtrace_${g}_fw1488e158.jsonl;; a1ef31c8) T=$TL/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl;; esac
    $P $D fresh $O/cosim/fw_$fw/copro_rom.hex $T $O/cosim/ref/${g}_$fw.jsonl -j ${J:-8} || echo "FRESH FAIL $g $fw"
  done
done
echo REF_DONE
