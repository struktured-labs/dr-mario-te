#!/usr/bin/env bash
# silfid lane (2026-10-06): DRSEEDZERO on the fair couch carts, with negative controls.
#   tools/silfid/build_carts.sh [outdir]          (default tmp/carts_silfid)
#   D  = c960dd49 snapshot + DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1   -> dbbb5007 (FAIR)
#   A  = D + DRABORTSTALE=1                                                                       -> b1b57638 (FAIR2)
#   +  = DRLGPRESTART=1 DRDISTROW=2                                -> FAIRPLUS 5b3d8183 / FAIR2PLUS 5a1695da
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts_silfid}"; mkdir -p "$OUT"
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
cvc() {
  local name=$1; shift
  rm -f drmario_copro_L20s1.nes
  env $CVC "$@" nice -n 19 $PY patch_cartridge_copro.py > "$OUT/$name.log" 2>&1 || { echo "BUILD FAIL $name"; tail -5 "$OUT/$name.log"; exit 1; }
  mv drmario_copro_L20s1.nes "$OUT/$name.nes"
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
CF="DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0 DRABORTSTALE=1"
# ---- negative controls: DRSEEDZERO unset and =0 must rebuild the staged / deployed carts byte-identically
couch ctl_D           $D
couch ctl_D_explicit  $D DRSEEDZERO=0
couch ctl_A           $A
couch ctl_DP          $D $P
couch ctl_DP_explicit $D $P DRSEEDZERO=0
couch ctl_AP          $A $P
couch ctl_AP_explicit $A $P DRSEEDZERO=0
cvc   ctl_cvc_A           $CF
cvc   ctl_cvc_A_explicit  $CF DRSEEDZERO=0
expect "$OUT/ctl_D.nes"            dbbb500743c60cad91f62f1076b7f638
expect "$OUT/ctl_D_explicit.nes"   dbbb500743c60cad91f62f1076b7f638
expect "$OUT/ctl_A.nes"            b1b576388dc2e1abffe6d1390430ebca
expect "$OUT/ctl_DP.nes"           $(md5 /home/struktured/projects/dr_mario_rl/tmp/couch_kit/fairplus_20261005/drmario_te_couch_fairplus_5b3d8183.nes)
expect "$OUT/ctl_DP_explicit.nes"  $(md5 /home/struktured/projects/dr_mario_rl/tmp/couch_kit/fairplus_20261005/drmario_te_couch_fairplus_5b3d8183.nes)
expect "$OUT/ctl_AP.nes"           $(md5 /home/struktured/projects/dr_mario_rl/tmp/couch_kit/fairplus_20261005/drmario_te_couch_fair2plus_5a1695da.nes)
expect "$OUT/ctl_AP_explicit.nes"  $(md5 /home/struktured/projects/dr_mario_rl/tmp/couch_kit/fairplus_20261005/drmario_te_couch_fair2plus_5a1695da.nes)
expect "$OUT/ctl_cvc_A.nes"        821cafdbc3017129cad3c66fcc93d605
expect "$OUT/ctl_cvc_A_explicit.nes" 821cafdbc3017129cad3c66fcc93d605
# ---- candidates
couch couch_D_sz   $D DRSEEDZERO=1
couch couch_DP_sz  $D $P DRSEEDZERO=1
couch couch_AP_sz  $A $P DRSEEDZERO=1
for f in couch_D_sz couch_DP_sz couch_AP_sz; do echo "BUILT $(md5 "$OUT/$f.nes")  $f.nes"; done
[ $fail = 0 ] && echo "NEGATIVE CONTROLS: ALL PASS" || { echo "NEGATIVE CONTROLS: FAILED"; exit 1; }
