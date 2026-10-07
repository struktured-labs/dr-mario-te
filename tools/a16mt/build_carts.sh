#!/usr/bin/env bash
# a16mt lane (2026-10-07): FAIR2PLUS + MIN_THINK -4 f (STEER13 "V11 MT 2"), with negative controls.
#   tools/a16mt/build_carts.sh [outdir]          (default tmp/carts_a16mt)
#   FAIR2PLUS = c960dd49 snapshot + D + DRABORTSTALE=1 DRLGPRESTART=1 DRDISTROW=2               -> 5a1695da (MIN_THINK 12 hooks = 6 f)
#   MT2       = FAIR2PLUS + DRMINTHINK=4 (4 hooks at the 2-hook/frame cadence = GO + 2 f)
# The commit gate is WDOG2 >= MIN_THINK (patch_cartridge_copro.py: p2_orient_ok and DRPROPHFIRST's pf_skip); the flag
# only moves those two CMP immediates, which the byte diff below asserts.
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts_a16mt}"; mkdir -p "$OUT"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
TE_DIR=/home/struktured/projects/dr-mario-te-v8.2
snap() { $PY -c "
import json,sys
s = json.load(open(sys.argv[1]))['flag_snapshot']
print(' '.join(f'{k}={v}' for k, v in sorted(s.items())))" "$1"; }
COUCH=$(snap experiments/lateflip/couch_c960dd49_flags.json)
couch() {
  local name=$1; shift
  env $COUCH TE_FOOTER=0 TE_DIR=$TE_DIR "$@" nice -n 19 $PY $TE_DIR/build_copro_branded_env.py drmario_v28cs.nes \
      "$OUT/$name.nes" > "$OUT/$name.log" 2>&1 || { echo "BUILD FAIL $name"; tail -5 "$OUT/$name.log"; exit 1; }
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
# ---- negative controls: the snapshot's MIN_THINK (12) unset-by-overlay and explicit must rebuild the staged carts
couch ctl_fair2plus          $A DRLGPRESTART=1 DRDISTROW=2
couch ctl_fair2plus_mt12     $A DRLGPRESTART=1 DRDISTROW=2 DRMINTHINK=12
couch ctl_fairplus_mt12      $D DRLGPRESTART=1 DRDISTROW=2 DRMINTHINK=12
expect "$OUT/ctl_fair2plus.nes"      5a1695da51a850b38eaf983bbae49206
expect "$OUT/ctl_fair2plus_mt12.nes" 5a1695da51a850b38eaf983bbae49206
expect "$OUT/ctl_fairplus_mt12.nes"  5b3d81830c83a50bb9aa8e37fe385448
# ---- candidate
couch fair2plus_mt2          $A DRLGPRESTART=1 DRDISTROW=2 DRMINTHINK=4
# the flag must move ONLY the MIN_THINK immediates (CMP #$0C -> CMP #$04), and must move something
$PY - "$OUT/ctl_fair2plus.nes" "$OUT/fair2plus_mt2.nes" <<'PYEOF' || fail=1
import sys
a, b = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
d = [i for i in range(len(a)) if a[i] != b[i]]
ok = len(a) == len(b) and d and all(a[i] == 0x0C and b[i] == 0x04 and a[i - 1] == 0xC9 for i in d)
print(f"BYTE DIFF fair2plus -> mt2: {len(d)} bytes at file offsets {[hex(i) for i in d]}, all CMP #$0C -> #$04: "
      f"{'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PYEOF
echo "BUILT $(md5 "$OUT/fair2plus_mt2.nes")  fair2plus_mt2.nes"
command grep -a -o '"DRMINTHINK": "[0-9]*"' "$OUT/fair2plus_mt2.log" | head -1
[ $fail = 0 ] && echo "NEGATIVE CONTROLS: ALL PASS" || { echo "NEGATIVE CONTROLS: FAILED"; exit 1; }
