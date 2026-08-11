#!/bin/bash
# Run one Tier-A CLAIR label. This permits true/shuffle to use different boxes.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
[[ -x "$PY" ]] || PY=/root/drm/venv/bin/python
export NUMBA_CACHE_DIR=${NUMBA_CACHE_DIR:-/tmp/dr-mario-te-numba-cache}
mkdir -p "$NUMBA_CACHE_DIR"
LABEL=${1:?usage: run_label.sh true|shuffle WORKERS}
W=${2:-4}
N=9000

case "$LABEL" in
  true)
    EXTRA=()
    OUT=out/full_A_clair_true
    ;;
  shuffle)
    test -f NULL_DOSE.json || { echo "missing NULL_DOSE.json"; exit 2; }
    read -r KEEP_NUM KEEP_DEN < <(
      "$PY" -c 'import json; d=json.load(open("NULL_DOSE.json")); assert d.get("validated") is True; print(d["null_keep_num"], d["null_keep_den"])'
    )
    EXTRA=(--null-keep-num "$KEEP_NUM" --null-keep-den "$KEEP_DEN")
    OUT=out/full_A_clair_shuffle
    ;;
  *) echo "LABEL must be true or shuffle"; exit 2 ;;
esac

mkdir -p out logs
bash run_gates.sh
"$PY" -u run_oracle.py --model lulu --future clair --label "$LABEL" \
  --seed-start 30000 --seed-count "$N" --segment 250 --workers "$W" \
  "${EXTRA[@]}" --outdir "$OUT" 2>&1 | tee -a "logs/full_A_clair_${LABEL}.log"
