#!/bin/bash
# run_slack_dose.sh -- is the executor's ~40% miss a CART defect or an instrument artefact?
#
# PRE-REGISTERED. The observational split (u-func 23/23 completed with >=2 rows of budget under
# the switch; w-v1-func 0/4 completed with ~0 budget) says the failures are REMAINING FALL, not
# depth. This is the designed version: hold everything else fixed and sweep only SLACK, the
# number of empty rows guaranteed below the trigger in BOTH columns.
#   PREDICTION: SLACK=0 -> strandings > 0 ; SLACK=4 -> strandings == 0.
#   REFUTATION: if SLACK=0 completes cleanly, the mechanism is wrong and that is the report.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
R="$D/tools/gate/run_one8.sh"
LOG="$D/tmp/clean/slackdose.log"
mkdir -p "$D/tmp/clean"; : >"$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
for s in 0 2 4; do
  say "=== SLACK=$s : v8+tuck, 12000f, synthetic descriptors ==="
  P8_SLACK=$s bash "$R" "s-slack$s" "$D/roms/v8tuck.nes" 12000 2 2>&1 | tee -a "$LOG"
done
say "=== DONE ==="
for s in 0 2 4; do
  t="s-slack$s"
  echo "${t}: $(command grep -a "SUMMARY tag=$t" "$D/tmp/clean/$t/probe8.log" 2>/dev/null | head -1)" | tee -a "$LOG"
done
