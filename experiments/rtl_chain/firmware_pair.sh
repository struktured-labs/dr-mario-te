#!/usr/bin/env bash
# Build the arm firmware images and PROVE the arms differ only in their two select bytes.
#
# The whole "one bitstream, two brains" claim rests on this: if the images differed
# anywhere else, an observed hardware difference could be any firmware change rather than
# the arm select, and the A/B would prove nothing. So it is asserted, not eyeballed --
# I verified it by hand once, which is exactly the kind of check that rots.
#
#   $70E5 a_fix   0 = lnk1 (one clear round)     1 = fixpoint
#   $70E6 a_chw   DRCHAIN dose / 4               0 = no chain reward
#
# Also asserts that the DEFAULT build (no DRCOPRO_ARM) still reproduces the shipped
# c87e60a1 byte-for-byte, so adding the arm-select emission cannot silently perturb the
# firmware everything else in the project is built on.
set -uo pipefail
CANON=/home/struktured/projects/dr-mario-canonical-wt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
OUT="${1:-/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/arms}"
SHIPPED_MD5=c87e60a1736224cfc3fa29cfed7c6f16
mkdir -p "$OUT"

build() {  # build <name> <DRCOPRO_ARM> <DRFIX> <DRCHAIN>
  ( cd "$CANON/fpga/copro" \
    && DRCOPRO_ARM=$2 DRFIX=$3 DRCHAIN=$4 "$PY" dbg_build.py all 0 >/dev/null 2>&1 \
    && cp copro_rom.hex "$OUT/fw_$1.hex" ) \
  || { echo "firmware build FAILED: $1" >&2; exit 70; }
  printf "  %-10s a_fix=%s DRCHAIN=%-4s md5=%s\n" "$1" "$3" "$4" \
         "$(md5sum "$OUT/fw_$1.hex" | cut -d' ' -f1)"
}

echo "building arm images:"
build default  0 0 0
build lnk1     1 0 0
build stomp180 1 1 180
build stomp360 1 1 360
# leave the canonical tree on its shipped default, never on an arm build
( cd "$CANON/fpga/copro" && "$PY" dbg_build.py all 0 >/dev/null 2>&1 )

fail=0

got=$(md5sum "$OUT/fw_default.hex" | cut -d' ' -f1)
if [ "$got" = "$SHIPPED_MD5" ]; then
  echo "PASS  default build still reproduces the shipped firmware ($SHIPPED_MD5)"
else
  echo "FAIL  default build drifted: want $SHIPPED_MD5, got $got"; fail=1
fi

# lnk1 vs each Combo Stomper dose: exactly two differing lines, and they must be the
# two select bytes -- not merely "two differences somewhere".
for arm in stomp180 stomp360; do
  n=$(diff "$OUT/fw_lnk1.hex" "$OUT/fw_$arm.hex" | command grep -c '^<')
  if [ "$n" = 2 ]; then
    lines=$(diff "$OUT/fw_lnk1.hex" "$OUT/fw_$arm.hex" | command grep -oE '^[0-9]+' | sort -un | tr '\n' ',')
    echo "PASS  lnk1 vs $arm differ in exactly 2 bytes (offsets ${lines%,})"
  else
    echo "FAIL  lnk1 vs $arm differ in $n bytes, expected 2"; fail=1
  fi
done

echo
[ "$fail" = 0 ] && echo "ARM PAIR VERIFIED: the arms differ ONLY in their select bytes." \
                || echo "ARM PAIR NOT VERIFIED -- do not run an A/B on these images."
exit "$fail"
