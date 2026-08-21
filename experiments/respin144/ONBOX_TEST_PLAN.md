# respin-144 on-box video gate + liveness plan (10.42.0.233)
DO NOT RUN until team-lead brokers a window (drm-sileval-ab owns the box).
All ssh: `sshpass -p 1 ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@10.42.0.233`
(a promptable connection is a bug). $0 cost. NO SD writes except the ONE flagged below.

## Deploy (no SD)
1. scp rbf -> /tmp/NES_theta400dblcanon_20260821_c0pin.rbf (tmpfs, not SD).
2. md5sum ON BOX must equal the staged rbf md5 (hash the cart/core that booted rule).
3. echo "load_core /tmp/NES_theta400dblcanon_20260821_c0pin.rbf" > /dev/MiSTer_cmd

## MANDATORY VIDEO-OUTPUT GATE (both modes must follow the request)
ADV7513 readout (corevideo procedure): i2c bus 1, addr 0x39
  CTS   = (r(0x04)&0xF)<<16 | r(0x05)<<8 | r(0x06)   -- == pixel clock in kHz @ fs=48k
  VIC   = r(0x3E) >> 2
  PLLOK = r(0x9E) bit 4
Steps:
  a. ini currently video_mode=8 (corevideo workaround). With the NEW core loaded:
     expect VIC=16, CTS=148500 (1080p60 must still work).
  b. ⚠ ONE SD WRITE (needs explicit approval): flip /media/fat/MiSTer.ini video_mode=8 -> 4
     (720p60; backup already exists: /media/fat/MiSTer.ini.corevideo_backup_720p; make a
     fresh /tmp copy anyway). Reload the core. Expect VIC=4, CTS=74250 — THE fix proof:
     the old broken cores emitted CTS=148500 on a 720p request.
  c. Restore video_mode=8 byte-exact from the /tmp copy, reload, re-verify VIC=16.
PASS = requested-mode CTS/VIC matches spec for BOTH 720p and 1080p, PLL locked.
FAIL contingency: workaround ini (video_mode=8) still leaves the box usable; do not iterate
on-box — bring the fit rpt home.

## DEFECT-2 soak-length input-bridge liveness criterion (mechanism = honest unknown)
After the video gate, schedule (owner call, post-A/B): cold reload BEST_AI_demo.mgl (the
boot-deterministic seed replays the same CvC sequence — FROZEN_NOTES replay lever) for
>= 6 h with a probe every 10 min:
  - scaler screenshot (must change hash vs previous — motion rule, 3-frame),
  - OSD open/close via virtual input F12 + screenshot delta (bridge liveness),
  - one savestate attempt per hour on slot 4 (file must appear; refusal while scaler
    alive = the freeze signature, per incidents/frozen_20260821/FROZEN_NOTES.md).
PASS = no freeze-signature event in >= 6 h (vs ~5 h to the original freeze).
A reproduction is ALSO a win: it dates the wedge to a deterministic match index.
