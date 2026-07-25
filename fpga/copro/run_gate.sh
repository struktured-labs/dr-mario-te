#!/usr/bin/env bash
# Cell-exact gate: baseline-firmware moves vs all-delta-firmware moves on the same corpus.
set -e
cd "$(dirname "$0")"
PY=~/projects/dr-mario-mods/.venv/bin/python
N="${1:-12}"
$PY gen_corpus.py "$N" >/dev/null
echo "== baseline build + run =="
$PY dbg_build.py baseline 0 >/dev/null 2>&1
./obj_mister/mister_vsim 2>&1 | grep -E "^case" | sed -E 's/ oracle.*//' > /tmp/gate_base.txt
echo "== all-delta build + run =="
$PY dbg_build.py all 0 >/dev/null 2>&1
./obj_mister/mister_vsim 2>&1 | grep -E "^case" | sed -E 's/ oracle.*//' > /tmp/gate_all.txt
echo "== baseline =="; cat /tmp/gate_base.txt
echo "== all-delta =="; cat /tmp/gate_all.txt
if diff -q /tmp/gate_base.txt /tmp/gate_all.txt >/dev/null; then
  echo "GATE PASS: CELL-EXACT across $N boards (baseline moves == all-delta moves)"
else
  echo "GATE FAIL: divergence"; diff /tmp/gate_base.txt /tmp/gate_all.txt
fi
# restore pristine baseline hex
$PY dbg_build.py baseline 0 >/dev/null 2>&1
md5sum copro_rom.hex
