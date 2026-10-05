#!/usr/bin/env bash
# execfid lane (2026-10-04): DRLGPRESTART (+ the existing DRDISTROW) on the fair carts, with negative controls.
#   tools/execfid/build_carts.sh [outdir]          (default tmp/carts_execfid)
#   couch D  = c960dd49 snapshot + DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1 -> dbbb5007 (FAIR)
#   couch A  = D + DRABORTSTALE=1                                                                     -> b1b57638 (FAIR2)
#   CvC fair abort = 3b8737a9 snapshot + DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0 DRABORTSTALE=1          -> 821cafdb
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts_execfid}"; mkdir -p "$OUT"
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
CF="DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0 DRABORTSTALE=1"
# ---- negative controls: the new flag unset and explicitly 0 must rebuild the staged carts byte-identically
couch ctl_couch_D            $D
couch ctl_couch_D_explicit   $D DRLGPRESTART=0
couch ctl_couch_A            $A
couch ctl_couch_A_explicit   $A DRLGPRESTART=0
couch ctl_couch_464_explicit DRLATEGUARD=1 DRSTUDYEND=1 DRLGPRESTART=0
cvc   ctl_cvc_A              $CF
cvc   ctl_cvc_A_explicit     $CF DRLGPRESTART=0
expect "$OUT/ctl_couch_D.nes"            dbbb500743c60cad91f62f1076b7f638
expect "$OUT/ctl_couch_D_explicit.nes"   dbbb500743c60cad91f62f1076b7f638
expect "$OUT/ctl_couch_A.nes"            b1b576388dc2e1abffe6d1390430ebca
expect "$OUT/ctl_couch_A_explicit.nes"   b1b576388dc2e1abffe6d1390430ebca
expect "$OUT/ctl_couch_464_explicit.nes" 464a4b7586061a265a4759568eca2363
expect "$OUT/ctl_cvc_A.nes"              821cafdbc3017129cad3c66fcc93d605
expect "$OUT/ctl_cvc_A_explicit.nes"     821cafdbc3017129cad3c66fcc93d605
# DRDISTROW=1 must stay the settle lane's B byte-for-byte after the =2 variant was added (pinned from the pre-=2 build)
couch ctl_couch_D_row1       $D DRDISTROW=1
couch ctl_couch_A_row1       $A DRDISTROW=1
expect "$OUT/ctl_couch_D_row1.nes"       78bc8e75992f4cabe06bc9045b58bc4b
expect "$OUT/ctl_couch_A_row1.nes"       45e3fe7c5ffba1c4da7b7eea816415d1
# ---- candidates (each default-off flag on its own, then combined; combined flags need a combined cert)
couch couch_D_lgp            $D DRLGPRESTART=1
couch couch_A_lgp            $A DRLGPRESTART=1
couch couch_D_row            $D DRDISTROW=1
couch couch_A_row            $A DRDISTROW=1
couch couch_D_lgp_row        $D DRLGPRESTART=1 DRDISTROW=1
couch couch_A_lgp_row        $A DRLGPRESTART=1 DRDISTROW=1
couch couch_D_row2           $D DRDISTROW=2
couch couch_A_row2           $A DRDISTROW=2
couch couch_D_lgp_row2       $D DRLGPRESTART=1 DRDISTROW=2
couch couch_A_lgp_row2       $A DRLGPRESTART=1 DRDISTROW=2
# (no CvC candidate: the CvC snapshot has DRPRESTART=0, so the defect cannot occur there)
for f in couch_D_lgp couch_A_lgp couch_D_row couch_A_row couch_D_lgp_row couch_A_lgp_row couch_D_row2 couch_A_row2 couch_D_lgp_row2 couch_A_lgp_row2; do
  echo "BUILT $(md5 "$OUT/$f.nes")  $f.nes"; done
[ $fail = 0 ] && echo "NEGATIVE CONTROLS: ALL PASS" || { echo "NEGATIVE CONTROLS: FAILED"; exit 1; }
