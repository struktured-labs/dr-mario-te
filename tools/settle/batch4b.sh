#!/bin/bash
# settle lane Mesen batch 4b: G3/G4 replays of the fair candidate D only (batch 4 trimmed once D met the G2 bar)
cd "$(dirname "$0")/../.."
for g in G3 G4; do
  timeout 5400 tools/lateflip/run_lateflip.sh ${g}_D tmp/carts/couch_fair_D.nes tmp/settle/cases/cases_${g}.lua 20000 2>&1 | tail -1
done
echo BATCH4_DONE
