#!/usr/bin/env bash
# silfid lane gate record for DRSEEDZERO on the fair couch carts.
#   tools/silfid/gates_final.sh > experiments/silfid/GATES.txt
# D = dbbb5007 flags (FAIR), A = D + DRABORTSTALE (b1b57638, FAIR2), P = DRLGPRESTART=1 DRDISTROW=2 (the "+" carts).
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
D="DRLATEGUARD=1,DRSTUDYEND=1,DRSETTLE=3,DRSETTLEPIN=0,DRPROPHFIRST=1"
A="$D,DRABORTSTALE=1"
P="DRLGPRESTART=1,DRDISTROW=2"
echo "# silfid gates ($(date -u +%Y-%m-%dT%H:%MZ), $(git rev-parse --short HEAD) + working tree)"
echo; echo "## 1. negative controls + candidates (tools/silfid/build_carts.sh)"
nice -n 19 tools/silfid/build_carts.sh tmp/carts_silfid 2>&1 | tail -14
echo; echo "## 2. tools/gate/run_cart_gates.sh (gravity-fidelity runs every ARMS entry incl. the new _sz arms; + test_seedzero)"
DRGATE_PY=$GPY nice -n 19 tools/gate/run_cart_gates.sh 2>&1 | tail -12
echo; echo "## 3. tests/test_gravity_fidelity.py, the _sz arms + their base arms, seeds 5/11/23, 6000 frames"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 6000 --seed $s --arm couch_fair_D_lgp_row2 --arm couch_fair_A_lgp_row2 \
     --arm couch_fair_D_lgp_row2_sz --arm couch_fair_A_lgp_row2_sz --arm couch_464a4b75 2>&1 | tail -6 | cut -c1-240
done
echo; echo "## 4. tests/test_seedzero.py (DEFECT gate, two-sided), counts summed over seeds 5/11/23, 3000 frames each"
nice -n 19 $GPY tests/test_seedzero.py --frames 3000 --seeds 5,11,23 2>&1 | tail -9 | cut -c1-260
for ov in "$A,$P,DRSEEDZERO=1" "$D,$P,DRSEEDZERO=1"; do
  echo; echo "## 5. tests/test_lateguard_census_cut.py LGCUT_OVERLAY=$ov"
  LGCUT_OVERLAY=$ov nice -n 19 $GPY tests/test_lateguard_census_cut.py 2>&1 | tail -14
done
echo; echo "## 6. static NMI census (tools/nmi126/census.py on capture_ir.py IR); budget 29780"
mkdir -p tmp/silfid_census
for arm in "DP:$D,$P" "AP:$A,$P" "DP_sz:$D,$P,DRSEEDZERO=1" "AP_sz:$A,$P,DRSEEDZERO=1"; do
  name=${arm%%:*}; ov=${arm#*:}
  $PY - "$ov" tmp/silfid_census/$name.manifest.json <<'PYEOF'
import json, sys
s = json.load(open("experiments/lateflip/couch_c960dd49_flags.json"))["flag_snapshot"]
s.update(dict(kv.split("=", 1) for kv in sys.argv[1].split(",")))
json.dump({"flag_snapshot": s}, open(sys.argv[2], "w"))
PYEOF
  nice -n 19 $GPY tools/nmi126/capture_ir.py tmp/silfid_census/$name.manifest.json tmp/silfid_census/${name}_ir.json > tmp/silfid_census/$name.capture.log 2>&1 || { echo "CAPTURE FAIL $name"; tail -3 tmp/silfid_census/$name.capture.log; }
  echo "-- couch_$name"; nice -n 19 $GPY tools/nmi126/census.py tmp/silfid_census/${name}_ir.json 2>&1 | command grep -a "WORST ADMISSIBLE\|ALL_PATHS\|FAIL"
done
# the TAP gate reads the recorded build-log flag snapshots tmp/carts/{couch,cvc}_tap2.log (ignored files): seed them
mkdir -p tmp/carts
for f in couch_tap2.log cvc_tap2.log; do [ -f tmp/carts/$f ] || cp /home/struktured/projects/dr-mario-execfid-wt/tmp/carts/$f tmp/carts/; done
echo; echo "## 7. TAP interface gate (experiments/reach/gate_tap_interface.py, P=2, 40000 frames, seed 3)"
for ov in "$A,$P,DRSEEDZERO=1" "$D,$P,DRSEEDZERO=1"; do
  echo "== couch ${ov//,/ }"
  nice -n 19 $GPY experiments/reach/gate_tap_interface.py --cart couch --tap 2 --frames 40000 --seed 3 --overlay $(echo "$ov" | tr ',' ' ') 2>&1 | tail -1
done
echo; echo "## 9. firmware: DRCOPRO_TUCKV3_SEEDMASK (fpga/copro/tuck_v3.py) -- negative control + build, then the defect gate"
for v in unset 0 1; do
  if [ $v = unset ]; then env -u DRCOPRO_TUCKV3_SEEDMASK nice -n 19 $PY experiments/reach/build_fw.py 540 tmp/silfid_fw_$v.hex 1 1 1 | tail -1
  else DRCOPRO_TUCKV3_SEEDMASK=$v nice -n 19 $PY experiments/reach/build_fw.py 540 tmp/silfid_fw_$v.hex 1 1 1 | tail -1; fi
done
echo "(want: unset and 0 -> md5 1488e1583ab7ad8b2011d4c136926faf = the shipped antibody-dist60 fw; 1 -> 4c005042928ad9474ddaa52961659660)"
nice -n 19 $GPY tests/test_tuck_seedmask.py 2>&1 | tail -3
echo; echo "GATES_FINAL DONE"
