#!/usr/bin/env bash
# silfid lane: PUBLOG capture #2 carts (DRP1HOLD + DRGPUMP on the DRPUBLOG debug-log cart), with negative controls.
#   tools/silfid/build_publog2.sh [outdir]          (default tmp/carts_publog2)
# Every control of tools/silfid/build_publog.sh (the shipped / staged carts and the PUBLOG cart 8355ddc7 rebuild
# byte-identically with the two new flags explicitly 0), then the capture #2 family.
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts_publog2}"; mkdir -p "$OUT"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
TE_DIR=/home/struktured/projects/dr-mario-te-v8.2
snap() { $PY -c "
import json,sys
s = json.load(open(sys.argv[1]))['flag_snapshot']
print(' '.join(f'{k}={v}' for k, v in sorted(s.items())))" "$1"; }
COUCH=$(snap experiments/lateflip/couch_c960dd49_flags.json)
CVC=$(snap experiments/lateflip/cvc_3b8737a9_flags.json)
couch() {
  local name=$1; shift
  env $COUCH TE_FOOTER=0 TE_DIR=$TE_DIR "$@" nice -n 19 $PY $TE_DIR/build_copro_branded_env.py drmario_v28cs.nes \
      "$OUT/$name.nes" > "$OUT/$name.log" 2>&1 || { echo "BUILD FAIL $name"; tail -5 "$OUT/$name.log"; exit 1; }
}
cvc() {   # name level-out-file env...
  local name=$1 outf=$2; shift 2
  rm -f "$outf"
  env "$@" nice -n 19 $PY patch_cartridge_copro.py > "$OUT/$name.log" 2>&1 || { echo "BUILD FAIL $name"; tail -5 "$OUT/$name.log"; exit 1; }
  mv "$outf" "$OUT/$name.nes"
}
md5() { md5sum < "$1" | cut -c1-32; }
fail=0
expect() {
  local got; got=$(md5 "$1")
  if [ "$got" = "$2" ]; then echo "IDENTITY $(basename "$1") == ${2:0:8}: PASS"
  else echo "IDENTITY $(basename "$1") got ${got:0:8} want ${2:0:8}: FAIL"; fail=1; fi
}
D="DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1"
A="$D DRABORTSTALE=1"
P="DRLGPRESTART=1 DRDISTROW=2"
NEW="DRPUBLOG=0 DRSLICEGUARD2=0 DRP1AIHI=0 DRP1HOLD=0 DRGPUMP=0 DRPUBLOG_PDW=0"
KIT=/home/struktured/projects/dr_mario_rl/tmp/couch_kit
# ---- negative controls: every new flag explicitly 0 rebuilds every shipped / staged cart byte-identically
couch ctl_D    $D $NEW
couch ctl_A    $A $NEW
couch ctl_DP   $D $P $NEW
couch ctl_AP   $A $P $NEW
couch ctl_Dsz  $D DRSEEDZERO=1 $NEW
cvc   ctl_cvc_A     drmario_copro_L20s1.nes $CVC DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0 DRABORTSTALE=1 $NEW
cvc   ctl_cvc_fair  drmario_copro_L20s1.nes $CVC DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0 $NEW
expect "$OUT/ctl_D.nes"    dbbb500743c60cad91f62f1076b7f638
expect "$OUT/ctl_A.nes"    b1b576388dc2e1abffe6d1390430ebca
expect "$OUT/ctl_DP.nes"   $(md5 $KIT/fairplus_20261005/drmario_te_couch_fairplus_5b3d8183.nes)
expect "$OUT/ctl_AP.nes"   $(md5 $KIT/fairplus_20261005/drmario_te_couch_fair2plus_5a1695da.nes)
expect "$OUT/ctl_Dsz.nes"  90b442c7f39d7d7cc1ff7b9f8e17a109
expect "$OUT/ctl_cvc_A.nes"    821cafdbc3017129cad3c66fcc93d605
expect "$OUT/ctl_cvc_fair.nes" $(md5 $KIT/fair_20261003/drmario_cvc_fair_4dfa9c79.nes)
# ---- capture #1's PUBLOG cart: the two new flags 0 must give 8355ddc7 (the cart that ran on bluemage 10/06)
BASE=$($PY tools/silfid/publog_flags.py cvcp2 DRP1AIHI=1 DRSLICEGUARD2=1)
cvc publog_cvcp2_ctl  drmario_copro.nes $BASE DRPUBLOG=1 DRP1HOLD=0 DRGPUMP=0 DRPUBLOG_PDW=0
expect "$OUT/publog_cvcp2_ctl.nes" 8355ddc7a802a2181a2f2f3f1360662c
# ---- capture #2: P1 held + the synthetic P1 attack at dr. lulu's 10/05 rate (T 27 = 2.86 volleys / play-min)
#      + the post-DONE watch (DRPUBLOG_PDW). pump2x = the same at T 53 (5.72 / play-min).
cvc hold_cvcp2        drmario_copro.nes $BASE DRPUBLOG=1 DRP1HOLD=1
cvc pump_nopdw_cvcp2  drmario_copro.nes $BASE DRPUBLOG=1 DRP1HOLD=1 DRGPUMP=1
cvc pump_cvcp2        drmario_copro.nes $BASE DRPUBLOG=1 DRP1HOLD=1 DRGPUMP=1 DRPUBLOG_PDW=1
cvc pump_cvcp2_t27    drmario_copro.nes $BASE DRPUBLOG=1 DRP1HOLD=1 DRGPUMP=1 DRPUBLOG_PDW=1 DRGPUMP_T=27
cvc pump2x_cvcp2      drmario_copro.nes $BASE DRPUBLOG=1 DRP1HOLD=1 DRGPUMP=1 DRPUBLOG_PDW=1 DRGPUMP_T=53
expect "$OUT/pump_cvcp2_t27.nes" $(md5 "$OUT/pump_cvcp2.nes")
for f in publog_cvcp2_ctl hold_cvcp2 pump_nopdw_cvcp2 pump_cvcp2 pump2x_cvcp2; do echo "BUILT $(md5 "$OUT/$f.nes")  $f.nes"; done
[ $fail = 0 ] && echo "NEGATIVE CONTROLS: ALL PASS" || { echo "NEGATIVE CONTROLS: FAILED"; exit 1; }
