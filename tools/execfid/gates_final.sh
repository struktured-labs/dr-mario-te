#!/usr/bin/env bash
# execfid lane FINAL gate record for DRLGPRESTART and DRDISTROW=2 on the fair couch carts.
#   tools/execfid/gates_final.sh > experiments/execfid/GATES.txt
# D = dbbb5007 flags (FAIR), A = D + DRABORTSTALE (b1b57638, FAIR2).
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
D="DRLATEGUARD=1,DRSTUDYEND=1,DRSETTLE=3,DRSETTLEPIN=0,DRPROPHFIRST=1"
A="$D,DRABORTSTALE=1"
echo "# execfid gates ($(date -u +%Y-%m-%dT%H:%MZ), $(git rev-parse --short HEAD) + working tree)"
echo; echo "## 1. negative controls + candidates (tools/execfid/build_carts.sh)"
nice -n 19 tools/execfid/build_carts.sh tmp/carts_execfid 2>&1 | tail -22
echo; echo "## 2. tools/gate/run_cart_gates.sh (gravity-fidelity runs every ARMS entry incl. the new ones, 3000 f, seed 5)"
DRGATE_PY=$GPY nice -n 19 tools/gate/run_cart_gates.sh 2>&1 | tail -11
echo; echo "## 3. tests/test_gravity_fidelity.py, new arms + D_abort control, seeds 5/11/23, 6000 frames"
echo "##    (dead-pill counter now excludes DRPRESTART GOs, identified by PRE_ACT2 0->1 in the GO frame; see the test)"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 6000 --seed $s --arm couch_fair_D --arm couch_fair_D_abort \
     --arm couch_fair_D_lgp --arm couch_fair_A_lgp --arm couch_fair_A_row2 --arm couch_fair_D_lgp_row2 --arm couch_fair_A_lgp_row2 \
     --arm couch_464a4b75 2>&1 | tail -9 | cut -c1-240
done
echo; echo "## 4. tests/test_lgprestart.py (DEFECT gate, two-sided), counts summed over seeds 5/11/23/77, 6000 frames each"
nice -n 19 $GPY tests/test_lgprestart.py --frames 6000 --seeds 5,11,23,77 2>&1 | tail -9 | cut -c1-330
for ov in "$A,DRLGPRESTART=1,DRDISTROW=2" "$D,DRLGPRESTART=1,DRDISTROW=2"; do
  echo; echo "## 5. tests/test_lateguard_census_cut.py LGCUT_OVERLAY=$ov"
  LGCUT_OVERLAY=$ov nice -n 19 $GPY tests/test_lateguard_census_cut.py 2>&1 | tail -14
done
echo; echo "## 6. static NMI census (tools/nmi126/census.py on capture_ir.py IR); budget 29780"
mkdir -p tmp/execfid_census
for arm in "D:$D" "A:$A" "D_lgp:$D,DRLGPRESTART=1" "A_lgp:$A,DRLGPRESTART=1" "A_row2:$A,DRDISTROW=2" \
           "D_lgp_row2:$D,DRLGPRESTART=1,DRDISTROW=2" "A_lgp_row2:$A,DRLGPRESTART=1,DRDISTROW=2"; do
  name=${arm%%:*}; ov=${arm#*:}
  $PY - "$ov" tmp/execfid_census/$name.manifest.json <<'PYEOF'
import json, sys
s = json.load(open("experiments/lateflip/couch_c960dd49_flags.json"))["flag_snapshot"]
s.update(dict(kv.split("=", 1) for kv in sys.argv[1].split(",")))
json.dump({"flag_snapshot": s}, open(sys.argv[2], "w"))
PYEOF
  nice -n 19 $GPY tools/nmi126/capture_ir.py tmp/execfid_census/$name.manifest.json tmp/execfid_census/${name}_ir.json > tmp/execfid_census/$name.capture.log 2>&1 || { echo "CAPTURE FAIL $name"; tail -3 tmp/execfid_census/$name.capture.log; }
  echo "-- couch_$name"; nice -n 19 $GPY tools/nmi126/census.py tmp/execfid_census/${name}_ir.json 2>&1 | command grep -a "WORST ADMISSIBLE\|ALL_PATHS\|FAIL"
done
echo; echo "## 7. TAP interface gate (experiments/reach/gate_tap_interface.py, P=2, 40000 frames, seed 3)"
for ov in "$A,DRLGPRESTART=1,DRDISTROW=2" "$D,DRLGPRESTART=1,DRDISTROW=2"; do
  echo "== couch ${ov//,/ }"
  nice -n 19 $GPY experiments/reach/gate_tap_interface.py --cart couch --tap 2 --frames 40000 --seed 3 --overlay $(echo "$ov" | tr ',' ' ') 2>&1 | tail -1
done
echo; echo "## 8. TAP mutant must be KILLED on the final flag set"
nice -n 19 $GPY experiments/reach/gate_tap_interface.py --cart couch --tap 2 --mut everyframe --frames 20000 --seed 3 --overlay $(echo "$A,DRLGPRESTART=1,DRDISTROW=2" | tr ',' ' ') 2>&1 | tail -1
echo; echo "GATES_FINAL DONE"
