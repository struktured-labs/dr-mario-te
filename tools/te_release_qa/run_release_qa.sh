#!/usr/bin/env bash
# The full Mesen QA matrix for a standalone TE release, then the PASS/FAIL summary.
#   usage: tools/te_release_qa/run_release_qa.sh <v11.nes> <v10.nes> <published-v9.nes> <base.nes>
# (v10's own matrix: branch claude/rhdn-release.) Every run is a real game driven from Lua on both
# controllers (see te_release_qa.lua); runs are sequential (one Mesen at a time), nice 19.
# Shared box: between runs it waits while $PAUSE_FILE (default dr_mario_rl/tmp/te1p/PAUSE) or the
# shared dr_mario_rl/tmp/PAUSE_ALL exists. A run is never stopped mid-way (run_qa.sh has wall-clock
# timeouts that a SIGSTOP would trip); one run is at most a few minutes.
# Writes tmp/te_release_qa/out/<run>/ and tmp/te_release_qa/SUMMARY.md (+ summary.json).
set -euo pipefail
NEW=${1:?usage: run_release_qa.sh <v11.nes> <v10.nes> <v9.nes> <base.nes>}; PREV=${2:?}; V9=${3:?}; BASE=${4:?}
R=$(cd "$(dirname "$0")/../.." && pwd)
Q=$R/tools/te_release_qa
PY=${PY:-python3}
W=$R/tmp/te_release_qa
PAUSE_FILE=${PAUSE_FILE:-/home/struktured/projects/dr_mario_rl/tmp/te1p/PAUSE}
PAUSE_ALL=${PAUSE_ALL:-/home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL}
rm -rf "$W/out"; mkdir -p "$W/out" "$W/roms"
# the same v11 bytes behind the No-Intro NES 2.0 header (mapper 1, submapper 5) -- what users with a
# No-Intro dump get from the IPS
"$PY" - "$NEW" "$W/roms/v11_nointro_header.nes" <<'PY'
import sys
b = open(sys.argv[1], "rb").read()
open(sys.argv[2], "wb").write(bytes.fromhex("4e45531a020410085000000000000001") + b[16:])
PY
run() {
  while [ -e "$PAUSE_FILE" ] || [ -e "$PAUSE_ALL" ]; do echo "paused ($PAUSE_FILE / $PAUSE_ALL)"; sleep 30; done
  "$Q/run_qa.sh" "$@" | tail -1
}
NI=$W/roms/v11_nointro_header.nes
run "$NEW"  v11_shots       shots    zeros  3
run "$NEW"  v11_go1p        go1p     zeros  1
run "$PREV" v10_go1p        go1p     zeros  1
run "$NEW"  v11_go1p_rndram go1p     random 9
run "$NEW"  v11_clear1p     clear1p  zeros  1
run "$PREV" v10_clear1p     clear1p  zeros  1
run "$NEW"  v11_onep        onep     zeros  1
run "$PREV" v10_onep        onep     zeros  1
QA_PAUSE=0 run "$NEW"  v11_onep_np  onep zeros 1
QA_PAUSE=0 run "$PREV" v10_onep_np  onep zeros 1
QA_PAUSE=0 run "$BASE" base_onep_np onep zeros 1
run "$NEW"  v11_twop        twop     zeros  1
run "$PREV" v10_twop        twop     zeros  1
run "$V9"   v9d_twop        twop     zeros  1
run "$NEW"  v11_twop_rndram twop     random 5
run "$NEW"  v11_cpuidle     cpuidle  zeros  1
run "$PREV" v10_cpuidle     cpuidle  zeros  1
run "$NEW"  v11_clearwin    clearwin zeros  1
run "$PREV" v10_clearwin    clearwin zeros  1
run "$NI"   v11ni_twop      twop     zeros  1
run "$NI"   v11ni_go1p      go1p     zeros  1
QA_SOAK_FRAMES=40000 run "$NEW" v11_soak_zero   soak zeros  7
QA_SOAK_FRAMES=40000 run "$NEW" v11_soak_rndram soak random 11
"$PY" "$Q/summarize_qa.py" "$W/out" "$W/SUMMARY.md" "$W/summary.json"
