#!/bin/bash
set -u
S2=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
L=$S2/logs/build_local.log
cd "$S2"
until command grep -aq "^\[done\]" "$L" || command grep -aqE "Traceback|REFUSED|Killed|MemoryError|did NOT reproduce" "$L"; do sleep 30; done
if ! command grep -aq "^\[done\]" "$L"; then echo "BUILD FAILED"; tail -20 "$L"; exit 1; fi
echo "=== BUILD DONE ==="; tail -8 "$L"
echo "=== FEATURES + GATES A3/A4 ==="
$PY s2_features.py --tag local 2>&1
echo "FEAT_EXIT=$?"
echo "=== CORPUS REPORT ==="
$PY s2_report.py --tag local 2>&1
echo "ALL_STAGES_COMPLETE"
