#!/bin/bash
# run_tuck_gate.sh -- the whole v8+DRTUCK gate, ONE arm at a time (Mesen is single-instance).
#
# P5_TUCK=2 (synthetic executor stress) everywhere: descriptors fire on nearly every pill, so
#   * the driver hook carries the tuck path at its MAXIMUM rate -> the strongest available
#     stress on the composition the MMC1 hardening has never been gated against, and
#   * the execution counts get real n instead of the ~2-per-2500-frames the geometric finder
#     yields against this probe's flat-stacking brain.
# Every arm is paired with a control that must come out DIFFERENT, or that gate is void.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
R="$D/tools/gate/run_one5.sh"
LOG="$D/tmp/clean/tuckgate.log"
mkdir -p "$D/tmp/clean"
: >"$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "=== MECH A: v8+tuck + DRHOLDBOARD=1, hardening ON  (expect 0 mixed-PRG / 0 bank0) ==="
bash "$R" t-mech-on   "$D/roms/v8tuck-hb1.nes"        3000 2 2>&1 | tee -a "$LOG"
say "=== MECH B: v8+tuck + DRHOLDBOARD=1, hardening OFF (DEFECT MUST FIRE) ==="
bash "$R" t-mech-off  "$D/roms/v8tuck-hb1-nofix.nes"  3000 2 2>&1 | tee -a "$LOG"
say "=== MECH C: v8 plain + DRHOLDBOARD=1, hardening OFF (defect reference, no tuck) ==="
bash "$R" t-plain-off "$D/roms/v8plain-hb1-nofix.nes" 3000 2 2>&1 | tee -a "$LOG"
say "=== MECH D: v8 plain + DRHOLDBOARD=1, hardening ON  (hardened reference, no tuck) ==="
bash "$R" t-plain-on  "$D/roms/v8plain-hb1.nes"       3000 2 2>&1 | tee -a "$LOG"

say "=== FUNC/EXEC: v8+tuck ship flags, 18000f ==="
bash "$R" t-func "$D/roms/v8tuck.nes"  18000 2 2>&1 | tee -a "$LOG"
say "=== EXEC CONTROL: v8 plain (DRTUCK=0), 18000f, SAME descriptors served ==="
bash "$R" t-ctl  "$D/roms/v8repro.nes" 18000 2 2>&1 | tee -a "$LOG"

say "=== ALL ARMS DONE ==="
for t in t-mech-on t-mech-off t-plain-off t-plain-on t-func t-ctl; do
  s=$(command grep -a "SUMMARY tag=$t" "$D/tmp/clean/$t/probe5.log" 2>/dev/null | head -1)
  echo "${t}: ${s:-NO LOG}" | tee -a "$LOG"
done
