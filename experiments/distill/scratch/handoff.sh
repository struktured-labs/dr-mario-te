#!/bin/bash
# handoff.sh — when PHASE 1 exits, hand its workers to the census automatically.
#
# WHY THIS IS A UNIT AND NOT A MANUAL STEP: the census is 128 games. At 3
# workers that is ~30 h; at 15 it is ~6. PHASE 1 frees 12 workers when it ends
# (~05:00 local). Leaving the reallocation to whoever happens to be awake is
# how 24 h gets spent on nothing.
#
# Safe to run at any time: it waits for PHASE 1 to be genuinely inactive, and
# the census is per-seed resumable so stopping and relaunching it loses only
# the games in flight (<=3).
set -uo pipefail
cd /home/struktured/projects/dr-mario-distill-wt/experiments/distill
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
LOG=out/handoff.log
say() { echo "[handoff $(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "armed; waiting for drm-a5-p1 to exit"
while systemctl --user is-active --quiet drm-a5-p1; do sleep 60; done
say "drm-a5-p1 is $(systemctl --user is-active drm-a5-p1); result=$(systemctl --user show -p Result --value drm-a5-p1) exit=$(systemctl --user show -p ExecMainStatus --value drm-a5-p1)"
BANKED=$(ls out/labels_m1/L20_unthin_held/ | grep -c '^seed_')
say "PHASE 1 banked ${BANKED}/173; replay failures $(grep -c 'REPLAY GATE FAIL' out/a5_phase1.log)"

# 1) derive features for the completed held arm (cheap, needed before fit2)
say "deriving m2 features for L20_unthin_held (12 workers)"
$PY -u m2_features.py L20_unthin_held 12 >> out/handoff_feat.log 2>&1
say "features done rc=$? — $(ls out/m2_features/L20_unthin_held/ | grep -c '^seed_') derived"

# 2) hand the freed workers to the census
say "stopping census (3 workers) to relaunch at 15"
systemctl --user stop drm-a5-census 2>/dev/null
sleep 5
BEFORE=$(ls out/labels_m1/L20_census_fresh/ | grep -c '^seed_')
systemd-run --user --collect --unit drm-a5-census -p MemoryMax=24G \
  -p MemorySwapMax=0 -p Nice=10 -p WorkingDirectory="$PWD" \
  bash -c "$PY -u m1_run.py census --stratum L20 --workers 15 >> out/a5_census.log 2>&1"
sleep 10
say "census relaunched at 15 workers: $(systemctl --user is-active drm-a5-census); banked ${BEFORE}/128 at handoff"
say "DONE"
