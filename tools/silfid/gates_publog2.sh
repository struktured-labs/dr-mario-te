#!/usr/bin/env bash
# silfid lane gate record for PUBLOG capture #2 (DRP1HOLD + DRGPUMP).   tools/silfid/gates_publog2.sh > experiments/silfid/GATES_PUBLOG2.txt
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
echo "# silfid PUBLOG capture #2 gates ($(date -u +%Y-%m-%dT%H:%MZ), $(git rev-parse --short HEAD) + working tree)"
echo; echo "## 1. negative controls + the carts (tools/silfid/build_publog2.sh)"
nice -n 19 tools/silfid/build_publog2.sh tmp/carts_publog2 2>&1 | tail -16
echo; echo "## 2. static NMI census, worst admissible frame / 29780 (tools/silfid/census_of.sh)"
for v in "publog:DRP1AIHI=1 DRSLICEGUARD2=1 DRPUBLOG=1" "hold:DRP1AIHI=1 DRSLICEGUARD2=1 DRPUBLOG=1 DRP1HOLD=1" \
         "pump:DRP1AIHI=1 DRSLICEGUARD2=1 DRPUBLOG=1 DRP1HOLD=1 DRGPUMP=1" \
         "pump_pdw:DRP1AIHI=1 DRSLICEGUARD2=1 DRPUBLOG=1 DRP1HOLD=1 DRGPUMP=1 DRPUBLOG_PDW=1" \
         "pump2x_pdw:DRP1AIHI=1 DRSLICEGUARD2=1 DRPUBLOG=1 DRP1HOLD=1 DRGPUMP=1 DRPUBLOG_PDW=1 DRGPUMP_T=53"; do
  name=${v%%:*}; ov=${v#*:}
  echo "-- cvcp2 $ov"; tools/silfid/census_of.sh $name cvcp2 $ov 2>&1 | command grep -a "WORST ADMISSIBLE"
done
echo; echo "## 3. tools/gate/run_cart_gates.sh"
DRGATE_PY=$GPY nice -n 19 tools/gate/run_cart_gates.sh 2>&1 | tail -12
echo; echo "## 4. tests/test_gravity_fidelity.py, the cvcp2 arms (P2 only; the pump's \$0318 stores replayed as opponent actions), seeds 5/11/23 x 3000 frames"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 3000 --seed $s --arm cvcp2_publog --arm cvcp2_hold --arm cvcp2_pump \
      --arm cvcp2_pump_t255 --arm couch_464a4b75 2>&1 | tail -6 | cut -c1-260
done
echo; echo "## 5. tests/test_lateguard_census_cut.py on the capture #2 cart (couch snapshot + the cvcp2 overlays)"
OV=$(/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python -c "
import json
c = json.load(open('experiments/lateflip/couch_c960dd49_flags.json'))['flag_snapshot']
d = json.load(open('experiments/silfid/cvcp2_flags.json'))['flag_snapshot']
d.update(DRPUBLOG='1', DRP1HOLD='1', DRGPUMP='1', DRPUBLOG_PDW='1')
print(','.join(f'{k}={v}' for k, v in sorted(d.items()) if c.get(k) != v))")
echo "LGCUT_OVERLAY=$OV"
LGCUT_OVERLAY=$OV nice -n 19 $GPY tests/test_lateguard_census_cut.py 2>&1 | tail -14
echo; echo "## 6. tests/test_publog.py (ring vs truth) and tests/test_gpump.py (hold + pump reference model), seeds 5/11"
nice -n 19 $GPY tests/test_publog.py --frames 2500 --seeds 5,11 2>&1 | tail -10
echo "-- the same ring test on the capture #2 flags (+ DRP1HOLD=1 DRGPUMP=1 DRPUBLOG_PDW=1, false-DONE injection)"
nice -n 19 $GPY tests/test_publog.py --frames 2500 --seeds 5,11 --extra "DRP1HOLD=1 DRGPUMP=1" --pdw 2>&1 | tail -10
for s in 5 11; do nice -n 19 $GPY tests/test_gpump.py --frames 4000 --seed $s 2>&1 | tail -7; done
echo; echo "GATES_PUBLOG2 DONE"
