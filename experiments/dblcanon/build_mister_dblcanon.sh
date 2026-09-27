#!/usr/bin/env bash
# MiSTer θ400+DRDBLCANON core compile (#123).  Modelled on ship_theta400_wrapper.sh,
# with the firmware guard pointed at the NEW hash and a RESTORE TRAP added.
#
# ⚠ NES_MiSTer-winner is a SHARED tree, not my worktree.  This script mutates exactly
# one file in it (copro_rom.hex) and restores it on ANY exit path, including failure
# and interrupt.  Nothing else in that tree is touched by this script; ship_build.sh
# writes its own outputs and archives.
#
# The compile produces a CANDIDATE, not an artifact: arm (b) is the sole decider, and
# a failing arm (b) means this bitstream is quarantined with a FAILED_GATE marker,
# never staged.  (team-lead ruling, 2026-08-18)
set -uo pipefail

FORK=/home/struktured/projects/NES_MiSTer-winner
SHIP=/home/struktured/projects/dr-mario-main-wt/experiments/rtl_chain/ship_build.sh
SCRATCH="${DRM_SCRATCH:?set DRM_SCRATCH}"
NEW_FW="$SCRATCH/fw_th400_canon1.hex"       # DRDBLCANON=1 build
WANT_FW=b03a586e8316ccf6741a15ac70123886    # its md5
BASE_FW=f78f1e9376405dc996404f68dfa9dfb8    # what the fork must start and end holding
SEED=13
TAG=theta400dblcanon

cd "$FORK" || exit 64

pre=$(md5sum copro_rom.hex | cut -d' ' -f1)
if [ "$pre" != "$BASE_FW" ]; then
  echo "ABORT: fork's copro_rom.hex is $pre, expected the θ400 baseline $BASE_FW." >&2
  echo "       Someone else may be mid-build in this shared tree -- not touching it." >&2
  exit 64
fi
cp -p copro_rom.hex "$SCRATCH/fork_copro_rom.orig.hex" || exit 64
echo "backed up fork firmware ($pre) -> $SCRATCH/fork_copro_rom.orig.hex"

restore() {
  cp -p "$SCRATCH/fork_copro_rom.orig.hex" "$FORK/copro_rom.hex"
  echo "RESTORED fork copro_rom.hex -> $(md5sum "$FORK/copro_rom.hex" | cut -d' ' -f1)"
}
trap restore EXIT INT TERM

cp "$NEW_FW" copro_rom.hex || exit 64
got=$(md5sum copro_rom.hex | cut -d' ' -f1)
if [ "$got" != "$WANT_FW" ]; then
  echo "ABORT: installed firmware md5 $got != expected $WANT_FW" >&2
  exit 64
fi
echo "fw-guard PRE : copro_rom.hex $got OK (DRDBLCANON=1)"

"$SHIP" "$SEED" "$TAG"
rc=$?

post=$(md5sum copro_rom.hex | cut -d' ' -f1)
echo "fw-guard POST: copro_rom.hex $post $( [ "$post" = "$WANT_FW" ] && echo OK || echo CHANGED-DURING-BUILD )"
[ "$post" = "$WANT_FW" ] || rc=64
echo "WRAPPER EXIT rc=$rc"
exit "$rc"
