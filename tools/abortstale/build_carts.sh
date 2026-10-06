#!/usr/bin/env bash
# Build the DRABORTSTALE carts on the fair-settle lineage (tools/settle/build_settle_carts.sh recipe), with the
# negative controls: every flag set below with DRABORTSTALE unset AND =0 must rebuild the staged carts byte-identically.
#   tools/abortstale/build_carts.sh [outdir]          (default tmp/carts_abort)
#   couch D  = c960dd49 snapshot + DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1 -> dbbb5007
#   CvC fair = 3b8737a9 snapshot + DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0                             -> 4dfa9c79
#   couch 464 = c960dd49 snapshot + DRLATEGUARD=1 DRSTUDYEND=1                                         -> 464a4b75
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts_abort}"; mkdir -p "$OUT"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
TE_DIR=/home/struktured/projects/dr-mario-te-v8.2
snap() { $PY -c "
import json,sys
s = json.load(open(sys.argv[1]))['flag_snapshot']
print(' '.join(f'{k}={v}' for k, v in sorted(s.items())))" "$1"; }
COUCH=$(snap experiments/lateflip/couch_c960dd49_flags.json)
CVC=$(snap experiments/lateflip/cvc_3b8737a9_flags.json)
couch() {   # couch <name> <extra env...>
  local name=$1; shift
  env $COUCH TE_FOOTER=0 TE_DIR=$TE_DIR "$@" nice -n 19 $PY $TE_DIR/build_copro_branded_env.py drmario_v28cs.nes \
      "$OUT/$name.nes" > "$OUT/$name.log" 2>&1 || { echo "BUILD FAIL $name"; tail -5 "$OUT/$name.log"; exit 1; }
}
cvc() {     # cvc <name> <extra env...>   (patch_cartridge_copro.py writes drmario_copro_L20s1.nes in the cwd)
  local name=$1; shift
  rm -f drmario_copro_L20s1.nes
  env $CVC "$@" nice -n 19 $PY patch_cartridge_copro.py > "$OUT/$name.log" 2>&1 || { echo "BUILD FAIL $name"; tail -5 "$OUT/$name.log"; exit 1; }
  mv drmario_copro_L20s1.nes "$OUT/$name.nes"
}
md5() { md5sum < "$1" | cut -c1-32; }
fail=0
expect() {  # expect <file> <md5>
  local got; got=$(md5 "$1")
  if [ "$got" = "$2" ]; then echo "IDENTITY $(basename "$1") == ${2:0:8}: PASS"
  else echo "IDENTITY $(basename "$1") got ${got:0:8} want ${2:0:8}: FAIL"; fail=1; fi
}
D="DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1"
CF="DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0"
# ---- negative controls (flag unset, and explicitly 0)
couch ctl_couch_D            $D
couch ctl_couch_D_explicit   $D DRABORTSTALE=0
couch ctl_couch_464_explicit DRLATEGUARD=1 DRSTUDYEND=1 DRABORTSTALE=0
cvc   ctl_cvc_fair           $CF
cvc   ctl_cvc_fair_explicit  $CF DRABORTSTALE=0
expect "$OUT/ctl_couch_D.nes"            dbbb500743c60cad91f62f1076b7f638
expect "$OUT/ctl_couch_D_explicit.nes"   dbbb500743c60cad91f62f1076b7f638
expect "$OUT/ctl_couch_464_explicit.nes" 464a4b7586061a265a4759568eca2363
expect "$OUT/ctl_cvc_fair.nes"           4dfa9c797c3a215cf7e0dc71c016de4f
expect "$OUT/ctl_cvc_fair_explicit.nes"  4dfa9c797c3a215cf7e0dc71c016de4f
# ---- candidates
couch couch_D_abort          $D DRABORTSTALE=1
cvc   cvc_fair_abort         $CF DRABORTSTALE=1
for f in couch_D_abort cvc_fair_abort; do echo "BUILT $(md5 "$OUT/$f.nes")  $f.nes"; done
[ $fail = 0 ] && echo "NEGATIVE CONTROLS: ALL PASS" || { echo "NEGATIVE CONTROLS: FAILED"; exit 1; }
