#!/bin/bash
# garbage-labels PILOT chain (PREREG_GARBAGE §6 order: gates before harvest,
# mimic/shuffle before any campaign).  Usage: chain_garbage.sh <WORKERS>
set -eo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
ORACLE="$PWD/../../eval47/stage2/oracle"
export NUMBA_CACHE_DIR="$PWD/../tmp-numba-cache"
mkdir -p out out/labels
export PYTHONPATH="$PWD:$PWD/..:$ORACLE:$ORACLE/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments"

W=${1:-8}

"$PY" gate_garbage.py 2>&1 | tee out/gates.log
command grep -aq 'GATE_GARBAGE PASS' out/gates.log

"$PY" harvest_garbage.py --set pilot --workers "$W" 2>&1 | tee out/pilot.log
command grep -aq 'HARVEST_OK' out/pilot.log

"$PY" analyze_garbage.py --set pilot 2>&1 | tee out/analyze_pilot.log
