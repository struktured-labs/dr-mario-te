#!/usr/bin/env bash
# Build racer then stomper360 SERIALLY. Restores the fork tree's firmware afterwards so it
# is never left sitting on an arm build (the discipline swap_arm.sh applied to the canonical
# tree, applied here to the fork too).
set -uo pipefail
HERE=/home/struktured/projects/dr-mario-qa-wt/experiments/rtl_chain
FORK=/home/struktured/projects/NES_MiSTer-winner
SHIPFW=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/arms/fw_tuckstomp180.hex
cp -a "$FORK/copro_rom.hex" "$FORK/copro_rom.hex.preship.bak" 2>/dev/null
restore() {
  echo "== restoring fork firmware to the SHIPPED image (f4b6dfbf)"
  cp -a "$SHIPFW" "$FORK/copro_rom.hex"
  md5sum "$FORK/copro_rom.hex"
}
trap restore EXIT
for P in racer stomper360; do
  echo "############ $P  $(date +%T)"
  "$HERE/build_personality.sh" "$P"
  echo "############ $P exit=$?  $(date +%T)"
done
echo "############ ALL DONE $(date +%T)"
