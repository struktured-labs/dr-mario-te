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
#            s-val-title  inject mode 0        -> TITLE-RETURN + MODE-STALL + GAP-STALL
#            s-val-mech   hardening OFF cart   -> MIXED_PRG / wipes / bank0 must fire
#            s-val-tuckwr DRTUCK=1 cart        -> tuckwr must go positive (it is 0 on the ship
#                                                 cart, which is what makes it an identity proof)
# Phase 3  the soak itself, sized to land before DEADLINE_EPOCH.
# Phase 4  if the soak came back PARTIAL and budget remains, continue in a second segment
#          rather than losing the rest of the window.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
R=$D/tools/gate
# ⚠ TARGET = v6e, NOT 087ff959. The staged v8 candidate is ON HOLD: its DRRTIVEC shield does
# `LDA $A02E` and falls into the game's NMI handler, so A is destroyed on every NMI the shield
# handles (release/v8_20260810/HOLD_DO_NOT_INSTALL.md). Confirmed here at byte level: the
# A-clobber sequence appears 2x in 087ff959 at file 0x4EFC/0xCEFC and 0x in v6e, which carries
# the 15-byte A-preserving shield at the same offsets. v6e differs from the held cart in
# EXACTLY 31 bytes -- the two shields plus the $FFFE IRQ vector low byte f3->f6 -- and its flag
# snapshot is identical. Soaking the held cart would have produced a confident five-hour clean
# headline for a build with a known register-corruption defect.
SHIP_MD5=c0082cb34259007854120d3d4ab9fa27
SHIP="$D/roms/v6e.nes"
BOOT=$D/tmp/soak/v6e_mmc1.nes
HELD=$D/tmp/soak/v8ship_soak_mmc1.nes      # the DEFECTIVE cart -- used ONLY as a killed mutant
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

# ---------------- Phase 0b: instrument capability ----------------
# Can Lua read the 6502 accumulator in THIS build, and under which key? README_GATE says
# `emu.getState().cpu` is nil, which could mean "no registers" or "different key" -- opposite
# consequences, so it is measured. Also counts $CEEC executions, which answers whether the
# DRRTIVEC shield path is live at all, register-free.
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
say "  accumulator candidates: $(command grep -a '^STATE .*\.a = \|^STATE a = ' "$DGO/diag_state.log" 2>/dev/null | command head -4 | tr '\n' ' ')"

# ---------------- Phase 1: calibration ----------------
say "--- phase 1: calibration (6000 frames, v6e ship bytes) ---"
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
# ⚠ THRESHOLDS LOWERED FOR THIS ARM ONLY. The soak keeps PS_STALL=7200 / PS_GAPMAX=3600, but a
# 3000-frame arm with a 900-frame injection window CANNOT reach either, so as originally written
# mode_stall and gap_stall were structurally incapable of firing in the very run meant to prove
# they can -- the same defect shape as an acceptance harness that keeps P1 alive. The FAULT is
# unchanged and genuine (mode really is frozen at 0 for 900 frames); only the THRESHOLD moves, to
# something the arm can cross. The soak arm's wide margins are untouched.
# ⚠ search_stall is NOT validated by this or any arm and is reported UNVALIDATED: it keys on the
# cart having stopped issuing GO while still in mode 4, and no instrument-side injection produces
# that without forging the detector's own input. The honest route is a cart-side fault build.
PS_INJECT=2 PS_INJA=1500 PS_INJB=2400 PS_STALL=600 PS_GAPMAX=600 \
                                      arm s-val-title  "$BOOT"  3000 900
PS_INJECT=0                           arm s-val-mech   "$NOFIX" 3000 900
PS_INJECT=0                           arm s-val-tuckwr "$TUCKC" 3000 900

# ---- Phase 2b: A-INTEGRITY, the check the previous 18k gate did not have ----
# The coordinator's point: a gate that counts matches cannot see a corrupted accumulator. This
# pair makes the soak SENSITIVE to it. The held cart is the killed mutant -- if s-val-aclob does
# NOT report FAIL_A_CORRUPTED, the A-check is not working and the soak's ACHK=PASS means nothing,
# so the driver says so loudly rather than proceeding on a check it has not seen fail.
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
  say "A-CHECK IS LIVE: it fired on the defect and stayed clean on the fix. Enabling for the soak."
else
  say "⚠ A-CHECK NOT USABLE (mutant did not fail, or fix did not pass, or registers unavailable)."
  say "  The soak will still run, but its ACHK line must be read as VOID, not as evidence."
fi

# ---------------- Phase 3: the soak ----------------
REM=$(left)
# reserve 12 min for the final segment's teardown + reporting
BUDGET=$(( REM - 720 ))
if [ "$BUDGET" -lt 600 ]; then say "FATAL: no budget left for the soak ($BUDGET s)"; exit 1; fi
FRAMES=$(python3 -c "print(int($BUDGET * $FPS * 0.92))")
say "--- phase 3: SOAK $FRAMES frames (budget ${BUDGET}s at ${FPS} fps, 8% margin) ---"
say "    ~$(python3 -c "print(round($FRAMES/60.0988/60,1))") minutes of emulated play"
t0=$(date +%s)
PS_ACHK=$ACHK_USABLE PS_INJECT=0 PS_CKPT=30000 arm s-soak "$BOOT" "$FRAMES" $(( BUDGET + 300 ))
src=$ARM_RC
say "soak rc=$src wall=$(( $(date +%s) - t0 ))s"

# ---------------- Phase 4: continue if it died early ----------------
if [ "$src" = 2 ] || [ "$src" = 1 ]; then
  REM=$(left); BUDGET=$(( REM - 420 ))
  if [ "$BUDGET" -gt 900 ]; then
    FRAMES2=$(python3 -c "print(int($BUDGET * $FPS * 0.92))")
    say "--- phase 4: soak returned $src with ${REM}s left; continuing $FRAMES2 frames ---"
    PS_ACHK=$ACHK_USABLE PS_INJECT=0 PS_CKPT=30000 arm s-soak2 "$BOOT" "$FRAMES2" $(( BUDGET + 240 ))
    say "soak2 rc=$ARM_RC"
  else
    say "phase 4 skipped: only ${REM}s left"
  fi
fi

say "=== drive_soak done ==="
