#!/bin/bash
# Replacement mutants m2b/m3b, sequenced after the v2 ladder's own completion artifact.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
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
