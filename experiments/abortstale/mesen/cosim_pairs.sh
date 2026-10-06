#!/bin/bash
# Adversarial preemption pairs: for every consecutive (A, B), A aborted at q * DONE(A), B uploaded while A still runs
# (18-cycle byte gaps = the cart's loop), B run to DONE; B compared with its fresh run. G2 only, q = $Q (default 0.5).
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
D=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/chain_cosim.py
TL=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
for g in G2 G3 G4; do
  case $g in G2) Q=${Q:-0.5};; *) continue;; esac
  for fw in 1488e158 a1ef31c8; do
    case $fw in 1488e158) T=$TL/pubtrace_${g}_fw1488e158.jsonl;; a1ef31c8) T=$TL/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl;; esac
    $P $D pairs $O/cosim/fw_$fw/copro_rom.hex $T $O/cosim/ref/${g}_$fw.jsonl $O/cosim/pairs/${g}_$fw.jsonl --q $Q --wgap 18 -j ${J:-8} \
      > $O/cosim/pairs/${g}_$fw.log 2>&1
    $P $D cmp $O/cosim/ref/${g}_$fw.jsonl $O/cosim/pairs/${g}_$fw.jsonl >> $O/cosim/pairs/${g}_$fw.log 2>&1
    tail -3 $O/cosim/pairs/${g}_$fw.log
  done
done
echo PAIRS_DONE
