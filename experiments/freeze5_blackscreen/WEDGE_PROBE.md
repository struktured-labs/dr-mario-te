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

> ⚠ **RETRACTED 2026-08-10** (this whole verdict + the numbers below) — see "RE-DERIVATION
> (2026-08-10)" §1/§2. It reads its result off `WEDGE_CONFIRMED` at 12:59:24Z / 13:02:26Z and
> `AUTO_REBOOT` at 13:02:26Z, all discriminator-only and all inside the window where the
> tracker was stopped, so there is no independent evidence of any kind. Worse, the "~30-minute"
> figure is `MIN_REBOOT_GAP=1800` and the "~3 minutes" figure is `CONSEC_NEEDED×INTERVAL=180 s`
> — both are constants in `wedge_probe.sh`, not measurements. ("a box booted 12:56" is also
> wrong: the box booted at 12:29:49Z; 12:56:22Z was simply the previous `CONSEC=6` event.)

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

## ~~★ IDLE CONTROL (accidental, 2026-08-05 13:02→22:22Z): 9h19m WEDGE-FREE~~ ⚠ VACUOUS

> ⚠ **RETRACTED 2026-08-10 — see "RE-DERIVATION (2026-08-10)" §3/§5 at the end of this file.**
> All 1,111 polls in this window read `fw_pid=none`/`fw_state=DEAD`/`busy_frac=?%`/`consec=0`.
> `CONSEC` only increments when `FW_STATE_CHAR="R"` (`wedge_probe.sh:188`) and `AUTO_REBOOT` is
> gated on `CONSEC≥6`, so the count **could not** have moved regardless of the box's state. The
> correction below (which says the count "never depended on FW_PID resolving") is itself wrong.
> This is not a weak control; it is no control.

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
> ⚠ **AMENDED 2026-08-10** — two rows are struck; see "RE-DERIVATION (2026-08-10)" §1/§2/§3.
> Rows anchored on *screenshot* ground truth survive; rows anchored on `AUTO_REBOOT`/
> `WEDGE_CONFIRMED` do not. The conclusion (CvC driver is the trigger) still rests on the
> three surviving screenshot rows, but its two struck legs must be re-run before it is quoted
> as a closed elimination.

| variable | result |
|---|---|
| ~~our PC-side IPC (tracker/screenshots)~~ | ⚠ **STRUCK** — read off `WEDGE_CONFIRMED`/`AUTO_REBOOT` only, inside the tracker-stopped blackout. Re-run needed. |
| ~~idle box (core loaded, no play)~~ | ⚠ **STRUCK** — no core was loaded, and the trigger was disconnected (`fw_pid=none` for all 1,111 polls). Vacuous. |
| strand20 / CMD-8 brain | exonerated — **holds on the 22:35Z screenshot TIMEOUT**; ⚠ the "6m15s" timing is retracted (a verified-healthy arm scored 3m01s) |
| MiSTer framework/firmware | exonerated — vanilla core alive 17min+ (motion-verified) **← screenshot-anchored, holds** |
| copro RTL / mapper 100 | **exonerated — s20b + human cart alive 47min+ (3 screenshots + motion) ← holds** (⚠ it also logged 96 ALERT_ONLYs in that same window — the clearest proof the trigger is non-specific) |
| **the CvC probe cart's DRIVER (autonav loop)** | **THE TRIGGER** (now supported by 3 of 5 legs, not 5 of 5) |

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

## ★★★ RE-DERIVATION (2026-08-10) — what the non-specific discriminator actually costs us

Read-only forensics against `/media/fat/wedge_probe.log` (16,222 lines, 2026-08-05T11:37:47Z →
2026-08-10T10:34:49Z, 14,124 poll rows), `/media/fat/wedge_probe_dmesg.log`,
`/media/fat/wedge_probe_recovery.log`, the duel ledger, and the pre-probe freeze record. Nothing
was written to the device; the θ400 soak (pid 525, `NES_theta400_20260809.rbf` +
`theta400_tuck_demo.mgl`) and `wedge_probe.sh` (pid 671) were untouched throughout — re-verified
after the fact (uptime continuous 4 d 12 h, same cmdline, single probe instance).
Working copies of the three logs: `tmp/wedge_forensics/` (gitignored).

### 0. The trigger's timing is set by two script constants, not by the machine

`wedge_probe.sh`: `INTERVAL=30`, `CONSEC_NEEDED=6`, `BUSY_FRAC_PCT=85`, `MIN_REBOOT_GAP=1800`.
`CONSEC` increments only when `FW_STATE_CHAR = "R"` **and** `busy_frac ≥ 85`, and resets to 0 on
a reload, on any sub-85 sample, and after every fired event (`:230`, `:247`). Therefore:

- **the earliest possible trigger after a core load is `CONSEC_NEEDED × INTERVAL` = 180 s**, and
- **`AUTO_REBOOT` only fires when `now − last_AUTO_REBOOT ≥ MIN_REBOOT_GAP = 1800 s`**; every
  earlier `CONSEC=6` event logs `ESCALATE` instead (`:227-230`).

Both numbers quoted as findings are these constants read back. Measured gaps between the three
AUTO_REBOOTs: **1820 s** and **1971 s** — the first two `CONSEC=6` events on the 182 s ESCALATE
grid to clear 1800. The intervening ESCALATEs sat at gaps 1275 / 1456 / 1638 and 1062 / 1244 /
1426 / 1607 / **1789** (that last one missed the bound by 11 s).

### 1. The three 2026-08-05 AUTO_REBOOTs — verdicts

Common to all three: `wedge_probe_dmesg.log` is **clean** at each reboot instant. The only new
kernel line is `input: misterclaw as /devices/virtual/input/inputN`, then the boot banner. No
OOM, no segfault, no hung-task, no driver reset, no `MiSTer_fb` error. The Aug-5 recovery-log
snapshots have **rotated away** (earliest surviving event is now 2026-08-08T02:07:19Z); only
`dr_mario_rl/tmp/film_review_20260804/recovery1.log` (AUTO_REBOOT #1's) survives.

**#1 — 2026-08-05T11:59:15Z ⇒ CORROBORATED BUT UNINFORMATIVE (a real fault was in progress; the
reboot is not evidence of it).**
- The `busy_frac`/`consec` fields **did not exist before 2026-08-05T11:56:14Z** (log line 36, the
  first carrying `busy_frac=?%`). `CONSEC` then ran 1,2,3,4,5,6 with no reset and AUTO_REBOOT
  fired at 11:59:15Z — **3 m 01 s after the discriminator was first armed, the floor.** It fired
  at the earliest instant it physically could. That timestamp carries no information about the
  machine.
- Independent evidence a real fault *was* present: `experiments/duel_ledger/ledger_20260805_0638_v3.csv`
  shows the save-state capture path dead from **11:26:39Z (STALE_x1) through 11:59:47Z
  (STALE_x11)** — last good capture 11:23:00Z. 33 minutes of dead save-states, and STALE_x4/x5
  (11:37:39Z / 11:41:17Z) land inside CAPTURE #1's confirmed black-screen window. CAPTURE #1 is
  real and independently corroborated.
- But that same run of STALEs **starts 11 minutes before the probe existed and survives the
  manual reboot at ~11:43:27Z**: captures at 11:47:27 / 11:50:32 / 11:53:37 / 11:56:42 were all
  STALE on a box booted three minutes earlier. So the fault does not attach to the 11:59:15Z
  moment.
- No blank screenshot, no dmesg signature, no unrecoverable framework state at 11:59:15Z.

**#2 — 2026-08-05T12:29:35Z ⇒ REFUTED. FALSE POSITIVE, with contemporaneous proof.**

`ledger_20260805_0800_v3.csv`, in the window the probe was continuously in `CONSEC≥6`
(ESCALATE 12:20:30 / 12:23:31 / 12:26:33):

| capture (UTC) | mode | virus P1/P2 | file |
|---|---|---|---|
| 12:18:40Z | 4 | 44 / 21 | `…20260805-081838.ss` |
| 12:21:44Z | 7 | 6 / 18 | `…20260805-082141.ss` |
| 12:24:48Z | 4 | 43 / 26 | `…20260805-082445.ss` |
| 12:27:51Z | 4 | **48 / 48** | `…20260805-082749.ss` |

Four distinct capture files, three different in-play boards, and a mode **4 → 7 → 4** transition
(match ended, a fresh match started at 48/48). The last of them is **1 m 44 s before the
reboot**. The box was playing, saving and starting new matches while the watchdog called it
wedged — and it was rebooted mid-match. This is the same class of evidence as the 2026-08-09
paired screenshots, but recorded on 2026-08-05 itself, in a file that was already on disk.

**#3 — 2026-08-05T13:02:26Z ⇒ UNEXPLAINED. Discriminator only.**
- The duel tracker was stopped at ~12:45Z for the IPC experiment; `ledger_20260805_0800_v3.csv`
  ends at 12:42:53Z. **Zero save-state coverage.**
- No PC-side screenshot exists anywhere for the 11:30–14:00Z window (mtime sweep across
  `dr_mario_rl/`, `dr-mario-qa-wt/`, `dr-mario-main-wt/`).
- dmesg clean; recovery snapshot rotated away.
- Its moment is fully explained by policy: five ESCALATEs, then AUTO_REBOOT at the first
  `CONSEC=6` whose gap (1971 s) cleared `MIN_REBOOT_GAP`.

⚠ **Collateral:** the "EXPERIMENT VERDICT (12:45Z): OUR IPC IS EXONERATED" section reads its
result off `WEDGE_CONFIRMED` at 12:59:24Z / 13:02:26Z and `AUTO_REBOOT` at 13:02:26Z — all
discriminator-only, all inside the tracker-stopped blackout. **That verdict does not survive
either** and needs re-running against the frame watchdog.

### 2. The arm-1 vs s20b A/B — **DIES** (not merely unrecoverable: positively refuted)

Time from every `RELOAD_OR_RESTART` to that arm's first trigger, over all ~60 core loads in the
5-day log:

| arm | time to first trigger | independent ground truth |
|---|---|---|
| vanilla `NES_20240408` + Battletoads | **+7 m 37 s** | **ALIVE** (frame returned at 6 m 29 s; 3 distinct md5s 22:57–22:58) |
| pre-strand20 `stomper180` + CvC (arm 1) | **+6 m 21 s** | screenshot **timeout** at 22:35Z |
| s20b + CvC (12:17 load) | **+3 m 02 s** | **ALIVE** — ledger, table above |
| s20b + CvC (12:44 load) | **+3 m 01 s** | none |
| **s20b + HUMAN cart** (the "survived 47+ min" arm) | **+3 m 01 s** | **ALIVE** — screenshots 23:05 / 23:30 / 23:49:53 + motion check |
| θ400 soak, 8 separate loads (Aug 9–10) | **+3 m 01 s … +3 m 03 s, 8/8** | **ALIVE** — paired screenshots + `frame_watchdog` 5/5 ALIVE |

- The floor is 180 s. **The modal time-to-first-trigger across ~60 core loads is 3 m 01–03 s.**
  The metric is saturated at its own floor.
- The arm the elimination chain calls **healthiest** (s20b + human cart, 47 min verified alive)
  **ties the arm it calls worst** (s20b CvC) at that floor — and racked up **96 ALERT_ONLYs
  during the very 47 minutes it was being certified clean.** That number was in the log the
  whole time.
- The two arms with *independently verified live display* (vanilla, human cart) sit at the two
  ends of the range (7 m 37 s and 3 m 01 s). The ordering is uncorrelated with wedging.
- "~30 min" = `MIN_REBOOT_GAP`. "worst 3 min" = `CONSEC_NEEDED × INTERVAL`. Arm-1's "6m15s"
  was an `ALERT_ONLY` — auto-reboot was already disabled, so **the A/B never had the
  `AUTO_REBOOT` readout it was designed around at all.**
- The inversion anticipated when this was flagged is confirmed, by a stronger route than
  "stronger AI searches harder": *every* arm — copro CvC, copro human cart, and stock vanilla —
  saturates an 85 %-of-one-core threshold. Anything that keeps the framework main thread busy
  for 3 minutes scores the floor.

**What survives from that night:** everything anchored on the METHOD RULE, not the trigger —
arm 1's screenshot **timeout** at 22:35Z (so "the old core wedges too / s20b-CMD-8 exonerated"
stands on its own evidence), the vanilla arm's returned frame + 3-distinct-md5 motion check, and
the human-cart arm's three screenshots + motion check. The **timings** and the **rate
comparison** do not survive.

### 3. "Clean soak hours" figures defined as absence of AUTO_REBOOT — enumerated

| # | where | claim | mark |
|---|---|---|---|
| 1 | `WEDGE_PROBE.md:203-222` | "IDLE CONTROL … 9h19m WEDGE-FREE (AUTO_REBOOT count stayed 3)" | **VACUOUS — the trigger was disconnected** (below) |
| 2 | `WEDGE_PROBE.md:472` | elimination row "idle box (core loaded, no play) — exonerated, 9h19m clean" | **VACUOUS + factually wrong**: no core was loaded; `fw_cmdline=[DEAD]` for the entire span, core reloaded only at 22:22:40Z |
| 3 | `experiments/eval47/MORNING_DIGEST_20260805.md:114` (and the identical copy in `dr-mario-main-wt/`) | "Idle exonerated — 9h19m at MENU, zero wedges. It needs active play." | **VACUOUS**, same figure |
| 4 | `WEDGE_PROBE.md:157` | "AUTO_REBOOTs at 11:59 and 12:29 (~30 min apart) vs ~28h clean overnight" | **UNSUPPORTED** — 30 min is `MIN_REBOOT_GAP`; the "28 h clean" predates the trigger entirely |
| 5 | `README.md:195` | "wedges the MiSTer's display path within **6–30 minutes**" | **UNSUPPORTED** — both endpoints are trigger artefacts. The only screenshot-confirmed recurrence interval on record is freeze #8 recurring **~65 min** after #7 |
| 6 | `WEDGE_PROBE.md:484` / `README.md:199` | "the 47-min clean run IS the booth condition" | **SURVIVES** — anchored on 3 screenshots + a motion check, *not* on AUTO_REBOOT absence (which was in fact 96 alerts) |

**Why #1–#3 are vacuous, mechanically.** The 9 h 19 m window is
2026-08-05T13:03:24Z → 22:22:09Z: **1,111 consecutive polls with `fw_pid=none`, `fw_state=DEAD`,
`busy_frac=?%`, `consec=0`.** With `fw_pid=none` the script sets `FW_STATE_CHAR=""` (`:120-122`)
and skips the `/proc/<pid>/stat` read, so the `CONSEC` gate
(`[ "$FW_STATE_CHAR" = "R" ] && [ "$BUSY_SPIN" -eq 1 ]`, `:188`) can never be true. `AUTO_REBOOT`
is gated on `CONSEC ≥ 6`. **The count could not have moved off 3 no matter what the box did.**
This corrects the existing note at `:213-222`, which says the AUTO_REBOOT count "never depended
on `FW_PID` resolving" — it depends on it completely, through `CONSEC`.

And the doc's own physical explanation ("at the menu the framework genuinely blocks, so the
signature is absent by construction") is **also wrong**: on the 16 later polls where `menu.rbf`
is loaded as a core and the framework *is* visible, `busy_frac` reads **100 %** and **99 %** on
the two samples that had a baseline. The menu does not block. The control was silent because of
the bare-argv **bug**, not because of framework physics.

### 4. What is NOT in doubt — the ORIGINAL freeze-5 sighting stands. Verified, plainly.

All three legs pre-date the discriminator and none of them touches `wchan`, `/proc/pid/stack`,
`State=R`, context-switch ratios, `busy_frac` or `consec`.

**Leg 1 — blank display.** Five black-screen captures, decoded pixel-by-pixel with
`frame_watchdog.decode_png`:

| capture | when | bytes | file md5 | `black_frac` | `pixhash` |
|---|---|---|---|---|---|
| `experiments/freeze5_20260802/blackscreen_1348.png` | 2026-08-02 13:48 | 1598 | `f43cc0e7124d…` | **1.000000** | `97a658c14a1859de` |
| `experiments/freeze5_20260802/f5b_a_160947.png` | 2026-08-02 16:09 | 1598 | `f43cc0e7124d…` | **1.000000** | `97a658c14a1859de` |
| `…/film_review_20260804/wedge2_0051.png` (freeze #4) | 2026-08-05 00:51 | 1598 | `f43cc0e7124d…` | **1.000000** | `97a658c14a1859de` |
| `…/wedge3_0157.png` (freeze #5) | 2026-08-05 01:57 | 1598 | `f43cc0e7124d…` | **1.000000** | `97a658c14a1859de` |
| `…/wedge7_0457.png` (freeze #7) | 2026-08-05 04:57 | 1598 | `f43cc0e7124d…` | **1.000000** | `97a658c14a1859de` |

All five are byte-identical, 100 % black, 256×448. Healthy frames from the same rig —
`post_recovery_2346`, `post_recovery2_0052`, `post_recovery3_0158`, `post_recovery5_0458`, and
tonight's two soak frames — are 8,980–9,524 bytes at `black_frac` 0.532–0.550 with **all
distinct** pixhashes. `wedge_s20b_freeze3_2345.png` (the *mid-play* family) is 8,980 bytes /
0.5499 black, correctly not a black-screen event. Note these frames were **returned**, not timed
out — so the black-screen family is proven by pixels, which is *stronger* than the standing
METHOD RULE requires.

**Leg 2 — dead save-states.** Contemporaneous tracker record `STALE x5` at freezes #4, #5 and #7
(`experiments/rtl_chain/ship/stomper180s20-seed2/REBUILD.md:70-105`), plus an independent RTL
derivation of *why* they come back 0 bytes: `savestates.vhd:158` (`SAVE_WAITSETTLE` requires
`paused` high for `SETTLECOUNT=100` consecutive cycles, resetting on any drop) and `nes.v:343`
(`corepause_active` additionally requires vblank and a CPU instruction boundary) —
`experiments/title_garble/TITLE_AUDIT.md:93-125`. That is a source-level argument about the NES
core, with no process forensics in it at all.

**Leg 3 — core reload does not clear it, a full reboot does.** `REBUILD.md`, freeze #8
(2026-08-05 ~06:0x–06:45 EDT): the black screen recurred **~65 min after freeze #7's menu-cycle
recovery** — "menu cycles do NOT clear whatever accumulates; escalated to FULL MiSTer REBOOT",
and the reboot moved the DHCP lease .226→.225, an independent side-effect that timestamps a real
reboot. (The earlier `:106` theory that "the menu.rbf cycle resets whatever accumulates" was the
reading as of #7 and was refuted by #8.)

**Chronology proves independence.** `wedge_probe.sh` was committed at **2026-08-05 07:39:46 EDT**
(commit `14bbf28`) and its log's first line is **2026-08-05T11:37:47Z** (= 07:37 EDT). Every one
of the five black-screen captures and the freeze-#8 reboot escalation happened *before that*.
The discriminator did not exist when the defect was characterised.

**Cross-check with the replacement.** Feed the two 2026-08-02 frames to the new frame-progress
watchdog: `black_frac = 1.0`, `changed_frac = 0.0`, `max_abs = 0` across captures **2 h 21 m
apart** ⇒ `WEDGED frames_static_black`. The new discriminator independently agrees with the
original sighting. **Do not over-correct: freeze-5 is a real defect.**

### 5. `fw_state=DEAD` spans = "NOT OBSERVED", confirmed — boot/menu windows, every one

1,175 DEAD polls of 14,124 (**8.3 %**), in exactly **four contiguous spans**, and *every span
begins at uptime 45–46 s* — the first poll after a reboot:

| span (UTC) | polls | duration | uptime @ start | ends at |
|---|---|---|---|---|
| 11:44:25 → 11:45:32 | 3 | 1.1 min | 46.2 s | `RELOAD_OR_RESTART prev=[DEAD]` @ 11:46:02 |
| 12:00:15 → 12:16:58 | 34 | 16.7 min | 46.0 s | @ 12:17:28 |
| 12:30:33 → 12:43:45 | 27 | 13.2 min | 45.2 s | @ 12:44:16 |
| **13:03:24 → 22:22:09** | **1,111** | **558.8 min** | 46.0 s | @ 22:22:40 |

Four corroborations that this is the bare-argv blind spot and not a dead framework:
1. every span starts at the first post-reboot poll and ends exactly at the poll where a
   core+mgl argv appears (`prev=[DEAD]`);
2. 1,172 of the 1,175 rows carry `consec=0` **and** `busy_frac=?%` (the other 3 predate the
   `busy_frac` field entirely) — i.e. `/proc/<pid>/stat` was never read, because there was no pid;
3. after the fix landed (~22:32–22:38Z on 08-05) the *same* condition logs as **alive**: three
   polls at 22:39:37 / 22:40:13 / 22:40:43Z read `fw_pid=525 fw_state=R … fw_cmdline=[/media/fat/MiSTer ]`;
4. **there are zero DEAD rows anywhere after 2026-08-05T22:22:09Z** — 4.5 further days, including
   eight menu transitions, all logged alive.

Span 4 *is* the "9 h 19 m IDLE CONTROL" (558.8 min = 9 h 18.8 m). So the control that certified
the discriminator's specificity is 1,111 consecutive polls in which the discriminator was
electrically disconnected from its own input.

## ★★★ LIVE VALIDATION OF THE FRAME WATCHDOG (2026-08-10, 59.6 min against the running θ400 soak)

The frame-progress watchdog was run against the live soak for a **59.6-minute window,
2026-08-10T10:37:04Z → 11:36:41Z**, 180 polls at N = 20 s, while the OLD probe (pid 671) kept
polling the same box every 30 s. This is the rare test bed the previous section created: **a
known-good system that the old discriminator calls wedged.**

**Soak integrity (checked before AND after).** Still `NES_theta400_20260809.rbf` +
`theta400_tuck_demo.mgl`; probe pid 671 unchanged; `/media/fat/Scripts/wedge_probe.sh` md5
`88f1a92f6cbae1f7c02faf894a1711e8` with mtime 2026-08-05 — byte-identical before and after, not
hot-edited; `ENABLE_AUTO_REBOOT=0` still at line 72 and its branch still gated on `-eq 1`;
`AUTO_REBOOT` count in the window = **0**. Nothing was written to the device, no core reloaded,
no input sent. Device reads were `misterclaw-send shell` with read-only commands only.

### Head-to-head — 19 / 19 contradictions, zero agreements

| | old `/proc` discriminator | new frame watchdog |
|---|---|---|
| polls in window | 120 (30 s) | 180 (20 s) |
| `fw_state=R` | **120 / 120** | n/a — never reads /proc |
| `busy_frac ≥ 100%` | 70 / 120 | n/a |
| max `consec` | 6 (its trigger point) | n/a |
| **verdict** | **19 × `ALERT_ONLY`** | **179 ALIVE + 1 INIT, 0 SUSPECT, 0 WEDGED** |

**Every one of the 19 `ALERT_ONLY` firings landed on an interval the new watchdog called ALIVE**
(`contradictions_old_alert_new_alive = 19`, `agreements_old_alert_new_wedged = 0`). The margin at
those 19 instants was 18×–107× the `min_changed_frac` floor:

| # | old `ALERT_ONLY` (UTC) | old busy/consec/state | new verdict | changed_frac | × floor |
|---|---|---|---|---|---|
| 1 | 10:39:05Z | 99% / 5 / R | **ALIVE** | 0.048061 | 48× |
| 4 | 10:48:12Z | 100% / 5 / R | **ALIVE** | 0.017944 | **18× (narrowest)** |
| 5 | 10:51:14Z | 100% / 5 / R | **ALIVE** | 0.106515 | 107× |
| … | (19 rows, full table in `results_live_validation/h2h.json`) | | all ALIVE | | |
| 19 | 11:33:45Z | 99% / 5 / R | **ALIVE** | 0.038914 | 39× |

The old probe fired on a metronome — every ~182 s, `consec` climbing 1→6, resetting, climbing
again — through a window in which the game completed roughly **41 matches**.

### Ground truth was established SEMANTICALLY, not just from pixel deltas

"Frames differ" alone could in principle be a blinking animation over a stalled game. So the
in-game VIRUS counters were decoded independently: the two 2-digit counter regions were cropped
from all 180 frames and clustered into distinct bitmaps (**15 distinct P1 values, 38 distinct
P2 values**), and each cluster was labelled by eye from a montage
(`results_live_validation/frames/p1_values.png`, `p2_values.png`).

* P1 ranged 48 → 29; P2 ranged 48 → 6.
* **39 joint counter resets** (both counters increase = a new board) plus 2 P1-only increases
  ⇒ **~41 matches in 59.6 min, one per ~87 s**. P2 is by far the faster clearer.
* Example verified by eye: frames 35→36 = VIRUS `48|46` → `47|43` (the *narrowest* interval in
  the window, changed_frac 0.0179) — real clears in both bottles, not noise.

### The legitimately-static screens — the hardest case — were caught and handled

Five polls landed on non-play screens, and **none produced even a single SUSPECT**:

| seq | time | what it actually is (verified by eye) | screen_class | changed_frac | verdict |
|---|---|---|---|---|---|
| 48 | 06:52:41 | match-end: bottles emptying, Dr. Mario sprite, `44|27` | **other** (chrome 0.548) | 0.2847 | ALIVE |
| 64 | 06:58:21 | board generation: pill-free board, counters equal `34|34` | in_match | 0.0315 | ALIVE |
| 118 | 07:16:21 | **both bottles completely empty**, counters `29|29` | in_match | 0.0548 | ALIVE |
| 150 | 07:27:01 | board generation, `38|38` | in_match | 0.0432 | ALIVE |
| 162 | 07:31:01 | board generation, `43|43` | in_match | 0.0234 | ALIVE |

The equal-counter + pill-free signature is the new-board generation animation (viruses are placed
in lockstep and the counter counts UP). Each such screen was captured by at most ONE poll — i.e.
they are all far shorter than N = 20 s, exactly as the DRHOLDBOARD timing argument predicts. **The
N > 9.98 s choice was load-bearing and held on real data.**

**This retires limitation #2 in part.** Frame 48 is a REAL non-play capture, and it scored
chrome 0.5479 — well below the 0.90 threshold — so the `in_match` fingerprint's negative side is
no longer synthetic-only. It has still not seen a real title / level-select screen.

### Independent reimplementation cross-check (the watchdog does not grade its own homework)

`independent_verify.py` recomputes `changed_frac`, `pixhash` and `black_frac` from the same 180
saved frames with a **different decoder (Pillow/libpng) and a different differ (numpy)**:

```
frames=180 unique_pixhashes=180 changed_frac range [0.017944, 0.284651]
below_floor=0 field_mismatches=0 verdict_mismatches=0 AGREEMENT=True
```

**All 180 frames are pixel-distinct** — the display never repeated a single frame in 60 minutes.
The verifier's own self-test is mutation-killed in both directions (`--selftest`): a
"always-static" mutant, an "always-alive" mutant and an inverted-black-detector mutant each exit
1; the unmutated file exits 0.

### The capture channel was tested for REAL, not just injected

Mutant C2 injected capture failures through `--offline-frames MISSING`, bypassing the actual
subprocess and network code. Both real paths were exercised here with a `PATH` shim (zero device
contact):

| shim | path exercised | result |
|---|---|---|
| exits non-zero | `subprocess.run` rc≠0 branch | `SUSPECT, SUSPECT, WEDGED capture_dead`, exit 2 |
| never answers | `subprocess.TimeoutExpired` branch | same, **capture_ms = 20 020 each, capture_dead in 61 s** |

⇒ **Real freeze-5 detection latency is 61 s** (3 × (capture_timeout 12 s + 8 s grace)), not
3 × 20 s of wall-clock interval. Worth knowing before anyone tunes K_cap.

### Cost and politeness, measured over 180 real captures

`capture_ms` mean **3004 ms**, max 6077 ms (first call only, the LAN discovery scan), all 180
captures succeeded (`capture_ok` 180/180). At N = 20 s that is a **15.0 % duty cycle**, 3
captures/min. Resolution was a constant 256×448 across all 180 polls, so the
`size_mismatch ⇒ changed_frac 1.0 ⇒ ALIVE` branch never engaged.

### NEW limitations found by this validation

5. **`misterclaw-send` silently falls back to LAN auto-discovery.** Given an unreachable host it
   scans the network and uses whatever MiSTer it finds: `-H 10.42.0.99` returned the real board's
   screen in 5.1 s, rc=0. Today that is harmless (`discover` finds exactly ONE board, the soak
   box) but it is a genuine **false-negative vector**: with a second MiSTer on the LAN the
   watchdog could report a healthy board's frames while the soak box is wedged, and nothing in
   the log would reveal it.
6. **The log does not record WHICH host each frame came from.** There is no `host`/`ip` field in
   the `framewd/1` record, so frame provenance cannot be audited after the fact. Combined with
   limitation 5 this is the weakest point in the architecture. Cheap fix: log the resolved IP per
   poll and alarm on it changing. NOT applied here — the file is validated as-is and changing it
   would invalidate the run above.
7. **Zero real WEDGED events were observed.** The frames channel's positive side is still
   evidenced only by mutants A/C/D/E/H, never by a real wedge on real hardware, because the soak
   stayed healthy for the whole window. This validation bounds the FALSE-POSITIVE rate (0 in 180
   polls / 59.6 min spanning ~41 matches and 5 non-play screens); it does not measure the
   false-negative rate on a real freeze-5.

### Verdict

Over 59.6 min the old discriminator raised 19 alarms and the new one raised none, on a system
proven healthy by decoded in-game state (~41 completed matches). **The 2026-08-09 finding stands
and is now quantified: the old signature's false-positive rate on healthy CvC play is ~100 %
of its firings (19/19), while the frame watchdog's is 0/180 polls.** Evidence:
`results_live_validation/` (watch.jsonl, wedge_probe_slice.txt, h2h.json,
independent_verify.json, capture_*_test.jsonl, 9 frames + 2 counter montages).

## ★★★ MORNING BRIEFING (2026-08-10) — the replacement watchdog, its hole, and what the old probe cost us

*Written overnight for the owner. Nothing below is quoted from memory: both batteries were re-run
from a clean tree immediately before this section was written — `frame_watchdog_mutants.py` →
`RESULT: ALL 12 MUTANTS KILLED`, exit 0; `adversarial/adversarial_battery.py` → `attacks that
LANDED: 8/12`, exit 0. Soak integrity re-checked read-only at 2026-08-10T12:15:30Z: pid 525 still
`/media/fat/MiSTer /media/fat/_Console/NES_theta400_20260809.rbf /media/fat/theta400_tuck_demo.mgl`,
uptime continuous at 4 d 13:36, `ENABLE_AUTO_REBOOT=0` at line 72,
`/media/fat/Scripts/wedge_probe.sh` md5 `88f1a92f6cbae1f7c02faf894a1711e8` — unchanged, not
hot-edited, no device-side twin staged.*

### ⚠ LEAD WITH THE HOLE

**The new watchdog is not fit to certify a soak, and the reason is the same shape as the bug it
replaces.** The old discriminator was validated against a control that could not fire, so its
false-POSITIVE side was never tested. The new one was validated against 59.6 minutes of a
demonstrably healthy soak, so its false-NEGATIVE side has never been tested. An adversarial pass
found the gap is not hypothetical:

* **Half the screen dead reads ALIVE.** Freeze P1's entire half of a real soak sequence and let
  P2 play: **7/7 ALIVE**, zero SUSPECT, 14×–44× the change floor, and 4 of 7 samples land inside
  the healthy 60-minute range.
* **One blinking NES tile keeps a dead screen ALIVE forever.** The capture is 256×224
  **pixel-doubled vertically** (measured: 224/224 row pairs byte-identical), so one 8×8 tile is
  128 image px against a 114.7 px floor. The floor is **0.90 tiles, not the ~1.8 tiles claimed
  above** — a 2× error from assuming square pixels. There is effectively no anti-blink margin.
* **Dr. Mario's attract demo reads ALIVE.** Real ROM, idle, sampled at the watchdog's own 20 s
  cadence: **5/5 ALIVE**, 22×–902× the floor, overlapping the healthy distribution. A box with no
  cart loaded, no AI and no soak running is certified healthy indefinitely.

Left running overnight in its current form, this watchdog would report a clean 8-hour soak on a
box sitting in attract mode with a comfortable margin. **Do not quote it as the authority for "N
clean hours" yet.** What it *is* ready for today is the capture channel and the wedge-detector
role — see §8 and §9.

### 1. What shipped (files, all committed, not pushed, not tagged)

| file | what it is |
|---|---|
| `experiments/freeze5_blackscreen/frame_watchdog.py` | the watchdog itself, PC-side, stdlib-only (own PNG decoder) |
| `experiments/freeze5_blackscreen/frame_watchdog_mutants.py` | 12-mutant killed-mutant battery |
| `experiments/freeze5_blackscreen/independent_verify.py` | reimplementation cross-check (Pillow + numpy), itself mutation-killed 3/3 |
| `experiments/freeze5_blackscreen/adversarial/adversarial_battery.py` | 12 attacks, 8 of which land |
| `experiments/freeze5_blackscreen/results_live_validation/` | the 59.6-min live run: `watch.jsonl`, `h2h.json`, `wedge_probe_slice.txt`, `independent_verify.json`, frames |

Commits: `36065a0` (re-derivation) → `5955b1e` (live validation) → `6e22b26` (adversarial) → this
section.

**What it measures.** Frame progress, and nothing else. It never reads `/proc`, so the
busy-vs-blocked confound that killed the old discriminator cannot reach it. Its only device
interaction is `misterclaw-send -H MiSTer screenshot`. There is **no reboot, reload, kill, ssh or
input code path anywhere in the file** — audited: the sole `subprocess.run` is the screenshot
call. Alarming is log + stderr + exit code 2.

**N = 20 s, K = 3, K_cap = 3.** N is bounded *from below* by the longest legitimate static screen
on the autonav cart — the final-board hold, force-released after `DRHOLDBOARD_F` = 600 frames =
**9.98 s** (`FINAL_BOARD_HOLD_REPORT.md:100-103`, scenario C `:149`). N = 20 s > 9.98 s ⇒ two
consecutive captures can never both land inside one hold. K = 3 then demands **60 s of proven zero
change**, 6× the hold cap. Measured cost over 180 real captures: `capture_ms` mean 3004 / max 6077
(first call only, LAN discovery) ⇒ **15.0 % duty cycle, 3 captures/min**.

**Comparison method.** Decoded **pixels**, never file bytes. `changed_frac` = fraction of pixels
whose max per-channel |Δ| exceeds `tol` = 8, thresholded at `min_changed_frac` = 1.0e-3. A
byte-compare is disqualified because two encodings of one frozen framebuffer differ in filter
choice and zlib framing — mutant D proves it on real data (5041 vs 10385 bytes, identical
`pixhash 444467276a70030b`). `screen_class` is diagnostic only and can never suppress a WEDGED
verdict.

### 2. The three mandatory killed mutants — verbatim, from the re-run

```
--- A_static_same_frame  [KILLED]   expected: final=WEDGED reason=frames_static
    exit=2  verdicts=['INIT', 'SUSPECT', 'SUSPECT', 'WEDGED']
    reasons =['first_frame', 'frames_static', 'frames_static', 'frames_static']
    | [2026-08-10T08:14:56-04:00] seq=1 INIT    first_frame         class=in_match changed=n/a static=0 capfail=0
    | [2026-08-10T08:14:56-04:00] seq=2 SUSPECT frames_static       class=in_match changed=0.0 static=1 capfail=0
    | [2026-08-10T08:14:56-04:00] seq=3 SUSPECT frames_static       class=in_match changed=0.0 static=2 capfail=0
    | [2026-08-10T08:14:56-04:00] seq=4 WEDGED  frames_static       class=in_match changed=0.0 static=3 capfail=0  <== ALERT
    | ALERT wedge_confirmed reason=frames_static evidence=.../A_static_same_frame/frames/alerts/wedge_000004_frames_static (NOTHING has been rebooted, reloaded, or killed)

--- B_live_real_pair  [KILLED]   expected: final=ALIVE reason=frames_differ
    exit=0  verdicts=['INIT', 'ALIVE']
    reasons =['first_frame', 'frames_differ']
    | [2026-08-10T08:14:56-04:00] seq=1 INIT    first_frame         class=in_match changed=n/a static=0 capfail=0
    | [2026-08-10T08:14:57-04:00] seq=2 ALIVE   frames_differ       class=in_match changed=0.089355 static=0 capfail=0

--- C_black_frozen  [KILLED]   expected: final=WEDGED reason=frames_static_black
    exit=2  verdicts=['INIT', 'SUSPECT', 'SUSPECT', 'WEDGED']
    reasons =['first_frame', 'frames_static_black', 'frames_static_black', 'frames_static_black']
    | [2026-08-10T08:14:58-04:00] seq=1 INIT    first_frame         class=black    changed=n/a static=0 capfail=0
    | [2026-08-10T08:14:58-04:00] seq=2 SUSPECT frames_static_black class=black    changed=0.0 static=1 capfail=0
    | [2026-08-10T08:14:58-04:00] seq=3 SUSPECT frames_static_black class=black    changed=0.0 static=2 capfail=0
    | [2026-08-10T08:14:58-04:00] seq=4 WEDGED  frames_static_black class=black    changed=0.0 static=3 capfail=0  <== ALERT

--- C2_capture_dead  [KILLED]   expected: final=WEDGED reason=capture_dead
    exit=2  verdicts=['SUSPECT', 'SUSPECT', 'WEDGED']
    reasons =['capture_fail', 'capture_fail', 'capture_dead']
    | [2026-08-10T08:14:58-04:00] seq=1 SUSPECT capture_fail        class=none     changed=n/a static=0 capfail=1
    | [2026-08-10T08:14:58-04:00] seq=2 SUSPECT capture_fail        class=none     changed=n/a static=0 capfail=2
    | [2026-08-10T08:14:58-04:00] seq=3 WEDGED  capture_dead        class=none     changed=n/a static=0 capfail=3  <== ALERT
```

B is the important one: **those are the exact two frames (21:45:01 → 21:45:52, VIRUS 47/26 →
45/32) over which the OLD discriminator was firing `ALERT_ONLY`.** C2 is the truer freeze-5
signature under the standing METHOD RULE — the screenshot service stops answering at all.

### 3. Live head-to-head against the running soak — 19/19 contradictions

59.62 min, 2026-08-10T10:37:04Z → 11:36:41Z, 180 polls at N = 20 s, while the old probe kept
polling the same box every 30 s.

| | old `/proc` discriminator | new frame watchdog |
|---|---|---|
| polls in window | 120 (30 s) | 180 (20 s) |
| `fw_state=R` | 120/120 | n/a — never reads /proc |
| `busy_frac ≥ 100 %` | 70/120 | n/a |
| **verdict** | **19 × `ALERT_ONLY`** | **179 ALIVE + 1 INIT, 0 SUSPECT, 0 WEDGED, 0 capture failures** |

`contradictions_old_alert_new_alive = 19`, `agreements_old_alert_new_wedged = 0`. Margin at those
19 instants: **18×–107×** the floor. Ground truth was established *semantically*, not from pixel
deltas alone — the in-game VIRUS counters were decoded from all 180 frames (15 distinct P1 values,
38 distinct P2 values, labelled by eye from montages), giving **~41 completed matches in 59.6 min**,
one per ~87 s. Five polls landed on non-play screens and none produced even a single SUSPECT.

**Two honest caveats on this head-to-head.** (a) Because 179/179 new polls were ALIVE, *any*
alignment yields 19/19 contradictions — this refutes the old probe, it does **not** test the new
one. (b) A real documentation defect: the per-alert table in the section above lists the alert
instants 30 s early (`10:39:05Z` etc.). Those are the *preceding* poll, at `consec=5`; the actual
`ALERT_ONLY` lines are at `10:39:35Z` etc., which is what `h2h.json` correctly used. Immaterial to
the result, corrected here for the record.

### 4. The adversarial pass — 12 attacks, 8 land. Verbatim.

Every attack was reproduced by running the real `frame_watchdog.py` against committed real inputs
(live-soak captures + real ROM captures taken off-device in fceux). **Zero device contact.**

```
--- GEOM floor is ~1 NES tile, not ~1.8
    ATTACK LANDS: 224/224 row pairs identical => 2x vdouble; floor 114.7 px = 0.90 NES tiles (writeup claims ~1.8, which assumes SQUARE px)
--- PARTIAL WEDGE: P1 bottle frozen
    ATTACK LANDS: 7/7 ALIVE, no SUSPECT; changed_frac 0.015459-0.044102 = 15x-44x the floor; roi note never fires (ROI spans BOTH bottles)
--- PARTIAL WEDGE: P1 ENTIRE HALF frozen
    ATTACK LANDS: 7/7 ALIVE, no SUSPECT; changed_frac 0.014474-0.043719 = 14x-44x the floor; roi note never fires (ROI spans BOTH bottles)
--- BLINK FLOOR: half a tile (8x8 img px)
    watchdog survives: changed_frac 0.000558 (0.56x floor) -> correctly WEDGED
--- BLINK FLOOR: ONE 8x8 NES tile
    ATTACK LANDS: changed_frac 0.001116 (1.12x floor) -> ALIVE forever on a dead screen
--- BLINK FLOOR: two tiles
    ATTACK LANDS: changed_frac 0.002232 (2.23x floor) -> ALIVE forever on a dead screen
--- SIZE FLAP fails OPEN
    ATTACK LANDS: identical FROZEN content, alternating height -> 7 x ALIVE with changed_frac=1.0 (compare() maps size_mismatch to MAXIMUM motion)
--- ATTRACT DEMO reads ALIVE
    ATTACK LANDS: 5/5 ALIVE at 20 s cadence; changed_frac 0.022147-0.901873 = 22x-902x floor -- overlaps the healthy soak range [0.017944, 0.284651]
--- real idle LEVEL-SELECT -> WEDGED
    watchdog survives: ['INIT', 'SUSPECT', 'SUSPECT', 'WEDGED', 'WEDGED'] (pixel-exactly static; alarm is correct for a soak, but reason='frames_static' names the display path, not the nav stall)
--- DEAD SENSOR reported ALIVE (stale frame-dir)
    ATTACK LANDS: ['INIT', 'ALIVE', 'ALIVE', 'ALIVE'] -- capture wrote NOTHING; watchdog re-read the PREVIOUS run's frames. No mtime/freshness check: existence+size only. Default --frame-dir is a FIXED path and seq always restarts at 1, so a restart re-enters used sequence numbers
--- CAPTURE rc!=0 (empty frame-dir)
    watchdog survives: ['SUSPECT', 'SUSPECT', 'WEDGED', 'WEDGED'] -> capture_dead
--- CAPTURE rc=0 but no file (empty frame-dir)
    watchdog survives: ['SUSPECT', 'SUSPECT', 'WEDGED', 'WEDGED'] -> capture_dead

==============================================================================
attacks that LANDED (watchdog defect reproduced): 8/12
  * GEOM floor is ~1 NES tile, not ~1.8
  * PARTIAL WEDGE: P1 bottle frozen
  * PARTIAL WEDGE: P1 ENTIRE HALF frozen
  * BLINK FLOOR: ONE 8x8 NES tile
  * BLINK FLOOR: two tiles
  * SIZE FLAP fails OPEN
  * ATTRACT DEMO reads ALIVE
  * DEAD SENSOR reported ALIVE (stale frame-dir)
```

Graded, including everything that only **WEAKENS** (these are not dismissals — they are defects
whose *trigger* is not demonstrated on this hardware, while the *mechanism* is fully demonstrated):

| # | attack | grade | note |
|---|---|---|---|
| 1 | legitimately-static screens (title / level-select / final-board hold / between-match / menu / screensaver) | **CLEARED** | real ROM captures: idle title *animates*; idle level-select is pixel-exactly static → WEDGED at 60 s, which is a **true** alarm on a soak (a nav stall is a failure) but the reason string blames the display path. `MiSTer.ini` on the box has **no** `video_off` and **no** screensaver key — one .ini line away from a `frames_static_black` false positive indistinguishable from freeze-5 |
| 2 | partial wedge — one player's side dead | **REFUTES** | 7/7 ALIVE at 14×–44× floor; `DEFAULT_ROI=(28,84,227,402)` spans BOTH bottles (measured P1 x[32,95), P2 x[160,223)) so `roi_static_streak` can never fire. Audio-dead and input-dead wedges are invisible by construction — no such channels exist |
| 2b | attract demo | **REFUTES** | the strongest result; see the hole above |
| 2c | floor mis-calibrated 2× | **REFUTES** | vertical pixel-doubling measured, not assumed |
| 2d | `size_mismatch` fails **OPEN** | **WEAKENS** | `compare()` maps "I cannot compare these" to changed_frac = **1.0**, i.e. maximum motion. A single resolution flap during a real wedge buys one free ALIVE that resets `consec_static`. Untested branch — the live run was 256×448 on all 180 polls. Correct behaviour is SUSPECT |
| 3 | capture-path failure (hang / rc≠0 / truncated PNG / stale cached image) | **CLEARED** | all four fail **safe** → `capture_dead` or `frames_static`. Real-binary probe: `--output` into a nonexistent dir returns rc=1 "Error: writing file" |
| 3b | dead sensor reported ALIVE by replaying the previous run's frames | **WEAKENS** | reproduced end-to-end: restart into the same frame-dir with a sensor that returns rc=0 and writes nothing ⇒ INIT/ALIVE/ALIVE/ALIVE with changed_frac **byte-identical** to the healthy run, while the device could be powered off. `capture()` checks existence + size, never mtime or inode; `--frame-dir` defaults to a fixed path and `seq` restarts at 1 |
| 3c | the watchdog does not know which board it is watching | **WEAKENS** | confirmed again by me at 12:15Z: the default host `MiSTer` is **not reachable**, every capture comes from a LAN auto-discovery scan, and the `framewd/1` record has **no host/ip field** — frame provenance cannot be audited after the fact. Harmless while exactly one board answers; a silent false-negative vector the moment there are two. Also: `misterclaw-send screenshot --help` does not print help, it **takes a screenshot** |
| 3d | documented hang latency measured on the wrong path | **WEAKENS** | in production the IP **is** cached, so `capture()` tries `[cached_ip, host]` = two full timeouts. Measured `capture_dead` at **81 s** after the last good frame, not the reported 61 s (+33 %). Detection still happens; K_cap is denominated in capture-timeouts, not intervals |
| 4 | is the head-to-head genuinely over the same window? | **CLEARED** | old slice `10:37:04Z–11:38:18Z` is a **superset** of the new window; 142 slice lines = 122 polls + 20 alerts; all 180 h2h rows carry an `old_ts`. Plus the 30 s label defect noted in §3 |

**The fix for the three REFUTES is already in the file and merely disabled.** `screen_class`
correctly labels attract/title frames `other` (chrome 0.0) — it is just forbidden from acting on
it; and the ROI machinery exists but spans both bottles. See §8.

### 5. Re-derivation verdicts — every claim, marked

| claim | mark | why |
|---|---|---|
| **AUTO_REBOOT #1**, 2026-08-05T11:59:15Z, as a *timestamped wedge* | **UNRECOVERABLE** | `busy_frac`/`consec` did not exist before 11:56:14Z; CONSEC ran 1→6 with no reset and fired at **exactly** `CONSEC_NEEDED × INTERVAL` = 3m01s after the discriminator was first armed. It fired at the earliest instant it physically could. The timestamp carries zero information |
| the *underlying fault* around #1 | **SURVIVES** | independent: `duel_ledger/ledger_20260805_0638_v3.csv` shows the save-state path dead 11:26:39Z → 11:59:47Z (STALE_x1…x11), and STALE_x4/x5 sit inside CAPTURE #1's confirmed black-screen window. But that run *starts 11 min before the probe existed* and *survives the manual 11:43 reboot* — so the fault does not attach to the 11:59:15Z moment |
| **AUTO_REBOOT #2**, 12:29:35Z | **DIES — proven false positive** | `ledger_20260805_0800_v3.csv`, inside the continuous CONSEC≥6 window: `12:18:40 mode=4 virus 44/21` · `12:21:44 mode=7 virus 6/18` · `12:24:48 mode=4 virus 43/26` · `12:27:51 mode=4 virus 48/48`. Four distinct captures, three different boards, a mode 4→7→4 transition (match ended, fresh match at 48/48), the last **1m44s before the reboot**. The box was playing and was rebooted mid-match. This was on disk the whole time |
| **AUTO_REBOOT #3**, 13:02:26Z | **UNRECOVERABLE — unexplained** | discriminator only. Tracker stopped ~12:45Z, no PC-side screenshot exists for the 11:30–14:00Z window, dmesg clean, recovery snapshot rotated out. Its timing is fully explained by policy: five ESCALATEs, then AUTO_REBOOT at the first CONSEC=6 whose gap (1971 s) cleared `MIN_REBOOT_GAP=1800` |
| **"OUR IPC IS EXONERATED" (12:45Z)** | **DIES** | read entirely off `WEDGE_CONFIRMED` + `AUTO_REBOOT` inside the tracker-stopped blackout. Its "~30-minute mean-time-to-wedge" is `MIN_REBOOT_GAP`; its "3 minutes of a fresh boot" is `CONSEC_NEEDED × INTERVAL`, and the box booted at 12:29:49Z, not 12:56. Needs re-running against the frame watchdog |
| **arm-1 vs s20b A/B (timing + rate comparison)** | **DIES — positively refuted, not merely unrecoverable** | (a) saturated at its own floor: modal time-to-first-trigger across ~60 core loads is 3m01–3m03s = `6 × 30 s`. (b) it ranks a **verified-healthy** arm as worst: s20b + human cart, display alive by 3 screenshots + a motion check over 47 min, scores 3m01s and logged **96 ALERT_ONLYs during those same "clean" 47 minutes**. (c) it ranks the other verified-healthy arm as best: stock vanilla NES core + Battletoads, no copro at all, scores 7m37s. Both verified-alive arms sit at opposite ends of the range. (d) the A/B's intended readout — AUTO_REBOOT count — was never taken: `ENABLE_AUTO_REBOOT` was already 0, the quoted "6m15s" is an `ALERT_ONLY` |
| arm-1's **screenshot TIMEOUT at 22:35Z** ("the old shipped core wedges too ⇒ s20b/CMD-8 exonerated") | **SURVIVES** | anchored on the METHOD RULE, not on the trigger |
| the **vanilla-core** exoneration | **SURVIVES** | returned frame + 3 distinct md5s = a real motion check |
| **isolation verdict "the CvC driver is the trigger"** | **SURVIVES, DEGRADED** | both anchors are screenshot-based and stand, but what remains is *one* confirmed CvC wedge vs *one* confirmed 47-min human-cart clean run. The **rate** framing is gone |
| clean-hours #1 `WEDGE_PROBE.md:203-222` — "9h19m WEDGE-FREE" | **DIES — VACUOUS** | 1,111 consecutive polls with `fw_pid=none`/`fw_state=DEAD`/`busy_frac=?%`/`consec=0`. The CONSEC gate `[ "$FW_STATE_CHAR" = "R" ] && [ "$BUSY_SPIN" -eq 1 ]` (`:188`) could never be true, and AUTO_REBOOT is gated on CONSEC≥6. The count could not have moved off 3 no matter what the box did |
| clean-hours #2 `WEDGE_PROBE.md:472` — "idle box (core loaded)" | **DIES** | vacuous *and* factually wrong: **no core was loaded**; `fw_cmdline=[DEAD]` for the whole span |
| clean-hours #3 `eval47/MORNING_DIGEST_20260805.md:114` | **DIES** | same figure, same mechanism. ⚠ an identical copy exists in `dr-mario-main-wt/` and still needs the same mark |
| clean-hours #4 `WEDGE_PROBE.md:157` — "~30 min apart vs ~28h clean overnight" | **DIES / UNRECOVERABLE** | the 30 min is `MIN_REBOOT_GAP`; the "~28 h clean" predates the trigger's existence entirely, so it is not an absence-of-AUTO_REBOOT figure — it is an absence of anything |
| clean-hours #5 `README.md:195` — "wedges within 6–30 minutes" | **DIES** | both endpoints are trigger artefacts. The only screenshot-confirmed recurrence interval on record is **~65 min** (freeze #7 → #8) |
| clean-hours #6 — "the 47-min clean run IS the booth condition" | **SURVIVES** | the one figure never defined by AUTO_REBOOT absence: 3 screenshots (23:05 / 23:30 / 23:49:53Z) + a motion check |
| `fw_state=DEAD` spans = "dead framework" | **DIES** | 1,175 DEAD polls in exactly four contiguous spans, **every one starting at uptime 45–46 s** (first poll after a reboot) and ending exactly where a core+mgl argv appears. 1,172/1,175 carry `consec=0` AND `busy_frac=?%` — the fields were never populated. After the bare-argv fix the same condition logs `fw_pid=525, fw_state=R`. Zero DEAD rows in the 4.5 days since |
| "at the menu the framework genuinely blocks, so the signature is absent by construction" | **DIES** | on the 16 later polls where `menu.rbf` is loaded and the framework *is* visible, `busy_frac` reads **100 %** and **99 %**. The menu does not block. The 9h19m control was silent because of the `FW_PID` bare-argv **bug** — a sharper and more transferable lesson than the physics story |

**The strongest single sentence in the whole re-derivation:** the control that certified the old
discriminator's specificity was 1,111 consecutive polls in which the discriminator was
*electrically disconnected from its own input*. It is not a weak control. **It is no control.**

### 6. The ORIGINAL freeze-5 sighting is INTACT

Stated plainly because the correction above is large and it would be easy to over-correct: **the
discriminator was non-specific, not fabricated. The thing it was pointed at is real.** All three
legs were re-verified, and none of them touches `wchan`, `/proc/pid/stack`, `State=R`,
context-switch ratios, `busy_frac` or `consec`.

* **Leg 1 — blank display.** Five black-screen captures decoded pixel-by-pixel: `blackscreen_1348.png`,
  `f5b_a_160947.png`, `wedge2_0051.png` (#4), `wedge3_0157.png` (#5), `wedge7_0457.png` (#7). All
  five: 1598 bytes, md5 `f43cc0e7124d…`, **`black_frac = 1.000000`**, pixhash `97a658c14a1859de` —
  byte-identical across three days. Contrast set from the same rig (`post_recovery_*`, tonight's
  soak frames) is 8,980–9,524 bytes at `black_frac` 0.532–0.550 with all-distinct pixhashes. The
  mid-play freeze family (`wedge_s20b_freeze3_2345.png`, 0.5499 black) is correctly **not** a
  black-screen event, so the classification separates the two freeze families rather than pooling
  them.
* **Leg 2 — dead save-states.** Contemporaneous "STALE ×5" at freezes #4/#5/#7, plus a
  source-level derivation of *why* they return 0 bytes: `savestates.vhd:158` (SAVE_WAITSETTLE
  needs `paused` high for 100 consecutive cycles, resetting on any drop) and `nes.v:343`
  (`corepause_active` additionally requires vblank + a CPU instruction boundary). Hardware
  argument, zero process forensics.
* **Leg 3 — core reload does not clear it, a full reboot does.** Freeze #8 recurred ~65 min after
  #7's menu-cycle recovery; the escalation to a full reboot moved the DHCP lease .226 → .225, an
  independent physical side effect.

**Chronology proves independence decisively.** `wedge_probe.sh` was committed 2026-08-05 07:39:46
EDT (`14bbf28`) and its log's first line is 11:37:47Z (= 07:37 EDT). Every black-screen capture,
both STALE-×5 failures and the freeze-#8 escalation happened **before that**. The discriminator did
not exist when the defect was characterised.

**And the replacement independently agrees.** Feeding the two 2026-08-02 frames to the new
watchdog — built without reference to them — gives `black_frac = 1.0`, `changed_frac = 0.0`,
`max_abs = 0` across captures 2h21m apart ⇒ **WEDGED / `frames_static_black`**.

**What we lost** is the ability to say *when* a wedge started, *how often* it recurs, and *which
arm* is worse. **What we did not lose is the defect itself.**

### 7. Corrections to claims made earlier in this file

History is left in place on purpose; these are the corrections, not edits.

1. §"Comparison method" says the floor is "114.7 px ≈ **1.8 NES tiles**". **Wrong by 2×** — the
   capture is vertically pixel-doubled, so it is **0.90 tiles**.
2. §"Limits" #1 records mutant F as a ">115 px (≈2 tile)" boundary. **The true boundary is ONE
   tile.**
3. §"Limits" #2 ("in_match negative side is synthetic only") is now **retired**: real title and
   level-select captures score chrome 0.0, and real frame 48 scored 0.5479.
4. §"Limits" #3 ("head-to-head not obtained") is **superseded** — it was obtained, read-only, 19/19.
5. §"Live validation" per-alert table lists the 19 alert instants **30 s early**; the true times
   are `10:39:35Z`… as in `h2h.json`.
6. §"Live validation" reports hang detection at **61 s**; on the production path (IP cached) it is
   **81 s**.

### 8. What must happen before this drives ANY automatic action

`ENABLE_AUTO_REBOOT` is 0 and **stays 0**. Nothing in this workflow reboots the board.

**Hard gate — non-negotiable: this must survive a REAL wedge before it drives anything.** The
frames channel's positive side is currently evidenced only by mutants A/C/D/E/H and by the five
committed 2026-08-02/05 black-screen captures. No real freeze-5 has occurred while it was
watching. Arming an action on an instrument whose alarm side has never fired in anger is exactly
the mistake this file already records twice.

Before it may even be *quoted* as a health certificate:

1. **Gate ALIVE on `screen_class == "in_match"`.** Kills attract-mode and title-screen false
   ALIVEs outright. The label already exists and is already correct; it is just forbidden from
   acting.
2. **Split `DEFAULT_ROI` into per-bottle P1/P2 regions and require BOTH to clear the floor.**
   Kills the partial wedge.
3. **Raise `min_changed_frac` to ~5e-3** — still 3.6× below the lowest healthy observation
   (0.017944) — restoring a real anti-blink margin and correcting the pixel-geometry error.
4. **`size_mismatch` → SUSPECT, never ALIVE.**
5. **Capture to a unique per-poll path and require the output file's mtime to postdate the poll
   start.** Kills the stale-frame-dir replay.
6. **Log the resolved host IP every poll and alarm when it changes**; stop relying on LAN
   auto-discovery.
7. **Runtime check that N exceeds the soaked cart's `DRHOLDBOARD_F`.** The whole timing argument
   is coupled to a build-time constant of a *different* artifact with no check that they still
   agree.

Then, and only then: **two-instrument agreement** (capture channel + frames channel, or frame
watchdog + a semantic ground truth) before any action, and the first action should be *notify*,
not reboot. The action path itself needs its own killed-mutant gate — an action that fires on a
wrong input is the failure mode we are already paying for.

### 9. Can soak results be trusted from here on?

**Not on this watchdog's ALIVE alone. Yes for the narrow claim it actually supports.**

* **What it can honestly certify today:** *"the screenshot service answered at every 20 s poll for
  N hours, and the picture was never static for 60 s."* That rules out freeze-5 — black screen,
  dead capture, frozen display — and it is a genuine, tested improvement on nothing. Its
  sensor-failure behaviour is safe in 4 of 5 tested modes.
* **What it cannot certify:** that the AI was playing. Half the machine can be dead, or the box
  can be in attract mode with no cart loaded, and it reads ALIVE with margin.
* **Therefore, until items 1–3 of §8 land:** every soak claim must be paired with a semantic
  ground truth. The tooling for this already exists and already worked on 180 frames — the VIRUS
  counter decode in `results_live_validation/` gave ~41 matches/hour. A save-state ledger
  (`duel_ledger/`) is the other acceptable anchor. **A soak with no semantic anchor is a soak with
  no result**, regardless of what the watchdog logged.
* **Run the capture channel now.** It is anchored on the standing METHOD RULE, it fails safe, and
  it correctly reclassifies all five committed black-screen captures. On the human cart use
  `--profile human`, which keeps the capture channel and disables the frames channel.

### 10. What to do about the historical soak results

**Retract, do not reinterpret.** Every "clean hours" figure defined as absence of `AUTO_REBOOT` is
void — not "uncertain", not "probably fine": the counter that defined it was, for the entire
9h19m control, disconnected from its own input, and elsewhere fires ~100 % false on healthy play
(19/19 tonight, 96 alerts during a verified-clean 47-minute human-cart run).

* **Void:** the 9h19m idle control (all three copies, including the one still unmarked in
  `dr-mario-main-wt/`), the "~28 h clean overnight", the README "6–30 minutes" wedge cadence, the
  "~30-minute mean-time-to-wedge", the arm-1 vs s20b timing/rate A/B, and the 12:45Z IPC
  exoneration.
* **Keep:** anything anchored on screenshots or save-states — the five black-screen captures, the
  STALE-×5 runs, arm 1's 22:35Z screenshot timeout, the vanilla-core motion check, the 47-min
  human-cart clean run (which is still the booth condition), and freeze #8's ~65-min recurrence.
* **Re-run, don't re-read:** the IPC-induction experiment and the arm-1/s20b comparison. Both are
  answerable with the frame watchdog's **capture channel** plus a save-state ledger, and neither
  needs the old discriminator at all.
* **No "N clean hours" figure has ever been computed for the current θ400 soak,** and none should
  be quoted until §8 items 1–3 land. The recovery log holds 1,111 `WEDGE_CONFIRMED` and 1,112
  `ALERT_ONLY` events firing every ~3 min continuously from 2026-08-08T02:04:17Z to
  2026-08-10T10:33:18Z on a box that is demonstrably playing. That is the number to distrust, not
  to average.

**Bottom line for the morning:** the old watchdog is disqualified and its damage is bounded and
enumerated; the original freeze-5 defect is intact and independently re-confirmed by the new
instrument; the new instrument is a real improvement with a real hole on the ALIVE side, that hole
is measured rather than suspected, and four of the seven fixes use machinery already sitting in
the file. Nothing was rebooted, reloaded, killed, or written to the device at any point, and the
θ400 soak is still running.
