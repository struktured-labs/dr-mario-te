#!/bin/bash
# PREREG_ROTDIR_V2: the WIN orient (copro 1) only, 16 fresh seeds, paired OFF/ON.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
while pgrep -x Mesen >/dev/null; do sleep 20; done
OFF_MD5=$(md5sum "$D/roms/rotdir_off.nes" | cut -d' ' -f1)
ON_MD5=$(md5sum "$D/roms/rotdir_on.nes"  | cut -d' ' -f1)
[[ "$OFF_MD5" == 9fefaedba9a27ba10f058ac239eeb77d ]] || { echo "OFF arm is NOT the reference cart"; exit 2; }
for s in 4001 4002 4003 4004 4005 4006 4007 4008 4009 4010 4011 4012 4013 4014 4015 4016; do
  for arm in off on; do
    cart="$D/roms/rotdir_${arm}.nes"; md5=$OFF_MD5; [[ $arm == on ]] && md5=$ON_MD5
    echo "### V2 CELL seed=$s arm=$arm"
    RW_SEED=$s RW_ARMTAG=$arm RW_CART="$cart" RW_CARTMD5=$md5 \
      "$D/tools/gate/run_rotwedge.sh" 1 12000 </dev/null 2>&1
  done
done
echo V2_BATCH_DONE
