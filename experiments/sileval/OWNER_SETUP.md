# OWNER_SETUP — what you do by hand vs what is automated (sileval lane)

## You (owner), by hand — ~15 minutes total

1. **SD load** (if you prefer SD-in-hand over scp): copy the contents of
   `experiments/sileval/out/newmister_bundle/` onto the new box's SD card:
   - `_Console/` → `/media/fat/_Console/`
   - `games/NES/` → `/media/fat/games/NES/`
   - `sileval_ship.mgl`, `sileval_p1slice.mgl`, `SILEVAL_BOX_ID` → `/media/fat/`
   (Skip this if you'd rather I scp it all once the box is on the network —
   then you only do steps 2–3.)
2. **Network**: ethernet in, boot, read the IP from the MiSTer OSD
   (Menu → System info) or your router's client list.
3. **Tell me the IP.** That's the whole handoff — one string.
4. *(Recommended, once, because both MiSTers share the same default MAC)*:
   give the new box a distinct MAC in `/media/fat/linux/u-boot.txt`
   (`ethaddr=...`) or a router DHCP reservation, so the two boxes can't
   shadow each other on the subnet.

## Me (automated), once I have the IP

- ssh key install + box identity checks (`SILEVAL_BOX_ID` sentinel; refuse to
  act if the IP is the live soak box).
- scp the bundle (if you skipped step 1) and md5-verify every file ON the SD.
- Fingerprint gate: cold-boot RNG check, silicon fingerprint board set,
  hash-the-cart-that-boots on every load.
- Seedjit template capture per arm + the same-seed/different-seed validity gate.
- Hardened-cart shakedown (70a857cc, 4ac725cf): boot + 10-min stability +
  save-state decode each.
- The DRP1SLICE A/B itself (`drm-sileval-ab` unit) — but ONLY after the prereg
  is registered (team-lead endpoint review pending).
- Optional unattended soak of any staged cart (`drm-sileval-watchdog` unit,
  its own log).

## What never happens

- No file on the LIVE soak MiSTer is read, written, or loaded by this lane.
- No SD write by me — SD content arrives via your copy or via scp to the
  new box only, and nothing is overwritten (every filename carries its hash).
- The DBLCANON core is staged, not activated; activating it is your call.
