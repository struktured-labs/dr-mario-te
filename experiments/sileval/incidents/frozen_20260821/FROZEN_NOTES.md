# Incident: overnight silicon freeze — DBLCANON core x hardened-prestart cart
2026-08-21, new MiSTer 10.42.0.233. OUT OF A/B PREREG SCOPE (different cart+core pair).

## The frozen pair (hashed ON CARD while frozen)
- cart `drmario_hardened_prestart_4ac725cf.nes` = `4ac725cf` (DRPRESTART=1, DRVERFIX-bearing hardened line)
- core `nes_theta400dblcanon_20260819.rbf` = `974de3ed` (DBLCANON — first-ever silicon soak of this pairing)
- Main `9d5f18d3` (update_all 260707), box booted ~04:53 UTC, demo (BEST_AI_demo.mgl) from ~05:01 UTC.

## Evidence
- Video frozen mid-match: FIVE screenshots byte-identical md5 `41950808…` spanning
  10:11:32 → 10:58:54 UTC (team-lead's pair + my 3-shot motion check + OSD probes).
  Frame: both bottles near-full (near-death regime), VIRUS counter digits blank/garbled,
  pill mid-throw. Cross-ref `dr-mario-clean-failure-geometry` (the tail regime) and the
  #129 render-family (counter region anomaly is render-state, not proof of RAM corruption).
- Scaler/cmd-pipe path ALIVE throughout: screenshots return fresh files on demand;
  misterclaw `status` answers; device hotplug at 10:13 UTC (sileval-inputd input11)
  was processed by main AFTER the video froze (fd open in main's table).
- Input→core dead: F12 OSD no-op via BOTH virtual keyboards (sileval-inputd event5 and
  misterclaw event4 — the latter present since boot, pre-freeze). OSD requires the
  core-side user_io bridge; its silence while the scaler lives localizes the wedge to
  the CORE/bridge, not the framework process.
- Savestate REFUSED on every channel: hotkey saves to slots 1/2/4 produced no .ss
  (team-lead's attempts + my explicit 3-slot attempt at ~11:01 UTC; savestates dir
  unchanged since 02:46). Main 260707's cmd pipe has NO savestate verb (strings-checked)
  — the hotkey/bridge path is the only trigger and it is the dead path.
  POSITIVE CONTROL: the identical channel chain produced 1,327,112-byte saves on this
  box yesterday (θ400 core, ship cart) — the refusal is state-specific, not tooling.
- MiSTer main thread: R/running, wchan=0, ~one full core, load pinned 1.00; cumulative
  CPU ≈ entire uptime, so the hot loop alone cannot date the freeze onset.

## Verdict (bounded)
RAM capture EXHAUSTED — no channel can snapshot the NES state without the core's
cooperation, and the core's HPS bridge is the wedged component. The banked record is:
frozen-frame evidence + save-refusal evidence + alive-scaler control, which together
form the freeze-family signature ("savestate refused while scaler alive").
NOT the known checkVerMatch hang (cart carries DRVERFIX) — either a distinct mechanism
or the untested DBLCANON x prestart pairing. Cross-ref: the OLD box's CvC/autonav
black-screen wedge family (userspace-spin main, scaler-alive variant differs) and
[[dr-mario-prestart-tuck-wedge]] (#115, reopened).

## Replay lever (recorded, not run)
The demo cart's seed is boot-deterministic: a cold reload of BEST_AI_demo.mgl replays
the same match sequence from the same constant seed. If the freeze is deterministic,
re-running the demo (~5-6 h unattended) reproduces it at the same match — the cheapest
next probe, and it can run overnight WITHOUT touching the A/B (needs an owner/lead
scheduling call; the A/B owns the box today).

Raw artifacts (incl. team-lead's originals + dmesg): `out/artifacts/frozen_20260821/`
(session-local); tracked copies of the load-bearing items sit beside this file.
