#!/usr/bin/env bash
# Swap the copro brain in an ALREADY-FITTED core, without re-running place & route.
#
# WHY THIS EXISTS, and a correction worth reading. The arm-select bytes ($70E5 a_fix,
# $70E6 DRCHAIN/4) live in the copro FIRMWARE, so on a CART they really are a two-byte
# patch of a file. On MiSTer they are not: CoproDrMario.sv pulls the firmware in with
#
#     initial $readmemh("copro_rom.hex", rom);
#
# which BAKES it into the bitstream. Swapping arms therefore needs a new .rbf -- but NOT a
# new fit. `quartus_cdb --update_mif` re-reads the hex into the existing placed-and-routed
# database and `quartus_asm` re-emits the bitstream, which is a couple of minutes instead
# of ~40.
#
# That is better than a full rebuild for the A/B, not merely cheaper: both arms come out of
# the SAME placement and the SAME routing, so nothing but the ROM contents differs. Any
# behavioural difference on hardware is the brain, and cannot be a fitter artifact.
#
# ⚠ DRCOPRO_TUCK=1 IS NOT OPTIONAL HERE. The firmware currently deployed on the MiSTer
# (751b6ce9) is the TUCK build -- verified by rebuilding it. An arm image built without
# DRCOPRO_TUCK would silently DROP the tuck enumerator, shipping a regression disguised as
# a brain upgrade. Every arm image below therefore carries tucks, and the two-byte assertion
# is run on the TUCK pair, which is the pair that actually ships.
#
# Usage: swap_arm.sh <lnk1|stomp180|stomp360>  [out-dir]
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
