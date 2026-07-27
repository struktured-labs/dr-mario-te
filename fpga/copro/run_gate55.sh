#!/usr/bin/env bash
# run_gate55.sh — task #55 base-vs-delta LOCKSTEP gate for the eval-winner (5-const) edit.
# Copy of run_gate.sh with TWO deliberate changes so it can run IN PARALLEL with the merge gate:
#   1. runs ./obj_mister_edit/mister_vsim  (the vsim re-verilated from the EDITED LeafEval.sv;
#      run_gate.sh's ./obj_mister/mister_vsim is the UNEDITED committed model and would test stale constants)
#   2. writes /tmp/gate55_base.txt + /tmp/gate55_all.txt  (run_gate.sh hardcodes /tmp/gate_base.txt +
#      /tmp/gate_all.txt, which the concurrent merge gate owns — sharing them clobbers both verdicts)
# Everything else is identical: base-firmware moves vs delta-firmware moves on the SAME N boards, cell-exact.
set -e
cd "$(dirname "$0")"
PY=~/projects/dr-mario-mods/.venv/bin/python
N="${1:-12}"
VSIM=./obj_mister_edit/mister_vsim
[ -x "$VSIM" ] || { echo "ERROR: $VSIM missing — re-verilate the edited RTL first"; exit 2; }
$PY gen_corpus.py "$N" >/dev/null
echo "== baseline build + run =="
$PY dbg_build.py baseline 0 >/dev/null 2>&1
$VSIM 2>&1 | grep -E "^case" | sed -E 's/ oracle.*//' > /tmp/gate55_base.txt
echo "== all-delta build + run =="
$PY dbg_build.py all 0 >/dev/null 2>&1
$VSIM 2>&1 | grep -E "^case" | sed -E 's/ oracle.*//' > /tmp/gate55_all.txt
echo "== baseline =="; cat /tmp/gate55_base.txt
echo "== all-delta =="; cat /tmp/gate55_all.txt
if diff -q /tmp/gate55_base.txt /tmp/gate55_all.txt >/dev/null; then
  echo "GATE55 PASS: CELL-EXACT across $N boards (baseline moves == all-delta moves, eval-winner RTL)"
else
  echo "GATE55 FAIL: divergence"; diff /tmp/gate55_base.txt /tmp/gate55_all.txt
fi
# restore the shipped delta hex (RTL-only edit => hex is UNCHANGED at c87e60a1; a different md5 is a red flag)
$PY dbg_build.py all 0 >/dev/null 2>&1
md5sum copro_rom.hex   # expect c87e60a1736224cfc3fa29cfed7c6f16 (edit is RTL-only, does not touch firmware)
