#!/bin/bash
# settle lane Mesen batch 3: G2/G3/G4 banked-timeline replays of the fair ledge-fix variants (one Mesen at a time)
cd "$(dirname "$0")/../.."
C=tmp/carts
ARMS="S15np:arm_couch_settle15_nopin A:couch_fair_A B:couch_fair_B C:couch_fair_C AB:couch_fair_AB BC:couch_fair_BC ABC:couch_fair_ABC 464B:arm_couch_464_B"
for g in G2 G3 G4; do
  for a in $ARMS; do
    tag=${a%%:*}; cart=${a#*:}
    timeout 5400 tools/lateflip/run_lateflip.sh ${g}_$tag $C/$cart.nes tmp/settle/cases/cases_${g}.lua 20000 2>&1 | tail -1
  done
done
echo BATCH3_DONE
