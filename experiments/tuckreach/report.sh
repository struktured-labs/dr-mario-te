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
echo; echo "## Verilator co-sim (RTL NES_MiSTer-dist 3b164c7), 10/03 couch boards; off = fw 1488e158 (late-flip lane timelines where not rerun)"
nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games G2,G3,G4 --ref-lateflip --pairs off:ship
for a in tl ro tr trtl; do
  echo; nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games G2 --ref-lateflip --pairs off:$a 2>&1 | \
    command grep -a -v '^\[off\]' ; done
echo; nice -n 19 $PY experiments/tuckreach/analyze_cosim.py tmp/cosim/runs --games G2 --pairs trtl:ship 2>&1 | command grep -a -E '^ship vs|DONE delta|DIFF'
echo; echo "## Mesen replay of the timelines on the REAL couch carts (c960dd49 = DIST60 couch, 464a4b75 = +LATEGUARD)"
args=()
for g in G2 G3 G4; do for c in c960 lg; do for f in base1488 ship; do
  tag=${f}_${c}_$g; [ -f "$T/$tag/lateflip_$tag.log" ] && args+=("${f}_$c:$g:$T/pubtrace_$tag.jsonl:$T/$tag/lateflip_$tag.log")
done; done; done
nice -n 19 $PY experiments/tuckreach/replay_eval.py "${args[@]}"
} 2>&1 | tee "$OUT"
