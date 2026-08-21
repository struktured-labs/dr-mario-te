#!/bin/bash
# PREREG_ROTDIR mutant kill sheet. Two orients are enough to decide every row of the table:
#   copro 1 (delta 1) = the WIN arm            -- M1/M2/M3/M4 must all fail to speed it up
#   copro 0 (delta 3) = a MUST-NOT-MOVE arm    -- M1/M2 must slow it down
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
# wait for the main ladder to finish rather than racing it
while [ ! -s "$D/tmp/rotdir_batch.log" ] || ! command grep -aq BATCH_DONE "$D/tmp/rotdir_batch.log"; do sleep 20; done
for m in m1 m2 m3 m4; do
  cart="$D/roms/rotdir_${m}.nes"; md5=$(md5sum "$cart" | cut -d' ' -f1)
  for s in 271 2001 3001; do
    for o in 0 1; do
      echo "### MUT $m seed=$s orient=$o md5=$md5"
      RW_SEED=$s RW_ARMTAG="$m" RW_CART="$cart" RW_CARTMD5="$md5" \
        "$D/tools/gate/run_rotwedge.sh" "$o" 12000 </dev/null 2>&1
    done
  done
done
echo MUT_BATCH_DONE
