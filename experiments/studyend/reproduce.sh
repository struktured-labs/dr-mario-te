#!/usr/bin/env bash
# Reproduce the DRSTUDYEND couch cart and its negative control, check both md5s, run the emitter test.
# Recipe = experiments/cvx/sota_20260927_reproduce.sh's couch line + DRSPAWNEDGE=1 (== the staged DIST60 couch cart
# c960dd49, reach-root build_spawnedge_carts.sh) [+ DRSTUDYEND=1].
# Needs (not in git): drmario_v28cs.nes in the repo root; TE_DIR = a te-v9 @ be24fb6c checkout.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); cd "$ROOT"; PY=${PY:-python3}; TE_DIR=${TE_DIR:?set TE_DIR to a te-v9@be24fb6c checkout}
OUT=${OUT:-$ROOT/tmp/studyend_repro}; mkdir -p "$OUT"
build() { local name=$1; shift
  env $(cat experiments/cvx/sota_20260927_couch_flags.env) DRSTUDY=1 DRSTUDY2P=1 DRSTUDY2P_INV=1 DRSTUDYCOUNTS=1 TE_FOOTER=0 \
      DRSTUDY_Y=0x98 DRNMITMP=1 DRREACHTX=1 DRTAPP=2 DRSPAWNEDGE=1 "$@" TE_DIR="$TE_DIR" \
      $PY "$TE_DIR/build_copro_branded_env.py" drmario_v28cs.nes "$OUT/$name.nes" > "$OUT/$name.log" 2>&1; }
build control
build studyend DRSTUDYEND=1
ok=1
chk() { got=$(md5sum < "$1" | cut -c1-32); [ "$got" = "$2" ] && echo "PASS $3 $got" || { echo "FAIL $3 got $got want $2"; ok=0; }; }
chk "$OUT/control.nes" c960dd499e877f01c483af1347ed8df6 "control (== staged DIST60 couch cart)"
chk "$OUT/studyend.nes" 8c6e419631ee80612379e8f5f0259d62 "DRSTUDYEND couch cart"
$PY tests/test_studyend.py || ok=0
[ $ok = 1 ] && echo "STUDYEND_REPRODUCE_PASS" || { echo "STUDYEND_REPRODUCE_FAIL"; exit 1; }
