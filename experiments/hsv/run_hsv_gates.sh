#!/usr/bin/env bash
# All DRHSV gates, reproducible. RTL = the NES_MiSTer fork worktree with claude/hsv-leaf checked out.
set -u
RTL=${RTL:-/home/struktured/projects/NES_MiSTer-hsv/rtl/mappers/LeafEval.sv}
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
H=$(cd "$(dirname "$0")" && pwd); T=$H/../../tmp; mkdir -p "$T"
cd "$H/gate"
# identity: flag-off preprocessed text == shipping 08f2343
git -C "$(dirname "$RTL")" show 08f23434cac449db7ee5f641958fcc00c616c29d:rtl/mappers/LeafEval.sv > "$T/LeafEval_ship.sv"
verilator -E -P "$T/LeafEval_ship.sv" | grep -v '^\s*$' > "$T/pp_ship.txt"; verilator -E -P "$RTL" | grep -v '^\s*$' > "$T/pp_off.txt"
cmp -s "$T/pp_ship.txt" "$T/pp_off.txt" && echo "IDENTITY flag-off == 08f2343: PASS" || echo "IDENTITY: FAIL"
$PY gate.py rtl --rtl "$RTL" --build "$T/gb_off" > "$T/gate_off.log" 2>&1
$PY gate.py rtl --rtl "$RTL" --define DRHSV --build "$T/gb_on" > "$T/gate_on.log" 2>&1
for m in row col sign delta; do
  $PY - "$RTL" "$T/mut_$m" "$m" <<'PY'
import sys, os
rtl, d, k = sys.argv[1:4]; src = open(rtl).read()
M = {"row": ("wr_ < 4'd9 && (wc", "wr_ < 4'd10 && (wc"), "col": ("wc == 4'd5)) ? 15'd512", "wc == 4'd2)) ? 15'd512"),
     "sign": ("- ((wr_ < 4'd9", "+ ((wr_ < 4'd9"), "delta": ("((wr_ < 4'd9 && (wc", "((!base_mode && wr_ < 4'd9 && (wc")}
a, b = M[k]; assert src.count(a) == 1; os.makedirs(d, exist_ok=True); open(d + "/LeafEval.sv", "w").write(src.replace(a, b, 1))
PY
  $PY gate.py rtl --rtl "$T/mut_$m/LeafEval.sv" --define DRHSV --build "$T/gb_$m" > "$T/gate_mut_$m.log" 2>&1 &
done; wait
for f in off on mut_row mut_col mut_sign mut_delta; do echo "== $f: $(grep -E '^PHASE' "$T/gate_$f.log" | tr '\n' ' ')"; done
cd "$H"; $PY gate_hsv_golden.py --game 220 --synth 120; $PY check_hsv_search.py --games 3
