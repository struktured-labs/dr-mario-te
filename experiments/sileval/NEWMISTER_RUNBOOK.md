# NEW MiSTer — day-one runbook (sileval lane)

Scope: bring the NEW box from "on the network" to "sileval A/B running" without
ever touching the LIVE soak MiSTer (10.42.0.x, the box `mister_ip.sh` resolves).
Complements `dr-mario-v8-wt/tmp/mister_dayone_kit/DAY_ONE.md` (the dr. lulu demo
kit — a separate purpose; both kits can live on the same SD).

Owner-manual vs automated split: see `OWNER_SETUP.md`. Everything below that
says "we" is scripted; everything that says "OWNER" needs hands.

## 0. The one hazard to internalize first

**Both MiSTers ship the same default MAC (`02:03:04:05:06:07`).** Consequences:
- ARP/mDNS discovery CANNOT distinguish the boxes. `mister_ip.sh` and the
  `-H MiSTer` skills belong to the LIVE box; nothing in this lane calls them.
  The new box's IP is EXPLICIT, owner-supplied, pinned in `sileval.env`.
- Two identical MACs on one subnet can also confuse the router/ARP tables.
  OWNER: ideally give the new box a distinct MAC (`/media/fat/linux/u-boot.txt`,
  `ethaddr=`) or at minimum a DHCP reservation, before both boxes are up
  simultaneously.
- Every scripted action on the new box first asserts the
  `/media/fat/SILEVAL_BOX_ID` sentinel (only the new box has it) and refuses
  to run if the target IP equals `LIVE_MISTER_IP`.

## 1. Network discovery + ssh (owner tells us the IP)

1. OWNER: connect ethernet, boot, read the IP off the MiSTer OSD
   (Menu → System info) or the router's client list. Tell us the IP.
2. We: `ssh-copy-id root@<IP>` (default password `1`), then verify
   `ssh root@<IP> uname -n` = `MiSTer` and `cat /tmp/CORENAME`.
3. We: pin the IP in `sileval.env` (`NEWMISTER_IP=`), never in any script.

## 2. Bundle copy (keep-versions)

1. We: `./stage_bundle.sh` (already run; re-run any time — every source md5 is
   verified at stage time). Output: `out/newmister_bundle/`.
2. OWNER (SD in hand) or we (over scp once step 1 is done): copy
   - `_Console/*.rbf` → `/media/fat/_Console/`
   - `games/NES/*.nes` → `/media/fat/games/NES/`
   - `sileval_*.mgl` → `/media/fat/`
   - `SILEVAL_BOX_ID` → `/media/fat/`
   Nothing is renamed, nothing overwritten: every artifact carries its md5 or
   date in its filename (pocket-sd-keep-versions rule).
3. We: `ssh root@<IP> md5sum` every copied file against `MD5SUMS.txt`.
   **The copy is not done until the on-SD hashes match.**

Note: the DBLCANON core `NES_theta400dblcanon_20260819.rbf` (`974de3ed`) is
STAGED ONLY — no MGL references it; activating it is a separate owner decision.

## 3. Fingerprint gate FIRST (before any result counts)

New silicon ≠ proven silicon until it recovers known answers:
1. **Hash the cart that boots** — step 2.3 above plus a per-boot check: the
   drivers hash the MGL's cart over ssh immediately before every `load_core`
   (watchdog-MGL-fallback lesson: a silent substitute cart converts a
   deployment failure into fake research).
2. **Silicon fingerprint rig** against the validated board set
   (`silicon_fingerprint_boards.json`, committed-placement readback per
   `dr-mario-silicon-fingerprint-rig`): the new box must reproduce the known
   vrdy24 answers cell-for-cell on the θ400 core before any sileval row runs.
3. Cold-boot RNG check: two power cycles, title save-states, rng0/rng1 must
   read $89/$88 both times (reset-constant seed confirmed on this box too).

## 4. Smoke (15 min)

- Boot `sileval_ship.mgl`: title clean, CvC reaches play, pills place.
- Screenshot service: `misterclaw-send --host <IP> screenshot --output /tmp/t.png`
  (takes a while to come up post-boot — verify core via `/tmp/CORENAME` over
  ssh, don't wait on port 9900).
- Save-state round trip: leftalt+f2, poll remote `stat -c '%s %Y'` until size
  stops moving and mtime advances, scp, `vendor/seedjit_ss.py info` decodes it.
  (0-byte scp = the known save/scp race, not a box fault.)

## 5. Hardened-cart shakedown (independent of the prereg)

`drmario_hardened_all_70a857cc.nes` and `drmario_hardened_prestart_4ac725cf.nes`
are on the SD from step 2. Shakedown = boot each by hand or via a temporary MGL,
confirm title + play + no wedge for ~10 min each, plus one save-state decode.
This is a plumbing check, not an endpoint — no statistics, no prereg claims.
Unattended soak of either cart: `sileval_watchdog.sh` (its own unit
`drm-sileval-watchdog`, its own log — never the live box's).

## 6. Seedjit template capture for the NEW box (per arm)

**The template pins cart+core+frame — a different template is a different
experiment.** The live box's `seedjit_template.ss` (md5 `0d9e7b2f…`) is NOT
reusable here: it pins the old box's cart lineage and, more importantly, a
template must be captured against the exact cart it will inject into.
Per arm (ship, slice):
1. Load the arm's MGL. At t≈1 s after the cart loads (pre-generation window is
   ~1 s wide: mode $00, boards empty; t≈2 s is already mid-generation), trigger
   leftalt+f2.
2. Pull the state (race-guarded), verify with `vendor/seedjit_ss.py info`:
   mode $00, virus counts 0/0, boards empty. If mode ≠ $00, recapture with an
   earlier trigger.
3. md5 the template and pin path+md5 in `sileval.env`
   (`TEMPLATE_SHIP*`, `TEMPLATE_SLICE*`).
4. Validity gate (per template, from the 2026-08-16 validation): inject the
   same seed twice → screenshots 0.00% differing pixels; two different seeds →
   >5% differing. Both must reproduce on the new box before row 1.

## 7. Start the A/B (only after the prereg is REGISTERED)

```
systemd-run --user --unit drm-sileval-ab \
  "$HOME/projects/dr-mario-sileval-wt/experiments/sileval/sileval_ab.sh"
journalctl --user -u drm-sileval-ab -f     # watch
touch experiments/sileval/out/HALT          # graceful stop
```
Resumable: finished (seed,arm) rows are skipped on restart. Cart+rbf hashed
before every boot; hash mismatch halts the run (prereg VOID 1).

## 8. Standing cautions

- Agent timestamps are UTC; MiSTer logs are UTC; local shell is EDT — `date`
  first when correlating.
- Never `pkill` by name; kill exact PIDs.
- The LIVE box's soak, log, SD, and `mister_ip.sh` are out of bounds for this
  lane in every direction.
- A low goes/matches reading is an instrument artifact until re-run + a
  same-runner positive control says otherwise.
