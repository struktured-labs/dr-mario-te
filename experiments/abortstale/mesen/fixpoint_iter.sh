#!/bin/bash
# One closed-loop iteration for the DRABORTSTALE arm (all games, both fw):
#   cases_k (lua) --Mesen A cart--> log_k --windowed chained co-sim on log_k's GO schedule--> chained timelines
#   --regen_cases.py--> cases_{k+1}.  Fixed point: cases_{k+1} == cases_k byte-for-byte (then log_k is self-consistent).
#   fixpoint_iter.sh K      (K=0 uses the banked chained case files and the existing runs/G?_A* logs)
set -u
K=${1:?iteration}; N=$((K + 1))
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
X=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale
TL=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
FC=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/cases
CA=$O/carts/drmario_te_couch_fair_abort_b1b57638.nes
F=$O/fix; mkdir -p $F
for g in ${GAMES:-G2 G3 G4}; do
  for fw in 1488e158 a1ef31c8; do
    case $fw in 1488e158) T=$TL/pubtrace_${g}_fw1488e158.jsonl; a=1488; c0=$FC/cases_${g}_fw1488_chain.lua;;
                a1ef31c8) T=$TL/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl; a=V1; c0=$FC/cases_${g}_fwa1ef31c8_chain.lua;; esac
    tag=${g}_A${a}
    if [ $K = 0 ]; then cases=$c0; log=$O/runs/$tag/lateflip_$tag.log
    else
      cases=$F/cases_${tag}_it$K.lua
      $O/tools/lateflip/run_lateflip.sh ${tag}_it$K $CA $cases 20000 0 2>&1 | tail -1
      log=$O/runs/${tag}_it$K/lateflip_${tag}_it$K.log
    fi
    if [ $K = 0 ] && [ -s $O/cosim/win/${g}_$fw.jsonl ]; then        # iteration 0 = cosim_window.sh's run (same inputs)
      cp $O/cosim/win/${g}_$fw.jsonl $F/win_${tag}_it$K.jsonl; command grep -a "window:" $O/cosim/win/${g}_$fw.log > $F/win_${tag}_it$K.log
    else
      $P $X/chain_cosim.py window $O/cosim/fw_$fw/copro_rom.hex $T $O/cosim/ref/${g}_$fw.jsonl $F/win_${tag}_it$K.jsonl \
         --log $log --wgap 18 -j ${J:-4} > $F/win_${tag}_it$K.log 2>&1
    fi
    $P $X/chain_cosim.py cmp $O/cosim/ref/${g}_$fw.jsonl $F/win_${tag}_it$K.jsonl >> $F/win_${tag}_it$K.log 2>&1
    $P $X/regen_cases.py $T $F/win_${tag}_it$K.jsonl $F/tl_${tag}_it$N.jsonl $F/cases_${tag}_it$N.lua > /dev/null
    if cmp -s $F/cases_${tag}_it$N.lua $cases; then st=FIXED; else st=CHANGED; fi
    echo "$tag it$K: $(command grep -a 'n=' $F/win_${tag}_it$K.log | cut -c1-200) -> cases it$N $st"
  done
done
echo "ITER_${K}_DONE"
