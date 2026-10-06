#!/bin/bash
# CHAINED pipeline co-sim of V1 + DRLEFLUSH (c51d2e21) on the abort cart's GO schedule (the copro-pipeline lane's
# chain_cosim.py, claude/abort-stale; sim_pubchain.cpp unchanged): whole game in ONE copro process, uploads start on the
# Mesen GO frames of an abort-cart (b1b57638) run, a still-running search is preempted (DRABORTSTALE), board bytes 18 NES
# cycles apart. Compared with the same firmware's fresh (one process per decision) references.
#   SCHED=AV1  : the abort-stale lane's A-cart + V1 Mesen runs (tmp/abort_stale/runs/<g>_AV1) -- its COSIM.txt section 3
#   SCHED=AV11 : this lane's A-cart + V1+DRLEFLUSH runs (tmp/v11/mesen/runs/<g>_AV11) -- the closed loop
# Also the lane's WINDOW mode (every aborted-into pill, 1 pill before .. 2 after) on the same schedule.
set -u
O=/home/struktured/projects/dr_mario_rl/tmp/v11/cosim
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
CC=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/chain_cosim.py
TLD=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
export VSIM=$O/obj_chain/vsim_chain COSIM_PAUSE=/home/struktured/projects/dr_mario_rl/tmp/v11/PAUSE
FW=${FW:-c51d2e21}; SCHED=${SCHED:-AV1}
case $SCHED in
  AV1)  LOG='/home/struktured/projects/dr_mario_rl/tmp/abort_stale/runs/{g}_AV1/lateflip_{g}_AV1.log';;
  *)    LOG="/home/struktured/projects/dr_mario_rl/tmp/v11/mesen/runs/{g}_$SCHED/lateflip_{g}_$SCHED.log";;
esac
mkdir -p $O/chain
pids=()
for g in G2 G3 G4; do
  log=${LOG//\{g\}/$g}; tl=$TLD/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl
  out=$O/chain/${g}_${FW}_abort_$SCHED.jsonl
  ( [ -s $out ] || $P $CC run $O/fw_$FW/copro_rom.hex $tl $out mesen:$log --abort --wgap 18 > $out.log 2>&1
    $P $CC cmp $O/ref/${g}_$FW.jsonl $out >> $out.log 2>&1 ) &
  pids+=($!)
done
for g in G2 G3 G4; do
  log=${LOG//\{g\}/$g}; tl=$TLD/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl
  out=$O/chain/${g}_${FW}_win_$SCHED.jsonl
  [ -s $out ] || $P $CC window $O/fw_$FW/copro_rom.hex $tl $O/ref/${g}_$FW.jsonl $out --log $log --wgap 18 -j 4 > $out.log 2>&1
  $P $CC cmp $O/ref/${g}_$FW.jsonl $out >> $out.log 2>&1
done
wait "${pids[@]}"
for f in $O/chain/G?_${FW}_*_$SCHED.jsonl.log; do echo "== $(basename $f)"; tail -4 $f; done
echo CHAIN_DONE
