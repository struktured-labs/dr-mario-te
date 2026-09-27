#!/bin/bash
# drive_soak2.sh -- the v6e soak, one process, self-sizing, SPLIT ACROSS SEEDS.
#
# ⚠ TARGET = v6e, NOT 087ff959. The staged v8 candidate is ON HOLD: its DRRTIVEC shield does
# `LDA $A02E` and falls into the game's NMI handler, so A is destroyed on every NMI the shield
# handles (release/v8_20260810/HOLD_DO_NOT_INSTALL.md). Confirmed at byte level: the A-clobber
# sequence appears 2x in 087ff959 at file 0x4EFC/0xCEFC and 0x in v6e, which carries the 15-byte
# A-preserving shield at those same offsets. v6e differs from the held cart in EXACTLY 31 bytes
# (two shields + the $FFFE IRQ vector low byte f3->f6) and its 57-flag snapshot is identical.
#
# WHY SEEDS, not one long run (coordinator's call): a five-hour run on ONE seed bounds THAT
# SEED. Splitting the same window across several seeds buys seed diversity for free -- it is the
# scientific benefit of running parallel instances without the shared-config change that
# parallelism would have needed. Segments are serial, so the Mesen seat is held by at most one
# of them at a time. Each segment is its own arm with its own SUMMARY, so a segment that
# completes is bankable even if a later one is cut off, and the bound pools over segments.
#
# Phase 0   byte identity: the image that BOOTS is the v6e cart.
# Phase 0b  instrument capability: are CPU registers reachable in this Mesen build, and is the
#           DRRTIVEC shield path even executed? Decides whether an A-check is possible at all.
# Phase 1   calibration: frames/sec (which sizes everything) + the HEALTHY maxima behind each
#           new threshold, so margins are measured rather than asserted.
# Phase 2   killed-mutant validation of the NEW detectors -- a check that cannot fail is not a
#           check, so each is driven with the fault it exists to catch BEFORE the soak.
# Phase 2b  A-integrity killed-mutant PAIR: the held cart must FAIL, v6e must PASS. If that does
#           not hold, the A-check is disabled and said to be void rather than shipped green.
# Phase 3   the soak, split into SEGMENTS across seeds, sized to land before DEADLINE_EPOCH.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
R=$D/tools/gate
SHIP_MD5=c0082cb34259007854120d3d4ab9fa27
SHIP="$D/roms/v6e.nes"
BOOT=$D/tmp/soak/v6e_mmc1.nes
HELD=$D/tmp/soak/v8ship_soak_mmc1.nes      # the DEFECTIVE cart -- used ONLY as a killed mutant
NOFIX=$D/tmp/soak/v8nofix_mmc1.nes
TUCKC=$D/tmp/soak/v8tuck_soak_mmc1.nes
LOG=$D/tmp/soak/drive.log
DEADLINE=${DEADLINE_EPOCH:?DEADLINE_EPOCH required}
SEEDS=${SOAK_SEEDS:-"114 4271 21013 30011"}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
left() { echo $(( DEADLINE - $(date +%s) )); }

# The Mesen seat is shared with ~40 lanes. run_soak.sh returns 4 = UNRUN when the seat never
# freed -- the POLITE failure, which must never be read as "the arm ran and found nothing". So
# rc=4 is retried until the deadline instead of falling through, which is how a soak silently
# becomes a no-op.
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

mkdir -p "$D/tmp/soak"
say "=== drive_soak2 start; budget ends $(date -d @"$DEADLINE" +%H:%M:%S), $(left)s left ==="
say "    target v6e $SHIP_MD5 ; seeds: $SEEDS ; Pocket cadence DLAT=34"

# ---------------- Phase 0 ----------------
say "--- phase 0: boot image identity ---"
python3 "$R/verify_soak_bytes.py" --src "$SHIP" --out "$BOOT" --md5 "$SHIP_MD5" 2>&1 | tee -a "$LOG"
if [ "${PIPESTATUS[0]}" != 0 ]; then say "FATAL: boot image is not the v6e cart"; exit 1; fi

# ---------------- Phase 0b ----------------
say "--- phase 0b: instrument capability (registers reachable? shield live?) ---"
DGO=$D/tmp/soak/s-diag; mkdir -p "$DGO"
for dtry in 1 2 3; do
  while ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null; do
    [ "$(left)" -lt 900 ] && break; sleep 10
  done
  ddisp=$((200 + RANDOM % 60)); rm -f "/tmp/.X${ddisp}-lock" "/tmp/.X11-unix/X${ddisp}"
  Xvfb ":$ddisp" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 & dx=$!
  sleep 2
  ( cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
    DISPLAY=":$ddisp" DG_OUT="$DGO" DG_MAXF=600 DG_TAG=s-diag \
    timeout -k 10 300 /home/struktured/projects/dr-mario-mods/run_mesen.sh "$BOOT" \
      "$R/diag_state.lua" ) >"$DGO/stdout.log" 2>&1
  kill "$dx" 2>/dev/null
  command grep -aq 'tag=s-diag' "$DGO/diag_state.log" 2>/dev/null && break
  say "phase 0b try $dtry produced no tagged log; retrying"
done
say "capability: $(command grep -a '^SUMMARY ' "$DGO/diag_state.log" 2>/dev/null || echo '<no log>')"
say "  Q2 in-callback getState: $(command grep -a '^Q2 inside' "$DGO/diag_state.log" 2>/dev/null || echo '<none>')"

# ---------------- Phase 1: calibration ----------------
say "--- phase 1: calibration (6000 frames, v6e ship bytes) ---"
t0=$(date +%s)
PS_INJECT=0 arm s-cal "$BOOT" 6000 900
cal_wall=$(( $(date +%s) - t0 ))
CAL=$D/tmp/soak/s-cal/probe_soak.log
FPS=$(command grep -a '^SOAK ' "$CAL" 2>/dev/null | command sed -n 's/.*fps=\([0-9.]*\).*/\1/p' | command tail -1)
[ -z "${FPS:-}" ] && FPS=55
say "calibration rc=$ARM_RC wall=${cal_wall}s measured fps=$FPS"
say "healthy maxima: $(command grep -a '^SOAK2 ' "$CAL" 2>/dev/null | command tail -1)"
say "ERR lines in calibration (must be none): $(command grep -ac '^ERR ' "$CAL" 2>/dev/null || echo 0)"

# ---------------- Phase 2: killed-mutant validation ----------------
say "--- phase 2: killed-mutant validation of the NEW detectors ---"
PS_INJECT=1 PS_INJA=1500 PS_INJB=2400 arm s-val-busy   "$BOOT"  3000 900
# ⚠ THRESHOLDS LOWERED FOR THIS ARM ONLY. A 3000-frame arm with a 900-frame injection window
# cannot cross PS_GAPMAX=3600 or PS_STALL=7200, so as originally written mode_stall and gap_stall
# were structurally incapable of firing in the very run meant to prove they can -- the same defect
# shape as an acceptance harness that keeps P1 alive. The FAULT is unchanged and genuine (mode
# really is frozen at 0 for 900 frames); only the THRESHOLD moves, to something the arm can cross.
# The soak arms keep their wide 7200/3600 margins.
# ⚠ search_stall is NOT validated by any arm and is reported UNVALIDATED: it keys on the cart
# having stopped issuing GO while still in mode 4, and no instrument-side injection produces that
# without forging the detector's own input. Honest route is a cart-side fault build.
PS_INJECT=2 PS_INJA=1500 PS_INJB=2400 PS_STALL=600 PS_GAPMAX=600 \
                                      arm s-val-title  "$BOOT"  3000 900
PS_INJECT=0                           arm s-val-mech   "$NOFIX" 3000 900
PS_INJECT=0                           arm s-val-tuckwr "$TUCKC" 3000 900

# ---------------- Phase 2b: A-integrity killed-mutant pair ----------------
say "--- phase 2b: A-integrity killed-mutant pair ---"
PS_ACHK=1 PS_INJECT=0 arm s-val-aclob "$HELD" 3000 900
PS_ACHK=1 PS_INJECT=0 arm s-val-aok   "$BOOT" 3000 900
AV_MUT=$(command grep -a '^ACHK ' "$D/tmp/soak/s-val-aclob/probe_soak.log" 2>/dev/null | command tail -1)
AV_FIX=$(command grep -a '^ACHK ' "$D/tmp/soak/s-val-aok/probe_soak.log"   2>/dev/null | command tail -1)
say "A-check on the HELD cart (must FAIL): ${AV_MUT:-<no log>}"
say "A-check on v6e          (must PASS): ${AV_FIX:-<no log>}"
ACHK_USABLE=0
case "$AV_MUT" in *FAIL_A_CORRUPTED*) case "$AV_FIX" in *verdict=PASS*) ACHK_USABLE=1;; esac;; esac
if [ "$ACHK_USABLE" = 1 ]; then
  say "A-CHECK IS LIVE: it fired on the defect and stayed clean on the fix. Enabled for the soak."
else
  say "⚠ A-CHECK NOT USABLE (mutant did not fail, or fix did not pass, or registers unavailable)."
  say "  The soak still runs, but its ACHK line must be read as VOID, not as evidence."
fi

# ---------------- Phase 3: the soak, split across seeds ----------------
NSEED=$(echo $SEEDS | wc -w)
REM=$(left); BUDGET=$(( REM - 600 ))          # reserve 10 min for teardown + reporting
if [ "$BUDGET" -lt 600 ]; then say "FATAL: no budget left for the soak ($BUDGET s)"; exit 1; fi
PERSEG=$(( BUDGET / NSEED ))
FRAMES=$(python3 -c "print(int($PERSEG * $FPS * 0.92))")
say "--- phase 3: SOAK $NSEED segments x $FRAMES frames (${PERSEG}s each at ${FPS} fps, 8% margin) ---"
say "    total ~$(python3 -c "print(int($FRAMES*$NSEED))") frames = ~$(python3 -c "print(round($FRAMES*$NSEED/60.0988/60,1))") minutes of emulated play"
for sd in $SEEDS; do
  RL=$(left)
  if [ "$RL" -lt 700 ]; then say "seed $sd SKIPPED: only ${RL}s left"; continue; fi
  # never let a segment overrun the deadline, even if an earlier one ran long
  SEGB=$(( RL - 600 )); [ "$SEGB" -gt "$PERSEG" ] && SEGB=$PERSEG
  SEGF=$(python3 -c "print(int($SEGB * $FPS * 0.92))")
  say "--- segment seed=$sd : $SEGF frames, ${SEGB}s budget ---"
  t0=$(date +%s)
  PS_SEED=$sd PS_ACHK=$ACHK_USABLE PS_INJECT=0 PS_CKPT=30000 \
    arm "s-soak-s$sd" "$BOOT" "$SEGF" $(( SEGB + 240 ))
  say "segment seed=$sd rc=$ARM_RC wall=$(( $(date +%s) - t0 ))s"
done

say "--- pooled bound ---"
python3 "$R/soak_bound.py" $D/tmp/soak/s-soak-s*/probe_soak.log 2>&1 | tee -a "$LOG"
say "=== drive_soak2 done ==="
