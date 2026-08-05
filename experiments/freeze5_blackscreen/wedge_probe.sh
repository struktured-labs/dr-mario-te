#!/bin/sh
# wedge_probe.sh -- lightweight periodic health probe for freeze #5 (the black-screen core
# wedge). Task: day-mission part 3, dr-mario-rl project.
#
# Known facts this is designed around (from the freeze log, not re-derived here):
#   - display dies; save-states (checked separately, from the PC) return 0 bytes
#   - a menu.rbf core reload (switching the ALREADY-RUNNING framework to a different core, NOT
#     a process restart) does NOT clear it
#   - a full reboot DOES clear it
#   - onset after ~28h uptime, then recurs within ~1h of the fresh reboot
#   - a PC-side script does a PREVENTIVE core reload every ~2h -- this probe must make those
#     distinguishable from genuine wedges, not conflate them
# That "menu.rbf cycle doesn't help, reboot does" signature points at ARM-side/framework-
# process or scaler/video-pipeline state, not FPGA core BRAM -- so this probe watches
# PROCESS/OS-level signals, not game state (a separate, PC-side save-state check already
# covers that half -- see project memory dr-mario-savestate-layout / mister-savestate-ram-read).
#
# Install: appended to /media/fat/linux/user-startup.sh (the standard MiSTer user-script hook,
# sourced by /etc/init.d/S99user at boot) so it survives the very reboot that clears each wedge.
#
# Output: /media/fat/wedge_probe.log (main signal log, one line per poll) and
# /media/fat/wedge_probe_dmesg.log (new kernel-log lines since the last poll, timestamped) --
# kept as two files so a `tail -f` on the main log isn't drowned by kernel chatter.

LOG=/media/fat/wedge_probe.log
DMESG_LOG=/media/fat/wedge_probe_dmesg.log
STATE=/tmp/wedge_probe_last_cmdline
INTERVAL=30
MAX_LINES=80000   # ~28h of history at 30s/line before rotating -- matches the observed onset window

while true; do
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  UPTIME=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)
  LOAD=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null)
  MEMFREE=$(command grep MemFree /proc/meminfo 2>/dev/null | awk '{print $2}')
  MEMAVAIL=$(command grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}')

  # Framework process: /media/fat/MiSTer, PID 1 argv is the running core+mgl. A PID that
  # disappears is a genuine process death (not the "core wedge" signature per the freeze log,
  # since reboot -- not process restart -- is what clears it, implying the process itself stays
  # alive but wedged); a cmdline CHANGE is a core switch (either the preventive reload or a
  # human/script-initiated one) -- log it distinctly from a plain poll line.
  # no pgrep on this busybox image -- ps aux + awk instead (PID is column 1, confirmed against
  # this device's `ps aux` header format directly, not assumed from a generic Linux convention)
  FW_PID=$(ps aux 2>/dev/null | command grep '/media/fat/MiSTer ' | command grep -v grep | awk '{print $1}' | head -1)
  if [ -n "$FW_PID" ] && [ -r "/proc/$FW_PID/cmdline" ]; then
    FW_CMDLINE=$(tr '\0' ' ' < "/proc/$FW_PID/cmdline" 2>/dev/null)
    FW_STATE=$(awk '/^State:/{print $2, $3}' "/proc/$FW_PID/status" 2>/dev/null)
    FW_THREADS=$(awk '/^Threads:/{print $2}' "/proc/$FW_PID/status" 2>/dev/null)
  else
    FW_PID="none"
    FW_CMDLINE="DEAD"
    FW_STATE="DEAD"
    FW_THREADS="0"
  fi

  RELOAD=""
  if [ -f "$STATE" ]; then
    PREV=$(cat "$STATE" 2>/dev/null)
    if [ "$PREV" != "$FW_CMDLINE" ]; then
      RELOAD="RELOAD_OR_RESTART prev=[$PREV] new=[$FW_CMDLINE]"
    fi
  fi
  printf '%s' "$FW_CMDLINE" > "$STATE" 2>/dev/null

  # /dev/MiSTer_cmd: the framework's own command/IPC node (used by scripts to trigger loads
  # etc). Existing + world-writable is the passive signal available without sending it a real
  # command (sending a bogus command risks side effects on a live game, avoided deliberately).
  CMDDEV="absent"
  if [ -e /dev/MiSTer_cmd ]; then
    if [ -w /dev/MiSTer_cmd ]; then CMDDEV="present+writable"; else CMDDEV="present+not_writable"; fi
  fi

  # HDMI/video output state, if the kernel exposes it (best-effort; DE10-Nano platform doesn't
  # expose a thermal zone the same way other SBCs do, so temperature is intentionally omitted
  # rather than faked).
  VIDEO=""
  for d in /sys/class/drm/card*-HDMI-A-*/status; do
    [ -f "$d" ] && VIDEO="$VIDEO $(basename "$(dirname "$d")")=$(cat "$d" 2>/dev/null)"
  done
  [ -z "$VIDEO" ] && VIDEO="n/a"

  echo "$TS uptime=${UPTIME:-?} load=${LOAD:-?} memfree=${MEMFREE:-?}kB memavail=${MEMAVAIL:-?}kB fw_pid=$FW_PID fw_state=${FW_STATE:-?} fw_threads=$FW_THREADS cmd_dev=$CMDDEV video=$VIDEO fw_cmdline=[$FW_CMDLINE] $RELOAD" >> "$LOG" 2>/dev/null

  # Drain new kernel-log lines (dmesg -c clears the ring buffer after reading, so this only
  # ever emits lines NEW since the last poll -- catches OOM-killer, segfault, USB/HDMI reset
  # signatures near a wedge without needing to diff a growing buffer).
  NEWDMESG=$(dmesg -c 2>/dev/null)
  if [ -n "$NEWDMESG" ]; then
    { echo "=== $TS ==="; echo "$NEWDMESG"; } >> "$DMESG_LOG" 2>/dev/null
  fi

  # bounded rotation so this never fills the SD card across a multi-day soak
  for f in "$LOG" "$DMESG_LOG"; do
    LINES=$(wc -l < "$f" 2>/dev/null || echo 0)
    if [ "$LINES" -gt "$MAX_LINES" ]; then
      tail -n $((MAX_LINES * 4 / 5)) "$f" > "${f}.tmp" 2>/dev/null && mv "${f}.tmp" "$f" 2>/dev/null
    fi
  done

  sleep "$INTERVAL"
done
