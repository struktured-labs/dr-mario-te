# DRDANGER D4 rbf + bluemage soak (2026-10-16)
- fw 70dad713 (`DRDANGER=1 build_fw.py 540 ... 16`), Quartus seed 21 via `experiments/drdanger/build_rbf.sh` (copy of
  a16mt/build_rbf.sh: tag antibody-dist60-v11-a16-drdanger, controls A16 b545d740 + V11 c51d2e21), clean db.
- verdict: SHIP AS-IS. ALMs 37,711/41,910; copro slack +0.418 ns; pll_hdmi +0.052 ns; FW-in-image PERFECT BIJECTION ==
  70dad713, both controls MISMATCH. **rbf md5 6caf70c9a790c56820b836901602c35a** (!= A16 e00a764e; unique across 47 builds).
- Soak cart: the capture-#3 CvC seat (437cd6aa, the cart A16 was soaked with: PUBLOG3_A16.mgl) rebuilt from
  claude/silfid-publog3 98ba19d7 with the u8 slam gate `DRSLAM_KOPEN=8 DRSLAM_KEND=8` -> **b0a3ce85**; the no-overlay
  and explicit k32/e255 controls rebuild 437cd6aa byte-identically; the diff is exactly the two slam immediates (32->8,
  255->8), as in the couch u8 cart 1ebd386e vs 5a1695da. (The couch u8 cart itself cannot self-soak: human P1.)
- bluemage: `_Console/NES_antibody_dist60_v11_a16_drdanger_seed21_20261016.rbf`,
  `games/NES/drmario_cvcp2_f2p_c3_u8_b0a3ce85.nes`, `DRDANGER_U8_CVC.mgl`, watcher `Scripts/freeze_watch_drdanger.sh`
  (freeze_watch v2.2 with the MGL retargeted) -> /media/fat/freeze_watch.log. Started 2026-10-16 18:33 ET.
