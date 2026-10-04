#!/bin/bash
# abort-stale Mesen batch: one Mesen at a time (run_lateflip.sh waits for any running Mesen), nice 19.
# D = dbbb5007 (couch fair kit), A = D + DRABORTSTALE=1; cases = the fair_v1_replay CHAINED case files.
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
C=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/cases
R=$O/tools/lateflip/run_lateflip.sh
CD=$O/carts/drmario_te_couch_fair_dbbb5007.nes
CA=${CA:-$O/carts/drmario_te_couch_fair_abort_b1b57638.nes}
for g in ${GAMES:-G2 G3 G4}; do
  for arm in ${ARMS:-A1488 AV1 D1488 DV1}; do
    case $arm in
      D1488) cart=$CD; cs=$C/cases_${g}_fw1488_chain.lua;;
      DV1)   cart=$CD; cs=$C/cases_${g}_fwa1ef31c8_chain.lua;;
      A1488) cart=$CA; cs=$C/cases_${g}_fw1488_chain.lua;;
      AV1)   cart=$CA; cs=$C/cases_${g}_fwa1ef31c8_chain.lua;;
    esac
    timeout 5400 $R ${g}_${arm}${SUF:-} $cart ${CASES_OVERRIDE:-$cs} 20000 ${STALE:-0} 2>&1 | tail -2
  done
done
echo BATCH_DONE
