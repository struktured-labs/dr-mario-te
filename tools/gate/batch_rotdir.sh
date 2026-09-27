#!/bin/bash
# PREREG_ROTDIR ladder: 4 constant orients x 3 seeds x {OFF, ON}, paired and INTERLEAVED.
# Every cell's FULL output is echoed -- an earlier version filtered to ^SUMMARY and silently
# swallowed 22 refusals, which read as a completed batch. Absence is not pass.
set -u
D=/home/struktured/projects/dr-mario-rotexec-wt
OFF_MD5=$(md5sum "$D/roms/rotdir_off.nes" | cut -d' ' -f1)
ON_MD5=$(md5sum "$D/roms/rotdir_on.nes"  | cut -d' ' -f1)
echo "OFF=$OFF_MD5 ON=$ON_MD5"
[[ "$OFF_MD5" == 9fefaedba9a27ba10f058ac239eeb77d ]] || { echo "OFF arm is NOT the reference cart"; exit 2; }
[[ "$ON_MD5" != "$OFF_MD5" ]] || { echo "ON and OFF are the same cart -- the flag is inert"; exit 2; }
cells=0; ok=0
for s in 271 2001 3001; do
  for o in 0 1 2 3; do
    for arm in off on; do
      cart="$D/roms/rotdir_${arm}.nes"; md5=$OFF_MD5; [[ $arm == on ]] && md5=$ON_MD5
      cells=$((cells+1))
      echo "### CELL seed=$s orient=$o arm=$arm"
      if RW_SEED=$s RW_ARMTAG=$arm RW_CART="$cart" RW_CARTMD5=$md5 \
           "$D/tools/gate/run_rotwedge.sh" "$o" 12000 </dev/null 2>&1; then ok=$((ok+1)); fi
    done
  done
done
echo "BATCH_DONE cells=$cells ok=$ok"
