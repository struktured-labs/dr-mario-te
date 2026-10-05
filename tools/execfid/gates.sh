#!/usr/bin/env bash
# execfid gates for DRLGPRESTART / DRDISTROW on the fair couch carts (D = dbbb5007 flags, A = D + DRABORTSTALE).
#   tools/execfid/gates.sh > experiments/execfid/GATES.txt
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
D="DRLATEGUARD=1,DRSTUDYEND=1,DRSETTLE=3,DRSETTLEPIN=0,DRPROPHFIRST=1"
A="$D,DRABORTSTALE=1"
echo "## tools/execfid/build_carts.sh (negative controls + candidates)"
nice -n 19 tools/execfid/build_carts.sh tmp/carts_execfid 2>&1 | tail -15
echo; echo "## tools/gate/run_cart_gates.sh"
DRGATE_PY=$GPY nice -n 19 tools/gate/run_cart_gates.sh 2>&1 | tail -12
echo; echo "## tests/test_gravity_fidelity.py, the new arms, seeds 5/11/23, 6000 frames"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 6000 --seed $s --arm couch_fair_D_abort --arm couch_fair_D_lgp \
     --arm couch_fair_A_lgp --arm couch_fair_A_row --arm couch_fair_D_lgp_row --arm couch_fair_A_lgp_row 2>&1 | tail -7
done 2>/dev/null
echo; echo "## tests/test_lgprestart.py (defect gate), seeds 5/11/23, 6000 frames"
nice -n 19 $GPY tests/test_lgprestart.py --frames 6000 --seeds 5,11,23,77 2>&1 | tail -7
for ov in "$A,DRLGPRESTART=1" "$A,DRLGPRESTART=1,DRDISTROW=1" "$D,DRLGPRESTART=1,DRDISTROW=1"; do
  echo; echo "## tests/test_lateguard_census_cut.py LGCUT_OVERLAY=$ov"
  LGCUT_OVERLAY=$ov nice -n 19 $GPY tests/test_lateguard_census_cut.py 2>&1 | tail -14
done
echo; echo "## static NMI census (tools/nmi126/census.py on capture_ir.py IR)"
mkdir -p tmp/execfid_census
for arm in "D:$D" "A:$A" "A_lgp:$A,DRLGPRESTART=1" "A_row:$A,DRDISTROW=1" "A_lgp_row:$A,DRLGPRESTART=1,DRDISTROW=1" "D_lgp_row:$D,DRLGPRESTART=1,DRDISTROW=1"; do
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
echo; echo "## TAP interface gate (experiments/reach/gate_tap_interface.py, 40000 frames, seed 3)"
for ov in "$A,DRLGPRESTART=1,DRDISTROW=1" "$D,DRLGPRESTART=1,DRDISTROW=1"; do
  echo "== couch ${ov//,/ }"
  nice -n 19 $GPY experiments/reach/gate_tap_interface.py --cart couch --tap 2 --frames 40000 --seed 3 --overlay $(echo "$ov" | tr ',' ' ') 2>&1 | tail -1
done
