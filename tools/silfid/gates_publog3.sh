#!/usr/bin/env bash
# silfid lane gate record for PUBLOG capture #3.   tools/silfid/gates_publog3.sh > experiments/silfid/GATES_PUBLOG3.txt
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
F2P="DRABORTSTALE=1 DRLGPRESTART=1 DRDISTROW=2"
X3="DRPUBLOG=1 DRPUBLOG_PDW=1 DRP1HOLD=1 DRGPUMP=1 DRP1DRAIN=1 DRNAVESC_NOPLAY=1 DRP1HOLDFIRST=1"
echo "# silfid PUBLOG capture #3 gates ($(date -u +%Y-%m-%dT%H:%MZ), $(git rev-parse --short HEAD) + working tree)"
echo; echo "## 1. negative controls + the cart (tools/silfid/build_publog3.sh)"
nice -n 19 tools/silfid/build_publog3.sh tmp/carts_publog3 2>&1 | tail -16
echo; echo "## 2. static NMI census, worst admissible frame / 29780 (tools/silfid/census_of.sh)"
for v in "c2:DRP1AIHI=1 DRSLICEGUARD2=1 DRPUBLOG=1 DRPUBLOG_PDW=1 DRP1HOLD=1 DRGPUMP=1" \
         "c3_noholdfirst:DRP1AIHI=1 DRSLICEGUARD2=1 $F2P DRPUBLOG=1 DRPUBLOG_PDW=1 DRP1HOLD=1 DRGPUMP=1 DRP1DRAIN=1 DRNAVESC_NOPLAY=1" \
         "c3:DRP1AIHI=1 DRSLICEGUARD2=1 $F2P $X3"; do
  name=${v%%:*}; ov=${v#*:}
  echo "-- $name: cvcp2 $ov"; tools/silfid/census_of.sh $name cvcp2 $ov 2>&1 | command grep -a "WORST ADMISSIBLE"
done
echo; echo "## 3. tools/gate/run_cart_gates.sh"
DRGATE_PY=$GPY nice -n 19 tools/gate/run_cart_gates.sh 2>&1 | tail -12
echo; echo "## 4. tests/test_gravity_fidelity.py (P2 only; the pump's \$0318 stores replayed as opponent actions), seeds 5/11/23 x 3000 frames"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 3000 --seed $s --arm cvcp2_c3 --arm cvcp2_pump --arm cvc_fair_abort \
      --arm couch_464a4b75 2>&1 | tail -5 | cut -c1-260
done
echo; echo "## 5. tests/test_lateguard_census_cut.py on the capture #3 cart (couch snapshot + the cvcp2 / capture #3 overlays)"
OV=$(/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python -c "
import json
c = json.load(open('experiments/lateflip/couch_c960dd49_flags.json'))['flag_snapshot']
d = json.load(open('experiments/silfid/cvcp2_flags.json'))['flag_snapshot']
d.update(DRABORTSTALE='1', DRLGPRESTART='1', DRDISTROW='2', DRPUBLOG='1', DRPUBLOG_PDW='1', DRP1HOLD='1', DRGPUMP='1',
         DRP1DRAIN='1', DRNAVESC_NOPLAY='1', DRP1HOLDFIRST='1')
print(','.join(f'{k}={v}' for k, v in sorted(d.items()) if c.get(k) != v))")
echo "LGCUT_OVERLAY=$OV"
LGCUT_OVERLAY=$OV nice -n 19 $GPY tests/test_lateguard_census_cut.py 2>&1 | tail -14
echo; echo "## 6. tests/test_publog.py on the capture #3 flags (ring vs truth + --pdw false-DONE injection), seeds 5/11"
nice -n 19 $GPY tests/test_publog.py --frames 2500 --seeds 5,11 --extra "$F2P DRP1HOLD=1 DRGPUMP=1 DRP1DRAIN=1 DRNAVESC_NOPLAY=1 DRP1HOLDFIRST=1" --pdw 2>&1 | tail -10
echo; echo "## 7. tests/test_gpump.py (hold / pump reference model / drain / escape guard; mutants), seeds 5/11"
for s in 5 11; do nice -n 19 $GPY tests/test_gpump.py --frames 3000 --seed $s 2>&1 | tail -10; done
echo; echo "GATES_PUBLOG3 DONE"
