#!/usr/bin/env bash
# silfid lane gate record for the DRPUBLOG debug-log cart.   tools/silfid/gates_publog.sh > experiments/silfid/GATES_PUBLOG.txt
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
echo "# silfid DRPUBLOG gates ($(date -u +%Y-%m-%dT%H:%MZ), $(git rev-parse --short HEAD) + working tree)"
echo; echo "## 1. negative controls + the cart (tools/silfid/build_publog.sh)"
nice -n 19 tools/silfid/build_publog.sh tmp/carts_publog 2>&1 | tail -12
echo; echo "## 2. static NMI census, worst admissible frame / 29780 (tools/silfid/census_of.sh)"
for v in "base_noguard:DRP1AIHI=1" "base:DRP1AIHI=1 DRSLICEGUARD2=1" "publog:DRP1AIHI=1 DRSLICEGUARD2=1 DRPUBLOG=1"; do
  name=${v%%:*}; ov=${v#*:}
  echo "-- cvcp2 $ov"; tools/silfid/census_of.sh $name cvcp2 $ov 2>&1 | command grep -a "WORST ADMISSIBLE"
done
echo "(the deployed fair CvC cart 4dfa9c79, for scale: unsliced P1 search, ALL_PATHS hook bound 98,601 -- not certifiable)"
echo; echo "## 3. tools/gate/run_cart_gates.sh"
DRGATE_PY=$GPY nice -n 19 tools/gate/run_cart_gates.sh 2>&1 | tail -12
echo; echo "## 4. tests/test_gravity_fidelity.py, the cvcp2 arms, seeds 5/11/23 x 3000 frames"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 3000 --seed $s --arm cvcp2_base --arm cvcp2_publog --arm couch_464a4b75 2>&1 | tail -4 | cut -c1-240
done
echo; echo "## 5. tests/test_lateguard_census_cut.py on the debug cart (couch snapshot + the cvcp2 overlays)"
OV=$(/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python -c "
import json
c = json.load(open('experiments/lateflip/couch_c960dd49_flags.json'))['flag_snapshot']
d = json.load(open('experiments/silfid/cvcp2_flags.json'))['flag_snapshot']
d['DRPUBLOG'] = '1'
print(','.join(f'{k}={v}' for k, v in sorted(d.items()) if c.get(k) != v))")
echo "LGCUT_OVERLAY=$OV"
LGCUT_OVERLAY=$OV nice -n 19 $GPY tests/test_lateguard_census_cut.py 2>&1 | tail -14
echo; echo "## 6. tests/test_publog.py (ring vs truth, zp restore, DRSLICEGUARD2 premise + mutant), seeds 5/11 x 2500 frames"
nice -n 19 $GPY tests/test_publog.py --frames 2500 --seeds 5,11 2>&1 | tail -10
echo; echo "GATES_PUBLOG DONE"
