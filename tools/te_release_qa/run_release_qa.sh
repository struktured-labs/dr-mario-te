#!/usr/bin/env bash
# The full Mesen QA matrix for a standalone TE release, then the PASS/FAIL summary.
#   usage: tools/te_release_qa/run_release_qa.sh <v10.nes> <published-v9.nes> <base.nes>
# Every run is a real game driven from Lua on both controllers (see te_release_qa.lua); runs are
# sequential (one Mesen at a time), nice 19. ~25 minutes on this box.
# Writes tmp/te_release_qa/out/<run>/ and tmp/te_release_qa/SUMMARY.md (+ summary.json).
set -euo pipefail
V10=${1:?usage: run_release_qa.sh <v10.nes> <v9.nes> <base.nes>}; V9=${2:?}; BASE=${3:?}
R=$(cd "$(dirname "$0")/../.." && pwd)
Q=$R/tools/te_release_qa
PY=${PY:-python3}
W=$R/tmp/te_release_qa
rm -rf "$W/out"; mkdir -p "$W/out" "$W/roms"
# the same v10 bytes behind the No-Intro NES 2.0 header (mapper 1, submapper 5) -- what users with a
# No-Intro dump get from the IPS
"$PY" - "$V10" "$W/roms/v10_nointro_header.nes" <<'PY'
import sys
b = open(sys.argv[1], "rb").read()
open(sys.argv[2], "wb").write(bytes.fromhex("4e45531a020410085000000000000001") + b[16:])
PY
run() { "$Q/run_qa.sh" "$@" | tail -1; }
run "$V10" v10_shots   shots zeros 3
run "$V9"  v9d_shots   shots zeros 3
run "$V10" v10_twop    twop  zeros 1
run "$V9"  v9d_twop    twop  zeros 1
run "$V10" v10_onep    onep  zeros 1
run "$V9"  v9d_onep    onep  zeros 1
QA_PAUSE=0 run "$V10"  v10_onep_np  onep zeros 1
QA_PAUSE=0 run "$V9"   v9d_onep_np  onep zeros 1
QA_PAUSE=0 run "$BASE" base_onep_np onep zeros 1
run "$W/roms/v10_nointro_header.nes" v10ni_twop twop zeros 1
run "$W/roms/v10_nointro_header.nes" v10ni_onep onep zeros 1
run "$V10" v10_twop_rndram twop random 5
run "$V10" v10_cpuidle  cpuidle zeros 1
run "$V9"  v9d_cpuidle  cpuidle zeros 1
run "$V10" v10_clearwin clearwin zeros 1
run "$V9"  v9d_clearwin clearwin zeros 1
QA_SOAK_FRAMES=40000 run "$V10" v10_soak_zero   soak zeros 7
QA_SOAK_FRAMES=40000 run "$V10" v10_soak_rndram soak random 11
"$PY" "$Q/summarize_qa.py" "$W/out" "$W/SUMMARY.md" "$W/summary.json"
