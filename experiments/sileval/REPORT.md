# sileval lane — banked state (2026-08-20 ~22:50 EDT, written under HOLD)

## Completed and verified on the NEW box (10.42.0.225)
- ssh key installed (rw-remount + StrictModes perms fix); passwordless root works.
- `/media/fat/SILEVAL_BOX_ID` sentinel planted.
- FULL bundle on SD, all NINE on-card md5s verified against MD5SUMS.txt:
  cores de7dea35 (θ400) + 974de3ed (DBLCANON, staged-not-activated),
  carts 9fefaedb (ship) / 010f4ffe (slice) / 70a857cc / 4ac725cf, both MGLs.
- Ship cart boots and plays CvC via sileval_ship.mgl (screenshots banked in the
  session scratchpad; virus counts progressing normally, P2 copro dominant).
- Remote channels proven WITHOUT misterclaw: uinput FIFO daemon
  (`/media/fat/linux/sileval_inputd.py` + `sileval_inject.py`) for hotkeys,
  stock `screenshot` MiSTer_cmd for captures. Save-state hotkey lands
  (1,327,112-byte .ss); race-guarded pull works.
- Full driver chain exercised live once (the disclosed accidental cycle,
  quarantined under `out/artifacts/_accidental_*_holdviolation/`): env gates,
  pre-boot cart+rbf hash (matched), seedjit inject of the vendored template,
  slot upload, menu-hop, MGL boot, F1 restore, 4 samples at 20 s cadence
  (decode: mode $04 play, healthy match rollover).

## Release-day gates — ALL PASS (2026-08-21, ~11:00-11:30 UTC, full log in git history)
- STEP 0 forensics: frozen DBLCANONxprestart state captured to the limit of any
  channel; save-refusal documented; un-wedged via load_core menu (no reboot
  needed; main restarts). See incidents/frozen_20260821/FROZEN_NOTES.md.
- Fixed MGLs re-copied; NINE on-card md5s re-verified post-update_all.
- Motion-verified first load under Main 260707: 3 distinct frames. Fixed-MGL
  format loads the cart correctly.
- Channel re-proof: savestate hotkey lands under new Main (1,327,112 B).
- Template validity gate: same-seed 48/48 + 47/47 virus cells, diff-seed
  11/85 + 10/84 — both controls fire. SLICE-arm cycle: same seed reproduces
  the IDENTICAL boards through the slice cart (48/48, 47/47, same evolved
  LFSR $75a6) — the paired-seed premise is silicon-proven on both arms.
- Cold-boot determinism: two uninjected loads byte-identical (46/46, 41/41
  even mid-play; rng frozen at $76/$f0 = the old box's exact constant).
- Cross-box fingerprint: new-box seed-4242 board vs the OLD box's banked
  2026-08-16 verify_4242 save-states — P1 48/48 exact; P2 old is a strict
  SUBSET (46/47; the missing cell is a virus the old snapshot had already
  cleared). Same silicon behavior, same cart+core pair as the A/B.
  HONESTY NOTE: this is a generation+early-play behavioral fingerprint; the
  committed-placement discriminator rig was not reconstructed (its expected
  answers for the theta400 core on the 18-board set were never recorded, so
  there is no old-box reference to compare against).
- Hardened shakedown, 10 min each on theta400: 70a857cc PASS (motion both
  ends, healthy rematch rollover 48/48); 4ac725cf PASS (mid-match 48/43).
  The cart that froze overnight on DBLCANON runs clean on theta400 —
  consistent with a pairing-specific freeze.

## NOT yet done (needs ~40 min of idle box, post-release; redo anything that
## spanned the no-video window)
- RE-COPY the fixed MGLs to /media/fat (Main 260707 changed MGL parsing:
  index="0" + absolute path now required; the on-SD copies are the OLD format
  and may silently load core-without-cart) and MOTION-VERIFY the first load
  (2-3 shots, distinct hashes) before anything counts — corevideo's hazard.
- RE-VERIFY the nine bundle md5s (03:00-UTC update_all modified the box) and
  re-confirm the savestate hotkey + inputd under the NEW Main before reuse.
- IP RECONCILED (2026-08-21, corevideo verification): same unit, lease moved
  .225 -> .233 across the update reboots; sentinel read back verbatim on .233;
  .225 is a dead lease. Env re-pinned to .233. The box now carries a unique
  locally-administered MAC 02:53:49:4c:45:56 ("SILEV") — MAC-collision hazard
  retired for this box, and MAC-scan rediscovery is safe if the lease wanders
  again. Bundle + savestates confirmed intact on .233 by corevideo.
- Same-seed/diff-seed template validity gate (2+1 cycles, cell-set rule).
- Cold-boot RNG read ($89/$88 at title).
- Fingerprint board set.
- Hardened-cart shakedown (70a857cc, 4ac725cf), 10 min each.
- A/B start (team-lead release + ARMED file, in that order).

## Box-side state the owner's power cycles will (correctly) erase
- The input daemon and its FIFO live in /tmp — they die on every reboot and
  are NOT auto-restarted (no user-startup.sh; consent pending). During HOLD
  the lane leaves them down: nothing of ours runs on the box at rest.
- On-SD files at rest: the bundle, the sentinel, the two helper .py files in
  /media/fat/linux — all inert without an ssh command from our side.

## Authorization model (post-incident)
- `out/ARMED` is a physical precondition: the A/B driver refuses at startup
  AND inside every hardware-touching helper (ensure_inputd / send_combo /
  take_shot), and the watchdog refuses at startup, all before any ssh.
  Unarmed refusal re-verified after each change (exit 2, zero network).
- ARMED does not exist while any HOLD stands.

## Outage record — 2026-08-21 07:45-15:15 EDT (~7.5 h, no data harm)
The A/B's first launch exited CLEANLY after ONE pair: every un-flagged ssh in
the seed loop's body read the loop's stdin, so cycle 1 consumed seed 27875 and
ssh consumed the other 239 seeds — "seed list complete" after 13 minutes, and
the monitor treated normal completion as non-alarming (its event also only
DELIVERS at a turn boundary — silent-success is a monitor design fault on two
axes). The one completed pair is clean (18 samples both arms, 0 fails) and is
KEPT; resume skips it. Fixes, each mutant-tested: loop reads fd 3 (slurper-
immune, 10/10 vs old shape's 1/10), ssh -n everywhere, startup FATAL if the
seed list length differs from the registered 240, completion FATAL if OK rows
< 480 at loop end, monitor rebuilt to alarm on unit-inactive-with-incomplete-
ledger. Prereg timeline shifts ~8 h; nothing else changes.

## Standing environmental notes
- DBLCANON status (2026-08-21): the owner ACTIVATED it on the new box during
  their manual A/B (pre-existing BEST_AI_demo.mgl; corevideo only path-fixed
  it). The staged-not-activated constraint now applies only to the OLD box's
  SD copy. The sileval A/B core pin (theta400_20260809, de7dea35) is
  unaffected and was re-hash-verified on-card by corevideo tonight.
- Owner is power-cycling for SNAC bring-up; two reboots + two power-offs
  observed tonight. All interrupted captures voided.
- Old-box migration rsync (team-lead's lane) will eventually rewrite SD
  content: RE-VERIFY the nine md5s before any A/B row after it runs
  (push is --ignore-existing, so bundle files are safe by construction —
  verify anyway, rule 11).
- POLICY (team-lead, 2026-08-21): NO update_all on the new box while an
  experiment is armed or running — the 03:00-UTC run replaced Main (260707)
  and changed MGL parsing under our feet; schedule around mutations, don't
  just catch them.
- 4 stale `misterclaw-mcp --host MiSTer` processes from OTHER sessions (Aug 19,
  pts/9,12,15,17) resolve by mDNS name — with the old box off, "MiSTer" may now
  resolve to the NEW box. Not this lane's processes; flagged to team-lead.

## Ledger close (2026-08-22 ~23:55 EDT, sileval-fable lane)
Final new-box A/B ledger: 410 rows = 255 OK (126 complete pairs = population A)
+ 154 boot-motion VOIDs (the 20:55-22:24 contention storm; seeds retryable but
now moot) + 1 conflated ssh-fail VOID (fixed in 8894c55). Interim instrument
check at the registered n=120 threshold: 4,589/4,589 samples decode, 0
unreadable (run pooled-only; no arm split viewed by this lane). Population B
DECLINED per the close-out (discordance 2.70% [1.55,4.65] => OR>=4 floor);
E1/E4a/E2 verdicts live in the close-out documents, which supersede this
lane's runbook plans. out/ARMED REMOVED — no driver may touch a box again
without a fresh registration and a fresh arm.

CONTEXT NOTE for the record: this lane's session lost several hours of context
(compaction) spanning the evening analysis; everything above the close-out
docs' authority was reconstructed from the git record before any action, and
the only tonight-action this lane took post-loss was read-only (ledger tally +
pooled coverage check) plus this disarm.
