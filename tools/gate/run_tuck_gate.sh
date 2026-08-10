#!/bin/bash
# run_tuck_gate.sh -- the whole v8+DRTUCK gate, ONE arm at a time (Mesen is single-instance).
# Aborts if the smoke arm's log is missing/untagged, so a broken instrument cannot burn the queue.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
R="$D/tools/gate/run_one5.sh"
LOG="$D/tmp/clean/tuckgate.log"
mkdir -p "$D/tmp/clean"
: >"$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "=== SMOKE: v8tuck 1500f, descriptors ON ==="
bash "$R" t-smoke  "$D/roms/v8tuck.nes"            1500  1 2>&1 | tee -a "$LOG"
command grep -aq "TUCK_EXEC_D1" "$D/tmp/clean/t-smoke/probe5.log" 2>/dev/null || {
  say "ABORT: smoke produced no valid SUMMARY -- instrument broken, queue not run"; exit 1; }

say "=== MECH A: v8tuck + DRHOLDBOARD=1, hardening ON (expect 0 mixed-PRG / 0 wipes) ==="
bash "$R" t-mech-on   "$D/roms/v8tuck-hb1.nes"        3000 1 2>&1 | tee -a "$LOG"
say "=== MECH B: v8tuck + DRHOLDBOARD=1, hardening OFF (DEFECT MUST FIRE) ==="
bash "$R" t-mech-off  "$D/roms/v8tuck-hb1-nofix.nes"  3000 1 2>&1 | tee -a "$LOG"
say "=== MECH C: v8 plain + DRHOLDBOARD=1, hardening OFF (reference defect rate) ==="
bash "$R" t-plain-off "$D/roms/v8plain-hb1-nofix.nes" 3000 1 2>&1 | tee -a "$LOG"
say "=== MECH D: v8 plain + DRHOLDBOARD=1, hardening ON (reference hardened) ==="
bash "$R" t-plain-on  "$D/roms/v8plain-hb1.nes"       3000 1 2>&1 | tee -a "$LOG"

say "=== FUNC/EXEC: v8tuck ship flags, 18000f, descriptors ON ==="
bash "$R" t-func "$D/roms/v8tuck.nes"  18000 1 2>&1 | tee -a "$LOG"
say "=== EXEC CONTROL: v8 plain (DRTUCK=0), 18000f, SAME descriptors served ==="
bash "$R" t-ctl  "$D/roms/v8repro.nes" 18000 1 2>&1 | tee -a "$LOG"
say "=== FUNC BASELINE: v8 plain, 18000f, descriptors OFF ==="
bash "$R" t-base "$D/roms/v8repro.nes" 18000 0 2>&1 | tee -a "$LOG"

say "=== ALL ARMS DONE ==="
for t in t-smoke t-mech-on t-mech-off t-plain-off t-plain-on t-func t-ctl t-base; do
  s=$(command grep -a SUMMARY "$D/tmp/clean/$t/probe5.log" 2>/dev/null | head -1)
  echo "${t}: ${s:-NO LOG}" | tee -a "$LOG"
done
