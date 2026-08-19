#!/bin/bash
# Complete mandatory oracle gate set. Any non-zero exit voids the launch.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
[[ -x "$PY" ]] || PY=/root/drm/venv/bin/python
export NUMBA_CACHE_DIR=${NUMBA_CACHE_DIR:-/tmp/dr-mario-te-numba-cache}
mkdir -p "$NUMBA_CACHE_DIR"
CANONICAL_QA=/home/struktured/projects/dr-mario-qa-wt/experiments
export PYTHONPATH="$PWD/bootstrap:$CANONICAL_QA${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p out logs

"$PY" gate_runtime_manifest.py 2>&1 | tee logs/gate_runtime_manifest.log
"$PY" -u gate_identity.py --seeds 12 --seed-start 40000 \
  2>&1 | tee logs/gate_identity.log
"$PY" -u gate_forkleak.py --seeds 4 --seed-start 41000 \
  2>&1 | tee logs/gate_forkleak.log
"$PY" gate_dist.py 2>&1 | tee logs/gate_dist.log
"$PY" gate_null_thinning.py 2>&1 | tee logs/gate_null_thinning.log
"$PY" test_oracle_verdict.py 2>&1 | tee logs/test_oracle_verdict.log
"$PY" test_runner_banking.py 2>&1 | tee logs/test_runner_banking.log
echo "ALL ORACLE GATES PASS"
