#!/usr/bin/env bash
# u8slam lane (2026-10-11): FAIR2PLUS with the slam stability window cut to 8 hooks in both phases (STEER14 "u8").
#   tools/u8slam/build_carts.sh [outdir]          (default tmp/carts_u8slam)
#   FAIR2PLUS = c960dd49 snapshot + D + DRABORTSTALE=1 DRLGPRESTART=1 DRDISTROW=2   -> 5a1695da (KOPEN 32, KEND 255)
#   U8        = FAIR2PLUS + DRSLAM_KOPEN=8 DRSLAM_KEND=8 (8 hooks at the 2-hook/frame cadence = 4 f; VCEND, KCROSS,
#               LOWY unchanged)
# The slam gate is dn_p2's `LDA STABLE_CT2 / CMP #K / BCS dn_p2_go` (patch_cartridge_copro.py), one compare per phase.
# K_END 255 is not special-cased anywhere: STABLE_CT2 saturates at $FE, so CMP #$FF never passes. Any K <= $FE is an
# ordinary K-hook stability gate through the same compare. The byte diff below asserts exactly those two immediates.
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts_u8slam}"; mkdir -p "$OUT"
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
A="DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1 DRABORTSTALE=1"
F2P="$A DRLGPRESTART=1 DRDISTROW=2"
# ---- negative controls: the snapshot's slam window, unset-by-overlay and explicit, must rebuild the couch cart
couch ctl_fair2plus            $F2P
couch ctl_fair2plus_k32_e255   $F2P DRSLAM_KOPEN=32 DRSLAM_KEND=255
expect "$OUT/ctl_fair2plus.nes"          5a1695da51a850b38eaf983bbae49206
expect "$OUT/ctl_fair2plus_k32_e255.nes" 5a1695da51a850b38eaf983bbae49206
# ---- candidate, and the two one-variable carts that locate each immediate
couch fair2plus_u8             $F2P DRSLAM_KOPEN=8 DRSLAM_KEND=8
couch loc_k8                   $F2P DRSLAM_KOPEN=8
couch loc_e8                   $F2P DRSLAM_KEND=8
$PY - "$OUT" <<'PYEOF' || fail=1
import sys
o = sys.argv[1]
rd = lambda n: open(f"{o}/{n}.nes", "rb").read()
base, u8, k8, e8 = rd("ctl_fair2plus"), rd("fair2plus_u8"), rd("loc_k8"), rd("loc_e8")
diff = lambda a, b: [i for i in range(len(a)) if a[i] != b[i]]
ok = len(base) == len(u8) == len(k8) == len(e8)
dk, de, du = diff(base, k8), diff(base, e8), diff(base, u8)
def show(tag, d, b):
    print(f"BYTE DIFF fair2plus -> {tag}: {len(d)} byte(s): " + ", ".join(
        f"file 0x{i:04X} ${base[i]:02X} -> ${b[i]:02X} (prev opcode ${base[i - 1]:02X}; "
        f"context {base[i - 4:i + 3].hex(' ')})" for i in d))
show("KOPEN=8 only", dk, k8); show("KEND=8 only", de, e8); show("u8", du, u8)
# each flag moves exactly one CMP immediate; u8 is exactly their union; K_OPEN is the documented 0x90C5
ok &= len(dk) == 1 and len(de) == 1 and dk != de and sorted(du) == sorted(dk + de)
ok &= dk == [0x90C5] and base[0x90C5] == 0x20 and u8[0x90C5] == 0x08
ok &= all(base[i - 1] == 0xC9 and u8[i] == 0x08 for i in du) and base[de[0]] == 0xFF
# both immediates follow LDA STABLE_CT2 ($6171): AD 71 61 C9 kk
ok &= all(base[i - 4:i] == bytes([0xAD, 0x71, 0x61, 0xC9]) for i in du)
print("BYTE DIFF u8 = {K_OPEN $20 -> $08, K_END $FF -> $08}, both `LDA $6171 / CMP #imm`: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
PYEOF
echo "BUILT $(md5 "$OUT/fair2plus_u8.nes")  fair2plus_u8.nes"
command grep -a -o '"DRSLAM_K[A-Z]*": "[0-9]*"' "$OUT/fair2plus_u8.log" | sort -u | tr '\n' ' '; echo
[ $fail = 0 ] && echo "NEGATIVE CONTROLS: ALL PASS" || { echo "NEGATIVE CONTROLS: FAILED"; exit 1; }
