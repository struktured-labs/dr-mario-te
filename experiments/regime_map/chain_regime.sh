#!/usr/bin/env bash
# drm-regime-farm: gates -> stage1 -> registered allocator -> stage2 -> analysis,
# chained so a masked crash can never run the farm ungated (PREREG sec 9).
set -eo pipefail
cd "$(dirname "$0")"
PY=../../.venv-regime/bin/python
FW=/mnt/data/drmario_cosim/fw/s20b
OUT=out
ROWS=$OUT/farm.jsonl
BACKUP=/mnt/data/drmario_cosim/results/regime_map
WORKERS=22
mkdir -p "$OUT" gates "$BACKUP"

marker () {  # marker <file> <string> — belt-and-suspenders on top of exit codes
  command grep -aq "$2" "$1" || { echo "CHAIN ABORT: $2 missing from $1"; exit 1; }
}

echo "== [1/6] farm validation gates (e,d,a1,a2) =="
$PY ../cosim_farm/gate_validate.py --fw "$FW" --max-pills 8 \
    --out gates/gate_a_chain.json 2>&1 | tee gates/gate_a_chain.log
marker gates/gate_a_chain.log "VALIDATION GATE: PASS"

echo "== [2/6] regime pure gates + mutants =="
$PY gate_regime.py 2>&1 | tee gates/gate_pure_chain.log
marker gates/gate_pure_chain.log "GATE_REGIME_PASS"

echo "== [3/6] regime RTL gates (g7 variants end-to-end, g8 L20) =="
$PY gate_regime.py --rtl 2>&1 | tee gates/gate_rtl_chain.log
marker gates/gate_rtl_chain.log "GATE_REGIME_PASS"

echo "== [4/6] stage 1: n=50 per cell =="
stage1 () { # arm variant level max_pills seed_start count
  $PY run_regime.py --arm "$1" --pressure "$2" --level "$3" --max-pills "$4" \
      --seed-start "$5" --seed-count "$6" --fw "$FW" --out "$ROWS" \
      --workers $WORKERS 2>&1 | tee -a "$OUT/farm_run.log"
  marker "$OUT/farm_run.log" RUN_REGIME_OK
  cp "$ROWS" "$BACKUP/farm.jsonl"
}
stage1 c1_L11_bursty bursty     11 300 30000 50
stage1 c2_L11_x2     bursty_x2  11 300 30500 50
stage1 c3_L11_aim    bursty_aim 11 300 31000 50
stage1 c4_L20_clean  clean      20 400 31500 50
stage1 c5_L20_bursty bursty     20 400 32000 50
stage1 c6_L20_aim    bursty_aim 20 400 32500 50

echo "== [5/6] interim analysis + REGISTERED stage-2 allocation =="
$PY analyze_regime.py --rows "$ROWS" --allocate --budget 400 \
    --out "$OUT/interim_map.json" 2>&1 | tee "$OUT/interim.txt"
marker "$OUT/interim.txt" ANALYZE_REGIME_OK

echo "== [6/6] stage 2 (allocator order; per-seed resume makes cuts safe) =="
$PY - "$OUT/interim_map.json" <<'EOF' > "$OUT/stage2_plan.txt"
import json, sys
res = json.load(open(sys.argv[1]))
cells = __import__("analyze_regime").CELLS
for arm, extra in res.get("stage2_alloc", {}).items():
    variant, level, max_pills, seed_start, _ = cells[arm]
    have = res["cells"][arm]["n"]
    print(arm, variant, level, max_pills, seed_start, have + extra)
EOF
cat "$OUT/stage2_plan.txt"
while read -r arm variant level max_pills seed_start count; do
  [ -z "$arm" ] && continue
  stage1 "$arm" "$variant" "$level" "$max_pills" "$seed_start" "$count"
done < "$OUT/stage2_plan.txt"

echo "== final analysis =="
$PY analyze_regime.py --rows "$ROWS" --out "$OUT/final_map.json" \
    2>&1 | tee "$OUT/final_map.txt"
marker "$OUT/final_map.txt" ANALYZE_REGIME_OK
cp "$ROWS" "$BACKUP/farm.jsonl"

echo "CHAIN COMPLETE"
