#!/bin/bash
# settle lane Mesen batch 4: G2/G3/G4 replays of the PROPH-first (D) fair variants
cd "$(dirname "$0")/../.."
C=tmp/carts
ARMS="D:couch_fair_D DB:couch_fair_DB DA:couch_fair_DA DAB:couch_fair_DAB"
for g in G2 G3 G4; do
  for a in $ARMS; do
    tag=${a%%:*}; cart=${a#*:}
    timeout 5400 tools/lateflip/run_lateflip.sh ${g}_$tag $C/$cart.nes tmp/settle/cases/cases_${g}.lua 20000 2>&1 | tail -1
  done
done
echo BATCH4_DONE
