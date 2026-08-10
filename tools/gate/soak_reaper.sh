#!/bin/bash
# soak_reaper.sh [--dry] -- reclaim the Mesen seat the moment an arm has finished writing.
#
# WHY THIS EXISTS
# emu.stop(0) does NOT terminate this Mesen build. Measured: diag_state.lua wrote its final line
# and called emu.stop(0) ~10 s in, and the process was still alive 4.5 minutes later, until
# run_soak.sh's `timeout` killed it. So every arm costs its FULL timeout, not the time its frames
# actually took. For this soak that is a 6000-frame calibration arm (~110 s of work) plus six
# 3000-frame validation arms (~55 s each) all charged at 900 s -- about 90 minutes of a 5-hour
# budget spent on nothing. Phase 3 sizes its segments from whatever time is LEFT, so that waste
# comes straight off the soak's frame count, which IS the deliverable. Reclaiming it is worth
# roughly 30% more soak frames.
#
# WHY IT IS EXTERNAL RATHER THAN A PATCH TO run_soak.sh
# The driver is live and calls run_soak.sh once per arm. Editing a script a running job re-reads
# is the standing hazard, so this runs alongside instead and touches nothing the driver owns.
#
# WHY IT KILLS ON `ACHK` AND NOT ON `SUMMARY`
# probe_soak.lua opens the log once (io.open "w", flushed per line) and writes, in order:
# SUMMARY, SOAK, SOAK2, QUART*, then the A-integrity verdict line ACHK, then logf:close().
# ACHK is the LAST write, and it is the one line this soak exists to produce. Reaping on the
# first sight of SUMMARY would race the remaining writes and could truncate the log precisely at
# the A-check verdict -- turning a real FAIL_A_CORRUPTED into a missing line, i.e. silently
# converting the killed-mutant evidence into "no result". ACHK is written unconditionally (it
# reports verdict=OFF when the check is disabled), so it is a universal terminal marker for
# every arm, injected or not.
#
# TARGETING -- WHY THIS CANNOT HIT ANOTHER LANE
# ~40 lanes share this box and a broad `pkill -f Mesen` would kill their work. This never matches
# on the process name. For each Mesen pid it reads /proc/<pid>/environ and extracts PS_OUT, the
# per-arm output directory that run_soak.sh exports into the emulator's own environment. A pid is
# a candidate ONLY if its own environment names this worktree's soak tree. Another lane's Mesen
# has a different PS_OUT (or none) and is skipped, whatever its command line looks like.
#
# Exits when the driver pid given in REAPER_DRIVER is gone, so it cannot outlive the run.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
MINE="$D/tmp/soak"
DRY=0; [ "${1:-}" = "--dry" ] && DRY=1
DRIVER="${REAPER_DRIVER:-}"
GRACE="${REAPER_GRACE:-3}"          # seconds after ACHK before signalling, paranoia margin
LOG="$D/tmp/soak/reaper.log"
say() { echo "[$(date +%H:%M:%S)] $*" >>"$LOG"; }

say "reaper start dry=$DRY driver=${DRIVER:-<none>} grace=${GRACE}s"
while :; do
  # stop when the driver is gone (or immediately, in dry mode, after one pass)
  if [ -n "$DRIVER" ] && ! kill -0 "$DRIVER" 2>/dev/null; then say "driver $DRIVER gone; reaper exit"; exit 0; fi
  for pid in $(pgrep -f 'Release/Mesen' 2>/dev/null); do
    [ "$pid" = "$$" ] && continue                          # never myself
    # ⚠ NAME PATTERNS LIE BOTH WAYS. pgrep -f matches any command line CONTAINING the string --
    # including this script's own, and including a sibling lane's runner that merely passes the
    # cart path as an argument. That exact mistake cost the v6e lane two COMPLETED arms, reported
    # as "Killed" with no result. So the pattern is only a cheap prefilter: the authority is
    # /proc/<pid>/exe, which resolves to the real binary this pid is EXECUTING. run_mesen.sh
    # execs Mesen in place, so the surviving pid genuinely is the emulator.
    exe=$(readlink -f "/proc/$pid/exe" 2>/dev/null)
    case "$exe" in */Release/Mesen) ;; *) continue;; esac
    envf="/proc/$pid/environ"
    [ -r "$envf" ] || continue
    # PS_OUT is exported by run_soak.sh into the emulator's environment; NUL-separated.
    psout=$(tr '\0' '\n' <"$envf" 2>/dev/null | command grep -a '^PS_OUT=' | command head -1 | command cut -d= -f2-)
    [ -n "${psout:-}" ] || continue
    case "$psout" in "$MINE"/*) ;; *) continue;; esac      # not mine -> never touch
    lg="$psout/probe_soak.log"
    command grep -aq '^ACHK ' "$lg" 2>/dev/null || continue
    if [ "$DRY" = 1 ]; then
      say "DRY: would reap pid=$pid tag=$(basename "$psout") (ACHK present, arm done)"
    else
      sleep "$GRACE"
      command grep -aq '^ACHK ' "$lg" 2>/dev/null || continue
      kill "$pid" 2>/dev/null && say "reaped pid=$pid tag=$(basename "$psout") -- arm finished, seat released early"
    fi
  done
  [ "$DRY" = 1 ] && { say "dry pass complete"; exit 0; }
  sleep 5
done
