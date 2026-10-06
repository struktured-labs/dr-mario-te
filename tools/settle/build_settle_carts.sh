#!/usr/bin/env bash
# Build the DRSETTLE carts on the lateguard couch / CvC lineage, with the negative controls.
#   tools/settle/build_settle_carts.sh [outdir]          (default tmp/carts)
# Couch = the c960dd49 flag snapshot (experiments/lateflip/couch_c960dd49_flags.json) + TE branding from the te-v8.2
# worktree's build_copro_branded_env.py (run from THIS worktree, so its patch_cartridge_copro.py is used), exactly as
# tools/lateflip/build_couch_lateguard.sh. CvC = the 3b8737a9 snapshot through patch_cartridge_copro.py (no branding).
# Negative controls (must reproduce the shipped/staged bytes with every new flag at its default AND set explicitly):
#   couch DRLATEGUARD=0                      -> c960dd49     couch DRLATEGUARD=1 DRSTUDYEND=1 -> 464a4b75
#   couch DRLATEGUARD=1                      -> fd08d7a3     CvC DRLATEGUARD=0 -> 3b8737a9, =1 -> 387bb7bd
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts}"; mkdir -p "$OUT"
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

# ---- negative controls: the new flags at their defaults, and set explicitly to the default value
couch ctl_couch_lg0            DRLATEGUARD=0
couch ctl_couch_lg0_explicit   DRLATEGUARD=0 DRSETTLE=15 DRSETTLEPIN=1
couch ctl_couch_lg1            DRLATEGUARD=1
couch ctl_couch_464            DRLATEGUARD=1 DRSTUDYEND=1
couch ctl_couch_464_explicit   DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=15 DRSETTLEPIN=1
cvc   ctl_cvc_lg0              DRLATEGUARD=0
cvc   ctl_cvc_387              DRLATEGUARD=1
cvc   ctl_cvc_387_explicit     DRLATEGUARD=1 DRSETTLE=15 DRSETTLEPIN=1
expect "$OUT/ctl_couch_lg0.nes"          c960dd499e877f01c483af1347ed8df6
expect "$OUT/ctl_couch_lg0_explicit.nes" c960dd499e877f01c483af1347ed8df6
expect "$OUT/ctl_couch_lg1.nes"          fd08d7a35df4369d9dc976b982dcda7f
expect "$OUT/ctl_couch_464.nes"          464a4b7586061a265a4759568eca2363
expect "$OUT/ctl_couch_464_explicit.nes" 464a4b7586061a265a4759568eca2363
expect "$OUT/ctl_cvc_lg0.nes"            3b8737a939c19b1d592218f79bbf869c
expect "$OUT/ctl_cvc_387.nes"            387bb7bd419ffaf9055ea64b7442f317
expect "$OUT/ctl_cvc_387_explicit.nes"   387bb7bd419ffaf9055ea64b7442f317

# ---- candidates: the FAIR settle (upload at the next NMI + readiness guard), with and without the explicit no-pin
couch couch_settle3            DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3
couch couch_settle3_nopin      DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0
cvc   cvc_settle3              DRLATEGUARD=1 DRSETTLE=3
cvc   cvc_settle3_nopin        DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0
# ---- test-only arms (never ship): the guard mutant, and fair-pin-only at the shipped settle (pricing / gate demo)
couch mut_couch_settle3_noguard DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLE_MUT=noguard DRSETTLEPIN=0
couch arm_couch_settle15_nopin  DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLEPIN=0
cvc   mut_cvc_settle3_noguard   DRLATEGUARD=1 DRSETTLE=3 DRSETTLE_MUT=noguard DRSETTLEPIN=0
# ---- fair LEDGE fixes on top of the fair settle (each its own default-off flag; combined builds need combined certs)
#   A = DRPROPHHOLD (PROPH pulses through the MIN_THINK hold), B = DRDISTROW (DISTGATE credits the frames left in the
#   current row), C = DRLEDGECOMMIT (PROPH-armed pills skip MIN_THINK)
FAIR="DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0"
couch couch_fair_A    $FAIR DRPROPHHOLD=1
couch couch_fair_B    $FAIR DRDISTROW=1
couch couch_fair_C    $FAIR DRLEDGECOMMIT=1
couch couch_fair_AB   $FAIR DRPROPHHOLD=1 DRDISTROW=1
couch couch_fair_BC   $FAIR DRDISTROW=1 DRLEDGECOMMIT=1
couch couch_fair_ABC  $FAIR DRPROPHHOLD=1 DRDISTROW=1 DRLEDGECOMMIT=1
couch arm_couch_464_B DRLATEGUARD=1 DRSTUDYEND=1 DRDISTROW=1
#   D = DRPROPHFIRST (PROPH's ledge escape before the rotation pre-phase, until the commit window opens)
couch couch_fair_D    $FAIR DRPROPHFIRST=1
couch couch_fair_DB   $FAIR DRPROPHFIRST=1 DRDISTROW=1
couch couch_fair_DA   $FAIR DRPROPHFIRST=1 DRPROPHHOLD=1
couch couch_fair_DAB  $FAIR DRPROPHFIRST=1 DRPROPHHOLD=1 DRDISTROW=1
# ---- the FAIR KIT (couch candidate = D; the no-study-end couch variant = fd08d7a3 + the same; CvC has no DRPROPH)
couch kit_couch_fair            DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1
couch kit_couch_fair_nostudyend DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1
cvc   kit_cvc_fair              DRLATEGUARD=1 DRSETTLE=3 DRSETTLEPIN=0
for f in couch_settle3 couch_settle3_nopin cvc_settle3 cvc_settle3_nopin mut_couch_settle3_noguard \
         arm_couch_settle15_nopin mut_cvc_settle3_noguard couch_fair_A couch_fair_B couch_fair_C couch_fair_AB \
         couch_fair_BC couch_fair_ABC arm_couch_464_B couch_fair_D couch_fair_DB couch_fair_DA couch_fair_DAB \
         kit_couch_fair kit_couch_fair_nostudyend kit_cvc_fair; do
  echo "BUILT $(md5 "$OUT/$f.nes")  $f.nes"
done
[ $fail = 0 ] && echo "NEGATIVE CONTROLS: ALL PASS" || { echo "NEGATIVE CONTROLS: FAILED"; exit 1; }
