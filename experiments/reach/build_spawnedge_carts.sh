#!/usr/bin/env bash
# Build the TAP carts with DRSPAWNEDGE off (IDENTITY: must reproduce the staged 198a95e3 couch / 33062615 CvC) and on.
# Recipes verbatim from h16-wt experiments/cvx/CHAIN540_REACH_BUILD.md + CHAIN540_REACH_TAP_BUILD.md (+ DRTAPP=2).
# Run from anywhere; builds in reach-wt (the canonical driver = cwd for the branded builder). Outputs: tmp/carts/.
set -euo pipefail
R=/home/struktured/projects/dr-mario-reach-wt; cd "$R"; mkdir -p tmp/carts
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
COUCH_ENV=$(cat /home/struktured/projects/dr-mario-h16-wt/tmp/flags_b_control.env)
CVC_ENV=$($PY -c "
import json,re
s=json.loads(re.search(r'##DRFLAGSNAPSHOT## (\{.*\})', open('/home/struktured/projects/dr-mario-tempo-wt/tmp/tuckguard/b_cvc_tg1_L20.log').read()).group(1))
print(' '.join(f'{k}={v}' for k,v in sorted(s.items())))")
for SE in 0 1; do
  env $COUCH_ENV DRSTUDY=1 DRSTUDY2P=1 DRSTUDY2P_INV=1 DRSTUDYCOUNTS=1 TE_FOOTER=0 DRSTUDY_Y=0x98 DRNMITMP=1 DRREACHTX=1 \
      DRTAPP=2 DRSPAWNEDGE=$SE TE_DIR=/home/struktured/projects/dr-mario-te-v8.2 \
      $PY /home/struktured/projects/dr-mario-te-v8.2/build_copro_branded_env.py drmario_v28cs.nes tmp/carts/couch_tap2_se$SE.nes \
      > tmp/carts/couch_tap2_se$SE.log 2>&1
  env $CVC_ENV DRNMITMP=1 DRREACHTX=1 DRTAPP=2 DRSPAWNEDGE=$SE $PY patch_cartridge_copro.py > tmp/carts/cvc_tap2_se$SE.log 2>&1
  mv drmario_copro_L20s1.nes tmp/carts/cvc_tap2_se$SE.nes
done
md5sum tmp/carts/couch_tap2_se0.nes tmp/carts/couch_tap2_se1.nes tmp/carts/cvc_tap2_se0.nes tmp/carts/cvc_tap2_se1.nes
[ "$(md5sum < tmp/carts/couch_tap2_se0.nes | cut -c1-32)" = 198a95e3d5f0ce5b671c1b8d02af54ce ] && echo "IDENTITY couch DRSPAWNEDGE=0 == 198a95e3: PASS" || echo "IDENTITY couch: FAIL"
[ "$(md5sum < tmp/carts/cvc_tap2_se0.nes | cut -c1-32)" = 33062615a9b76fb9233445daa7899caa ] && echo "IDENTITY cvc DRSPAWNEDGE=0 == 33062615: PASS" || echo "IDENTITY cvc: FAIL"
