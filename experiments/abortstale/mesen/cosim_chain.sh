#!/bin/bash
# Realistic chained co-sims: each game in ONE copro process, GO times = the Mesen run's own GO frames.
#   wait  mode: the D cart schedule (today: the upload waits for the previous DONE)
#   abort mode: the D+DRABORTSTALE schedule (the upload + GO lands on schedule, preempting a running search)
# Board bytes 18 NES cycles apart (the cart's upload loop is ~19 cycles/byte), so the dead search runs during the upload.
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
D=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/chain_cosim.py
TL=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
RUNS=${RUNS:-$O/runs}; OUT=${OUT:-$O/cosim/chain}; mkdir -p $OUT
for g in ${GAMES:-G2 G3 G4}; do
  for fw in 1488e158 a1ef31c8; do
    case $fw in 1488e158) T=$TL/pubtrace_${g}_fw1488e158.jsonl; a=1488;; a1ef31c8) T=$TL/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl; a=V1;; esac
    for mode in ${MODES:-wait abort}; do
      case $mode in wait) log=$RUNS/${g}_D$a/lateflip_${g}_D$a.log; ab="";; abort) log=$RUNS/${g}_A$a/lateflip_${g}_A$a.log; ab=--abort;; esac
      echo "$g $fw $mode $T $log $ab"
    done
  done
done | xargs -P ${J:-12} -L 1 bash -c 'g=$0; fw=$1; mode=$2; T=$3; log=$4; ab=$5; '"$P $D"' run '"$O"'/cosim/fw_$fw/copro_rom.hex $T '"$OUT"'/${g}_${fw}_${mode}.jsonl mesen:$log $ab --wgap 18 > '"$OUT"'/${g}_${fw}_${mode}.log 2>&1; '"$P $D"' cmp '"$O"'/cosim/ref/${g}_$fw.jsonl '"$OUT"'/${g}_${fw}_${mode}.jsonl >> '"$OUT"'/${g}_${fw}_${mode}.log 2>&1'
echo CHAIN_DONE
