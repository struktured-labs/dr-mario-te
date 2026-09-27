#!/usr/bin/env bash
# Reproduce the CANON SOTA 2026-09-27 firmware + carts from this tree and check every md5 (SOTA_20260927.md).
# Needs (not in git): the base ROM drmario_v28cs.nes in the repo root, and TE_DIR = a checkout of branch te-v9 @ be24fb6c
# (provides build_copro_branded_env.py + TE branding). The rbf itself needs Quartus + the NES_MiSTer fork (see the record).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); cd "$ROOT"; PY=${PY:-python3}; TE_DIR=${TE_DIR:?set TE_DIR to a te-v9@be24fb6c checkout}
OUT=${OUT:-$ROOT/tmp/sota_repro}; mkdir -p "$OUT"
$PY experiments/reach/build_fw.py 540 "$OUT/fw540_reachtap.hex" 1 1
env $(cat experiments/cvx/sota_20260927_couch_flags.env) DRSTUDY=1 DRSTUDY2P=1 DRSTUDY2P_INV=1 DRSTUDYCOUNTS=1 TE_FOOTER=0 DRSTUDY_Y=0x98 \
    DRNMITMP=1 DRREACHTX=1 DRTAPP=2 TE_DIR="$TE_DIR" $PY "$TE_DIR/build_copro_branded_env.py" drmario_v28cs.nes "$OUT/couch.nes" > "$OUT/couch.log" 2>&1
env $(cat experiments/cvx/sota_20260927_cvc_flags.env) DRNMITMP=1 DRREACHTX=1 DRTAPP=2 $PY patch_cartridge_copro.py > "$OUT/cvc.log" 2>&1
mv drmario_copro_L20s1.nes "$OUT/cvc.nes"
ok=1
chk() { got=$(md5sum < "$1" | cut -c1-32); [ "$got" = "$2" ] && echo "PASS $3 $got" || { echo "FAIL $3 got $got want $2"; ok=0; }; }
chk "$OUT/fw540_reachtap.hex" 77ec742cf0446b49a7f363b34c522864 firmware
chk "$OUT/couch.nes" 198a95e3d5f0ce5b671c1b8d02af54ce couch-cart
chk "$OUT/cvc.nes" 33062615a9b76fb9233445daa7899caa cvc-cart
[ $ok = 1 ] && echo "SOTA_REPRODUCE_PASS" || { echo "SOTA_REPRODUCE_FAIL"; exit 1; }
