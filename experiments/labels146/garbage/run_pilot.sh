#!/bin/bash
set -eo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
ORACLE="$PWD/../../eval47/stage2/oracle"
export NUMBA_CACHE_DIR="$PWD/../tmp-numba-cache"
export PYTHONPATH="$PWD:$PWD/..:$ORACLE:$ORACLE/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments"
"$PY" -u harvest_garbage.py --set "${1:-pilot}" --workers "${2:-8}" 2>&1 | tee -a "out/${1:-pilot}.log"
command grep -aq 'HARVEST_OK' "out/${1:-pilot}.log"
"$PY" -u analyze_garbage.py --set "${1:-pilot}" 2>&1 | tee "out/analyze_${1:-pilot}.log"
