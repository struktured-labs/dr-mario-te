#!/bin/bash
# One headless Mesen run of a settle-lane probe (settle_probe.lua on a copro cart, base_gravity_probe.lua on a base ROM).
#   run_probe.sh <tag> <rom.nes> <probe.lua> [maxframes]      (extra env passes through: ST_*, BS_*)
# A mapper-100 copro cart is header-remapped to MMC1 first; a mapper-1 ROM is used as is.
# Seat discipline (tools/lateflip/run_lateflip.sh): waits while ANY Mesen runs (another lane may own the single seat),
# never kills a Mesen it did not start; private TMPDIR / XDG config, Mesen's test runner (no GUI, no instance pipe).
set -euo pipefail
D="$(cd "$(dirname "$0")/../.." && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
tag="${1:?tag}"; rom="$(realpath "${2:?rom}")"; probe="$(realpath "${3:?probe}")"; maxf="${4:-60000}"
out="$D/tmp/settle/$tag"; mkdir -p "$out"
rt="$out/runtime-tmp"; rm -rf -- "$rt"; mkdir -p "$rt/xdg/Mesen2"; cp "$SANDBOX" "$rt/xdg/Mesen2/settings.json"
rm -f "$out"/settle_*.log "$out"/base_*.log "$out/stdout.log"
mapper=$("$PY" -c "import sys; r=open(sys.argv[1],'rb').read(16); print((r[7]&0xF0)|(r[6]>>4))" "$rom")
if [[ "$mapper" == 100 ]]; then
  run_rom="$out/${tag}_mmc1.nes"; "$PY" "$D/tools/gate/remap_mapper.py" "$rom" "$run_rom" >"$out/remap.log" 2>&1
else
  run_rom="$rom"
fi
echo "[$tag] rom md5 $(md5sum "$rom" | cut -d' ' -f1) mapper $mapper  run md5 $(md5sum "$run_rom" | cut -d' ' -f1)  probe $(basename "$probe")"
for _ in $(seq 1 3600); do pgrep -x Mesen >/dev/null || break; sleep 2; done
pgrep -x Mesen >/dev/null && { echo "[$tag] Mesen seat busy after 2 h" >&2; exit 3; }
deadline=$(( maxf / 10 + 900 ))
(
  cd "$(dirname "$MESEN")"
  export TMPDIR="$rt" XDG_CONFIG_HOME="$rt/xdg" DOTNET_GCHeapHardLimit=60000000
  export ST_OUT="$out/" ST_TAG="$tag" ST_MAXF="$maxf" BS_OUT="$out/" BS_TAG="$tag" BS_MAXF="$maxf"
  exec nice -n 19 "$RUN_MESEN" "$run_rom" "$probe" -testrunner "-timeout=$deadline"
) >"$out/stdout.log" 2>&1 &
runpid=$!
ok=0
for _ in $(seq 1 $((deadline / 2))); do
  if command grep -aqs "^SUMMARY tag=$tag" "$out"/settle_*.log "$out"/base_*.log 2>/dev/null; then ok=1; break; fi
  kill -0 "$runpid" 2>/dev/null || { sleep 2; command grep -aqs "^SUMMARY tag=$tag" "$out"/settle_*.log "$out"/base_*.log 2>/dev/null && ok=1; break; }
  sleep 2
done
sleep 1; kill "$runpid" 2>/dev/null || true; wait "$runpid" 2>/dev/null || true
if [[ "$ok" == 1 ]]; then command grep -ah "^SUMMARY" "$out"/settle_*.log "$out"/base_*.log 2>/dev/null; exit 0; fi
echo "[$tag] no SUMMARY (see $out/stdout.log)" >&2; tail -5 "$out"/settle_*.log "$out"/base_*.log "$out/stdout.log" 2>/dev/null >&2; exit 4
