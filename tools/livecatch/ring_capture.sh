#!/usr/bin/env bash
# LIVE-CATCH ring buffer: periodic MiSTer save-states, pulled race-safely, last N kept.
#
# The user cannot produce a replay of the blunder -- by the time he says "it did it again"
# the pill has landed and the moment is gone. The machine can: snapshot continuously, keep
# a rolling window, and when he says "again" the evidence is already on disk. Zero effort
# from him beyond saying the word.
#
# A save-state carries the game's board AND the cart's PRG-RAM, so each frame holds both
# what the SEARCH committed (driver mailbox) and what the DRIVER was doing with it.
# ss_decode.py turns that into the cascade-vs-execution verdict.
#
# ⚠ THE USER SEES THIS. Triggering a save-state flashes MiSTer's on-screen message. He is
# watching the match, so the interval is a courtesy decision, not just a sampling one --
# default 20s, and --once exists for a single grab.
#
# THE 0-BYTE RACE, WHICH IS REALLY A PARTIAL-WRITE RACE. The core writes the .ss
# asynchronously after the keystroke. scp'ing immediately yields 0 bytes or a truncated
# file, and a truncated save-state still parses far enough to look decodable. So we wait
# DEVICE-SIDE for the file to reach its exact expected size AND stop changing, then verify
# the md5 end to end after the copy. ss_decode.py refuses anything that is not exactly
# 1327112 bytes as a second line of defence.
set -uo pipefail

HOST=${MISTER_HOST:-10.42.0.225}
SLOT=4                 # slot 4: least likely to hold something the user wants
INTERVAL=20
KEEP=40
OUT="/home/struktured/projects/dr_mario_rl/tmp/livecatch"
ONCE=0
DRYRUN=0
SS_SIZE=1327112
SSDIR=/media/fat/savestates/NES

while [ $# -gt 0 ]; do
  case "$1" in
    --host)     HOST=$2; shift 2 ;;
    --slot)     SLOT=$2; shift 2 ;;
    --interval) INTERVAL=$2; shift 2 ;;
    --keep)     KEEP=$2; shift 2 ;;
    --out)      OUT=$2; shift 2 ;;
    --once)     ONCE=1; shift ;;
    --dry-run)  DRYRUN=1; shift ;;   # pull the newest existing .ss, press NOTHING
    -h|--help)  command sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done

mkdir -p "$OUT"
SSH="ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$HOST"

$SSH true 2>/dev/null || { echo "MiSTer $HOST not reachable" >&2; exit 65; }

# Which ROM is loaded -> which .ss filename the keystroke will write.
#
# ★ THIS MUST COME FROM WHAT IS LOADED, NOT FROM WHAT WAS SAVED LAST. The first version
# fell back to the newest .ss stem, which on the live machine gave "latch_converged_v2"
# while the console was actually running "latch_converged_native" -- so the ring would have
# waited on a path the core never writes and captured nothing, or worse, re-pulled a stale
# state and decoded it as if it were live.
#
# MiSTer launches these carts through a .mgl wrapper, and the save-state is named after the
# ROM INSIDE the wrapper, not the wrapper itself. So resolve .mgl -> <file path="...">.
GAME=$(misterclaw-send --host "$HOST" status 2>/dev/null \
       | command grep -i '^Game:' | cut -d: -f2- | tr -d ' \r')
case "$GAME" in
  *.mgl)
    ROM=$($SSH "cat '$GAME' 2>/dev/null" \
          | command grep -oE 'path="[^"]+"' | head -1 | cut -d'"' -f2) ;;
  "") ROM="" ;;
  *)  ROM="$GAME" ;;
esac
BASE=$(basename "${ROM:-}" 2>/dev/null); BASE=${BASE%.*}
if [ -z "$BASE" ]; then
  echo "cannot determine the loaded ROM (status='$GAME')." >&2
  echo "  Refusing to guess from the newest save-state: that names whatever was saved" >&2
  echo "  LAST, which is not necessarily what is running now." >&2
  exit 66
fi
TARGET="$SSDIR/${BASE}_${SLOT}.ss"
# --dry-run exercises the whole pull/verify/ring path while pressing NOTHING, so the
# capture side can be tested end to end without putting a save-state flash on the screen
# the user is watching. It pulls the newest state already on the device instead.
if [ "$DRYRUN" = 1 ]; then
  TARGET=$($SSH "ls -t $SSDIR/*.ss 2>/dev/null | head -1")
  [ -n "$TARGET" ] || { echo "dry-run: no existing .ss on the device to pull" >&2; exit 66; }
fi
echo "== live-catch: host $HOST  rom '$BASE'  slot $SLOT  every ${INTERVAL}s  keep $KEEP"
echo "   target on device : $TARGET"
echo "   ring on host     : $OUT"

# ★ DO NOT CLOBBER SOMETHING THE USER SAVED. If slot N already holds a state, park a copy
# beside it once, before we ever overwrite it.
# Skipped under --dry-run: that mode overwrites nothing, and backing up the file it merely
# READS puts a stray file on the user's SD card for no reason. (It did exactly that on the
# first run, and mislabelled it "slot 4" because the dry-run retarget happens above.)
if [ "$DRYRUN" = 0 ] && $SSH "[ -f '$TARGET' ]"; then
  if ! $SSH "[ -f '$TARGET.livecatch-backup' ]"; then
    $SSH "cp -p '$TARGET' '$TARGET.livecatch-backup'" \
      && echo "   pre-existing slot $SLOT state backed up to $(basename "$TARGET").livecatch-backup"
  else
    echo "   pre-existing slot $SLOT state already backed up (leaving it alone)"
  fi
fi

grab() {
  local stamp; stamp=$(date +%Y%m%d-%H%M%S)
  local dest="$OUT/${BASE}_${stamp}.ss"

  if [ "$DRYRUN" = 0 ]; then
    # note the pre-existing mtime so we can require it to CHANGE, not merely exist
    local before; before=$($SSH "stat -c %Y '$TARGET' 2>/dev/null || echo 0")
    misterclaw-send --host "$HOST" input combo leftalt "f$SLOT" >/dev/null 2>&1 \
      || { echo "   [$stamp] keystroke failed" >&2; return 1; }
    # wait for a NEW file that has reached full size and stopped growing
    local tries=0 sz=0 mt=0 psz=-1 pmt=-1 stable=0
    while [ $tries -lt 60 ]; do
      read -r sz mt < <($SSH "stat -c '%s %Y' '$TARGET' 2>/dev/null || echo '0 0'")
      if [ "$mt" != "$before" ] && [ "$sz" = "$SS_SIZE" ] \
         && [ "$sz" = "$psz" ] && [ "$mt" = "$pmt" ]; then
        stable=1; break
      fi
      psz=$sz; pmt=$mt; tries=$((tries + 1)); sleep 0.25
    done
    if [ "$stable" != 1 ]; then
      echo "   [$stamp] save-state never settled (size $sz, expected $SS_SIZE) -- skipping" >&2
      return 1
    fi
  fi

  scp -q -o ConnectTimeout=5 "root@$HOST:$TARGET" "$dest" 2>/dev/null || {
    echo "   [$stamp] scp failed" >&2; rm -f "$dest"; return 1; }

  # end-to-end integrity: size AND md5 must match the device copy
  local lsz rmd5 lmd5
  lsz=$(stat -c %s "$dest" 2>/dev/null || echo 0)
  if [ "$lsz" != "$SS_SIZE" ]; then
    echo "   [$stamp] local copy is $lsz bytes, expected $SS_SIZE -- discarding" >&2
    rm -f "$dest"; return 1
  fi
  rmd5=$($SSH "md5sum '$TARGET'" | cut -d' ' -f1)
  lmd5=$(md5sum "$dest" | cut -d' ' -f1)
  if [ "$rmd5" != "$lmd5" ]; then
    echo "   [$stamp] md5 mismatch (device $rmd5 vs local $lmd5) -- discarding" >&2
    rm -f "$dest"; return 1
  fi
  echo "   [$stamp] captured $(basename "$dest")  md5 ${lmd5:0:8}"
}

prune() {
  local n; n=$(ls -1t "$OUT"/*.ss 2>/dev/null | wc -l)
  if [ "$n" -gt "$KEEP" ]; then
    ls -1t "$OUT"/*.ss | tail -n +$((KEEP + 1)) | while read -r f; do rm -f "$f"; done
  fi
}

if [ "$ONCE" = 1 ]; then grab; prune; exit $?; fi

echo "   Ctrl-C to stop. When the user says it happened again, decode the newest frames:"
echo "     ss_decode.py \$(ls -1t $OUT/*.ss | head -6)"
while true; do
  grab; prune
  sleep "$INTERVAL"
done
