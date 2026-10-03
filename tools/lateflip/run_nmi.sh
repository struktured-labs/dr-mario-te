#!/bin/bash
# One headless Mesen run of an NMI-census probe (lateflip_nmi.lua or cvc_nmi.lua) on one cart.
#   run_nmi.sh <tag> <cart.nes> <probe.lua> <ir.json> [maxframes]      (extra env passes through: LF_CASES, LN_POKE_*)
# Seat discipline copied from run_lateflip.sh: waits while ANY Mesen runs, never kills one it did not start.
set -euo pipefail
D="$(cd "$(dirname "$0")/../.." && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
tag="${1:?tag}"; cart="$(realpath "${2:?cart}")"; probe="$(realpath "${3:?probe}")"; ir="$(realpath "${4:?ir}")"
maxf="${5:-60000}"
out="$D/tmp/lateflip_nmi/$tag"; mkdir -p "$out"
rt="$out/runtime-tmp"; rm -rf -- "$rt"; mkdir -p "$rt/xdg/Mesen2"; cp "$SANDBOX" "$rt/xdg/Mesen2/settings.json"
mmc1="$out/${tag}_mmc1.nes"; log="$out/nmi_${tag}.log"; rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/lateflip/nmi_addrs.py" "$ir" "$cart" "$out/addrs.lua"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart md5 $(md5sum "$cart" | cut -d' ' -f1)  probe $(basename "$probe")"
for _ in $(seq 1 1800); do pgrep -x Mesen >/dev/null || break; sleep 2; done
pgrep -x Mesen >/dev/null && { echo "[$tag] Mesen seat busy after 1 h" >&2; exit 3; }
deadline=$(( maxf / 15 + 600 ))
(
  cd "$(dirname "$MESEN")"
  export TMPDIR="$rt" XDG_CONFIG_HOME="$rt/xdg" DOTNET_GCHeapHardLimit=40000000
  export LN_DIR="$D/tools/lateflip" LN_OUT="$out/" LN_TAG="$tag" LN_ADDRS="$out/addrs.lua" LN_MAXF="$maxf"
  export LF_OUT="$out/" LF_TAG="$tag" LF_MAXF="$maxf"
  exec nice -n 19 "$RUN_MESEN" "$mmc1" "$probe" -testrunner "-timeout=$deadline"
) >"$out/stdout.log" 2>&1 &
runpid=$!
for _ in $(seq 1 $((deadline / 2))); do
  command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null && break
  kill -0 "$runpid" 2>/dev/null || break
  sleep 2
done
sleep 1; kill "$runpid" 2>/dev/null || true; wait "$runpid" 2>/dev/null || true
command grep -a "^SUMMARY\|^CVC\|^REFUTE\|^NESTED" "$log" || { echo "[$tag] no SUMMARY (see $out/stdout.log)" >&2; tail -3 "$log" >&2; exit 4; }
