# Freeze #5 black-screen watchdog instrument — day mission part 3, 2026-08-05

Design + deploy a lightweight periodic probe on the MiSTer so that when the next black-screen
wedge hits, we capture *what died* instead of just a blank screenshot.

## The facts this is designed around (given, not re-derived here)

- Display dies; save-states (checked separately, from the PC) return 0 bytes.
- A `menu.rbf` core reload — telling the *already-running* framework process to switch to a
  different core — does **not** clear it.
- A full reboot **does** clear it.
- Onset after ~28h uptime, then recurs within ~1h of a fresh reboot.
- A PC-side script does a **preventive core reload every ~2h** — the instrument must make those
  distinguishable from genuine wedges, not conflate the two.

**What that signature rules in/out:** since switching cores (which reprograms the FPGA and resets
core-local BRAM) does *not* clear the wedge, but a full reboot (which restarts the ARM-side Linux
process and its whole userspace) *does*, the state that's actually broken lives on the ARM
side — the framework process, its video/scaler output path, or something in the kernel/driver
stack underneath it — not in the FPGA core's own memory. So this instrument watches
**process/OS-level signals**, not game state (a separate PC-side save-state check already covers
that half — see project memory `mister-savestate-ram-read` / `dr-mario-savestate-layout`).

## What it watches

`wedge_probe.sh` polls every 30s and appends one line to `/media/fat/wedge_probe.log`:

- `uptime`, `load` (1/5/15min), `memfree`/`memavail` (`/proc/meminfo`) — resource exhaustion has a
  visible signature (a slow leak would show as `memavail` trending down across the ~28h onset
  window; a sudden OOM-adjacent event shows as a cliff).
- `fw_pid`, `fw_state`, `fw_threads` — is `/media/fat/MiSTer` (the framework process, confirmed by
  direct `ps aux` inspection on the device, not assumed from generic MiSTer docs) still alive, and
  in what scheduler state (`R`/`S`/`D`/`Z`/...)? `D` (uninterruptible sleep) held for many
  consecutive polls would point at a stuck kernel-side I/O wait (e.g. SD card, framebuffer ioctl)
  — a materially different diagnosis than a live-but-spinning or genuinely dead process.
- `cmd_dev` — whether `/dev/MiSTer_cmd` (the framework's own IPC/command node, confirmed present
  on this device) exists and is writable. Checked passively (existence + permission bits) rather
  than by sending it a real command, deliberately: a bogus command risks side effects on a live
  human-vs-AI match, which this instrument must never do.
- `video` — HDMI output status via `/sys/class/drm/card*-HDMI-A-*/status` if the kernel exposes
  it. On this device (DE10-Nano-class SoC) it doesn't — confirmed by direct check, not assumed —
  so this reads `n/a` today. Left in as a real check (not silently dropped) in case a driver
  update ever exposes it, since it would be the most direct signal available if it existed.
- `fw_cmdline` — the framework's full command line (which `.rbf`/`.mgl` it's currently running).
  **Reload/restart detection**: compared against the previous poll's value; a change is logged as
  `RELOAD_OR_RESTART prev=[...] new=[...]` on that line. This is how the PC-side 2h preventive
  reload becomes distinguishable after the fact from an unscheduled one that might correlate with
  a wedge — by wall-clock spacing (regular ~2h gaps vs. an outlier) once the log has history, not
  by trying to guess the PC's schedule from the MiSTer side.
- New kernel-log lines since the last poll, via `dmesg -c` (read-and-clear, so it only ever emits
  what's genuinely new — avoids the failure mode of diffing a wrapping ring buffer and silently
  missing entries), into a **separate** file `/media/fat/wedge_probe_dmesg.log` so a `tail -f` on
  the main signal log isn't drowned by kernel chatter. Catches OOM-killer, segfault, and USB/driver
  reset signatures near a wedge.

Both log files self-rotate (keep the most recent ~80,000 lines, trimmed in 20% chunks) so a
multi-day soak can't fill the SD card.

## What it deliberately does NOT do

- No active provocation (no simulated load, no forced core reloads, no `/dev/MiSTer_cmd` writes)
  — this runs continuously against whatever the human/AI match is actually doing, and must not be
  itself a confound.
- No attempt to read game/save-state RAM — that's the PC-side check's job, kept separate on
  purpose so a failure in one doesn't take down the other data source.
- No temperature monitoring — checked for `/sys/class/hwmon/*` and `/sys/class/thermal/*` directly
  on the device; neither exists on this platform. Not faked or estimated.

## Deployment (done, live as of this session)

- Script: `/media/fat/Scripts/wedge_probe.sh` (this file's twin, copied here for provenance —
  the live copy on the SD card is the one that matters operationally).
- Started immediately via `nohup ... &` (survives SSH disconnect; confirmed running under a fresh
  SSH session after backgrounding).
- Installed for persistence across the reboot that will eventually clear the next wedge: appended
  to `/media/fat/linux/user-startup.sh` (the standard MiSTer user-script hook, sourced by
  `/etc/init.d/S99user` at boot — confirmed by reading that init script directly, matching the
  existing entries for `misterclaw` and `remote.sh` already in that file), guarded the same way
  those are (`[[ -e ... ]] && ... &`).
- **Did not reboot the device to test the boot hook** — it's mid-soak-test hardware; verified the
  hook syntax is consistent with the two working entries already in the file instead. First real
  test of the boot path will be whichever reboot clears the next wedge (or a deliberate one, if the
  team wants to verify the hook sooner — not done unilaterally here).
- Hostname used throughout: `MiSTer.local`, per the note that the IP address moves and things
  hardcoded to an IP go stale — confirmed reachable at time of deployment.

## Retrieval, once a wedge happens

```
scp root@MiSTer.local:/media/fat/wedge_probe.log .
scp root@MiSTer.local:/media/fat/wedge_probe_dmesg.log .
```

Read the tail of `wedge_probe.log` around the reported wedge time: is `fw_pid` still a live PID
(process alive, wedge is downstream of the process itself — scaler/video path) or gone (process
died outright)? Is `fw_state` stuck on the same value across many consecutive polls, and if so
which one? Does `memavail` show a trend into the wedge, or a cliff? Cross-reference
`RELOAD_OR_RESTART` lines against the known ~2h preventive-reload cadence to rule those out, then
look for anything else nearby in `wedge_probe_dmesg.log`.

## What's NOT done here (scope boundary, stated plainly)

This instrument observes; it does not yet act (no auto-recovery, no alert/notification). Task was
"design the instrument... capture what died" — implemented and deployed. A follow-up decision
(alerting, or an auto-reboot-on-confirmed-wedge policy) is a separate call for the team once real
wedge data comes back, not made unilaterally here.

## CAPTURE #1 (2026-08-05 11:42Z, first instrumented black-screen)

The probe caught the wedge live (capture1_20260805_1142.log). Findings:
- Framework process ALIVE: fw_state=R (running), 2 threads, /dev/MiSTer_cmd
  present+writable — the ARM process did NOT die.
- NO memory leak: memfree ~322MB, stable across every poll.
- NO kernel events: dmesg stream empty through the wedge.
- THE SIGNATURE: fw_state=R at EVERY 30s poll with load pinned ≈1.0 — a
  healthy framework sleeps (S) between frames; this one busy-spins,
  consistent with a poll loop on the HPS↔FPGA bridge that never completes.
  The display/save-state/screenshot paths all die together because they all
  cross that bridge.
- Onset ~97 min after a FRESH full reboot ⇒ long-uptime accumulation is NOT
  required; the earlier 28h-clean stretch was likely coincidence or
  load-pattern-dependent.
Next instrument iteration (when needed): sample the framework's
/proc/<pid>/wchan + userspace stack (or strace -p for a few seconds) at
wedge time to name the exact spin site; capture FPGA bridge register state
if accessible. Remedy direction: watchdog that detects sustained fw_state=R
+ dead video and auto-reboots (bounded), pending a real fix in
core/framework interaction.
