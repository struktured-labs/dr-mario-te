#!/bin/bash
# Replacement mutants m2b/m3b, sequenced after the v2 ladder's own completion artifact.
set -u
D=/home/struktured/projects/dr-mario-rotexec-wt
while ! command grep -aq V2_BATCH_DONE "$D/tmp/rotdir_v2b.log" 2>/dev/null; do sleep 30; done
for m in m2b m3b; do
  cart="$D/roms/rotdir_${m}.nes"; md5=$(md5sum "$cart" | cut -d' ' -f1)
  for s in 271 2001 3001 4001 4002 4003; do
    for o in 0 1; do
      echo "### MUT2 $m seed=$s orient=$o md5=$md5"
      RW_SEED=$s RW_ARMTAG="$m" RW_CART="$cart" RW_CARTMD5="$md5" \
        "$D/tools/gate/run_rotwedge.sh" "$o" 12000 </dev/null 2>&1
    done
  done
done
echo MUT2_BATCH_DONE
