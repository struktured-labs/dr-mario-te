#!/usr/bin/env bash
# One command to print everything the farm currently knows: gate verdicts, throughput,
# per-board arm diffs, and the paired A/B at whatever n has accumulated so far.
#
# The A/B is resumable and runs for hours, so this is designed to be run REPEATEDLY while
# it accumulates -- the n it reports is simply the n finished at that moment.
set -u
PY="${PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}"
HERE="$(cd "$(dirname "$0")" && pwd)"
D=/mnt/data/drmario_cosim

echo "################ VALIDATION GATE ################"
for f in "$D"/gate/validate_pure.json "$D"/gate/validate_full_s20b.json; do
  [ -f "$f" ] && $PY - "$f" <<'EOF'
import json,sys
r=json.load(open(sys.argv[1]))
print(f"\n{sys.argv[1]}")
print(f"  overall pass: {r.get('pass')}   failures: {r.get('failures')}")
if 'gate_e_orientation' in r: print(f"  (e) orientation : {r['gate_e_orientation']['pass']}")
if 'gate_d_physics' in r:
    g=r['gate_d_physics']; print(f"  (d) physics     : {g['pass']}  ({g['checked']} cases)")
if 'gate_a_determinism' in r:
    g=r['gate_a_determinism']
    print(f"  (a1) fresh/fresh: {not g['a1_fresh_vs_fresh_mismatched_seeds']}  "
          f"mismatched={g['a1_fresh_vs_fresh_mismatched_seeds']}")
    print(f"  (a2) fresh/REUSE: {not g['a2_fresh_vs_reused_mismatched_seeds']}  "
          f"mismatched={g['a2_fresh_vs_reused_mismatched_seeds']}")
EOF
done
for f in "$D"/gate/agree_smoke3.json "$D"/gate/agree_l11_20.json; do
  [ -f "$f" ] && $PY - "$f" <<'EOF'
import json,sys
r=json.load(open(sys.argv[1]))
print(f"\n{sys.argv[1]}")
print(f"  (b) agreement farm==stock: {r['n_mismatch']==0}  "
      f"({r['n']-r['n_mismatch']}/{r['n']} identical col+orient+clocks)")
print(f"      {r['secs_per_decision_farm']:.1f}s/dec farm vs "
      f"{r['secs_per_decision_stock']:.1f}s/dec stock "
      f"({r.get('speedup_farm_over_stock') or 0:.2f}x)")
EOF
done

echo
echo "################ PER-BOARD ARM DIFF ################"
for f in "$D"/results/decide_compare_*.json; do
  [ -f "$f" ] || continue
  $PY - "$f" <<'EOF'
import json,sys
r=json.load(open(sys.argv[1]))
print(f"\n{sys.argv[1]}  ({r['n_boards']} real-L11 boards, base={r['base']})")
for k,v in r['arms'].items():
    t=r['tuck_published'][k]
    print(f"  {k:<12} fw={v['fw_md5'][:8]}  {v['secs_per_decision']:5.1f}s/dec  "
          f"tuck descriptor published {t}/{r['n_boards']} ({t/r['n_boards']:.0%})")
for k,c in r['comparisons'].items():
    print(f"  {k:<12} PLACEMENT differs {c['n_placement_differs']}/{c['n']} "
          f"({c['frac_placement_differs']:.0%})  col {c['n_col_differs']} "
          f"orient {c['n_orient_differs']}  search cost {c['search_cost_ratio']:.2f}x")
EOF
done

echo
echo "################ THROUGHPUT ################"
for l in "$D"/logs/ab_*_*.log; do
  [ -f "$l" ] || continue
  n=$(grep -c "^\[" "$l" 2>/dev/null || echo 0)
  last=$(grep "^\[" "$l" 2>/dev/null | tail -1)
  echo "  $(basename "$l"): $n games done   $last"
done
echo "  host $(hostname): $(nproc) cores, load $(cut -d' ' -f1-3 /proc/loadavg)"

echo
echo "################ PAIRED A/B ################"
for f in "$D"/results/ab_*.jsonl; do
  [ -f "$f" ] || continue
  echo; echo "--- $f ---"
  $PY "$HERE/analyze.py" "$f" --a s20b --b s20t3 2>&1 | tail -30
done
