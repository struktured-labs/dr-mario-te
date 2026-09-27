#!/usr/bin/env bash
# chain_autopsy.sh — the autopsy consumer chain (PREREG_AUTOPSY).
#
# The census is a PRODUCER running in its own unit; this is the CONSUMER. It
# labels whatever failures exist, sleeps, and labels again, until the census
# unit exits — then runs the validation and the analysis once.
#
# Every stage is gated on the previous stage's success MARKER, never on a unit
# being active. Progress is graded by ROW GROWTH (labels on disk), because a
# live unit proves nothing about whether work is happening.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
export NUMBA_CACHE_DIR="$PWD/../tmp-numba-cache"
export PYTHONPATH=/home/struktured/projects/dr-mario-qa-wt/experiments
W=${1:-4}
mkdir -p out/labels logs

# STARTUP ASSERT: gates green before a single label row is written.
"$PY" - <<'PYEOF' || exit 1
import json
g = json.load(open("out/gate_autopsy.json"))
for k in ("G1", "G2", "G3", "G4", "G5"):
    assert g[k]["pass"], f"gate {k} not green"
print("[assert] gates G1-G5 GREEN")
PYEOF

while true; do
    "$PY" run_autopsy.py --workers "$W" 2>&1 | tee -a logs/autopsy.log
    n=$(ls out/labels/autopsy_*.json.gz 2>/dev/null | wc -l)
    echo "[chain] labeled games on disk: $n  at $(date -Is)" | tee -a logs/autopsy.log
    if ! systemctl --user is-active --quiet drm-autopsy-census; then
        echo "[chain] census unit is gone — final pass then validate" | tee -a logs/autopsy.log
        "$PY" run_autopsy.py --workers "$W" 2>&1 | tee -a logs/autopsy.log
        break
    fi
    sleep 900
done

"$PY" validate_autopsy.py --labels mimic 2>&1 | tee logs/val_mimic.log
command grep -aq 'MIMIC FAIL_NO_CLAIMS' logs/val_mimic.log || { echo "V4 VOID"; exit 1; }

"$PY" validate_autopsy.py --labels true --workers "$W" 2>&1 | tee logs/val_true.log
command grep -aq 'VALIDATE_OK true' logs/val_true.log || exit 1

"$PY" validate_autopsy.py --labels shuffle --workers "$W" 2>&1 | tee logs/val_shuffle.log
command grep -aq 'VALIDATE_OK shuffle' logs/val_shuffle.log || exit 1

"$PY" validate_autopsy.py --positive-control --workers "$W" 2>&1 | tee logs/poscontrol.log
command grep -aq 'POSITIVE_CONTROL' logs/poscontrol.log || exit 1

"$PY" analyze_autopsy.py 2>&1 | tee logs/analyze.log
command grep -aq 'ANALYZE_OK' logs/analyze.log || exit 1

echo "AUTOPSY_CHAIN_OK"
