#!/bin/sh
# wedge_probe.sh -- lightweight periodic health probe for freeze #5 (the black-screen core
# wedge), now with bounded auto-recovery. Task: day-mission part 3 (+ hot follow-on after
# CAPTURE #1), dr-mario-rl project.
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
# CAPTURE #1 (2026-08-05 11:42Z, see WEDGE_PROBE.md): framework process alive, fw_state=R at
# every 30s poll, load pinned ~1.0, no memory leak, no kernel events -- a poll loop on the
# HPS<->FPGA bridge that never completes. That's the anatomy this auto-recovery logic targets.
#
# WHY fw_state=R ALONE IS NOT THE TRIGGER: the only local reference data available (capture1's
# own log) doesn't include a confirmed-healthy comparison window to rule out "R is what a 30s
# point-sample of a normally frame-paced process just happens to show" -- stated honestly rather
# than assumed away. Instead of trusting a single instantaneous scheduler-state sample, this adds
# a SECOND, load-bearing (AND, not OR) discriminator that doesn't depend on having that baseline:
# sustained CPU-time consumption between polls, read from /proc/<pid>/stat's utime+stime fields
# (kernel-accounted clock ticks, not a point sample -- a process that's mostly sleeping between
# rare "caught in R" observations will show LOW accumulated ticks over a 30s window regardless of
# what state any single poll happens to catch it in; a genuine busy-spin will show ~100% of one
# core sustained). Detection requires BOTH signals together, for N consecutive polls.
#
# Install: appended to /media/fat/linux/user-startup.sh (the standard MiSTer user-script hook,
# sourced by /etc/init.d/S99user at boot) so it survives the very reboot that clears each wedge.
#
# Output:
#   /media/fat/wedge_probe.log         -- main signal log, one line per poll
#   /media/fat/wedge_probe_dmesg.log   -- new kernel-log lines since the last poll
#   /media/fat/wedge_probe_recovery.log -- WEDGE_CONFIRMED / AUTO_REBOOT / ESCALATE events only,
#                                          plus the wchan/stack/status snapshot taken at the one
#                                          moment it's still possible to take it
# kept as separate files so a `tail -f` on the main log isn't drowned by kernel chatter, and the
# recovery ledger is trivially greppable/mailable on its own.

LOG=/media/fat/wedge_probe.log
DMESG_LOG=/media/fat/wedge_probe_dmesg.log
RECOVERY_LOG=/media/fat/wedge_probe_recovery.log
STATE=/tmp/wedge_probe_last_cmdline
UTIME_STATE=/tmp/wedge_probe_last_cputicks
LAST_REBOOT_FILE=/media/fat/wedge_probe_last_reboot
INTERVAL=30
MAX_LINES=80000        # ~28h of history at 30s/line before rotating -- matches the observed onset window

# --- auto-recovery tuning ---
CONSEC_NEEDED=6         # 6 polls * 30s = 3min sustained before considering a wedge confirmed
BUSY_FRAC_PCT=85        # sustained CPU-time >= 85% of one core over the interval = "genuinely spinning"
CLK_TCK=$(getconf CLK_TCK 2>/dev/null); CLK_TCK=${CLK_TCK:-100}   # confirmed 100 on this device; fall back if getconf is absent
MIN_REBOOT_GAP=1800     # 30 min between auto-reboots (bounds); a second trigger inside the window escalates instead

# RE-ENABLED 2026-08-05T22:2xZ after a brief, mistaken disable. I initially read the three
# 2026-08-05 auto-reboots (11:59:15Z/12:29:35Z/13:02:26Z) as false positives from a coarse
# side-by-side of fw_state/load/memfree against CAPTURE #1. That comparison was too weak to
# support the conclusion: WEDGE_PROBE.md's own "AUTO-RECOVERY FIRING #1" section has the
# stronger evidence (wchan=0 + EMPTY /proc/<pid>/stack + State=R + nonvoluntary>>voluntary
# ctxt switches at the moment of firing -- consistent with a genuine non-blocking userspace
# spin), and the follow-on controlled experiment (ruling out the team's own IPC traffic) plus
# the idle-at-menu control (zero triggers over 9h19m with no core loaded) both support "this is
# a real, intrinsic wedge under active CvC play," not a healthy-play false positive. An A/B
# experiment (arm 1, pre-strand20 shipped core) was already in flight when I nearly shipped the
# disable -- its readout depends on AUTO_REBOOT firing, so leaving it off would have silently
# blinded that experiment to a real wedge. Left ON. The two independent bugs this incident did
# surface for real (FW_PID regex blind spot on bare argv, and the missing self-cleanup-on-start)
# are fixed below regardless of this reversal. See WEDGE_PROBE.md "AUTO-RECOVERY POST-MORTEM".
ENABLE_AUTO_REBOOT=1

CONSEC=0

# Self-cleanup: if a fixed/redeployed copy of this script starts while an older instance is
# still running (e.g. this deploy, replacing the version that caused the incident above), stop
# the older one so only one instance is ever active. This runs ON-DEVICE as normal singleton-
# on-start behavior, not as an externally issued kill.
SELF_PID=$$
for p in $(ps aux 2>/dev/null | command grep 'wedge_probe.sh' | command grep -v grep | awk '{print $1}'); do
  if [ "$p" != "$SELF_PID" ]; then
    kill "$p" 2>/dev/null
  fi
done
sleep 1

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
  #
  # BUG FIXED 2026-08-05: the original pattern was '/media/fat/MiSTer ' (trailing space),
  # written assuming the process always has a core+mgl argv. When the framework is running with
  # NO arguments (sitting at the core-select menu, argv is bare "/media/fat/MiSTer"), that
  # pattern doesn't match and this reported fw_pid=none/fw_state=DEAD for a framework that was
  # actually alive -- confirmed directly: after the third unwanted auto-reboot above landed the
  # framework at the menu instead of reloading its mgl, this misdetection hid that state from
  # wedge_probe.log for 9+ hours (looked like "process died", was actually "process alive, no
  # core loaded, my regex has a blind spot"). Matches with-args and bare invocations both.
  FW_PID=$(ps aux 2>/dev/null | command grep -E '/media/fat/MiSTer($| )' | command grep -v grep | awk '{print $1}' | head -1)
  if [ -n "$FW_PID" ] && [ -r "/proc/$FW_PID/cmdline" ]; then
    FW_CMDLINE=$(tr '\0' ' ' < "/proc/$FW_PID/cmdline" 2>/dev/null)
    FW_STATE=$(awk '/^State:/{print $2, $3}' "/proc/$FW_PID/status" 2>/dev/null)
    FW_STATE_CHAR=$(awk '/^State:/{print $2}' "/proc/$FW_PID/status" 2>/dev/null)
    FW_THREADS=$(awk '/^Threads:/{print $2}' "/proc/$FW_PID/status" 2>/dev/null)
  else
    FW_PID="none"
    FW_CMDLINE="DEAD"
    FW_STATE="DEAD"
    FW_STATE_CHAR=""
    FW_THREADS="0"
  fi

  RELOAD=""
  PID_OR_CORE_CHANGED=0
  if [ -f "$STATE" ]; then
    PREV=$(cat "$STATE" 2>/dev/null)
    if [ "$PREV" != "$FW_CMDLINE" ]; then
      RELOAD="RELOAD_OR_RESTART prev=[$PREV] new=[$FW_CMDLINE]"
      PID_OR_CORE_CHANGED=1
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

  # --- second discriminator: sustained CPU-time consumption, from /proc/<pid>/stat (utime+stime
  # in clock ticks). Field indexing verified directly against this device's /proc/PID/stat
  # layout (utime=field14, stime=field15 overall; here counted at $12/$13 of REST after
  # stripping "PID (COMM) ", since COMM can itself contain spaces/parens -- stripping only up to
  # the LAST ") " handles that). ---
  BUSY_FRAC="?"
  BUSY_SPIN=0
  if [ "$FW_PID" != "none" ] && [ -r "/proc/$FW_PID/stat" ]; then
    REST=$(sed 's/^[0-9]* (.*) //' "/proc/$FW_PID/stat" 2>/dev/null)
    UTIME=$(echo "$REST" | awk '{print $12}')
    STIME=$(echo "$REST" | awk '{print $13}')
    if [ -n "$UTIME" ] && [ -n "$STIME" ]; then
      CPUTICKS=$((UTIME + STIME))
      if [ -f "$UTIME_STATE" ] && [ "$PID_OR_CORE_CHANGED" -eq 0 ]; then
        PREV_TICKS=$(cat "$UTIME_STATE" 2>/dev/null)
        PREV_TICKS=${PREV_TICKS:-0}
        DELTA_TICKS=$((CPUTICKS - PREV_TICKS))
        [ "$DELTA_TICKS" -lt 0 ] && DELTA_TICKS=0     # PID reuse guard: negative delta -> ignore this sample
        # busy fraction as a percent of one core over the (roughly INTERVAL-second) poll gap:
        # delta_ticks / (INTERVAL * CLK_TCK) * 100, integer arithmetic
        BUSY_FRAC=$((DELTA_TICKS * 100 / (INTERVAL * CLK_TCK)))
        if [ "$BUSY_FRAC" -ge "$BUSY_FRAC_PCT" ]; then BUSY_SPIN=1; fi
      fi
      echo "$CPUTICKS" > "$UTIME_STATE" 2>/dev/null
    fi
  else
    rm -f "$UTIME_STATE" 2>/dev/null
  fi
  # A cmdline change invalidates the utime baseline (new/restarted process; comparing ticks
  # across two different processes sharing a PID would be meaningless) -- already guarded above
  # via PID_OR_CORE_CHANGED, and the counter below also resets on it.

  # --- compound wedge condition: fw_state starts with R AND sustained busy-spin, both required ---
  if [ "$PID_OR_CORE_CHANGED" -eq 1 ]; then
    CONSEC=0   # a reload/restart is never evidence of a wedge continuing; start clean
  elif [ "$FW_STATE_CHAR" = "R" ] && [ "$BUSY_SPIN" -eq 1 ]; then
    CONSEC=$((CONSEC + 1))
  else
    CONSEC=0
  fi

  echo "$TS uptime=${UPTIME:-?} load=${LOAD:-?} memfree=${MEMFREE:-?}kB memavail=${MEMAVAIL:-?}kB fw_pid=$FW_PID fw_state=${FW_STATE:-?} fw_threads=$FW_THREADS cmd_dev=$CMDDEV video=$VIDEO busy_frac=${BUSY_FRAC}% consec=$CONSEC fw_cmdline=[$FW_CMDLINE] $RELOAD" >> "$LOG" 2>/dev/null

  # Drain new kernel-log lines (dmesg -c clears the ring buffer after reading, so this only
  # ever emits lines NEW since the last poll -- catches OOM-killer, segfault, USB/HDMI reset
  # signatures near a wedge without needing to diff a growing buffer).
  NEWDMESG=$(dmesg -c 2>/dev/null)
  if [ -n "$NEWDMESG" ]; then
    { echo "=== $TS ==="; echo "$NEWDMESG"; } >> "$DMESG_LOG" 2>/dev/null
  fi

  # --- WEDGE CONFIRMED: take the one-shot diagnostic snapshot, then bounded auto-reboot ---
  if [ "$CONSEC" -ge "$CONSEC_NEEDED" ]; then
    {
      echo "=== $TS WEDGE_CONFIRMED fw_pid=$FW_PID consec=$CONSEC busy_frac=${BUSY_FRAC}% ==="
      echo "--- /proc/$FW_PID/status ---"
      cat "/proc/$FW_PID/status" 2>/dev/null
      echo "--- /proc/$FW_PID/wchan ---"
      cat "/proc/$FW_PID/wchan" 2>/dev/null; echo
      echo "--- /proc/$FW_PID/stack ---"
      cat "/proc/$FW_PID/stack" 2>/dev/null || echo "(not readable / not available on this kernel)"
      echo "--- /proc/$FW_PID/task/*/stat (per-thread state, since fw_threads=$FW_THREADS) ---"
      for t in /proc/$FW_PID/task/*/stat; do
        [ -r "$t" ] && cat "$t" 2>/dev/null && echo
      done
    } >> "$RECOVERY_LOG" 2>/dev/null

    if [ "$ENABLE_AUTO_REBOOT" -eq 1 ]; then
      NOW_EPOCH=$(date -u +%s)
      LAST_REBOOT_EPOCH=0
      [ -f "$LAST_REBOOT_FILE" ] && LAST_REBOOT_EPOCH=$(cat "$LAST_REBOOT_FILE" 2>/dev/null)
      LAST_REBOOT_EPOCH=${LAST_REBOOT_EPOCH:-0}
      GAP=$((NOW_EPOCH - LAST_REBOOT_EPOCH))

      if [ "$LAST_REBOOT_EPOCH" -ne 0 ] && [ "$GAP" -lt "$MIN_REBOOT_GAP" ]; then
        echo "$TS ESCALATE wedge_confirmed_again gap_since_last_autoreboot=${GAP}s (< ${MIN_REBOOT_GAP}s bound) -- NOT rebooting, human decision point" >> "$RECOVERY_LOG" 2>/dev/null
        echo "$TS ESCALATE (see $RECOVERY_LOG)" >> "$LOG" 2>/dev/null
        CONSEC=0   # avoid re-logging ESCALATE every poll while still wedged; one escalation record is enough signal
      else
        echo "$NOW_EPOCH" > "$LAST_REBOOT_FILE" 2>/dev/null
        echo "$TS AUTO_REBOOT triggered (consec=$CONSEC busy_frac=${BUSY_FRAC}%), syncing then rebooting" >> "$RECOVERY_LOG" 2>/dev/null
        echo "$TS AUTO_REBOOT (see $RECOVERY_LOG)" >> "$LOG" 2>/dev/null
        sync
        sleep 1
        reboot
        exit 0
      fi
    else
      # ENABLE_AUTO_REBOOT=0: log the signature as data (this is exactly the healthy-baseline
      # measurement the discriminator needs before it can be trusted with reboot authority) but
      # take no action. NOT a confirmed wedge by itself -- cross-reference against an actual
      # reported black screen before treating any single ALERT_ONLY line as one.
      echo "$TS ALERT_ONLY wedge_signature_seen consec=$CONSEC busy_frac=${BUSY_FRAC}% (auto-reboot DISABLED, see WEDGE_PROBE.md post-mortem)" >> "$RECOVERY_LOG" 2>/dev/null
      echo "$TS ALERT_ONLY (see $RECOVERY_LOG)" >> "$LOG" 2>/dev/null
      CONSEC=0
    fi
  fi

  # bounded rotation so this never fills the SD card across a multi-day soak
  for f in "$LOG" "$DMESG_LOG" "$RECOVERY_LOG"; do
    [ -f "$f" ] || continue
    LINES=$(wc -l < "$f" 2>/dev/null || echo 0)
    if [ "$LINES" -gt "$MAX_LINES" ]; then
      tail -n $((MAX_LINES * 4 / 5)) "$f" > "${f}.tmp" 2>/dev/null && mv "${f}.tmp" "$f" 2>/dev/null
    fi
  done

  sleep "$INTERVAL"
done
