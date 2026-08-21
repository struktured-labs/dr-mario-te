#!/usr/bin/env bash
# drm-c5precision (runs ON rbm-train-2): remote gate suite -> cross-host
# bit-exactness gate -> n=500 c5 extension burn -> chained analysis.
# Chained so a masked crash can never run the burn ungated
# (PREREG_C5_PRECISION_EXT.md sec 7-8).
set -eo pipefail
cd "$(dirname "$0")"
PY=/root/drm/venv/bin/python
FW=/mnt/data/drmario_cosim/fw/s20b
OUT=/root/drm/c5ext/out
ROWS=$OUT/farm.jsonl
WORKERS=2
mkdir -p "$OUT" gates
# progress: run_regime's per-game "[n/N] seed=... rate=... games/h" lines land
# in farm_run.log; keep the promised name as a symlink for ssh readers.
ln -sf "$OUT/farm_run.log" "$OUT/progress.log"

marker () {  # marker <file> <string> — belt-and-suspenders on top of exit codes
  command grep -aq "$2" "$1" || { echo "CHAIN ABORT: $2 missing from $1"; exit 1; }
}

echo "== [1/6] farm validation gates (e,d,a1,a2) on this host =="
$PY ../cosim_farm/gate_validate.py --fw "$FW" --max-pills 8 \
    --out gates/gate_a_remote.json 2>&1 | tee gates/gate_a_remote.log
marker gates/gate_a_remote.log "VALIDATION GATE: PASS"

echo "== [2/6] regime pure gates + mutants on this host =="
$PY gate_regime.py 2>&1 | tee gates/gate_pure_remote.log
marker gates/gate_pure_remote.log "GATE_REGIME_PASS"

echo "== [3/6] regime RTL gates (g7 variants end-to-end, g8 L20) on this host =="
$PY gate_regime.py --rtl 2>&1 | tee gates/gate_rtl_remote.log
marker gates/gate_rtl_remote.log "GATE_REGIME_PASS"

echo "== [4/6] extension population-gate selftest (mutants M-a..M-f) =="
$PY analyze_c5ext.py --selftest 2>&1 | tee gates/gate_selftest_remote.log
marker gates/gate_selftest_remote.log "ANALYZE_C5EXT_SELFTEST_PASS"

echo "== [5/6] cross-host bit-exactness gate (seeds 33000/33002, full c5 config) =="
[ -f gates/xhost_local.json ] || { echo "CHAIN ABORT: gates/xhost_local.json (local reference) missing"; exit 1; }
$PY xhost_gate.py --fw "$FW" --out gates/xhost_remote.json 2>&1 | tee gates/xhost_remote.log
marker gates/xhost_remote.log "XHOST_RUN_OK"
$PY xhost_gate.py --compare gates/xhost_local.json gates/xhost_remote.json \
    2>&1 | tee gates/xhost_compare.log
marker gates/xhost_compare.log "XHOST_GATE_PASS"

echo "== [6/6] burn: c5ext_L20_bursty n=500, even seeds 34000-34998 =="
$PY run_regime.py --arm c5ext_L20_bursty --pressure bursty --level 20 \
    --max-pills 400 --seed-start 34000 --seed-count 500 --fw "$FW" \
    --out "$ROWS" --workers $WORKERS 2>&1 | tee -a "$OUT/farm_run.log"
marker "$OUT/farm_run.log" RUN_REGIME_OK

echo "== chained analysis =="
$PY analyze_c5ext.py --rows "$ROWS" --out "$OUT/c5ext_summary.json" \
    2>&1 | tee "$OUT/c5ext_summary.txt"
marker "$OUT/c5ext_summary.txt" ANALYZE_C5EXT_OK

echo "CHAIN COMPLETE"
