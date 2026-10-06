#!/bin/bash
# DRLEFLUSH verification matrix (Verilator, RTL 3b164c7 DIST60 defines). Run inside a v11-* systemd user unit so the
# lane throttle (PAUSE file + 8-runnable cap) governs every vsim; no wall-clock timeouts anywhere.
#   1. fresh references (one process per decision, chain_cosim.py fresh): V1+flush c51d2e21 G2/G3/G4, 1488+flush
#      25bdb23a G2, and V1 a1ef31c8 G2 as the reproduction check of the copro-pipeline lane's banked refs (which are used
#      for V1 G3/G4 and 1488e158 G2: same RTL, same sim source and flags)
#   2. POISON matrix (poison_cosim.py): engine state randomised at the GO's reset release
#        ON_all       V1+flush, all 180 registers, seed 1 G2/G3/G4 + seed 2 G2   -> must be exact vs ON fresh
#        ON_dph1/2    V1+flush, dphase := 1 / 2 only (the measured hazard), G2  -> must be exact
#        OFF_all      V1, all registers, seed 1, G2                         -> positive control (must differ)
#        OFF_dph1/2   V1, dphase := 1 / 2 only, G2                          -> positive control (dphase alone)
#        OFF_allbut   V1, all registers EXCEPT dphase, seed 1, G2/G3/G4      -> enumeration: nothing else is live
#        ON_allram    V1+flush, all registers + copro work RAM, seed 1, G2   -> informational (firmware leftovers)
#   3. adversarial pairs (chain_cosim.py pairs, the copro-pipeline lane's test): every consecutive G2 pair, A preempted
#      at q * DONE(A), B to DONE, vs B fresh -- q 0.5 (the lane's), 0.25, 0.75 for V1+flush; q 0.5 for 1488+flush
#   STAGE=fresh|poison|pairs|all
set -u
O=/home/struktured/projects/dr_mario_rl/tmp/v11/cosim
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
H=$(cd "$(dirname "$0")" && pwd)
CC=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/chain_cosim.py
TLD=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
export VSIM=$O/obj_chain/vsim_chain COSIM_PAUSE=/home/struktured/projects/dr_mario_rl/tmp/v11/PAUSE
J=${J:-8}
STAGE=${STAGE:-all}
tl() { case $2 in 1488e158|25bdb23a) echo $TLD/pubtrace_$1_fw1488e158.jsonl;; *) echo $TLD/pubtrace_$1_fwa1ef31c8_fwlane.jsonl;; esac; }
mkdir -p $O/ref $O/poison $O/pairs
if [ $STAGE = fresh ] || [ $STAGE = all ]; then
  LANEREF=/home/struktured/projects/dr_mario_rl/tmp/abort_stale/cosim/ref
  for x in "c51d2e21 G2" "c51d2e21 G3" "c51d2e21 G4" "25bdb23a G2" "a1ef31c8 G2"; do
    set -- $x
    [ -s $O/ref/${2}_$1.jsonl ] || $P $CC fresh $O/fw_$1/copro_rom.hex $(tl $2 $1) $O/ref/${2}_$1.jsonl -j $J
  done
  $P $CC cmp $LANEREF/G2_a1ef31c8.jsonl $O/ref/G2_a1ef31c8.jsonl | sed "s/^/lane-ref-repro V1 G2: /"
  for x in "a1ef31c8 G3" "a1ef31c8 G4" "1488e158 G2"; do
    set -- $x; [ -s $O/ref/${2}_$1.jsonl ] || cp $LANEREF/${2}_$1.jsonl $O/ref/${2}_$1.jsonl
  done
  for g in G2 G3 G4; do
    $P $CC cmp $O/ref/${g}_a1ef31c8.jsonl $O/ref/${g}_c51d2e21.jsonl | sed "s/^/flush-vs-V1 fresh $g: /"
  done
  $P $CC cmp $O/ref/G2_1488e158.jsonl $O/ref/G2_25bdb23a.jsonl | sed "s/^/flush-vs-1488 fresh G2: /"
  echo FRESH_DONE
fi
if [ $STAGE = poison ] || [ $STAGE = all ]; then
  run() {   # tag fw games spec seeds [--ram]
    local tag=$1 fw=$2 games=$3 spec=$4 seeds=$5; shift 5
    for g in $games; do
      out=$O/poison/${tag}_$g.jsonl
      [ -s $out ] || $P $H/poison_cosim.py run $O/fw_$fw/copro_rom.hex $(tl $g $fw) $out --spec "$spec" --seeds $seeds -j $J "$@"
      $P $H/poison_cosim.py cmp $O/ref/${g}_$fw.jsonl $out
    done
  }
  run ON_all     c51d2e21 "G2 G3 G4" all 1
  run ON_all_s2  c51d2e21 "G2" all 2
  run ON_dph1    c51d2e21 "G2" set:dphase=1 0
  run ON_dph2    c51d2e21 "G2" set:dphase=2 0
  run OFF_dph1   a1ef31c8 "G2" set:dphase=1 0
  run OFF_dph2   a1ef31c8 "G2" set:dphase=2 0
  run OFF_all    a1ef31c8 "G2" all 1
  run OFF_allbut a1ef31c8 "G2 G3 G4" allbut:dphase 1
  run ON_allram  c51d2e21 "G2" all 1 --ram
  echo POISON_DONE
fi
if [ $STAGE = pairs ] || [ $STAGE = all ]; then
  for q in 0.5 0.25 0.75; do
    out=$O/pairs/G2_c51d2e21_q$q.jsonl
    [ -s $out ] || $P $CC pairs $O/fw_c51d2e21/copro_rom.hex $(tl G2 c51d2e21) $O/ref/G2_c51d2e21.jsonl $out --q $q --wgap 18 -j $J
    $P $CC cmp $O/ref/G2_c51d2e21.jsonl $out
  done
  out=$O/pairs/G2_25bdb23a_q0.5.jsonl
  [ -s $out ] || $P $CC pairs $O/fw_25bdb23a/copro_rom.hex $(tl G2 25bdb23a) $O/ref/G2_25bdb23a.jsonl $out --q 0.5 --wgap 18 -j $J
  $P $CC cmp $O/ref/G2_25bdb23a.jsonl $out
  echo PAIRS_DONE
fi
