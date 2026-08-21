#!/bin/bash
# soak_phase3.sh -- phase 3 ONLY: the seed-segmented v6e soak.
#
# WHY THIS EXISTS RATHER THAN RE-RUNNING drive_soak2.sh
# The first driver completed phases 0, 0b, 1, 2 and 2b and then DIED at 09:32 with phase 3 zero
# frames in. Cause: it was launched with `systemd-run --user --scope` from an agent background
# task, and --scope attaches the unit to the CALLER's session; when the harness reaped that
# background task at ~24 minutes the scope went with it. This script is therefore launched as a
# transient systemd --user SERVICE (not a scope), which is detached and outlives its launcher.
#
# Re-running the whole driver would repeat ~25 minutes of validation that already passed and is
# preserved in tmp/soak/drive_phase012.log. Those results stand on their own and are NOT re-derived
# here; this script consumes them as constants:
#     FPS=60.0          measured by the phase 1 calibration arm (6000 frames, wall=100s, 0 ERR)
#     ACHK_USABLE=0     phase 2b: the killed mutant did NOT fail, so the A-check is VOID by the
#                       pre-registered rule. It stays OFF here. That is not a silent drop -- it
#                       is the recorded verdict, and the report must headline it.
#
# The soak's own arms are untouched: same run_soak.sh, same probe_soak.lua, same cart, so the
# four segments remain byte-identical instrumentation and the pooled bound stays homogeneous.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
R=$D/tools/gate
BOOT=$D/tmp/soak/v6e_mmc1.nes
LOG=$D/tmp/soak/drive.log
SEEDS="${SOAK_SEEDS:-114 4271 21013 30011}"
FPS="${SOAK_FPS:-60.0}"
DEADLINE="${DEADLINE_EPOCH:?DEADLINE_EPOCH required}"
left() { echo $(( DEADLINE - $(date +%s) )); }
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

ARM_RC=0
arm() {  # arm <tag> <cart> <frames> <timeout>
  local tag="$1" cart="$2" fr="$3" tmo="$4"
  while :; do
    SEAT_WAIT_POLLS=180 bash "$R/run_soak.sh" "$tag" "$cart" "$fr" "$tmo" 2>&1 | tee -a "$LOG"
    ARM_RC=${PIPESTATUS[0]}
    [ "$ARM_RC" != 4 ] && return 0
    if [ "$(left)" -lt 900 ]; then say "$tag: seat never freed and budget is gone -- UNRUN"; return 0; fi
    say "$tag: seat held by another lane; $(left)s budget left, waiting again"
  done
}

say "=== phase 3 RELAUNCH (detached service) ==="
say "    v6e c0082cb3 ; seeds: $SEEDS ; FPS=$FPS from phase 1 ; ACHK=0 (VOID per phase 2b)"

# ⚠ The boot image must still be the v6e cart. The first driver proved this in phase 0, but that
# was a different process 30 minutes ago and other lanes write into this same tmp tree -- one of
# them is running arms against v8ship_soak_mmc1.nes right now. Re-checking costs nothing and is
# the difference between soaking the ship cart and soaking whatever last landed at that path.
BOOT_MD5=$(md5sum "$BOOT" | command cut -d' ' -f1)
say "    boot image md5=$BOOT_MD5"
if [ "$BOOT_MD5" != "1e421ca63bbc949767ea27e2c0279ece" ]; then
  say "FATAL: boot image is NOT the phase-0-verified v6e cart -- refusing to soak an unknown ROM"
  exit 1
fi

NSEED=$(echo $SEEDS | wc -w)
REM=$(left); BUDGET=$(( REM - 600 ))
if [ "$BUDGET" -lt 600 ]; then say "FATAL: no budget left for the soak ($BUDGET s)"; exit 1; fi
PERSEG=$(( BUDGET / NSEED ))
FRAMES=$(python3 -c "print(int($PERSEG * $FPS * 0.92))")
say "--- SOAK $NSEED segments x $FRAMES frames (${PERSEG}s each at ${FPS} fps, 8% margin) ---"
say "    total ~$(python3 -c "print(int($FRAMES*$NSEED))") frames = ~$(python3 -c "print(round($FRAMES*$NSEED/60.0988/60,1))") minutes of emulated play"

for sd in $SEEDS; do
  RL=$(left)
  if [ "$RL" -lt 700 ]; then say "seed $sd SKIPPED: only ${RL}s left"; continue; fi
  SEGB=$(( RL - 600 )); [ "$SEGB" -gt "$PERSEG" ] && SEGB=$PERSEG
  SEGF=$(python3 -c "print(int($SEGB * $FPS * 0.92))")
  say "--- segment seed=$sd : $SEGF frames, ${SEGB}s budget ---"
  t0=$(date +%s)
  PS_SEED=$sd PS_ACHK=0 PS_INJECT=0 PS_CKPT=30000 \
    arm "s-soak-s$sd" "$BOOT" "$SEGF" $(( SEGB + 240 ))
  say "segment seed=$sd rc=$ARM_RC wall=$(( $(date +%s) - t0 ))s"
done

say "--- pooled bound ---"
python3 "$R/soak_bound.py" $D/tmp/soak/s-soak-s*/probe_soak.log 2>&1 | tee -a "$LOG"
say "=== soak_phase3 done ==="
