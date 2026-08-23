#!/bin/bash
# build_human.sh <tag> [extra DRFLAG=VAL ...]
#
# HUMAN-CHALLENGE cart (#148): the person plays P1 on a real pad, the certified copro AI plays P2.
#
# ONE SOURCE OF TRUTH for the flags: roms/manifests/combo-hardened-pp3sl-20260820.json's
# flag_snapshot -- the #140 CERTIFIED next-generation hardened-class cart (md5 2b806db8),
# which already carries DRVERFIX(#129) + DRUNPAUSE(#133) + DRSTARTGUARD(#134) + DRROTDIR(#114)
# + DRPRESPIPE Q=3 (#126 enforcement 2) + DRPRESTART. We then apply the HUMAN deltas:
#
#   DRHUMAN=1     P1 = human passthrough: no copro search for P1, no $F5/$F7 injection,
#                 no P1 gravity pin.
#   DRP1NATIVE=0  FORCED. The emitter asserts `DRP1NATIVE=1 with DRHUMAN=1 is refused`
#                 (P1 is a person; the cart must not drive them). The combo class carries
#                 DRP1NATIVE=1, so this delta is mandatory, not cosmetic.
#   DRP1SLICE=0   FORCED, TRANSITIVELY. `DRP1SLICE=1 without DRP1NATIVE=1 is refused`.
#                 => DRP1SLICE IS NOT REPRESENTABLE ON A HUMAN CART. It slices the P1 NATIVE
#                 SEARCH; a human cart has no P1 search to slice. Consequently #140's PP_RAN
#                 interlock (the pp-phase/slice-tick collision guard) has no second machine to
#                 guard against on this image -- the collision config cannot arise here.
#   DRBUILDID=0   pinned per owner directive (the emitter would DEFAULT it to 1 on a human cart).
#
# Flags that are SET in the snapshot but that the emitter STRUCTURALLY NEUTRALISES under
# DRHUMAN=1 -- kept at their certified values so the recipe stays a pure superset, and
# recorded here so nobody reads them as live behaviour:
#   DRUNPAUSE=1   `if UNPAUSE and not HUMAN_P1` -- not emitted. Not needed: #133's hazard was
#                 the P1 EXECUTOR rewriting $F5 every hook. On a human cart nothing writes $F5,
#                 so START keeps stock pause/unpause semantics BY CONSTRUCTION.
#   DRNAVESC=1    `if NAVESC and not HUMAN_P1` -- not emitted (a human's pause would read as
#                 "stuck" and the watchdog would un-pause them).
#   DRP1WIGGLE=0  asserted-off against DRHUMAN anyway.
# DRSTUDY is held at the snapshot's 0 (the emitter would default it to 1 on a human cart);
# holding it keeps this image a minimal delta from the certified 2b806db8.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${1:?usage: build_human.sh <tag> [DRFLAG=VAL ...]}"; shift || true
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python

eval "$($PY - <<'EOF'
import json
f = json.load(open("roms/manifests/combo-hardened-pp3sl-20260820.json"))["flag_snapshot"]
f["DRHUMAN"] = "1"
f["DRP1NATIVE"] = "0"
f["DRP1SLICE"] = "0"
f["DRBUILDID"] = "0"
f["DRBUILDID_TAG"] = "HUMN"
for k, v in sorted(f.items()):
    print(f"export {k}={v!r}")
EOF
)"
for kv in "$@"; do export "${kv?}"; done

echo "--- human build: tag=$TAG ---"
env | command grep -a '^DR' | sort | sed 's/^/    /'
$PY tools/romgen.py build --out "roms/${TAG}.nes" --base drmario_v28cs.nes --tag "$TAG"
md5sum "roms/${TAG}.nes"
