#!/bin/bash
# run_d135probe.sh <probe.lua> <arm fix|leak> <frames> -- one arm of the #135 adoption gate.
#
# Runs the ACTUAL patched probe out of THIS worktree (not pockettuck-wt: run_framedense.sh and
# friends hardcode a sibling tree, which is the #118/#127 literal hazard and would have gated a
# file I did not patch), and reads back the guard's own census.
#
# Launch discipline copied from run_framedense.sh / run_d131gate.sh -- all six failure modes in
# dr-mario-mesen-launch-verification: headless -testrunner (no mutex, no Xvfb), per-arm TMPDIR +
# XDG_CONFIG_HOME + output dir, census file deleted before launch and required to reappear
# NEWER than the launch, exact-pid reap, never a name-pattern kill.
set -euo pipefail

# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
SRC=/home/struktured/projects/dr-mario-pockettuck-wt      # cart + remap_mapper.py only
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
CART="$SRC/roms/drmario_tuck_cvc_mister.nes"
CART_MD5=9fefaedba9a27ba10f058ac239eeb77d
W=0x5200          # DRPOCKET=0 => P2's window is $5200.  $5000 would be OPEN BUS = silent inert.

probe="${1:?probe.lua}"; arm="${2:?fix|leak}"; maxf="${3:?frames}"; seed="${D135_SEED:-114}"
tag="d135_${probe%.lua}_${arm}_${maxf}_s${seed}"

[[ -f "$D/tools/gate/$probe" ]] || { echo "no such probe: $D/tools/gate/$probe" >&2; exit 2; }
# HASH THE CART THAT BOOTS -- filename is not provenance (dr-mario-watchdog-mgl-silent-cart-fallback).
got=$(md5sum "$CART" | cut -d' ' -f1)
[[ "$got" == "$CART_MD5" ]] || { echo "CART MD5 MISMATCH: $got != $CART_MD5" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

# SEAT CHECK: match the Mesen BINARY, never the lua filename -- this script's own command line
# carries the probe name and would match itself (harness-pgrep-self-match).  Zombies excluded.
if ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
     | command grep -av '^Z' >/dev/null; then
  echo "a Mesen is already alive -- refusing to run two arms concurrently" >&2; exit 3
fi

out="$D/tmp/d135/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; census="$out/d135_census.txt"
rm -f "$census" "$out/stdout.log"
"$PY" "$SRC/tools/gate/remap_mapper.py" "$CART" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] probe=$probe arm=$arm frames=$maxf cart_md5=$got"

deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$census"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export D135_OUT="$out"
    [[ "$arm" == "leak" ]] && export D135_LEAK=1 || true
    # every probe in the family reads its own prefix; set them all rather than branching.
    export FD_OUT="$out" FD_TAG="$tag" FD_ARM=A FD_W="$W" FD_MAXF="$maxf" FD_SEED="$seed" \
           FD_DLAT=34 FD_ANYTIME=0 FD_TFIND=synth FD_ORIENT=-1 \
           SC_OUT="$out" SC_MAXF="$maxf" SC_SEED="$seed" SC_DLAT=12 SC_SHOTS=0 \
           FP_OUT="$out" FP_TAG="$tag" FP_MAXF="$maxf" FP_SEED="$seed" FP_DLAT=34 FP_P1DRIVE=1 \
           D1_OUT="$out" D1_TAG="$tag" D1_W="$W" D1_MAXF="$maxf" D1_SEED="$seed"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/$probe" -testrunner "-timeout=$deadline"
  ) >"$out/stdout.log" 2>&1 &
  runpid=$!

  # run to completion (the census is written continuously; we want the FINAL counts)
  waited=0
  while kill -0 "$runpid" 2>/dev/null && (( waited < deadline )); do sleep 5; waited=$((waited+5)); done
  kill "$runpid" 2>/dev/null || true
  wait "$runpid" 2>/dev/null || true

  if [[ -f "$census" ]]; then
    mt=$(stat -c %Y "$census")
    if (( mt < launched )); then echo "[$tag] STALE CENSUS" >&2; exit 4; fi
    echo "[$tag] OK on try $try: $(cat "$census")"
    exit 0
  fi
  echo "[$tag] try $try produced NO census file; retrying" >&2
  sleep 5
done
# No census means the probe never loaded (dead Mesen, stale mutex, rc=134).  That is a FAILURE,
# never "no leak seen" -- absence is not a pass.
echo "[$tag] FAILED: no census after 3 tries" >&2
exit 1
