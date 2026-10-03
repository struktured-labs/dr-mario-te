#!/bin/bash
# Re-run every DRTUCKREACH / DRTUCKLIVE / DRROOTORD analysis over the banked outputs (tmp/, not in git) and write
# experiments/tuckreach/GATE_TUCKREACH.txt. Inputs: tmp/py65/*.jsonl (py65_ab.py), tmp/cosim/runs (cosim_run.py),
# tmp/replay (replay.sh). The long runs themselves are not repeated here.
set -u
cd "$(dirname "$0")/../.."
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
T=tmp/replay
OUT=experiments/tuckreach/GATE_TUCKREACH.txt
{
echo "# DRTUCKREACH / DRTUCKLIVE / DRROOTORD gates -- $(date -Is) -- $(git rev-parse --short HEAD)"
echo; echo "## static (shipped-style delta hexes)"
nice -n 19 $PY experiments/tuckreach/gate_static.py
echo; echo "## py65 whole decision (stub -> search -> tuck extension -> DONE), golden-leaf engine emulator"
nice -n 19 $PY experiments/tuckreach/gate_py65.py tmp/py65/*_ab.jsonl ${GATE_PY65_ARGS:-}
echo "### mutants + tie stress + RAM (banked run: gate_py65.py tmp/py65/couch_ab.jsonl --mutants --ram)"
command grep -a -A20 "^mutant boards" tmp/py65/gate_mut2.log
echo; echo "## reach mask bijection, 6502 == reach_fw, V2 constants T_LAT 13 / G0 3 (run_reachparam.py gate_reach_mask.py --tap)"
cat tmp/gates/reach_mask_V2_13_3.log
G=/home/struktured/projects/dr-mario-fwtuckreach-gate-wt/tmp/gates
for f in reach_search_V1 reach_search_V2 dist_golden_V1 dist_golden_V2; do
  [ -f $G/$f.log ] && { echo; echo "## legacy gate $f (dist-target tree 1f430974 + this branch's firmware patch; same hexes)"; command grep -a -v "^ *MISMATCH" $G/$f.log | tail -25; }
done
echo; echo "## Verilator co-sim (RTL NES_MiSTer-dist 3b164c7), 10/03 couch boards; off = fw 1488e158 (late-flip lane timelines where not rerun)"
nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games G2,G3,G4 --ref-lateflip --pairs off:ship
for a in tl ro tr trtl; do
  echo; nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games G2 --ref-lateflip --pairs off:$a 2>&1 | \
    command grep -a -v '^\[off\]' ; done
echo; nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games G2 --pairs trtl:ship 2>&1 | command grep -a -E '^ship vs|DONE delta|same boards|DIFF'
echo; echo "### V2 (mask 13 / 3) vs V1 (ship), G2, judged with the 13 / 3 mask"
DRREACH_TLAT=13 DRREACH_G0=3 nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games G2 --pairs ship:v2 2>&1 | command grep -a -E '^v2 vs|DONE delta|same boards|DIFF'
[ -f tmp/cosim/runs/pubtrace_H927_off.jsonl ] && { echo; echo "### banked 9/27 couch boards (H927 = cases_hsv2_20260927, ANTIBODY games), off vs ship"; nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games H927 --pairs off:ship 2>&1 | command grep -a -v DIFF; }
echo; echo "## Mesen replay of the timelines on REAL couch carts (the late-flip lane's probe; timelines keyed to each cart's own GO)"
echo "# carts: c960 = DIST60 couch c960dd49 | lg = +LATEGUARD 464a4b75 | abc = fair settle + ledge fixes ABC d2fa0c01 |"
echo "#        nopin = fair settle, no pin 1bc29003 | fairD = fair cart D dbbb5007 (settle kit) | fairDmt8 = D + DRMINTHINK=8 050b0a65"
echo "# hexes: base1488 = fw 1488e158 | ship = V1 a1ef31c8 | v2 = V2 b7e54520 (mask 13/3)"
args=()
for g in G2 G3 G4; do for c in c960 lg abc nopin fairD fairDmt8; do for f in base1488 ship v2; do
  tag=${f}_${c}_$g; if [ -f "$T/$tag/lateflip_$tag.log" ] && command grep -aq "^SUMMARY" "$T/$tag/lateflip_$tag.log"; then
    args+=("${f}_$c:$g:$T/pubtrace_$tag.jsonl:$T/$tag/lateflip_$tag.log"); fi
done; done; done
nice -n 19 $PY experiments/tuckreach/replay_eval.py "${args[@]}"
echo; echo "### per flag, G2 42-board subset (the 8 kill boards, the 21 copro != python boards, big DONE deltas, a few others)"
args=("base1488_c960:G2:$T/sub_base1488_G2.jsonl:$T/base1488_c960_G2/lateflip_base1488_c960_G2.log"
      "base1488_lg:G2:$T/sub_base1488_G2.jsonl:$T/base1488_lg_G2/lateflip_base1488_lg_G2.log")
for f in tr ro tl trtl; do for c in c960 lg; do
  args+=("${f}_$c:G2:$T/pubtrace_${f}_${c}_G2sub.jsonl:$T/${f}_${c}_G2sub/lateflip_${f}_${c}_G2sub.log"); done; done
args+=("ship_c960:G2:$T/sub_ship_G2.jsonl:$T/ship_c960_G2/lateflip_ship_c960_G2.log" "ship_lg:G2:$T/sub_ship_G2.jsonl:$T/ship_lg_G2/lateflip_ship_lg_G2.log")
nice -n 19 $PY experiments/tuckreach/replay_eval.py "${args[@]}"
} 2>&1 | tee "$OUT"
