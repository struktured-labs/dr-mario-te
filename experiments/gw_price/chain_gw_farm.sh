#!/usr/bin/env bash
# drm-gw-farm: gates -> farm run -> analysis, chained so a session reap cannot
# strand the run between steps (PREREG_GW_PRICE §8). Gates red => farm not spent.
set -e
cd "$(dirname "$0")"
PY=../../.venv-gw/bin/python
OUT=out
RES=/mnt/data/drmario_cosim/results/gw_price
mkdir -p "$RES"

echo "== [1/3] gate suite =="
$PY gate_gw_price.py 2>&1 | tee "$OUT/gate_result.txt"

echo "== [2/3] farm run (base+deepen on N1, rand+worst on N2) =="
$PY run_gw_price.py --out "$RES/farm.jsonl" --workers 20 \
    --verdict "$OUT/prescreen_52100.jsonl.summary.json" 2>&1 \
    | tee -a "$OUT/farm_run.log"
cp "$RES/farm.jsonl" "$OUT/farm.jsonl"

echo "== [3/3] analysis =="
$PY analyze_gw_price.py --farm "$RES/farm.jsonl" \
    --prescreen "$OUT/prescreen_52100.jsonl.summary.json" \
    --out "$OUT/pricing_verdict.json" 2>&1 | tee "$OUT/analysis.txt"

echo "CHAIN COMPLETE"
