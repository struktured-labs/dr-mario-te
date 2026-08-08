#!/usr/bin/env bash
# Build the gate-readout debug firmwares (DRCOPRO_TUCKV3_DBGPUB=1 and =2) plus the
# theta=150 control, into /mnt/data/drmario_cosim/fw/<name>/copro_rom.hex.
#
# Uses build_dbgpub.py, which writes to a named path and pins the emitter modules to
# this worktree -- see its docstring for why both of those matter. The repo's shipping
# fpga/copro/copro_rom.hex is never opened for writing here; the SHIP CHECK at the end
# proves it.
#
# GUARD: the DBGPUB=0 build must reproduce 5d010f62 exactly, the shipped s20t3 image.
# If the debug emit ever leaks into the default build, or a knob drifts, this fails
# loudly before any measurement is taken. The s20t3 recipe below (note DRFIX=1, which
# is not guessable from the arm name) was recovered by exhaustive knob sweep after the
# arms already in fw/ turned out to carry no provenance sidecar.
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"
SHIP="$(cd ../../fpga/copro && pwd)/copro_rom.hex"
SHIP_MD5_BEFORE=$(md5sum "$SHIP" | cut -d' ' -f1)
FW=/mnt/data/drmario_cosim/fw
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python

build() {  # build <outdir> <dbgpub>
  env DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1 DRFIX=1 \
      DRSTRAND=20 DRCHAIN=180 DRCOPRO_ARM=1 \
      DRCOPRO_TUCKV3_THETA="${THETA:-150}" DRCOPRO_TUCKV3_DBGPUB="$2" \
      "$PY" "$HERE/build_dbgpub.py" "$FW/$1/copro_rom.hex" >/dev/null
  echo "$1 (DBGPUB=$2 theta=${THETA:-150}) -> $(md5sum "$FW/$1/copro_rom.hex" | cut -c1-8)"
}

build dbg_ctl0 0
CTL=$(md5sum "$FW/dbg_ctl0/copro_rom.hex" | cut -c1-8)
[ "$CTL" = "5d010f62" ] || { echo "GUARD FAILED: DBGPUB=0 gave $CTL, expected 5d010f62"; exit 4; }
echo "GUARD PASS: DBGPUB=0 is byte-identical to the shipped s20t3 image"

build dbg_pub1 1
build dbg_pub2 2
build dbg_pub3 3

# The debug images must NOT collide with the control -- an identical hash here is the
# signature of the emit not reaching the image at all, which is exactly how the
# cross-worktree tuck_v3 import first showed itself.
for a in dbg_pub1 dbg_pub2 dbg_pub3; do
  h=$(md5sum "$FW/$a/copro_rom.hex" | cut -c1-8)
  [ "$h" != "$CTL" ] || { echo "GUARD FAILED: $a is identical to the control ($h)"; exit 5; }
done
echo "GUARD PASS: both debug images are hash-distinct from the control and each other"

SHIP_MD5_AFTER=$(md5sum "$SHIP" | cut -d' ' -f1)
[ "$SHIP_MD5_BEFORE" = "$SHIP_MD5_AFTER" ] \
  || { echo "FATAL: ship hex changed ($SHIP_MD5_BEFORE -> $SHIP_MD5_AFTER)"; exit 9; }
echo "SHIP CHECK: fpga/copro/copro_rom.hex untouched ($SHIP_MD5_AFTER)"
