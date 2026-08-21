#!/usr/bin/env bash
# MiSTer θ400+DRDBLCANON respin with the C0-pin video fix (respin-144).
# Modelled on dr-mario-tempo-wt/experiments/dblcanon/build_mister_dblcanon.sh.
# The winner tree must be at commit 1297a6c (b20864a + the NES.qsf C0 pin).
set -uo pipefail

FORK=/home/struktured/projects/NES_MiSTer-winner
SHIP=/home/struktured/projects/dr-mario-main-wt/experiments/rtl_chain/ship_build.sh
HERE=$(dirname "$(readlink -f "$0")")
NEW_FW=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400dblcanon-seed13/copro_rom.hex
WANT_FW=b03a586e8316ccf6741a15ac70123886    # DRDBLCANON=1 firmware (byte-exact keep)
BASE_FW=f78f1e9376405dc996404f68dfa9dfb8    # what the fork must start and end holding
WANT_COMMIT=08f2343
SEED=13
TAG=theta400dblcanon-c0pin

cd "$FORK" || exit 64

at=$(git rev-parse --short HEAD)
[ "$at" = "$WANT_COMMIT" ] || { echo "ABORT: fork at $at, want $WANT_COMMIT (C0-pin commit)" >&2; exit 64; }
command grep -q 'PLLOUTPUTCOUNTER_X0_Y5_N1' NES.qsf || { echo "ABORT: C0 pin absent from NES.qsf" >&2; exit 64; }

pre=$(md5sum copro_rom.hex | cut -d' ' -f1)
if [ "$pre" != "$BASE_FW" ]; then
  echo "ABORT: fork's copro_rom.hex is $pre, expected baseline $BASE_FW (someone mid-build?)" >&2
  exit 64
fi
cp -p copro_rom.hex "$HERE/fork_copro_rom.orig.hex" || exit 64

restore() {
  cp -p "$HERE/fork_copro_rom.orig.hex" "$FORK/copro_rom.hex"
  echo "RESTORED fork copro_rom.hex -> $(md5sum "$FORK/copro_rom.hex" | cut -d' ' -f1)"
}
trap restore EXIT INT TERM

cp "$NEW_FW" copro_rom.hex || exit 64
got=$(md5sum copro_rom.hex | cut -d' ' -f1)
[ "$got" = "$WANT_FW" ] || { echo "ABORT: installed fw md5 $got != $WANT_FW" >&2; exit 64; }
echo "fw-guard PRE : copro_rom.hex $got OK (DRDBLCANON=1)"

"$SHIP" "$SEED" "$TAG"
rc=$?

post=$(md5sum copro_rom.hex | cut -d' ' -f1)
echo "fw-guard POST: copro_rom.hex $post $( [ "$post" = "$WANT_FW" ] && echo OK || echo CHANGED-DURING-BUILD )"
[ "$post" = "$WANT_FW" ] || rc=64
echo "WRAPPER EXIT rc=$rc"
exit "$rc"
