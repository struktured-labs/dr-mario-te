#!/usr/bin/env bash
# Swap the copro brain in an ALREADY-FITTED core, without re-running place & route.
#
# ⚠⚠ THIS SCRIPT DOES NOT WORK, AND IS KEPT ONLY AS THE RECORD OF WHY.
#
# The premise was: swap the copro firmware in an already-fitted core with
# `quartus_cdb --update_mif` + `quartus_asm`, ~2 minutes instead of a ~40 minute refit, with
# both arms coming out of the SAME placement so a hardware difference could not be a fitter
# artifact. That premise is FALSE.
#
# `--update_mif` only updates memories whose contents come from a MIF/HEX ASSIGNMENT (IP or
# qsf). CoproDrMario.sv initialises the firmware ROM with
#
#     initial $readmemh("copro_rom.hex", rom);      // CoproDrMario.sv:160
#
# which Quartus resolves at SYNTHESIS. update_mif has nothing to update, exits successfully,
# and quartus_asm re-emits the SAME bitstream. MEASURED -- three "different" arms:
#
#     ship build      NES.rbf   f7d3382a...
#     swap stomp180   NES.rbf   f7d3382a...   identical
#     swap stomp360   NES.rbf   f7d3382a...   identical
#
# The failure is quiet and it is dangerous: every command succeeds, and the core you deploy
# runs whatever firmware was baked at synthesis. Here that was 751b6ce9, which writes no arm
# bytes, so the arm registers power up to 0 and the core runs lnk1 -- a REAL 60.2% brain.
# The wrong core would have played well, just not as the arm on the label, and the
# investigation would have gone looking for a bug in a chain reward that never ran.
#
# LESSON: a flag existing is not a flag applying. Verify the ARTIFACT CHANGED, not that the
# command exited 0. The acceptance check is now explicit in the ship path: the new rbf md5
# must DIFFER from the previous arm's.
#
# TO ACTUALLY SWAP ARMS: full clean compile with the chosen firmware in place and the seed
# pinned. The same-placement property is then established by REPRODUCTION -- identical RTL,
# same pinned seed, only ROM contents differing, so matching slack is evidence the placement
# reproduced -- rather than by construction.
#
# Usage: swap_arm.sh <lnk1|stomp180|stomp360>  [out-dir]
echo "swap_arm.sh is DISABLED -- see the header. Use a full compile with the firmware in place." >&2
exit 64
set -euo pipefail
ARM="${1:?usage: swap_arm.sh <lnk1|stomp180|stomp360> [out-dir]}"
OUT="${2:-/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/arms}"
FORK=/home/struktured/projects/NES_MiSTer-winner
CANON=/home/struktured/projects/dr-mario-canonical-wt
QBIN=/home/struktured/intelFPGA_lite/23.1std/quartus/bin
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python

case "$ARM" in
  lnk1)     FIX=0; DOSE=0   ;;
  stomp180) FIX=1; DOSE=180 ;;
  stomp360) FIX=1; DOSE=360 ;;
  *) echo "unknown arm '$ARM' (lnk1 | stomp180 | stomp360)" >&2; exit 64 ;;
esac

if [ ! -f "$FORK/output_files/NES.fit.rpt" ]; then
  echo "no fitted database in $FORK -- run a full compile first" >&2; exit 65
fi

mkdir -p "$OUT"
echo "== building firmware: a_fix=$FIX DRCHAIN=$DOSE =="
( cd "$CANON/fpga/copro" \
  && DRCOPRO_TUCK=1 DRCOPRO_ARM=1 DRFIX=$FIX DRCHAIN=$DOSE "$PY" dbg_build.py all 0 >/dev/null \
  && cp copro_rom.hex "$FORK/copro_rom.hex" \
  && cp copro_rom.hex "$OUT/fw_$ARM.hex" )
# leave the canonical tree on its default (shipped) firmware, not an arm build
( cd "$CANON/fpga/copro" && "$PY" dbg_build.py all 0 >/dev/null )

echo "== re-initialising memory + re-assembling (no place & route) =="
cd "$FORK"
"$QBIN/quartus_cdb" NES -c NES --update_mif
"$QBIN/quartus_asm" NES -c NES

cp output_files/NES.rbf "$OUT/NES_$ARM.rbf"
echo
echo "arm      : $ARM  (a_fix=$FIX DRCHAIN=$DOSE)"
echo "firmware : $(md5sum "$OUT/fw_$ARM.hex" | cut -d' ' -f1)"
echo "rbf      : $(md5sum "$OUT/NES_$ARM.rbf" | cut -d' ' -f1)"
echo
echo "Deploy with a DEVICE-SIDE md5 check -- copy, then verify on the MiSTer itself."
