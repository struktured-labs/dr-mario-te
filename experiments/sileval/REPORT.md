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

## NOT yet done (needs ~40 min of idle box, post-release; redo anything that
## spanned the no-video window)
- RE-COPY the fixed MGLs to /media/fat (Main 260707 changed MGL parsing:
  index="0" + absolute path now required; the on-SD copies are the OLD format
  and may silently load core-without-cart) and MOTION-VERIFY the first load
  (2-3 shots, distinct hashes) before anything counts — corevideo's hazard.
- RE-VERIFY the nine bundle md5s (03:00-UTC update_all modified the box) and
  re-confirm the savestate hotkey + inputd under the NEW Main before reuse.
- RECONFIRM THE BOX IP: corevideo reports the new box at 10.42.0.233;
  sileval.env pins 10.42.0.225 (pre-update lease). Resolve with team-lead
  before arming; the sentinel check is the identity backstop either way.
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

## Standing environmental notes
- Owner is power-cycling for SNAC bring-up; two reboots + two power-offs
  observed tonight. All interrupted captures voided.
- Old-box migration rsync (team-lead's lane) will eventually rewrite SD
  content: RE-VERIFY the nine md5s before any A/B row after it runs.
- 4 stale `misterclaw-mcp --host MiSTer` processes from OTHER sessions (Aug 19,
  pts/9,12,15,17) resolve by mDNS name — with the old box off, "MiSTer" may now
  resolve to the NEW box. Not this lane's processes; flagged to team-lead.
