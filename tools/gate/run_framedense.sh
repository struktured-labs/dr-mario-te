#!/bin/bash
# run_framedense.sh <arm A|B|C> <frames> [tfind geom|synth] -- ONE arm of PREREG_FRAMEDENSE.
#
# Launch discipline (dr-mario-mesen-launch-verification, all six failure modes):
#   * headless -testrunner: returns from Program.Main BEFORE SingleInstance is constructed,
#     so no named mutex, no pipe, no Xvfb (and no "Xvfb degrades after one launch").
#   * own TMPDIR + XDG_CONFIG_HOME per arm so native-dependency extraction cannot collide.
#   * own OUTPUT DIR per arm -- two arms sharing one directory produced NO LOG AT ALL.
#   * log deleted BEFORE launch, then required to reappear carrying THIS arm's tag AND
#     THIS launch's start time (tag identifies an arm, not a run).
#   * poll for SUMMARY and reap the EXACT pid (never a name pattern: the runner's own
#     command line carries the cart path and would match itself).
# The prereg forbids running two arms of this gate concurrently -- this script is
# sequential by construction and refuses to start if another framedense arm is alive.
set -euo pipefail

# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
CART="$D/roms/drmario_tuck_cvc_mister.nes"
CART_MD5=9fefaedba9a27ba10f058ac239eeb77d
W=0x5200          # DRPOCKET=0 => P2's window is $5200. $5000 would be OPEN BUS = silent inert.

arm="${1:?arm A|B|C}"; maxf="${2:?frames}"; tfind="${3:-synth}"
tag="fd${arm}_${maxf}_${tfind}${FD_ORIENT:+_o$FD_ORIENT}${FD_DLAT:+_d$FD_DLAT}${FD_ANYTIME:+_at}"

# HASH THE CART THAT BOOTS -- filename is not provenance.
got=$(md5sum "$CART" | cut -d' ' -f1)
[[ "$got" == "$CART_MD5" ]] || { echo "CART MD5 MISMATCH: $got != $CART_MD5" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

# SEAT CHECK. Match the Mesen BINARY, not the lua filename: an earlier version grepped for
# 'probe_framedense.lua' and matched the CALLING SHELL, whose command line happened to carry
# that string from an unrelated fmtcheck invocation -- harness-pgrep-self-match, live.
if ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null; then
  echo "a Mesen is already alive -- refusing to run two arms concurrently" >&2; exit 3
fi

out="$D/tmp/framedense/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/framedense.log"
rm -f "$log" "$out/stdout.log" "$out/hooks.csv"
"$PY" "$D/tools/gate/remap_mapper.py" "$CART" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] arm=$arm frames=$maxf w=$W tfind=$tfind cart_md5=$got mmc1_md5=$(md5sum "$mmc1" | cut -d' ' -f1)"

# measured ~0.04 s/frame for this probe family; generous so a fixed ceiling can never
# truncate a run into a SUMMARY-less log (which is UNREPORTED, not zero).
deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export FD_OUT="$out" FD_TAG="$tag" FD_ARM="$arm" FD_W="$W" FD_MAXF="$maxf" \
           FD_DLAT="${FD_DLAT:-34}" FD_ANYTIME="${FD_ANYTIME:-0}" FD_SEED=114 FD_TFIND="$tfind" FD_ORIENT="${FD_ORIENT:--1}"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_framedense.lua" -testrunner "-timeout=$deadline"
  ) >"$out/stdout.log" 2>&1 &
  runpid=$!

  ok=0
  for _ in $(seq 1 $((deadline / 2))); do
    if command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null; then ok=1; break; fi
    if ! kill -0 "$runpid" 2>/dev/null; then
      sleep 3
      command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null && ok=1
      break
    fi
    sleep 5
  done
  kill "$runpid" 2>/dev/null || true
  wait "$runpid" 2>/dev/null || true

  if [[ "$ok" == 1 ]]; then
    # freshness: the log must have been created AFTER this launch (a tag cannot tell
    # two runs of one arm apart -- that hole cost a whole mechanism arm once).
    mt=$(stat -c %Y "$log")
    if (( mt < launched )); then echo "[$tag] STALE LOG (mtime $mt < launch $launched)" >&2; exit 4; fi
    echo "[$tag] OK on try $try"
    command grep -a "^SUMMARY" "$log"
    exit 0
  fi
  echo "[$tag] try $try produced no tagged SUMMARY; retrying" >&2
  sleep 5
done
echo "[$tag] FAILED after retries" >&2
exit 1
