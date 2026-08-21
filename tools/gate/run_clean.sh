#!/bin/bash
# run_clean.sh <lua> <envprefix> <maxf> <tag>=<cart.nes> [<tag>=<cart.nes> ...]
#
# ⚠ WHY THIS EXISTS. Mesen2 is single-instance via a .NET named MUTEX
# (/tmp/.dotnet/shm/global/<guid>) plus a named pipe (/tmp/CoreFxPipe_<guid>). A crashed or
# reaped instance leaves BOTH behind; the next launch then decides it is not the first
# instance and tries to forward its args, dying with "Pipe hasn't been connected yet" --
# sometimes producing NO log at all, and (observed) sometimes producing a log from a run that
# never really drove the cart. That silently corrupted a whole arm battery: d-mmc1only was
# recorded as copro GO=0 / wedged, and on a clean re-run it plays perfectly (GO=9, full round
# cycle). NEVER trust an arm whose log is missing or whose tag does not match.
#
# So: before every single launch, with NO Mesen running, clear both stale artifacts; after
# every launch, VERIFY the log exists and carries this arm's tag, and retry once if not.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
LUA="${1:?lua}"; PFX="${2:?env prefix, e.g. P4}"; MAXF="${3:?maxframes}"; shift 3
DISP=${GATE_DISP:-:181}
LOGNAME="$(basename "$LUA" .lua).log"

wait_seat() {
  for _ in $(seq 1 150); do
    ps -eo args | command grep -a "$MESEN" | command grep -av grep >/dev/null || return 0
    sleep 2
  done
  echo "[clean] ABORT: Mesen seat held by another lane"; return 1
}
clear_stale() {   # ONLY safe with no Mesen running -- caller must have waited
  rm -f /tmp/.dotnet/shm/global/* /tmp/CoreFxPipe_* 2>/dev/null || true
}
ensure_disp() {
  local n="${DISP#:}"
  [ -e "/tmp/.X11-unix/X$n" ] && return 0
  rm -f "/tmp/.X$n-lock"
  Xvfb "$DISP" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 &
  for _ in $(seq 1 15); do [ -e "/tmp/.X11-unix/X$n" ] && return 0; sleep 1; done
  echo "[clean] ABORT: Xvfb did not come up on $DISP"; return 1
}

ensure_disp || exit 2
for spec in "$@"; do
  tag="${spec%%=*}"; cart="${spec#*=}"
  out="$D/tmp/clean/$tag"; mkdir -p "$out"
  mmc1="$D/tmp/clean/${tag}_mmc1.nes"
  $PY "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >/dev/null
  for try in 1 2; do
    wait_seat || exit 3
    clear_stale
    echo "[clean] === $tag (try $try) ==="
    rm -f "$out/$LOGNAME"
    # NOTE: `${PFX}_OUT=val cmd` is NOT an assignment prefix in bash -- a word containing an
    # expansion before the `=` is parsed as a COMMAND, so it silently became
    # "P3_OUT=/path: No such file or directory" and every arm produced no log. Build the
    # environment with explicit `export` instead.
    (
      cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release || exit 1
      export DISPLAY="$DISP"
      export "${PFX}_OUT=$out" "${PFX}_MAXF=$MAXF" "${PFX}_TAG=$tag" "${PFX}_DLAT=34" "${PFX}_SEED=114"
      timeout -k 10 600 /home/struktured/projects/dr-mario-mods/run_mesen.sh "$mmc1" "$LUA"
    ) > "$out/stdout.log" 2>&1
    # VERIFY: log present AND tagged for THIS arm
    if command grep -aq "tag=$tag" "$out/$LOGNAME" 2>/dev/null; then
      command grep -a SUMMARY "$out/$LOGNAME"; break
    fi
    echo "[clean] arm $tag produced no valid log (single-instance forward?) -- retrying"
    command grep -a 'Pipe hasn' "$out/stdout.log" 2>/dev/null | head -1
  done
done
echo "[clean] ALL DONE"
