#!/bin/bash
# run_stomp.sh <tag> <cart> <maxframes> <selftest 0|1> [keepalive] [seed]
# OAM-leak census (task #46) on an arbitrary cart, via Mesen's headless test runner --
# no Xvfb (which dies after one launch in this sandbox) and no single-instance pipe.
# SELFTEST=1 injects digit sprites on a non-play frame: the detector MUST report GARBLE,
# which is what proves a zero-leak result on the fixed cart is real and not a dead probe.
set -euo pipefail

D="$(cd "$(dirname "$0")/../.." && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
LUA="$D/tmp/task46/stomp_census3.lua"

tag="${1:?tag}"; cart="${2:?cart}"; maxf="${3:?frames}"; selftest="${4:?0-or-1}"
keep="${5:-0}"; seed="${6:-1}"

[[ -f "$cart" ]] || { echo "missing cart: $cart" >&2; exit 2; }
[[ -f "$LUA"  ]] || { echo "missing lua: $LUA" >&2; exit 2; }

out="$D/tmp/stomp/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"
log="$out/run.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart md5 $(md5sum "$cart" | cut -d' ' -f1)  selftest=$selftest"

for _ in $(seq 1 600); do
  ps -eo args | command grep -a "$MESEN" | command grep -av grep >/dev/null || break
  sleep 2
done

deadline=$(( maxf / 25 + 240 ))
for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export DOTNET_GCHeapHardLimit=40000000
    export SC_OUT="$out" SC_MAXF="$maxf" SC_KEEPALIVE="$keep" SC_PC=0
    export SC_SEED="$seed" SC_RLAT=2 SC_DLAT=12 SC_SHOTS=1 SC_SELFTEST="$selftest"
    exec "$RUN_MESEN" "$mmc1" "$LUA" -testrunner "-timeout=$deadline"
  ) >"$out/stdout.log" 2>&1 &
  runpid=$!

  ok=0
  for _ in $(seq 1 $((deadline / 2))); do
    if command grep -aq "^SUMMARY" "$log" 2>/dev/null; then ok=1; break; fi
    if ! kill -0 "$runpid" 2>/dev/null; then
      sleep 3; command grep -aq "^SUMMARY" "$log" 2>/dev/null && ok=1
      break
    fi
    sleep 2
  done
  kill "$runpid" 2>/dev/null || true
  wait "$runpid" 2>/dev/null || true
  if [[ "$ok" == 1 ]]; then
    echo "[$tag] OK on try $try"
    command grep -a "^SUMMARY" "$log"
    echo "[$tag] GARBLE events: $(command grep -ac '^GARBLE' "$log" || true)"
    command grep -a '^GARBLE' "$log" | head -5
    exit 0
  fi
  echo "[$tag] try $try produced no SUMMARY; retrying" >&2
  sleep 5
done
echo "[$tag] FAILED after 3 tries" >&2
exit 4
