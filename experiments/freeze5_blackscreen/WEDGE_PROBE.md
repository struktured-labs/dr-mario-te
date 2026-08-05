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

## AUTO-RECOVERY FIRING #1 (2026-08-05 11:59:15Z) — the wedge is USERSPACE

The watchdog fired correctly (consec=6, busy_frac=100%), captured the state
snapshot (recovery1_20260805_1159.log), synced and rebooted — the soak
self-healed with no human action. What the snapshot proves:

- **wchan = 0 and /proc/<pid>/stack EMPTY** ⇒ the process is NOT blocked in
  any kernel call. Combined with State=R, the framework is spinning in
  USERSPACE, not stuck on a driver/bridge ioctl. This REFUTES the
  "blocked on the HPS-FPGA bridge" reading from capture #1 — it's a
  userspace busy-loop (poll/retry) that never exits.
- **Thread 524 = R, thread 914 = S**: only the main thread spins; the
  second thread sleeps normally. utime 39564 / stime 50358 with
  nonvoluntary_ctxt_switches 8312 ≫ voluntary 1189 = classic
  compute-bound spin, not I/O wait.
- Memory normal (RSS 5.8MB, VmPeak 71MB) — no leak, consistent with
  capture #1.

**Next diagnostic (for the silicon session or a spare box):** the exact spin
site needs userspace visibility — `perf top -p <pid>` / repeated
`cat /proc/<pid>/stat` field-30 (kstkeip) sampling, or gdb/strace if
installable on this image. Since the process is in userspace, the MiSTer
framework's own source (main loop, user_io poll) is the place to look; a
core-side signal that never asserts would present exactly this way.

## CONTROLLED EXPERIMENT (2026-08-05 12:45Z): is OUR OWN IPC inducing it?

Wedge cadence collapsed today: AUTO_REBOOTs at 11:59 and 12:29 (~30 min
apart), vs ~28 h clean overnight. What changed is OUR traffic, not the
core: the duel tracker writes /dev/MiSTer_cmd every 180 s (save-state ring
capture), plus screenshots (misterclaw :9900), plus a 2 h preventive
reload — and the wedge is a USERSPACE spin in the framework, i.e. exactly
the process that services that IPC.

EXPERIMENT: from 12:45Z the tracker AND the preventive-reload loop are
STOPPED; the core runs the duel with the wedge probe as the only observer
(read-only /proc + dmesg, no IPC writes). Read the result off
wedge_probe.log's AUTO_REBOOT lines:
- No wedge for >2 h ⇒ our save-state/screenshot IPC is implicated as the
  trigger. Consequences: (a) the Sept-12 booth is SAFE (no such traffic in
  human play), (b) the soak rig needs a gentler capture cadence or an
  IPC-free capture path, (c) the "28 h then hourly" overnight pattern is
  explained by load, not accumulation.
- Wedge anyway ⇒ our traffic is exonerated; the spin is intrinsic to
  core+framework and stays a launch-blocking risk to fix before the booth.
Restart both loops after the verdict either way.

## EXPERIMENT VERDICT (2026-08-05 13:05Z): OUR IPC IS EXONERATED

With the tracker and preventive loop STOPPED (probe read-only, zero IPC
writes), the wedge recurred TWICE more — WEDGE_CONFIRMED at 12:59:24Z and
13:02:26Z, AUTO_REBOOT at 13:02:26Z. The userspace spin is INTRINSIC to
this core+framework combination under continuous CvC play; our save-state/
screenshot traffic is not the trigger.

⚠ CONSEQUENCE FOR SEPT 12: this is a LAUNCH-BLOCKING risk, not a lab
artifact. Human play at the booth exercises the same core in the same
framework — a ~30-minute mean-time-to-wedge would be visible to a crowd.
It also now recurs within ~3 minutes of a fresh boot in the worst case
(12:59 wedge on a box booted 12:56), so "reboot before the demo" is NOT a
mitigation. Escalated to the top of the silicon-session agenda alongside
the brain work.

Next diagnostic steps (in order):
1. EIP sampling at wedge time (assigned) to name the spin site.
2. ISOLATE THE VARIABLE: run the SHIPPED pre-strand20 core (stomper180,
   71d2de37) under identical CvC load — does it wedge too? If not, the
   regression entered with s20b (CMD-8 GO traffic is the prime suspect —
   the same doubling flagged in the freeze accounting).
3. If the shipped core also wedges: framework/core-interaction bug, needs
   the MiSTer framework source; consider pinning a known-good framework
   build for the booth.

## ★ IDLE CONTROL (accidental, 2026-08-05 13:02→22:22Z): 9h19m WEDGE-FREE

After the 13:02Z auto-reboot the box was left at MENU (the duel was never
relaunched — the auto-relaunch feature was still being built). It sat idle
for **9 hours 19 minutes with ZERO wedges** (AUTO_REBOOT count stayed 3,
load pinned 1.00 the whole time). That is a far stronger control than
anything designed today: the wedge requires the DUEL CORE ACTIVELY PLAYING,
not merely powered/booted. Combined with the IPC-exoneration result, the
trigger is core+framework interaction under continuous CvC gameplay.

## A/B ARM 1 STARTED (2026-08-05 22:22:46Z): pre-strand20 core

AB_wedge_old180.mgl (rbf NES_stomper180_20260801 = the shipped champion
71d2de37, same cart/probe as s20b's mgl) loaded and playing. Measurement:
time-to-first-wedge vs s20b's measured ~30 min (worst 3 min) under
identical idle-observer conditions (tracker + preventive loop remain OFF).
Read AUTO_REBOOT count/timestamps in wedge_probe.log.
