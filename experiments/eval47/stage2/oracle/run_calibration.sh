#!/bin/bash
# Endpoint-blind calibration for the dose-matched shuffled-label null.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
[[ -x "$PY" ]] || PY=/root/drm/venv/bin/python
export NUMBA_CACHE_DIR=${NUMBA_CACHE_DIR:-/tmp/dr-mario-te-numba-cache}
mkdir -p "$NUMBA_CACHE_DIR"
W=${1:-4}

mkdir -p out logs

"$PY" -u run_oracle.py --model lulu --future clair --label true \
  --seed-start 42000 --seed-count 60 --segment 60 --workers "$W" \
  --outdir out/cal_clair_true 2>&1 | tee logs/cal_clair_true.log

"$PY" -u run_oracle.py --model lulu --future clair --label shuffle \
  --seed-start 42000 --seed-count 60 --segment 60 --workers "$W" \
  --outdir out/cal_clair_shuffle_raw 2>&1 | tee logs/cal_clair_shuffle_raw.log

"$PY" calibrate_null.py --true-run out/cal_clair_true \
  --raw-mutant-run out/cal_clair_shuffle_raw --out NULL_DOSE_RAW.json \
  2>&1 | tee logs/calibrate_null.log

echo "RAW CALIBRATION COMPLETE. Validate the proposed q under A7 before"
echo "updating the committed, validated NULL_DOSE.json."
