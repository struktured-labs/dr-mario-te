#!/bin/bash
# labels-146 PILOT chain (PREREG_LABELS §2-§6).
# Usage: chain_pilot.sh <WORKERS>
# Stages, each gated on the previous stage's success MARKER:
#   T  targets   : make_targets.py (mechanical sampling rule, asserts)
#   G  gates     : gate_labels.py  (G1 replay, M-stale, M-dedup-off, G4)
#   H  harvest   : harvest_labels.py (80 states, per-seed atomic, resumable)
#   Vt validate  : true labels — claims + forced-move outcome A/B
#   Vs mutant    : shuffle labels — dose-matched, must not outperform true
#   Vm mutant    : mimic labels — must print MIMIC FAIL_NO_CLAIMS
set -eo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
ORACLE="$PWD/../eval47/stage2/oracle"
export NUMBA_CACHE_DIR="$PWD/tmp-numba-cache"
mkdir -p "$NUMBA_CACHE_DIR" out
export PYTHONPATH="$PWD:$ORACLE:$ORACLE/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments"

W=${1:-4}

"$PY" make_targets.py 2>&1 | tee out/targets.log
command grep -aq 'TARGETS_OK n=80' out/targets.log

"$PY" gate_labels.py 2>&1 | tee out/gates.log
command grep -aq 'GATES_OK' out/gates.log

"$PY" harvest_labels.py --workers "$W" 2>&1 | tee out/harvest.log
command grep -aq 'HARVEST_OK' out/harvest.log

"$PY" validate_labels.py --labels true --workers "$W" 2>&1 | tee out/val_true.log
command grep -aq 'VALIDATE_OK true' out/val_true.log

"$PY" validate_labels.py --labels shuffle --workers "$W" 2>&1 | tee out/val_shuffle.log
command grep -aq 'VALIDATE_OK shuffle' out/val_shuffle.log

"$PY" validate_labels.py --labels mimic 2>&1 | tee out/val_mimic.log
command grep -aq 'MIMIC FAIL_NO_CLAIMS' out/val_mimic.log

echo "PILOT_CHAIN_OK"
