#!/bin/bash
# build_hardened.sh <tag> [extra DRFLAG=VAL ...]
#
# HARDENED cart family (branch hardened-129-133-134) = the shipped CvC tuck configuration
# (roms/manifests/tuck-cvc-mister.json, output 9fefaedb -- the cart on the live MiSTer soak)
# plus the four owner-approved hardening deltas:
#   DRVERFIX=1     #129: bound checkVerMatch's vertical scan (3-byte stock fix)
#   DRUNPAUSE=1    #133: stock START semantics for P1 (a paused match is exitable)
#   DRSTARTGUARD=1 #134: guard the driver's START injection sites off match/transit frames
#   DRROTDIR=1     #114 v3 GO: shortest-direction rotation (-1.976 f/pill)
# DRPRESTART stays 0 (pending #136). DRBUILDID pinned 0 (stamp never moves under a comparison).
#
# Flags come verbatim from tuck-cvc-mister.json's flag_snapshot (ONE source of truth), then the
# hardened deltas, then caller overrides -- so gate arms are built by OVERRIDING single flags,
# e.g.:  tools/build_hardened.sh hardened-c1-verfix DRUNPAUSE=0 DRSTARTGUARD=0 DRROTDIR=0
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${1:?usage: build_hardened.sh <tag> [DRFLAG=VAL ...]}"; shift || true
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python

eval "$($PY - <<'EOF'
import json
f = json.load(open("roms/manifests/tuck-cvc-mister.json"))["flag_snapshot"]
f["DRVERFIX"] = "1"       # #129
f["DRUNPAUSE"] = "1"      # #133
f["DRSTARTGUARD"] = "1"   # #134
f["DRROTDIR"] = "1"       # #114 v3 GO
f["DRPRESTART"] = "0"     # explicit: pending #136, owner gate
f["DRBUILDID"] = "0"      # pinned
for k, v in sorted(f.items()):
    print(f"export {k}={v!r}")
EOF
)"
for kv in "$@"; do export "${kv?}"; done

echo "--- hardened build: tag=$TAG ---"
env | command grep -a '^DR' | sort | sed 's/^/    /'
$PY tools/romgen.py build --out "roms/${TAG}.nes" --base drmario_v28cs.nes --tag "$TAG"
md5sum "roms/${TAG}.nes"
