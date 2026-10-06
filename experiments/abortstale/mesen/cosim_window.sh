#!/bin/bash
# Abort-arm windowed co-sims (all games, both fw), Mesen GO schedule of the D+DRABORTSTALE cart runs.
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
D=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/chain_cosim.py
TL=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
for g in ${GAMES:-G2 G3 G4}; do
  for fw in 1488e158 a1ef31c8; do
    case $fw in 1488e158) T=$TL/pubtrace_${g}_fw1488e158.jsonl; a=1488;; a1ef31c8) T=$TL/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl; a=V1;; esac
    $P $D window $O/cosim/fw_$fw/copro_rom.hex $T $O/cosim/ref/${g}_$fw.jsonl $O/cosim/win/${g}_$fw.jsonl \
      --log $O/runs/${g}_A$a/lateflip_${g}_A$a.log --wgap 18 -j ${J:-1} > $O/cosim/win/${g}_$fw.log 2>&1
    $P $D cmp $O/cosim/ref/${g}_$fw.jsonl $O/cosim/win/${g}_$fw.jsonl >> $O/cosim/win/${g}_$fw.log 2>&1
    tail -4 $O/cosim/win/${g}_$fw.log
  done
done
echo WINDOW_DONE
