#!/bin/bash
# Liveness witness for DRPRESPIPE, both arms. The CONTROL arm is the positive
# control in reverse: on a cart WITHOUT the flag, PP_PH is never written, so
# the witness must read ZERO there. A nonzero control would mean the probe is
# counting something else.
set -eo pipefail
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
FR="${FR:-9000}"

arm () {  # $1 cart  $2 tag
  local out="$D/tmp/psforce/$2"; mkdir -p "$out"
  local rt="$out/runtime-tmp"; rm -rf -- "$rt"; mkdir -p "$rt/xdg/Mesen2"
  cp "$SANDBOX" "$rt/xdg/Mesen2/settings.json"
  local mmc1="$out/$2_mmc1.nes"
  # ⚠ STALE-LOG TRAP: the wait loop greps for the SUMMARY tag, and a PREVIOUS
  # run's log satisfies that grep instantly -- the arm then "succeeds" without
  # Mesen having produced anything. Delete the log and require it to be newer
  # than launch (same discipline as run_probe6_hardened.sh).
  rm -f "$out/force.log"
  local launched; launched=$(date +%s)
  "$PY" "$D/tools/gate/remap_mapper.py" "$1" "$mmc1" >"$out/remap.log" 2>&1
  echo "[$2] cart=$(md5sum "$1" | cut -d' ' -f1)"
  ( cd "$(dirname "$MESEN")"
    export TMPDIR="$rt" XDG_CONFIG_HOME="$rt/xdg"
    export PS_OUT="$out" PS_TAG="$2" PS_MAXF="$FR"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_prespipe_force.lua" -testrunner "-timeout=$((FR/12+300))"
  ) >"$out/stdout.log" 2>&1 &
  local pid=$!
  for _ in $(seq 1 $((FR/12+300))); do
    command grep -aq "SUMMARY tag=$2" "$out/force.log" 2>/dev/null && break
    kill -0 "$pid" 2>/dev/null || break
    sleep 5
  done
  kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true
  [[ -f "$out/force.log" ]] || { echo "[$2] NO LOG -- FAILURE, not zero" >&2; return 1; }
  local mt; mt=$(stat -c %Y "$out/force.log")
  (( mt >= launched )) || { echo "[$2] STALE LOG -- refusing to report it" >&2; return 4; }
  command grep -a "^SUMMARY" "$out/force.log" || { echo "[$2] NO SUMMARY -- FAILURE, not zero" >&2; return 1; }
}

# #148: arms are overridable so the SAME instrument can witness a HUMAN image.
#   run_prespipe_force.sh <control.nes> <flagon.nes> [tagsuffix]
# Default arms remain the CvC #138 pair, so existing invocations are unchanged.
CTRL="${1:-$D/roms/hardened-prestart-20260820.nes}"
FLAGON="${2:-$D/roms/prespipe-hardened-q3.nes}"
SUF="${3:-}"
arm "$CTRL" "control$SUF"
arm "$FLAGON" "flagon$SUF"
