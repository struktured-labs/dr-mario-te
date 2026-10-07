# RESULT (a16mt lane, 2026-10-07): A16 firmware and a MIN_THINK −4 f cart for FAIR2PLUS. STAGED, NOT DEPLOYED

STEER13 (h16 `experiments/cvx/RESULT_STEER13.md`, 7fee23d5) recommended couch-testing two changes on the FAIR2PLUS bot
(cart 5a1695da + V11 rbf 43aa62d5):
- **A16:** the DIST60 endgame target gate widened from ≤ 4 to ≤ 16 viruses (+2.94 pp vs dr. lulu under silicon-like
  execution).
- **MT2:** the cart's MIN_THINK commit gate cut from GO + 6 f to GO + 2 f (+4.75 pp in the anytime-commit model).

Both are built here as one-variable changes reproduced from main 530f0316.

## Short answer
1. **MT2 has no measured benefit in the real cart. NOT RECOMMENDED for the couch.**
   - The cart (`170f179d`) passes every cart gate.
   - In chained + garbage Mesen replays it commits ~1.7 f earlier but locks every pill at the SAME frame.
   - The descent is started by the slam gate, not by the commit:
     - ≥ 10 viruses: the published answer must be stable for `DRSLAM_KOPEN` = 32 hooks (16 f);
     - < 10 viruses: DONE (`K_END` 255);
     - capsule low (Y < 8): `K_CROSS` 8 hooks.
   - STEER13's model starts the descent at the commit, so its −2.15 f/pill and +4.75 pp do not carry over.
   - What MT2 does change is which answer the capsule moves on. It landed 3 of 1,197 pills on an earlier, non-final
     published answer where FAIR2PLUS landed the final. It created no hybrids.
2. **A16 is built, gated and compiled.**
   - Firmware `b545d740` = V11 + `DRDIST_VK=16`, one byte from V11.
   - rbf seed 21 `e00a764e` is SHIP AS-IS: copro +0.418 ns, pll_hdmi +0.052 ns. Seed 3 failed pll_hdmi.
   - FW-in-image 16/16. Every firmware gate passes.
   - Verilator co-sim: A16 == V11 on every ≤ 4-virus board (103/103) and on a > 16-virus sample (109/109). On 5..16
     viruses it changes the final on 75/512 pills (14.6%), at +0.01 f median first-publish latency.
   - In the replays the FAIR2PLUS cart executes the A16 answer on 71/75 of those pills. On the other 4 the A16 answer
     arrives only at DONE (33-47 f), LATEGUARD keeps the earlier (= V11) answer, and the landing equals V11's.
   - 0 hybrids.
   - **The A16 candidate = ANTIBODY_DIST_A16_FAIR2PLUS (cart 5a1695da + rbf e00a764e). It is ready for a silicon
     soak, then the couch.**
3. **Combined certificate = the couch candidate: FAIR2PLUS 5a1695da (cart unchanged) on V11 + A16.** Over 1,197
   replayed pills:
   - FAIR2PLUS on V11 + A16: 1,141 ==final / 0 hybrids / 21 frozen;
   - FAIR2PLUS on V11: 1,145 / 0 / 17;
   - the 4-pill difference is the 4 late A16 answers, which land exactly where V11 lands them.
   - The cart gates do not depend on the firmware.
   - MT2 on A16 was also replayed (1,139 / 0 / 23) as evidence only. It is not in the kit.

## 1. MT2: FAIR2PLUS + `DRMINTHINK=4`
**Build** (`tools/a16mt/build_carts.sh`):
- Negative controls: FAIR2PLUS flags with MIN_THINK unset and with `=12` explicit rebuild **5a1695da**; FAIRPLUS flags +
  `=12` rebuild **5b3d8183**.
- Candidate **`170f179db8d63c24a0b1bcd747c9df7e`**. It differs from 5a1695da in exactly 2 bytes, the two `CMP #$0C`
  immediates of the commit gate (`p2_orient_ok` and DRPROPHFIRST's `pf_skip`), now `#$04`. MIN_THINK counts hooks, at
  2 hooks per frame.

**Gates** (`experiments/a16mt/GATES_CART.txt`, `tools/a16mt/gates_cart.sh`): all PASS.

| gate | FAIR2PLUS | FAIR2PLUS + MT2 |
|---|---|---|
| `tools/gate/run_cart_gates.sh` (7 suites; gravity fidelity over every arm, incl. the new one) | ALL PASS | ALL PASS |
| gravity fidelity, seeds 5/11/23 × 6000 f (pinned 464a4b75 must FAIL) | PASS ×3 | PASS ×3 (464a4b75 KILLED ×3) |
| `test_lgprestart` (4 seeds × 6000 f; FAIR2 A must show the defect: 16/25 dropped) | 0/24 dropped | 0/30 dropped, LATEGUARD refuses 29 |
| `test_lateguard_census_cut` | GATE_LGCUT PASS | GATE_LGCUT PASS (5 mutants killed) |
| static NMI census, worst admissible frame / 29,780 | 28,001 | 28,001 (immediates only) |
| TAP interface P = 2, 40k f; `everyframe` mutant | PASS | PASS; mutant KILLED |

MIN_THINK touches neither gravity nor the pad path, and the gravity gate confirms it: the unmodified game under the
recorded pads is identical. No new fairness exposure.

**Replays** (`experiments/a16mt/REPLAYS.txt`, section A):
- Mesen, real carts, CHAINED, silicon garbage delivered (`tools/execfid/execfid_probe.lua`). The copro is served from
  Verilator co-sim timelines of the shipped RTL + V11.
- Harness control: the FAIR2PLUS rerun equals the execfid lane's banked `A_lgp_row2` runs pill for pill (0 differences
  in landing or lock frame on all 6 case files).

| set (pills) | FAIR2PLUS ==final / hybrid / frozen | MT2 ==final / hybrid / frozen | lock-frame Δ, same landing | commit Δ |
|---|---|---|---|---|
| FAIR2 games 10/04 (m2g1-3, m4g1, M4G2) + 10/03 G2 (624) | 596 / 0 / 4 | 594 / 0 / 6 | **+0.00 f** (622 pills; 1 faster, 2 slower) | −1.7 f (471 earlier, 1 later) |
| FAIR-owner games 10/04 (m1g1-2, m3g1-3, m5g2) on NEW V11 co-sim timelines (573) | 549 / 0 / 13 | 548 / 0 / 14 | **+0.00 f** (572 pills; 0 faster, 0 slower) | −1.8 f (449 earlier, 0 later) |
| **all 12 sets (1,197)** | **1,145 / 0 / 17** | **1,142 / 0 / 20** | **+0.00 f** (1,194) | −1.7 f |

MT2 changed three landings, all in endgames, each from the copro final to an EARLIER published answer:
- **M4G2 p100** (16 viruses, the knife-edge stretch, landing row 14):
  - MT2 commits the first publish (col 2, at 1.8 f) at f4 and moves there.
  - The final (col 5, 5.9 f) arrives at f8. LATEGUARD prices the 3 presses back as unfinishable and freezes.
  - The pill lands on col 2 (a non-final published answer), 3 f later.
  - FAIR2PLUS was still inside its think gate at f8 and went straight to col 5.
- **M4G1 p130** (3 viruses): the same shape. MT2 lands on the earlier publish a16; FAIR2PLUS lands on the final a22.
  Silicon also landed a16.
- **M5G2 p157** (7 viruses): MT2 lands on the earlier publish a16, 12 f later; FAIR2PLUS lands on the final a28.

**Why the lock frame does not move.** Take m2g2 p60:
- the commit moves f8 → f6, and the lateral moves finish f12 → f11;
- DOWN starts at f21 in both, 16 f after the answer published at f5 (`STABLE_CT2 ≥ K_OPEN`);
- the lock is at f37 in both.

The cart descends only on DONE or on a stable answer. MIN_THINK only bounds when steering may begin, and steering
finishes long before the slam opens. The one place MIN_THINK can change a landing is where gravity binds, and there it
added non-final landings rather than removing any.
⇒ The tempo lever in this cart is the slam stability window (`DRSLAM_KOPEN` / `K_END`), not MIN_THINK. It is untested
here, and lowering it slams on unfinished answers that LATEGUARD cannot take back. It goes to the simulator first.

**Where the slam window lives** (for a later lane; not varied here):
- **Symbol:** `patch_cartridge_copro.py` `K_OPEN` (line ~1236) = env **`DRSLAM_KOPEN`**. The emitter default is 255;
  the couch flag snapshot `experiments/lateflip/couch_c960dd49_flags.json` and every fair cart incl. FAIR2PLUS use
  **32**.
- **Units: HOOKS, not frames:**
  - the slam gate compares `STABLE_CT2` ($6171, hooks the published answer has been unchanged; zeroed on a change and
    at a new pill);
  - the driver runs 2 hooks per frame, so 32 hooks = 16 frames.
- **Test site:** the `dn_p2` slam gate (`LDA STABLE_CT2 / CMP #K_OPEN / BCS dn_p2_go`, ~line 4115), reached only once
  the capsule is aligned and orient-locked and the search is not DONE.
- **In the FAIR2PLUS cart 5a1695da the immediate is the single byte at file offset 0x90C5 ($20).** Measured by
  rebuilding with `DRSLAM_KOPEN=31`: exactly that byte changes, to $1F.
- **Siblings:**
  - `K_END` (`DRSLAM_KEND` 255 = DONE only), used when the BCD virus count is < `VC_ENDGAME` (`DRSLAM_VCEND` 10);
  - `K_CROSS` (`DRSLAM_KCROSS` 8 hooks), used when the capsule is low (Y < `CROSS_LOWY` = `DRSLAM_LOWY` 8).
  - Precedence: low → K_CROSS, else endgame → K_END, else K_OPEN.

## 2. A16: firmware V11 + `DRDIST_VK=16`
**Change:**
- `fpga/copro/dist_6502.py`: `VK` now comes from the env var `DRDIST_VK` (default 4).
- `experiments/reach/build_fw.py`: arg 12 = vk. The build asserts that the dist routine came from this tree and has the
  requested vk.
- Recipe: `build_fw.py 540 OUT 1 1 1 1 1 1 19 8 1 16` → **`b545d74055e4a2b64037e1a3d2c0a150`**.
- The firmware differs from V11 c51d2e21 in ONE byte: `$A422 CMP #$05` → `#$11`.
- On boards with 5..16 viruses the routine now runs the D scan and writes a target.
- On ≤ 4 or > 16 viruses it executes exactly V11's instructions.

**Firmware gates:**

| gate | result |
|---|---|
| identity: `build_fw.py` flag off / vk 4 explicit | c51d2e21, 1488e158, a1ef31c8 byte-identical |
| `gate_dist_fw.py` (py65, emitted target routine vs the Leaf6Decider rule; boards and mutant sample selected by vk) | vk 4 control == banked GATE_DIST record (13,505 synth targets, cycles 11,152 / 16,297); **vk 16 PASS**: 22,646 boards, 0 mismatches, 0 write-count violations, 7 mutants KILLED incl. the vk+1 boundary (`vk5` → vk 17 here, 73 boards); cost median 17,187, **max 28,250 cycles = 0.33 ms = 0.020 f**, once per decision |
| `gate_dist_golden.py` (py65 WHOLE search, engine leaf = golden + HSV + D of the firmware-written target), legacy tree 1f430974 + the leflush lane's gate patch (on main it asserts "golden module shadowed") | vk 4 control == the leflush lane's record line for line (154 / 283 / 60 / 20); **vk 16 PASS**: game 652/652, couch 659/659, synth 60/60, > 16 20/20 == golden mirror; target written == rule on all 1,391; the term moved 133 / 190 / 7 / 0 decisions |
| Verilator co-sim (vsim_pub2 = RTL 3b164c7 + copro6502), A16 vs V11 on the 10/04 + 10/03 G2 couch boards | ≤ 4 viruses **103/103 identical** (publishes with frame times, final, DONE, tuck); > 16-virus sample **109/109 identical**; 5..16 viruses: final changed on **75/512** (m5g2 33/138, m1g2 13/81, m1g1 10/85, m4g1 7/57, m2g2 6/43, m2g3 3/31, G2 2/58, M4G2 1/19); first publish A16 − V11 median +0.01 f (p90 +0.03, max +0.33); DONE median +0.01 f (p90 +0.33) |
| `gate_reach_search` | not re-run: its image is built without DRDIST, so A16 cannot reach it |

**Quartus** (`experiments/a16mt/build_rbf.sh`):
- Setup: full clean compile of the DIST60 RTL 3b164c7 with qsf a7a0ce8b + SEED, one compile at a time, nice 19, in the
  shared fork tree NES_MiSTer-winner. The tree was restored after each compile: 18cf064 / hex f78f1e93 / qsf 701f6962.

| seed | rbf md5 | copro (≥ +0.10) | pll_hdmi (≥ −0.062) | ALMs | verdict |
|---|---|---|---|---|---|
| 3 | ebfb15ba | +0.591 | **−0.596** | 37,687 | FAIL (pll_hdmi) |
| **21** | **e00a764e236d8d9fda0446f1c7273a96** | **+0.418** | **+0.052** | 37,711 (4,199 free) | **SHIP AS-IS**, worst-case margin +0.114 ns |

- Both A16 fits reproduce DIST60's fits at the same seed number for number (ANTIBODY_DIST_BUILD.md: seed 3 +0.591 /
  −0.596 / 37,687; seed 21 +0.418 / +0.052 / 37,711). V11 c51d2e21 had landed elsewhere (seed 3 +0.453 / −0.023).
- The bitstream's placement therefore depends on the ROM contents, as a seed-like lottery.
- FW in image (seed 21): b545d740 is a **16/16 PERFECT BIJECTION**.
  - The V11 control MISMATCHES on exactly the 2 bit-lanes the changed byte touches: (2, hi) and (4, hi), $05 → $11.
  - The 1488e158 control mismatches 16/16.
  - The netlist has the HSV / fallback / DRDIST logic.
- The rbf is unique across 45 archived builds and differs from every V11 / DIST60 rbf (`stage_rbf.sh` refuses
  otherwise).

## 3. Combined certificate: FAIR2PLUS 5a1695da on V11 + A16 (the couch candidate). MT2 on A16 is shown as evidence
**Firmware-independent cart gates.** Every gate in section 1 runs the real emitted driver against a model mailbox: the
gravity, lgprestart, TAP and census gates. The firmware cannot reach them, so they hold for the combination as
measured.

**Firmware-dependent part: chained + garbage Mesen replays on V11 + A16 timelines** (`REPLAYS.txt` section C).
- Each game's A16 timeline is the A16 co-sim on every ≤ 16-virus pill plus V11's records on > 16 viruses.
- `tools/a16mt/merge_timelines.py` verifies that copy is legitimate: ≤ 4-virus pills and a > 16 sample must be
  co-sim-identical to V11.

**Results.** 12 case files, 1,197 pills. Each cell is ==final / hybrid / frozen.

| cart \ timelines | V11 (c51d2e21) | V11 + A16 (b545d740) |
|---|---|---|
| FAIR2PLUS 5a1695da | 1,145 / 0 / 17 | 1,141 / 0 / 21 |
| FAIR2PLUS + MT2 170f179d | 1,142 / 0 / 20 | **1,139 / 0 / 23** |

**Does the A16 gate actually fire on these games?** Yes. Pills where A16's final differs from the DIST4 (V11) final, of
the pills with 5..16 viruses:

| m2g1 | m2g2 | m2g3 | m4g1 | M4G2 | 10/03 G2 | m1g1 | m1g2 | m3g1-3 | m5g2 | total |
|---|---|---|---|---|---|---|---|---|---|---|
| 0/0 | 6/43 | 3/31 | 7/57 | 1/19 | 2/58 | 10/85 | 13/81 | 0/0 | 33/138 | **75/512** |

- The full per-pill list (virus count, V11 and A16 finals, when the A16 final first appears, where FAIR2PLUS landed it)
  is `REPLAYS.txt` section C3.
- The cart lands the A16 final on 71/75.
- 29 of M5G2's 33 changes fall in its long 7-virus stall (p147-p187, the sealed-column game): A16 retargets most pills
  there.

- **Firmware effect at a fixed cart (A16 vs V11):** the 4 "lost" finals are the 4 late A16 answers described above,
  m1g1 p85/p86/p88 (9 viruses) and m1g2 p107 (6 viruses).
  - On each, A16 first publishes V11's answer at ~2.3-2.6 f and switches only at DONE.
  - LATEGUARD refuses the change, so the pill lands exactly where V11 lands it.
  - So no landing is worse than V11's. These are pills where A16's term arrived too late to act.
  - On the 75 pills where A16 changes the answer, it is visible by a median 3.5 f and by ≤ 6 f on 55.
- **Combination (MT2 on A16 vs FAIR2PLUS on A16):**
  - 2 landing changes (M4G1 p130, M4G2 p100), the same mechanism as on V11.
  - Lock-frame tempo −0.00 f (1,195 same-landing pills); commits 1.75 f earlier.
  - No new hybrid, no new refusal class.
- **Scope of these replays:** every case starts from the SILICON board of that pill (chained only across the
  spawn/prestart edge). They measure execution fidelity and timing, not what A16 does to the game's later boards.
  That is the sim's job (STEER13: +2.94 pp).

## 4. What remains for a silicon soak
- **Nothing here ran on a MiSTer.** rbf e00a764e has never been loaded on silicon. rivalmage and bluemage were not
  touched.
- **A16 rbf soak (needs the owner's OK for bluemage):**
  - load + freeze soak of FAIR2PLUS 5a1695da (and the CvC cart 821cafdb) on e00a764e, the same watcher as the V11
    soak;
  - first, a boot / screenshot check that the core comes up.
  - ⚠ CvC carts run DRPRESTART=0, so a CvC soak cannot exercise the couch cart's prestart path.
- **Silicon fidelity in the newly active regime:** a PUBLOG-style capture (silfid lane, dr-mario-rl h16
  `experiments/silfid/`) on e00a764e, checking silicon copro == Verilator on 5..16-virus boards.
  - This is the regime A16 newly activates; capture #3 covered ≤ 20 viruses on V11.
  - The D scan adds ≤ 28,250 6502 cycles before Pass 0, so publish timing shifts by ~0.01-0.02 f there.
- **Couch:** ANTIBODY_DIST_A16_FAIR2PLUS vs dr. lulu and the owner, against FAIR2PLUS as the control.
- **MT2:** no soak recommended.
  - The tempo lever is the slam window (`DRSLAM_KOPEN` 32 hooks / `K_END` 255; location in section 1).
  - It goes to the simulator first, not to a cart.

## Files
- **Cart:** `tools/a16mt/build_carts.sh`, `gates_cart.sh` → `experiments/a16mt/GATES_CART.txt`; test arms in
  `tests/test_gravity_fidelity.py`, `tests/test_lgprestart.py`.
- **Firmware:** `fpga/copro/dist_6502.py`, `experiments/reach/build_fw.py` (arg 12); gates
  `experiments/dist/gate_dist_fw.py`, `gate_dist_golden.py` (vk-aware).
- **rbf:** `experiments/a16mt/build_rbf.sh`, `stage_rbf.sh`.
- **Replays:**
  - `tools/a16mt/pubtrace_games.sh`: co-sim timelines;
  - `merge_timelines.py`;
  - `auto_replays.sh`, `replay_batch.sh`, `replay_table.py`, `report.sh` → `experiments/a16mt/REPLAYS.txt`;
  - `throttle.sh`: PAUSE_A16MT / PAUSE_ALL + a cap of 8.
- **Kit** (dr_mario_rl, not in git): `tmp/couch_kit/a16mt_20261007/`.
