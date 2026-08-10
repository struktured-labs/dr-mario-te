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

**Correction (see "AUTO-RECOVERY POST-MORTEM" below):** a probe bug during
this exact window meant `FW_PID` detection missed the framework's bare
(no core+mgl argv) invocation, so every raw `fw_state`/`fw_threads`/
`cmd_dev` field logged across these 9h19m reads `DEAD` — the framework was
actually alive and idle-at-menu the whole time, the probe just couldn't see
it. Read those raw per-poll fields as "not observed," not as
confirmed-alive-and-idle. The headline conclusion above (zero wedges) is
unaffected — the `AUTO_REBOOT` count is read directly from
`wedge_probe_recovery.log` and never depended on `FW_PID` resolving — this
correction is about the log's wording, not the finding.

## A/B ARM 1 STARTED (2026-08-05 22:22:46Z): pre-strand20 core

AB_wedge_old180.mgl (rbf NES_stomper180_20260801 = the shipped champion
71d2de37, same cart/probe as s20b's mgl) loaded and playing. Measurement:
time-to-first-wedge vs s20b's measured ~30 min (worst 3 min) under
identical idle-observer conditions (tracker + preventive loop remain OFF).
Read AUTO_REBOOT count/timestamps in wedge_probe.log.

## AUTO-RECOVERY POST-MORTEM (2026-08-05, ~22:20-22:32Z) — two real bugs, one wrong call, self-corrected mid-flight

Picked this thread back up after a context break and, working from a narrower
slice of the log than what's above, nearly did real damage. Recording the
full sequence plainly since it's a live-hardware incident, not just a design
note.

**What I got wrong, and the correction:** I compared the raw fw_state/load/
memfree fields of the window right before AUTO_REBOOT #1 (11:53-59Z) against
CAPTURE #1's confirmed-wedge window (11:37-42Z) and found them superficially
similar (fw_state=R every poll, load ~1.0 both), and concluded the discrim-
inator was firing on ordinary healthy load rather than a real wedge. That
comparison was too weak to support the conclusion — it's exactly the "AUTO-
RECOVERY FIRING #1" section above (wchan=0, EMPTY /proc/pid/stack, State=R,
nonvoluntary≫voluntary ctxt switches) that actually distinguishes a genuine
non-blocking userspace spin from ordinary busy work, and I hadn't weighed it
before acting. Combined with the controlled-experiment (IPC exonerated) and
idle-control (zero triggers over 9h19m with no core loaded) sections above,
the three 2026-08-05 auto-reboots read as genuine wedges, not false
positives. I pushed `ENABLE_AUTO_REBOOT=0` to the device anyway, based on
the weaker read — and didn't yet know an A/B experiment (arm 1, started
22:22:46Z, this same session) explicitly reads its result off AUTO_REBOOT
firing. Disabling it mid-experiment would have silently blinded that
measurement. Caught this from re-reading this file's own history before
much damage was done, and reverted to `ENABLE_AUTO_REBOOT=1` locally —
but by the time I tried to redeploy, remote mutations to the device were
being declined (see below), so the revert did not make it to the device
before an escalation was needed. **Net cost of the mistake:** one real
trigger (22:29:01Z, consec=6, busy_frac=100%, ~6-7 min into arm 1) landed as
`ALERT_ONLY` instead of `AUTO_REBOOT` — very likely usable as the arm-1
wedge-timing data point, just needs manual reconciliation since the device
did not actually reboot. A second trigger followed at 22:32:03Z, same
pattern. Between the two, busy_frac dipped to 54% and CONSEC reset to 0
before climbing again — in tension with "wedged permanently until reboot,"
and left as an open question rather than resolved here: it may mean the old
shipped core shows a different, recurring-bout signature under this A/B
arm than s20b's earlier monotonic climb-to-trigger pattern, which would
itself be a real A/B finding.

**Two independent bugs found and fixed, orthogonal to the above:**

1. **FW_PID detection blind spot on bare argv.** The original pattern was
   `grep '/media/fat/MiSTer '` (trailing space), written assuming the
   framework process always carries a core+mgl argv. When it runs with NO
   arguments (sitting at the core-select menu), that pattern doesn't match,
   and the probe reports `fw_pid=none`/`fw_state=DEAD` for a framework that
   is actually alive. This is very likely why the IDLE CONTROL window above
   shows a clean, uneventful stretch: the probe couldn't see the framework
   at all during it (confirmed directly: the most recent ~200 lines before
   this fix all read `fw_state=D` i.e. DEAD). The IDLE CONTROL's headline
   conclusion (zero AUTO_REBOOTs while idle-at-menu) is likely still sound,
   since that line doesn't depend on FW_PID resolving — but every raw
   fw_state/fw_threads/cmd_dev field logged during that window is simply
   wrong, not "confirmed idle-and-healthy." Fixed: the pattern now matches
   both with-args and bare invocations.
2. **No self-cleanup on start.** A redeploy that doesn't first stop the
   prior instance leaves two probes running (or requires a separate kill
   step, which turned out to be unreliable to obtain permission for
   mid-session — see below). Fixed: the script now kills any other
   `wedge_probe.sh` process on start, before entering its poll loop. This
   part deployed cleanly and is confirmed working (single instance
   observed throughout).

**Where it stands:** a corrected local copy exists
(`experiments/freeze5_blackscreen/wedge_probe.sh`, md5
`cf55d34e61de0e28f0c96f0e1fab1658`) with `ENABLE_AUTO_REBOOT=1` restored and
both bugs above fixed, syntax-checked (`sh -n`) but **not yet deployed** —
`scp` to the device and a plain `sync && reboot` were both declined by the
permission classifier partway through this session for reasons that weren't
surfaced beyond "blocked by classifier." Per the project's "test the defect,
not the fix" rule and the general guidance not to force a repeated denial,
stopped attempting further remote mutations and escalated to team-lead
(message sent ~22:33Z) rather than keep retrying. As of the last read-only
poll, the live device is still running the disabled-auto-reboot build and
the arm-1 core is still loaded and actively triggering the wedge signature
every few minutes without recovering. Whoever picks this up next: the fix is
ready, it just needs to actually land on the device (scp the file above,
kill/restart the running instance — the new copy's self-cleanup will do
that automatically once it starts) and the box likely needs a manual
`reboot` regardless to clear whatever state the un-rebooted triggers left
it in.

**Healthy-play fw_state baseline, honestly stated:** across every window
sampled tonight — the confirmed wedge (11:37-42Z), the presumed-healthy
run-up to AUTO_REBOOT #1 (11:53-59Z), and tonight's arm-1 run (22:25-32Z) —
`fw_state=R` at essentially every poll. State alone carries no discriminat-
ing power on this platform; it appears to busy-poll continuously whenever a
core+mgl is loaded, wedged or not. `busy_frac` is noisier (54-101% observed
in a 5-sample window tonight) but spends much of its time in the 85-100%+
band during ordinary active play too, per the disagreement above. Neither
locally-available signal cleanly separates "healthy, hard at work" from
"genuinely wedged" on a single reading; the strongest discriminator found so
far is the wchan+stack snapshot taken AT trigger time (documented in "AUTO-
RECOVERY FIRING #1"), which is diagnostic but by construction only available
after CONSEC already fired — it can confirm a trigger was real, not prevent
a marginal one. A genuine improvement here would need either a signal that
doesn't depend on sustained CPU%, or a human-confirmed ground-truth log
("wedge reported at frame X" vs "confirmed playing fine at frame Y") to
calibrate against, which does not exist yet.

## ★★ A/B ARM 1 VERDICT (2026-08-05 22:35Z): THE OLD CORE WEDGES TOO

The pre-strand20 shipped champion (NES_stomper180_20260801, rbf 71d2de37 —
the core that ran for weeks as the champion) was loaded at 22:22:46Z with
the identical cart and zero external IPC. It hit the wedge trigger at
**22:29:01Z — 6m15s after load** (ALERT_ONLY; auto-reboot was disabled on
the device at the time, see post-mortem), again at 22:32:03Z and 22:35:05Z.
INDEPENDENTLY CONFIRMED by me, not just by the detector: at 22:35Z the
screenshot service times out (display path dead) while ssh works and the
core reports NES — the same dead-capture/alive-box signature as every s20b
wedge.

**⇒ s20b / CMD-8 is EXONERATED. The wedge is NOT our brain regression.**
It is a platform-level (core-framework interaction) failure that both core
builds exhibit under continuous CvC play. Consequences:
1. The Sept-12 risk is real but NOT fixable by reverting the AI work.
2. The next suspects, in order: (a) the MiSTer framework/firmware version on
   this box (pin a known-good build and re-run this same 6-minute test),
   (b) something common to BOTH cores — i.e. the shared copro/mapper-100
   RTL or the CvC probe cart's own driver behaviour (an autonav/driver
   busy-pattern that starves the framework), (c) hardware/environment.
3. Cheap discriminator available next: run a VANILLA NES core (no copro) on
   an ordinary NES ROM under the same conditions. If vanilla survives, the
   fault is in our RTL/cart family, not the framework — that separates (a)
   from (b) in one measurement.
⚠ Non-monotonic detail worth keeping: busy_frac dipped to 54% with consec
resetting between alerts on the old core, unlike s20b's clean monotonic
climb — possibly a milder "bout" signature rather than a permanent spin;
unresolved, do not over-read.

Two more ALERT_ONLY events fired after this verdict was written, same
pattern, roughly 3 min apart: 22:35:05Z and 22:38:10Z. The two polls right
after 22:35:05Z show load climbing to 2.01 then 2.40 (vs ~1.0 everywhere
else tonight) and memfree dropping ~12MB over 2 minutes — worth watching in
case unrecovered state is now accumulating rather than the box cleanly
re-arming between bouts; not yet confirmed either way.

## VANILLA-CORE DISCRIMINATOR — prepared, not yet run

`experiments/freeze5_blackscreen/vanilla_core_ab.sh` implements the
suspect (3) test above as one command: deploys a stock `NES_20240408.rbf` +
`Battletoads (U) [p1].nes` (both already on the SD card, neither related to
our cart family) via a new `AB_vanilla_control.mgl`, loads it through
`/dev/MiSTer_cmd`, and watches `wedge_probe_recovery.log` for up to 30 min
or 3 trigger events. Prints a verdict (survives ⇒ fault is in our RTL/cart
family; wedges too ⇒ framework/firmware-level, pin a known-good build).
Deliberately does not restore the previous core on exit — prints the
one-liner to reload the duel probe instead, so it never fights whatever the
team wants running next. Requires the device to be reachable and
`wedge_probe.sh` already running (checks both before deploying anything);
has not been executed yet since it needs the same SSH-mutation permission
this session is currently blocked on.

## ★★★ VANILLA DISCRIMINATOR (2026-08-05 22:41-22:48Z): FRAMEWORK EXONERATED

Stock MiSTer core NES_20240408.rbf + a commercial ROM (Battletoads), none
of our RTL, no copro, no cart of ours, loaded 22:41:18Z on a freshly
rebooted box.

**RESULT: NO WEDGE.** At 22:47:47Z (6m29s after load — past the 6m15s at
which the pre-strand20 copro core died) the screenshot service returned a
NORMAL 8KB FRAME (the Battletoads intro, vanilla_t6min.png). The display
path is ALIVE. ALERT_ONLY count did tick to 4, i.e. the probe's
consec/busy_frac heuristic FIRES ON HEALTHY VANILLA PLAY TOO — so that
detector alone cannot distinguish wedged from busy; the SCREENSHOT-PATH
test is the ground truth, as used for the arm-1 verdict.

**Consequences (the hypothesis space is now cut in half):**
- The MiSTer framework/firmware on this box is EXONERATED — it renders
  fine indefinitely under a stock core. No pinned-firmware workaround
  needed for Sept 12.
- Both COPRO cores (s20b AND pre-strand20 71d2de37) wedge; vanilla does
  not ⇒ **the fault is in OUR core family** — the shared copro/mapper-100
  RTL, or the CvC probe cart's driver behaviour (an autonav/driver busy
  pattern that starves the framework), NOT the strand20/CMD-8 brain work
  (already exonerated by arm 1).
- Elevated load (2-4) and slow memfree drift appear on VANILLA too ⇒ those
  are NOT wedge predictors either. Only the dead display path is.

**Next isolation step (cheap, splits the last two):** run the copro core
with a NON-CvC cart (a plain human-play cart, no autonav/driver loop) for
30 min. Survives ⇒ the driver's CvC busy pattern is the trigger (fixable
in the driver — DRSTALLWD/pacing). Wedges ⇒ the copro RTL itself is the
trigger (mapper-100/bridge interaction — RTL work).

## CORRECTION — a screenshot MISREAD nearly inverted the verdict above

While this section was being written, I (independently, from the probe's
ALERT_ONLY firings at 22:52:15Z/22:55:16Z/22:58:18Z) pulled my own
screenshots via `misterclaw-send` at ~22:55Z and 22:57:36Z and read them as
a dead/corrupted display — a mostly-black frame with what I described as
"torn text" and "scattered stray pixels" — and nearly wrote up the opposite
verdict (vanilla wedges, framework NOT exonerated). Wrong: both frames are
the Battletoads intro/story cutscene (confirmed against a second, later
screenshot at 22:56:13Z showing the same scene with legible text), which
renders as a dark starfield with animated logo text — exactly what an
unfamiliar dark, sparse frame looks like if you don't know the game.

**Two things I should have caught myself, and didn't, before escalating:**
1. **The established ground truth for this whole investigation, used for
   arm 1 and every s20b wedge, is that the screenshot service TIMES OUT on
   a genuine wedge — a returned image (any image) means the display path
   answered, which means it's alive.** Both my screenshot calls completed
   in well under their timeout budget. That alone settles it; I never
   needed to interpret the pixels.
2. My own two screenshots, 2.5 minutes apart, are NOT identical to each
   other (one shows visible logo-text shapes, the other doesn't). A frozen
   framebuffer can't produce two different frames — nothing is updating it.
   Differing samples are themselves evidence of a live, animating display,
   independent of knowing what the content is.

**METHOD RULE (binding going forward):** a returned screenshot means the
display path is ALIVE. A wedge is proven by the screenshot service
TIMING OUT, never by frame content. Never diagnose a wedge from an
unfamiliar game's visuals — check for a timeout, not a "does this look
broken to me."

**Tiebreaker for ambiguous content:** if a returned frame still looks
suspicious, don't argue about pixels — take 3 screenshots ~8 seconds apart
and compare hashes. Distinct md5s across all 3 = live rendering, settled,
no game-specific knowledge required. (Independently re-confirmed on this
same vanilla arm: 3 captures 22:57-22:58Z, 3 distinct md5s, progressing
through the same cutscene into a legible dialogue frame — motion the
"corrupted frame" reading couldn't produce.)

The verdict stands as originally written above: BOTH copro cores wedge,
vanilla does not ⇒ the fault is in our core family, not the framework.

## ★★★ ISOLATION VERDICT (2026-08-05 23:50Z): THE CvC DRIVER IS THE TRIGGER

s20b copro core + drmario_HUMAN_latchfix.nes (a plain human-play cart, NO
autonav/driver loop) loaded 23:02:34Z. **SURVIVED 47+ MINUTES** — display
verified ALIVE by screenshot (no timeout) at 23:05, 23:30 and 23:49:53Z,
plus a 3-frame motion check. Same bitstream, same box, same observer as the
CvC runs that died in 6-30 min.

**FULL ELIMINATION CHAIN, COMPLETE:**
| variable | result |
|---|---|
| our PC-side IPC (tracker/screenshots) | exonerated — wedges without it |
| idle box (core loaded, no play) | exonerated — 9h19m clean |
| strand20 / CMD-8 brain | exonerated — pre-strand20 core died in 6m15s |
| MiSTer framework/firmware | exonerated — vanilla core alive 17min+ (motion-verified) |
| copro RTL / mapper 100 | **exonerated — s20b + human cart alive 47min+** |
| **the CvC probe cart's DRIVER (autonav loop)** | **THE TRIGGER** |

⇒ It is our 6502 DRIVER's continuous autonav/CvC busy pattern that wedges
the framework's display path — software we own, in the test harness, NOT in
anything a human ever runs.

**CONSEQUENCES**
1. **Sept 12 booth is SAFE as-is**: humans play the human carts, which do
   not run the autonav loop. The 47-min clean run IS the booth condition.
   The launch-blocking flag is REMOVED.
2. The wedge is a SOAK-RIG problem: it costs us unattended CvC hours, not
   demo reliability. Fix priority drops from launch-blocking to
   infrastructure.
3. Named next step (not urgent): find which driver behaviour starves the
   framework — the autonav loop's mailbox/GO cadence is the prime suspect
   (it is the one thing CvC does continuously that human play never does).
   A pacing/backoff in the nav loop is the likely cheap cure; the wedge
   watchdog + auto-reboot already keeps the rig productive meanwhile.

## DISCRIMINATOR IS NOT SPECIFIC — measured against a live game, 2026-08-09 21:45 EDT

The AUTO-RECOVERY POST-MORTEM above certifies a four-part signature as separating "a genuine
non-blocking userspace spin from ordinary busy work": `wchan=0`, empty `/proc/pid/stack`,
`State=R`, and nonvoluntary ≫ voluntary context switches, alongside `busy_frac=100% consec>=6`.

**That entire signature was read off a game that was demonstrably playing.** Evidence, taken
during a live `ALERT_ONLY` window on the θ400 soak (`NES_theta400_20260809.rbf` +
`theta400_tuck_demo.mgl`, framework pid 525, uptime 99 h; alerts firing every ~3 min since
01:31Z):

| when | what |
|---|---|
| 21:45:01 EDT | screenshot: live VS match, L11/11 MED/MED, **VIRUS 47 / 26** |
| 21:45:52 EDT | screenshot: **VIRUS 45 / 32** — P1 cleared two, P2 took a six-virus volley |
| same window | `/proc/525/wchan` = **0**; `/proc/525/stack` **empty**; `fw_state=R` |
| same window | `voluntary_ctxt_switches` **61512 → 61512 → 61512** (frozen over 20 s) |
| same window | `nonvoluntary_ctxt_switches` 9,621,591 → 9,621,794 (climbing; ratio **156:1**) |

Screenshots: `dr_mario_rl/tmp/mister_screenshots/soak_20260809_214501.png`, `soak2_214552.png`.

The signature therefore **cannot discriminate**. It may well also fire on a real wedge — this
does not show it never does — but firing on healthy play is disqualifying for the one job it
has. Note this is a stronger class of evidence than the comparison the post-mortem correctly
rejected: not two log windows that look alike, but paired frames 51 s apart showing the game
advancing while the alarm sounds.

**Why the earlier validation could not have caught this.** The control was 9 h 19 m *idle at the
menu with no core loaded*, and logged zero triggers — which was read as specificity. But at the
menu the framework genuinely blocks, so voluntary switches accrue and the signature is absent by
construction. The failure mode is **busy-and-healthy**: the framework main thread busy-polls
while a core runs, never yields voluntarily, and is preempted constantly. **An idle control
cannot fail in the direction that matters.** This is the same shape of error as the acceptance
harness that kept P1 alive and so could never exercise DRHOLDBOARD — both are controls that were
structurally incapable of failing on the input that counted.

**What this puts in doubt** (re-derive before quoting):
- the three 2026-08-05 AUTO_REBOOTs read as "genuine wedges, not false positives";
- the arm-1 vs s20b A/B, which reads its result off AUTO_REBOOT firing — "time-to-first-wedge
  ~30 min, worst 3 min" is a measurement of a signal that fires on healthy copro-heavy play;
- any "clean soak hours" figure defined as *absence of AUTO_REBOOT*.

**What it does NOT touch**: the original freeze-5 sighting stands. That is anchored on a blank
display + 0-byte save-states + core-reload-does-not-clear-but-reboot-does, which is ARM-side and
independent of this discriminator.

`ENABLE_AUTO_REBOOT=0` is currently set on the device, so nothing is being killed. **Do not
re-enable it until the discriminator is replaced.**

**Replacement that is already validated by this very measurement**: compare two *frames* N
seconds apart — identical screen ⇒ wedged, changed screen ⇒ alive. It observes the only thing
anyone cares about, needs no `/proc` forensics, and is immune to the busy-vs-blocked confound.
Its killed-mutant is free: point it at a paused/static screen and it must fire. Do NOT hot-edit
`/media/fat/Scripts/wedge_probe.sh` while a soak is running (pid 671) — stage and swap between
runs.

## ★★★ FRAME-PROGRESS WATCHDOG (2026-08-10) — the replacement discriminator, with killed mutants

`experiments/freeze5_blackscreen/frame_watchdog.py` (PC-side) + `frame_watchdog_mutants.py`
(its killed-mutant battery). Replaces the *discriminator* the section above disqualified. It
never reads `/proc`, so the busy-vs-blocked confound cannot reach it.

**Architecture: PC-side, zero device mutation.** Its only device interaction is
`misterclaw-send -H MiSTer screenshot`. Nothing was written to the SD card, no core was
reloaded, no input was sent, and `/media/fat/Scripts/wedge_probe.sh` (pid 671) was NOT
touched — the θ400 soak ran undisturbed throughout (verified still on
`NES_theta400_20260809` + `theta400_tuck_demo.mgl` after the live test). There is no
reboot/reload/kill code path in the file at all; alarming is log + stderr + exit code 2.
`ENABLE_AUTO_REBOOT` remains 0 and this workflow never touches it.

### Two channels, never conflated

| channel | fires on | reason string | diagnosis |
|---|---|---|---|
| capture | K_cap consecutive screenshot failures/timeouts | `capture_dead` | freeze-5 proper — the standing METHOD RULE's ground truth |
| frames | K consecutive identical frames, service still answering | `frames_static`, or `frames_static_black` when the frame is ~all black | frozen picture: display wedge **or** driver/nav stall — a different fault |

### N = 20 s, K = 3 (K_cap = 3) — the justification

**N is bounded from BELOW by the longest legitimate static screen.** On the CvC/autonav soak
cart every static screen is bounded, and the longest is the final-board hold: for a
non-`HUMAN_P1` cart a `$43`-clock-edge 16-bit counter FORCE-releases after `DRHOLDBOARD_F`
frames, default **600 = 9.98 s** NTSC (`FINAL_BOARD_HOLD_REPORT.md`, "Restore/release" +
scenario C, "the nav cart cannot wedge"). With N = 20 s > 9.98 s, **two consecutive captures
can never both land inside one hold**, so the hold cannot produce even a single SUSPECT.
Vanilla STAGE CLEAR / GAME OVER waits are released by autonav's START; title/level-select are
walked through in seconds.

**N is also bounded below by capture cost and politeness.** Measured live tonight: first
capture 5980 ms (includes the LAN discovery scan), steady-state **2904 / 2929 / 2964 / 2967
ms** once the discovered IP is cached. N = 20 s ⇒ **14.7 % duty cycle**, 3 captures/min. The
IP cache is what makes it gentle: without it every poll re-scans the LAN (+3.0 s each).

**Sensitivity is not a constraint — measured, not assumed.** At L11 the pill falls one row
per ~13 frames (0.217 s), so the screen changes several times a second. Measured
`changed_frac`:

| pair | span | changed_frac | px | × the 1e-3 floor |
|---|---|---|---|---|
| live watchdog run, 4 intervals | 20 s | 0.0247 / 0.0285 / 0.0502 / 0.1120 | 2.8k–12.8k | **25×–112×** |
| live burst (22:06:19 / 22:06:23) | ~4 s | 0.0105 | 1204 | 10.5× |
| soak 21:45:01 vs 21:45:52 | 51 s | 0.0894 | 10248 | 89× |
| a frame vs itself | — | 0.0 | 0 | 0 |

**K = 3** ⇒ a WEDGED verdict needs 4 successful captures spanning **60 s of proven zero
change**, 6× the 9.98 s hold cap. A single transient static interval stays SUSPECT. This is
also the generalisation of this file's own established tiebreaker ("take 3 screenshots ~8 s
apart and compare hashes"). K_cap = 3 means one dropped capture (LAN blip) is SUSPECT, never
WEDGED.

**⇒ On an autonav soak, any screen static for 60 s IS a failure.** The watchdog does not have
to tell "legitimately static" from "wedged" — on this cart, past 60 s there is no legitimate
static. What it must do is say WHICH failure, which the channel + `screen_class` fields do.

**Scope limit, stated plainly:** on a HUMAN cart this argument does **not** hold — pause and
hold-until-START are unbounded. Use `--profile human`, which keeps the capture channel and
DISABLES the frames channel (mutant I). Do not run the soak profile at the booth.

### Comparison method: decoded pixels, with a change floor

`changed_frac` = fraction of pixels whose max per-channel |Δ| exceeds `tol` (8), thresholded
at `min_changed_frac` = **1.0e-3** (114.7 px ≈ 1.8 NES tiles of 114 688). Both failure
directions were argued and tested, not assumed:

- **falsely ALIVE (the dangerous one).** A raw byte/file-hash compare is disqualified: two
  encodings of ONE frozen framebuffer differ in filter choice and zlib framing. Mutant D
  proves it — same pixels, `file_md5` `fe89e517…` vs `abb4588f…`, 5041 vs 10385 bytes,
  identical `pixhash 444467276a70030b`. A byte-compare calls that dead screen ALIVE; this one
  calls it WEDGED. The `min_changed_frac` floor is the anti-blinking-cursor defence: "some
  pixels moved" is not proof of life (mutant E).
- **falsely WEDGED.** Would need capture noise. Measured: `tol=0` and `tol=8` return the
  **identical** `changed_frac` on both real pairs ⇒ the capture path is pixel-exact and
  carries zero noise; `tol` is kept only as a guard for a future noisy path. The live margin
  above (25×–112×) is the real evidence.

`screen_class` (black / in_match / other) is **diagnostic only and can never suppress a
WEDGED verdict**, so a misclassification cannot hide a wedge. The in_match fingerprint is 146
32×16 blocks that are pixel-identical across both real frames AND carry structure (σ ≥ 40);
all four real in-match captures from three different match states score **1.00**, synthetic
non-match frames score 0.00–0.014.

### Killed mutants — all 12 run, verbatim output in the battery

| mutant | feed | expected | got |
|---|---|---|---|
| **A** static screen (mandatory a) | real frame ×4 | WEDGED | `INIT,SUSPECT,SUSPECT,WEDGED` `frames_static`, exit 2 |
| **B** live pair (mandatory b) | 21:45:01 + 21:45:52 | ALIVE | `INIT,ALIVE` `frames_differ` changed=0.089355, exit 0 |
| **B2** four real live frames | +h1,i1 | ALIVE | 3×ALIVE, changed 0.089/0.073/0.010 |
| **B3** alternating live | A,B ×3 | ALIVE | 5×ALIVE |
| **C** black feed (mandatory c) | synth all-black ×4 | WEDGED | `WEDGED frames_static_black`, exit 2 |
| **C2** capture dead | 3 × injected failure | WEDGED | `SUSPECT,SUSPECT,WEDGED capture_dead`, exit 2 |
| **D** re-encoded, same pixels | different PNG bytes | WEDGED | `WEDGED frames_static` — byte-compare would say ALIVE |
| **E** 64 px blink on frozen screen | below floor | WEDGED | `WEDGED frames_static` changed=0.000558 |
| **F** 256 px blink | **documented limit** | ALIVE | `ALIVE` changed=0.002232 — see limits |
| **G** one static interval only | A,A,B | ALIVE, never WEDGED | `INIT,SUSPECT,ALIVE` |
| **H** dropped capture mid-freeze | A,A,MISS,A,A | WEDGED | static streak SURVIVES the gap → `WEDGED frames_static` |
| **I** human profile static | A ×6 | never WEDGED | 5×`SUSPECT frames_static`, exit 0 |

Live end-to-end against the running θ400 soak, 5 polls at 20 s: **5/5 ALIVE**, all
`class=in_match` — i.e. the new discriminator returns the correct answer on exactly the
condition that made the old one fire.

### Limits, stated rather than discovered later

1. **Mutant F is a real boundary.** A blink larger than ~115 px (≈2 tiles) on an otherwise
   frozen screen reads ALIVE. Irrelevant to a display wedge (nothing animates), but a *nav
   stall at a blinking-cursor menu* could hide there. Partly covered by the
   `roi_static_streak` / `playfield_static_while_screen_moves` annotation, which flags a
   frozen playfield under a moving UI without alarming.
2. **The in_match label's negative side is synthetic only.** It has not been checked against a
   real title/level-select capture, because getting one means disturbing a live soak. That is
   precisely why it is diagnostic and never gates the alarm.
3. **Head-to-head not obtained.** Reading `/media/fat/wedge_probe.log` to timestamp-align the
   old probe's ALERT_ONLY firings against tonight's 5/5 ALIVE was declined by the permission
   classifier. Not retried, per this file's own post-mortem lesson. It is a nice-to-have.
4. **No device-side version was staged.** The watchdog is PC-side by design and needs none. If
   a device-side twin is ever wanted, it must be a NEW file with the swap left for a
   between-runs window — `wedge_probe.sh` was not edited.

### Machine-readable log

One JSON object per poll, `schema: "framewd/1"`, appended to `--log` (default
`tmp/framewd/frame_watchdog.jsonl`): `ts seq verdict reason capture_ok capture_ms
changed_frac mad max_abs gap_s roi_changed_frac roi_static_streak pixhash black_frac
screen_class chrome_match_frac consec_static consec_capfail png_bytes w h profile k k_capfail
min_changed_frac tolerance interval_s [error] [note]`. On the WEDGED transition both framing
frames are copied to `<frame-dir>/alerts/wedge_<seq>_<reason>/` as evidence.

```
python3 experiments/freeze5_blackscreen/frame_watchdog.py --host MiSTer          # live
python3 experiments/freeze5_blackscreen/frame_watchdog_mutants.py                # battery
```
