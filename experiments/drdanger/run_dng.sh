#!/usr/bin/env bash
# run_dng.sh TAG HEX LINES FIRST LAST [J] -> tmp/drdanger/vd/TAG/out/<idx>.txt (one vsim_dng reply per board line)
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; tag=$1; hex=$2; lines=$3; a=$4; b=$5; j=${6:-10}
D="$R/tmp/drdanger/vd/$tag"; mkdir -p "$D/out"; cp "$hex" "$D/copro_rom.hex"
export D lines VS="$R/tmp/drdanger/obj_dng/vsim_dng"
seq "$a" "$b" | xargs -P "$j" -I{} bash -c '[ -s "$D/out/{}.txt" ] || { r=$(sed -n "{}p" "$lines" | (cd "$D" && nice -n 19 "$VS" 64)) && echo "$r" > "$D/out/{}.txt"; }'
echo "$tag done $(date -Is)"
