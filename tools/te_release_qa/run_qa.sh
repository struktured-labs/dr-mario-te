#!/usr/bin/env bash
# Headless Mesen QA for the standalone TE release (te_release_qa.lua).
#   usage: tools/te_release_qa/run_qa.sh <rom.nes> <tag> <title|onep|twop|soak> [zeros|random] [seed]
# Outputs: tmp/te_release_qa/out/<tag>/ (qa.log, frames.txt, *.png, dump_*.txt)
#
# Isolation (other agents share this box and the dr-mario-mods Mesen build):
#   * a PRIVATE portable copy of the Mesen build under tmp/te_release_qa/mesen/ -- its own settings.json,
#     so the shared Release/settings.json is never touched (RamPowerOnState is set per run here);
#   * --testrunner mode: no window, no X display, and it never reaches the single-instance pipe;
#   * flock: one QA Mesen at a time from this tree; nice 19; hard timeout.
# The settings file is derived from the source build's by a targeted text edit, because Mesen silently
# falls back to defaults (io/os disabled in Lua) when it cannot deserialize a re-serialized settings.json.
set -euo pipefail
ROM=${1:?usage: run_qa.sh <rom.nes> <tag> <scenario> [zeros|random] [seed]}; TAG=${2:?tag}; SCEN=${3:?scenario}
RAM=${4:-zeros}; SEED=${5:-1}
R=$(cd "$(dirname "$0")/../.." && pwd)
SRC=${MESEN_SRC:-/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release}
PY=${PY:-python3}
W=$R/tmp/te_release_qa; M=$W/mesen; OUT=$W/out/$TAG/
mkdir -p "$M" "$OUT"
if [ ! -x "$M/Mesen" ]; then
  for f in "$SRC"/*; do
    case "$(basename "$f")" in
      Debugger|RecentGames|SaveStates|Saves|Screenshots|Cheats|HdPacks|Satellaview|GameConfig|settings.json*|*.nes|*.png|*.csv|*.txt) ;;
      *) cp -a "$f" "$M/" ;;
    esac
  done
  cp -a "$SRC/MesenNesDB.txt" "$M/" 2>/dev/null || true
fi
"$PY" - "$SRC/settings.json" "$M/settings.json" "$RAM" <<'PY'
import json, re, sys
src, dst, ram = sys.argv[1], sys.argv[2], sys.argv[3]
state = {"zeros": "AllZeros", "random": "Random", "ones": "AllOnes"}[ram]
t = open(src, "rb").read().decode("utf-8")
t = re.sub(r'"SingleInstance":\s*true', '"SingleInstance": false', t)
i = t.index('"Nes": {'); j = t.index('"RamPowerOnState"', i); k = t.index("\n", j)
t = t[:j] + re.sub(r'"(AllZeros|Random|AllOnes)"', f'"{state}"', t[j:k]) + t[k:]
d = json.loads(t.lstrip("﻿"))
assert d["Nes"]["RamPowerOnState"] == state and d["Debug"]["ScriptWindow"]["AllowIoOsAccess"] is True
open(dst, "wb").write(t.encode("utf-8"))
PY
rm -f "$OUT"/*.png "$OUT"/dump_*.txt "$OUT"/qa.log "$OUT"/frames.txt
exec 9>"$W/.lock"
flock -w 900 9 || { echo "another QA Mesen holds $W/.lock"; exit 9; }
set +e
nice -n 19 timeout 1500 env QA_OUT="$OUT" QA_SCEN="$SCEN" QA_SEED="$SEED" QA_SOAK_FRAMES="${QA_SOAK_FRAMES:-40000}" \
  QA_PAUSE="${QA_PAUSE:-1}" PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet" \
  "$M/Mesen" --testrunner --timeout=1400 "$(readlink -f "$ROM")" "$R/tools/te_release_qa/te_release_qa.lua" \
  > "$OUT/stdout.txt" 2>&1
rc=$?
set -e
echo "mesen exit $rc  ($TAG $SCEN ram=$RAM seed=$SEED rom md5 $(md5sum < "$ROM" | cut -c1-32))" | tee "$OUT/exit.txt"
grep -a -E "^(FREEZE|SCRIPT_ERROR|STATS|DONE|NAV_TIMEOUT|WAIT_TIMEOUT|ROUND_TIMEOUT)" "$OUT/qa.log" || true
exit $rc
