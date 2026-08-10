#!/bin/bash
# drive_soak.sh -- the whole soak, one process, self-sizing.
#
# Phase 0  byte identity: the image that BOOTS is the ship cart (verify_soak_bytes.py).
# Phase 1  calibration: a short arm on the ship bytes. Gives (a) frames/sec, which is what
#          sizes the soak, and (b) the HEALTHY maxima for every new threshold, so the soak's
#          margins are measured rather than guessed.
# Phase 2  killed-mutant validation of the NEW detectors. A check that cannot fail is not a
#          check, so each one is driven with the fault it exists to catch BEFORE the soak runs:
#            s-val-busy   inject BUSY=1        -> STUCK-BUSY must fire
#            s-val-title  inject mode 0        -> TITLE-RETURN and GAP-STALL must fire
#            s-val-mech   hardening OFF cart   -> MIXED_PRG / wipes / bank0 must fire
#            s-val-tuckwr DRTUCK=1 cart        -> tuckwr must go positive (it is 0 on the ship
#                                                 cart, which is what makes it an identity proof)
# Phase 3  the soak itself, sized to land before DEADLINE_EPOCH.
# Phase 4  if the soak came back PARTIAL and budget remains, continue in a second segment
#          rather than losing the rest of the window.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
R=$D/tools/gate
SHIP_MD5=087ff959ac510c613bbbd2eb1ac5ecf3
SHIP="$D/release/v8_20260810/v8 REMATCH (hardened).nes"
BOOT=$D/tmp/soak/v8ship_soak_mmc1.nes
NOFIX=$D/tmp/soak/v8nofix_mmc1.nes
TUCKC=$D/tmp/soak/v8tuck_soak_mmc1.nes
LOG=$D/tmp/soak/drive.log
DEADLINE=${DEADLINE_EPOCH:?DEADLINE_EPOCH required}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
left() { echo $(( DEADLINE - $(date +%s) )); }

# The Mesen seat is shared with ~40 other lanes and two were already queued when this started.
# run_soak.sh returns 4 = UNRUN when the seat never freed -- that is the POLITE failure, and it
# must never be read as "the arm ran and found nothing". So retry rc=4 until the deadline instead
# of falling through with a default, which is how a soak silently becomes a no-op.
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
say "=== drive_soak start; budget ends $(date -d @"$DEADLINE" +%H:%M:%S), $(left)s left ==="

# ---------------- Phase 0: byte identity ----------------
say "--- phase 0: boot image identity ---"
python3 "$R/verify_soak_bytes.py" --src "$SHIP" --out "$BOOT" --md5 "$SHIP_MD5" 2>&1 | tee -a "$LOG"
if [ "${PIPESTATUS[0]}" != 0 ]; then say "FATAL: boot image is not the ship cart"; exit 1; fi

# ---------------- Phase 1: calibration ----------------
say "--- phase 1: calibration (6000 frames, ship bytes) ---"
t0=$(date +%s)
PS_INJECT=0 arm s-cal "$BOOT" 6000 900
crc=$ARM_RC
cal_wall=$(( $(date +%s) - t0 ))
CAL=$D/tmp/soak/s-cal/probe_soak.log
FPS=$(command grep -a '^SOAK ' "$CAL" 2>/dev/null | command sed -n 's/.*fps=\([0-9.]*\).*/\1/p' | command tail -1)
[ -z "${FPS:-}" ] && FPS=55
say "calibration rc=$crc wall=${cal_wall}s measured fps=$FPS"
say "healthy maxima: $(command grep -a '^SOAK2 ' "$CAL" 2>/dev/null | command tail -1)"

# ---------------- Phase 2: killed-mutant validation ----------------
say "--- phase 2: killed-mutant validation of the NEW detectors ---"
PS_INJECT=1 PS_INJA=1500 PS_INJB=2400 arm s-val-busy   "$BOOT"  3000 900
PS_INJECT=2 PS_INJA=1500 PS_INJB=2400 arm s-val-title  "$BOOT"  3000 900
PS_INJECT=0                           arm s-val-mech   "$NOFIX" 3000 900
PS_INJECT=0                           arm s-val-tuckwr "$TUCKC" 3000 900

# ---------------- Phase 3: the soak ----------------
REM=$(left)
# reserve 12 min for the final segment's teardown + reporting
BUDGET=$(( REM - 720 ))
if [ "$BUDGET" -lt 600 ]; then say "FATAL: no budget left for the soak ($BUDGET s)"; exit 1; fi
FRAMES=$(python3 -c "print(int($BUDGET * $FPS * 0.92))")
say "--- phase 3: SOAK $FRAMES frames (budget ${BUDGET}s at ${FPS} fps, 8% margin) ---"
say "    ~$(python3 -c "print(round($FRAMES/60.0988/60,1))") minutes of emulated play"
t0=$(date +%s)
PS_INJECT=0 PS_CKPT=30000 arm s-soak "$BOOT" "$FRAMES" $(( BUDGET + 300 ))
src=$ARM_RC
say "soak rc=$src wall=$(( $(date +%s) - t0 ))s"

# ---------------- Phase 4: continue if it died early ----------------
if [ "$src" = 2 ] || [ "$src" = 1 ]; then
  REM=$(left); BUDGET=$(( REM - 420 ))
  if [ "$BUDGET" -gt 900 ]; then
    FRAMES2=$(python3 -c "print(int($BUDGET * $FPS * 0.92))")
    say "--- phase 4: soak returned $src with ${REM}s left; continuing $FRAMES2 frames ---"
    PS_INJECT=0 PS_CKPT=30000 arm s-soak2 "$BOOT" "$FRAMES2" $(( BUDGET + 240 ))
    say "soak2 rc=$ARM_RC"
  else
    say "phase 4 skipped: only ${REM}s left"
  fi
fi

say "=== drive_soak done ==="
