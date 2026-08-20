#!/bin/bash
# stage_bundle.sh — assemble the new-box SD bundle at out/newmister_bundle/,
# verifying every artifact md5 against the registered values. $0, no network.
# The OWNER copies the result to the new box's SD (or we scp it once the IP
# exists). KEEP-VERSIONS naming: every file carries its identity in its name;
# nothing on the SD is ever overwritten in place.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
V8=~/projects/dr-mario-v8-wt
KIT=$V8/tmp/mister_dayone_kit
WINNER=~/projects/NES_MiSTer-winner
B="$HERE/out/newmister_bundle"
mkdir -p "$B/_Console" "$B/games/NES"

want() { # $1 src, $2 md5, $3 dst
  got=$(md5sum "$1" | cut -d' ' -f1)
  [ "$got" = "$2" ] || { echo "FATAL: $1 md5 $got != $2"; exit 2; }
  cp "$1" "$3"
}

# cores
want "$KIT/NES_theta400_20260809.rbf" de7dea35a9fa03a622cccc8068bd935e \
     "$B/_Console/NES_theta400_20260809.rbf"
# DBLCANON core: staged for later activation, no MGL references it yet
want "$WINNER/output_files/NES.rbf" 974de3ed0464edf666b45768007e7be6 \
     "$B/_Console/NES_theta400dblcanon_20260819.rbf"

# sileval A/B carts
want "$V8/roms/hardened-ctrl-ship-20260819.nes" 9fefaedba9a27ba10f058ac239eeb77d \
     "$B/games/NES/drmario_tcvc_ship_9fefaedb.nes"
want "$V8/roms/tcvc-p1slice.nes" 010f4ffe350df3b57561f8ce3bc4320b \
     "$B/games/NES/drmario_tcvc_p1slice_010f4ffe.nes"

# hardened-cart shakedown carts
want "$V8/roms/hardened-all-20260819.nes" 70a857cc05f36d7d2e8300f233c8bd52 \
     "$B/games/NES/drmario_hardened_all_70a857cc.nes"
want "$V8/roms/hardened-prestart-20260820.nes" 4ac725cffe84c547b358e3700e6df04d \
     "$B/games/NES/drmario_hardened_prestart_4ac725cf.nes"

# loaders + box identity sentinel
cp "$HERE/mgl/sileval_ship.mgl" "$HERE/mgl/sileval_p1slice.mgl" "$B/"
printf 'sileval-new-box staged %s from sileval-139\n' "$(date -Is)" > "$B/SILEVAL_BOX_ID"

( cd "$B" && find . -type f ! -name MD5SUMS.txt | sort | xargs md5sum > MD5SUMS.txt )
echo "bundle staged at $B"
cat "$B/MD5SUMS.txt"
