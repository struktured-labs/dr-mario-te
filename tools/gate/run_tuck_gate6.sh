#!/bin/bash
# run_tuck_gate6.sh -- v8+DRTUCK gate, probe6 (fixed trigger-row latency), one arm at a time.
#
# ORDER IS DELIBERATE: the defect-must-fire control runs FIRST. If MECH-OFF and PLAIN-OFF both
# come back with zero mixed-into-PRG loads then the defect is not present in the v8 lineage at
# all and every "0 events" result below it is VOID, not a pass. Published reference to beat:
# a-v6crepro = MIXED_total 126 / MIXED_PRG_nonboot 18 / soft8036 20 / wipes 18 / sr_resets 2.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
R="$D/tools/gate/run_one6.sh"
LOG="$D/tmp/clean/tuckgate6.log"
mkdir -p "$D/tmp/clean"
: >"$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "=== VOID-BREAKER 1: v8+tuck + HB=1, hardening OFF -- DEFECT MUST FIRE ==="
bash "$R" t6-mech-off  "$D/roms/v8tuck-hb1-nofix.nes"  3000 2 2>&1 | tee -a "$LOG"
say "=== VOID-BREAKER 2: v8 plain + HB=1, hardening OFF -- defect reference, no tuck ==="
bash "$R" t6-plain-off "$D/roms/v8plain-hb1-nofix.nes" 3000 2 2>&1 | tee -a "$LOG"
say "=== MECH: v8+tuck + HB=1, hardening ON, tucks firing -- the never-gated composition ==="
bash "$R" t6-mech-on   "$D/roms/v8tuck-hb1.nes"        3000 2 2>&1 | tee -a "$LOG"

say "=== FUNC/EXEC: v8+tuck ship flags, 18000f ==="
bash "$R" t6-func "$D/roms/v8tuck.nes"  18000 2 2>&1 | tee -a "$LOG"
say "=== EXEC CONTROL: v8 plain (DRTUCK=0), 18000f, SAME descriptors served ==="
bash "$R" t6-ctl  "$D/roms/v8repro.nes" 18000 2 2>&1 | tee -a "$LOG"

say "=== ALL ARMS DONE ==="
for t in t6-mech-off t6-plain-off t6-mech-on t6-func t6-ctl; do
  s=$(command grep -a "SUMMARY tag=$t" "$D/tmp/clean/$t/probe6.log" 2>/dev/null | head -1)
  echo "${t}: ${s:-NO LOG}" | tee -a "$LOG"
done
