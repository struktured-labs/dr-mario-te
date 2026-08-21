#!/bin/bash
# run_tuck_gate2.sh -- probe6 arms: the composition test the probe5 mechanism arms could NOT do,
# plus the high-n execution pair.
#
# WHY A SECOND PASS. probe5's mechanism arms published ZERO tucks (t-mech-on: tuck_pub=0 in 12
# searches). Cause, measured: DRHOLDBOARD=1 -- the very trigger the mechanism gate needs -- makes
# the driver stamp HOLD_BUF over the live playfield every hook, so a board-derived descriptor
# evaluates on garbage. A board-derived probe therefore CANNOT test "long hook + tucks firing".
# probe6 mode 3 publishes a board-independent descriptor so the tuck branch runs on every hook
# while the trigger is present. probe6 mode 2 fixes probe5's other instrument defect (trigger row
# so shallow the capsule was already past it when the copro answer arrived).
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
R="$D/tools/gate/run_one6.sh"
LOG="$D/tmp/clean/tuckgate2.log"
mkdir -p "$D/tmp/clean"; : >"$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "=== MECH A2: v8+tuck + HOLDBOARD=1, hardening ON,  tucks FIRING (expect 0 mixed-PRG) ==="
bash "$R" u-mech-on   "$D/roms/v8tuck-hb1.nes"        3000 3 2>&1 | tee -a "$LOG"
say "=== MECH B2: v8+tuck + HOLDBOARD=1, hardening OFF, tucks FIRING (DEFECT MUST FIRE) ==="
bash "$R" u-mech-off  "$D/roms/v8tuck-hb1-nofix.nes"  3000 3 2>&1 | tee -a "$LOG"
say "=== MECH C2: v8 plain + HOLDBOARD=1, hardening OFF (defect reference, no tuck code) ==="
bash "$R" u-plain-off "$D/roms/v8plain-hb1-nofix.nes" 3000 3 2>&1 | tee -a "$LOG"
say "=== FUNC+EXEC: v8+tuck ship flags, 18000f, mode 2 ==="
bash "$R" u-func "$D/roms/v8tuck.nes"  18000 2 2>&1 | tee -a "$LOG"
say "=== EXEC CONTROL: v8 plain (DRTUCK=0), 18000f, SAME descriptors ==="
bash "$R" u-ctl  "$D/roms/v8repro.nes" 18000 2 2>&1 | tee -a "$LOG"
say "=== DONE ==="
for t in u-mech-on u-mech-off u-plain-off u-func u-ctl; do
  s=$(command grep -a "SUMMARY tag=$t" "$D/tmp/clean/$t/probe6.log" 2>/dev/null | head -1)
  echo "${t}: ${s:-NO LOG}" | tee -a "$LOG"
done
