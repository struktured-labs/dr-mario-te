#!/usr/bin/env bash
# a16mt lane: the cart gate record for FAIR2PLUS + MIN_THINK -4 f (DRMINTHINK=4), beside FAIR2PLUS itself.
#   tools/a16mt/gates_cart.sh > experiments/a16mt/GATES_CART.txt
# Same gates as tools/execfid/gates_final.sh (the FAIR2PLUS record), on A+LGP+ROW2 (5a1695da) and A+LGP+ROW2+MT2.
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
D="DRLATEGUARD=1,DRSTUDYEND=1,DRSETTLE=3,DRSETTLEPIN=0,DRPROPHFIRST=1"
A="$D,DRABORTSTALE=1"
F2P="$A,DRLGPRESTART=1,DRDISTROW=2"
MT2="$F2P,DRMINTHINK=4"
echo "# a16mt cart gates ($(date -u +%Y-%m-%dT%H:%MZ), $(git rev-parse --short HEAD) + working tree)"
echo; echo "## 1. negative controls + candidate (tools/a16mt/build_carts.sh)"
nice -n 19 tools/a16mt/build_carts.sh tmp/carts_a16mt 2>&1 | tail -8
echo; echo "## 2. tools/gate/run_cart_gates.sh (gravity-fidelity runs every ARMS entry incl. the MT2 arm, 3000 f, seed 5)"
DRGATE_PY=$GPY nice -n 19 tools/gate/run_cart_gates.sh 2>&1 | tail -11
echo; echo "## 3. tests/test_gravity_fidelity.py, FAIR2PLUS / FAIR2PLUS+MT2 / the pinned 464a4b75 (must FAIL), seeds 5/11/23, 6000 frames"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 6000 --seed $s --arm couch_fair_A_lgp_row2 \
     --arm couch_fair_A_lgp_row2_mt2 --arm couch_464a4b75 2>&1 | tail -5 | cut -c1-240
done
echo; echo "## 4. tests/test_lgprestart.py (DEFECT gate, two-sided), counts summed over seeds 5/11/23/77, 6000 frames each"
nice -n 19 $GPY tests/test_lgprestart.py --frames 6000 --seeds 5,11,23,77 --arm couch_fair_A --arm couch_fair_A_lgp_row2 \
   --arm couch_fair_A_lgp_row2_mt2 2>&1 | tail -5 | cut -c1-330
for ov in "$F2P" "$MT2"; do
  echo; echo "## 5. tests/test_lateguard_census_cut.py LGCUT_OVERLAY=$ov"
  LGCUT_OVERLAY=$ov nice -n 19 $GPY tests/test_lateguard_census_cut.py 2>&1 | tail -14
done
echo; echo "## 6. static NMI census (tools/nmi126/census.py on capture_ir.py IR); budget 29780"
mkdir -p tmp/a16mt_census
for arm in "A_lgp_row2:$F2P" "A_lgp_row2_mt2:$MT2"; do
  name=${arm%%:*}; ov=${arm#*:}
  $PY - "$ov" tmp/a16mt_census/$name.manifest.json <<'PYEOF'
import json, sys
s = json.load(open("experiments/lateflip/couch_c960dd49_flags.json"))["flag_snapshot"]
s.update(dict(kv.split("=", 1) for kv in sys.argv[1].split(",")))
json.dump({"flag_snapshot": s}, open(sys.argv[2], "w"))
PYEOF
  nice -n 19 $GPY tools/nmi126/capture_ir.py tmp/a16mt_census/$name.manifest.json tmp/a16mt_census/${name}_ir.json > tmp/a16mt_census/$name.capture.log 2>&1 || { echo "CAPTURE FAIL $name"; tail -3 tmp/a16mt_census/$name.capture.log; }
  echo "-- couch_$name"; nice -n 19 $GPY tools/nmi126/census.py tmp/a16mt_census/${name}_ir.json 2>&1 | command grep -a "WORST ADMISSIBLE\|ALL_PATHS\|FAIL"
done
echo; echo "## 7. TAP interface gate (experiments/reach/gate_tap_interface.py, P=2, 40000 frames, seed 3)"
# the gate reads the couch flag snapshot from a gitignored build log (the execfid record used 0627ae8b): absence is FAIL
TAPLOG=tmp/carts/couch_tap2.log
[ "$(md5sum < $TAPLOG 2>/dev/null | cut -c1-8)" = 0627ae8b ] || echo "FAIL: $TAPLOG missing or not 0627ae8b (copy it from dr-mario-execfid-wt/tmp/carts/)"
for ov in "$F2P" "$MT2"; do
  echo "== couch ${ov//,/ }"
  nice -n 19 $GPY experiments/reach/gate_tap_interface.py --cart couch --tap 2 --frames 40000 --seed 3 --overlay $(echo "$ov" | tr ',' ' ') 2>&1 | tail -1
done
echo; echo "## 8. TAP mutant must be KILLED on the MT2 flag set"
nice -n 19 $GPY experiments/reach/gate_tap_interface.py --cart couch --tap 2 --mut everyframe --frames 20000 --seed 3 --overlay $(echo "$MT2" | tr ',' ' ') 2>&1 | tail -1
echo; echo "GATES_CART DONE"
