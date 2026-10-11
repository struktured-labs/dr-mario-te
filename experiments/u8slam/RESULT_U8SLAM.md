# RESULT (u8slam lane, 2026-10-11): the slam-gate cut "u8" on the real cart, in chained Mesen replays. EMULATOR ONLY

STEER14 (dr-mario-rl h16 `experiments/cvx/RESULT_STEER14.md`, b18a251e) predicted in the simulator that cutting the
cart's slam stability window to 8 hooks in both phases ("u8": `DRSLAM_KOPEN` 32 → 8, `DRSLAM_KEND` 255 → 8) locks
pills about 9.6 f sooner and still lands about 99 % of them on the copro's final answer. u8 had never run on a cart.
This lane built it and replayed it against today's couch cart (FAIR2PLUS 5a1695da) with the a16mt lane's harness and
corpus: 12 couch games, 1,197 pills, on the V11 (c51d2e21) and V11 + A16 (b545d740) firmware timelines.

## Verdict
**Yes: u8 locks sooner on the real cart, and by about what the simulator said.**

| firmware timelines | lock frame, u8 − FAIR2PLUS, paired over 1,197 pills | ≥ 10 viruses (847) | < 10 viruses (350) | landed on the copro final, FAIR2PLUS → u8 |
|---|---|---|---|---|
| V11 | **−7.57 f** [−8.29, −6.85] | −3.74 f [−4.53, −2.95] | −16.83 f [−17.90, −15.77] | 1,145 → 1,138 (8 lost, 1 gained) |
| V11 + A16 | **−7.54 f** [−8.26, −6.82] | −3.66 f [−4.46, −2.87] | −16.92 f [−17.94, −15.89] | 1,141 → 1,135 (7 lost, 1 gained) |

- Intervals are 95 % t intervals over pills. A bootstrap over the 12 games gives −7.57 {−9.61, −5.12} on V11 and
  −7.54 {−9.52, −5.13} on A16.
- **The cost is 7 net landings in 1,197 on V11 and 6 on A16 (0.6 / 0.5 pp), every one on a non-final PUBLISHED
  answer; 0 hybrids in any cart.**
  - It falls almost entirely on endgame pills whose final answer arrives more than 16 f after the first publish,
    most of them tuck finals, which only exist at DONE. FAIR2PLUS waits for DONE below 10 viruses and lands 10 of
    those 20 pills on the final (V11); u8 lands 4.
  - On the 1,134 non-tuck pills the landed-on-final rate goes 99.56 % → 99.29 %.
- Every cart gate the a16mt lane ran passes on u8, including gravity fidelity and the 1-press-per-2-frames TAP gate.
- **This makes u8 a soak candidate, not a couch result.** What these replays cannot say is in section 6. The main
  open items are what the lost endgame tucks are worth in play, and that u8 doubles the number of searches the cart
  aborts mid-flight (9 % → 18 % of pills), a path the replay serves from clean co-sim timelines.

## 1. The cart
**Build** (`tools/u8slam/build_carts.sh`, FAIR2PLUS recipe + two env overrides):
- Negative controls: FAIR2PLUS flags with the slam window unset and with `DRSLAM_KOPEN=32 DRSLAM_KEND=255` explicit
  both rebuild **5a1695da**.
- Candidate **u8 = `1ebd386e86743e6bb512f645f8cb15b7`**. It differs from 5a1695da in exactly 2 bytes:

| file offset | byte | what | context |
|---|---|---|---|
| 0x90C5 | $20 → $08 | `K_OPEN` (≥ 10 viruses) | `AD 71 61 C9 20` = `LDA STABLE_CT2 / CMP #$20` |
| 0x90D9 | $FF → $08 | `K_END` (< 10 viruses) | `AD 71 61 C9 FF` = `LDA STABLE_CT2 / CMP #$FF` |

- One-variable carts confirm which byte is which: `DRSLAM_KOPEN=8` alone (k8, 4b53df67) moves only 0x90C5;
  `DRSLAM_KEND=8` alone (e8, 1792aecf) moves only 0x90D9. u8 is exactly their union.
- **K_END semantics.** 255 is not handled by separate code. All three phases use the same compare,
  `LDA STABLE_CT2 / CMP #K / BCS dn_p2_go`, and `STABLE_CT2` saturates at $FE, so `CMP #$FF` can never pass: that is
  the whole "DONE only" mechanism. `K_END` = 8 is therefore an ordinary 8-hook (4 f) stability gate below 10
  viruses, which is what was asked for. `K_CROSS` 8, `LOWY` 8, `VCEND` 10 and `DRSLAM_MATURE` 2 are unchanged.

## 2. Cart gates (`experiments/u8slam/GATES_CART.txt`, `tools/u8slam/gates_cart.sh`): all PASS

| gate | FAIR2PLUS | u8 |
|---|---|---|
| `tools/gate/run_cart_gates.sh` (7 suites; gravity fidelity over every arm, incl. the new one) | ALL PASS | ALL PASS |
| gravity fidelity, seeds 5/11/23 × 6000 f (pinned 464a4b75 must FAIL) | PASS ×3 | PASS ×3, no driver store changes world RAM (464a4b75 KILLED ×3) |
| `test_lgprestart` (4 seeds × 6000 f; FAIR2 A must show the defect: 16/25 dropped) | 0/24 dropped | 0/27 dropped |
| `test_lateguard_census_cut` | GATE_LGCUT PASS | GATE_LGCUT PASS (5 mutants killed) |
| static NMI census, worst admissible frame / 29,780 | 28,001 | 28,001 (immediates only) |
| TAP interface P = 2, 40k f; `everyframe` mutant | PASS | PASS; mutant KILLED |

- The gate IRs were checked to carry the new immediates: every u8 arm's driver has `CMP #$08` at all three
  `STABLE_CT2` compares; the FAIR2PLUS arms have $20 / $08 / $FF.
- The lgprestart gate shows the early slam is live in the py65 world: DONEs arriving while the capsule is still
  falling drop from 375 to 322.
- **Fairness.** u8 changes only when DOWN starts to be held. The unmodified game under the recorded pads is
  identical (gravity gate), and the tapped buttons keep their 2-frame cadence (TAP gate). In the Mesen traces
  themselves no cart ever shows an A/B/L/R press on two consecutive frames (0 of about 3,600 press frames per cart
  and firmware). That trace count has no killed mutant behind it; the TAP gate does.

## 3. Replays (`experiments/u8slam/REPLAYS.txt`; per-pill rows in `pills_{v11,a16}.jsonl`)
- Mesen, real carts, CHAINED, silicon garbage delivered (`tools/execfid/execfid_probe.lua`, unmodified). The copro
  is served from the a16mt lane's Verilator co-sim timelines and case files, unchanged.
- **Harness control:** this lane's FAIR2PLUS rerun equals the a16mt lane's banked FAIR2PLUS runs pill for pill on
  both firmwares (0 of 1,197 pills differ in landing or lock frame, twice).
- Lock and DOWN are frames since the spawn. "Disarmed" = `SLAM_ARM` is 0 while the pill's search runs, so the pill
  may only descend at DONE. Strata are fixed before treatment: the virus count of the case board, whether the
  copro's final carries a tuck descriptor, and whether the previous pill took a garbage volley (the pill whose
  search is the DRPRESTART one).

### 3.1 Paired lock frame, u8 − FAIR2PLUS (mean [95 % t over pills] {95 % bootstrap over games})

| stratum | n | V11 | V11 + A16 |
|---|---|---|---|
| all pills | 1,197 | −7.57 [−8.29, −6.85] {−9.61, −5.12} | −7.54 [−8.26, −6.82] {−9.52, −5.13} |
| ≥ 10 viruses | 847 | −3.74 [−4.53, −2.95] {−4.66, −2.87} | −3.66 [−4.46, −2.87] {−4.58, −2.83} |
| < 10 viruses (endgame) | 350 | −16.83 [−17.90, −15.77] {−20.20, −12.34} | −16.92 [−17.94, −15.89] {−20.31, −12.68} |
| tuck pills | 63 / 66 | −7.81 [−11.00, −4.62] {−12.12, −4.46} | −7.27 [−9.99, −4.55] {−10.24, −4.52} |
| pills right after garbage | 83 | −1.37 [−2.82, +0.08] {−2.79, −0.11} | −1.77 [−3.22, −0.32] {−2.69, −0.97} |

- Pills earlier / same / later: 901 / 181 / 115 on V11, 904 / 179 / 114 on A16.
- On the pills that land in the same place in both carts (1,188 / 1,189) the difference is −7.45 / −7.46 f.
- The whole pill cycle shortens by the same amount: spawn to next spawn −7.66 f [−8.62, −6.69] on V11 and −7.94 f
  [−8.95, −6.93] on A16. Nothing after the lock gives the time back.
- Post-garbage pills barely move because their answer is usually DONE before the spawn (74 of 83 already descend
  on DONE in FAIR2PLUS).

### 3.2 Absolute, per cart (V11 timelines; A16 is within 0.5 f and 0.4 pp on every row, see REPLAYS.txt)

| stratum | cart | lock frame, mean (median) | DOWN starts, mean | GO → lock | disarmed pills | DOWN opened by DONE / stability / never |
|---|---|---|---|---|---|---|
| all (1,197) | FAIR2PLUS | 41.77 (40) | f 28.00 | 40.68 | 109 (9.1 %) | 518 / 662 / 17 |
| | u8 | 34.20 (31) | f 18.04 | 32.55 | 218 (18.2 %) | 270 / 911 / 16 |
| ≥ 10 viruses (847) | FAIR2PLUS | 38.69 (36) | f 25.17 | 37.31 | 109 (12.9 %) | 175 / 662 / 10 |
| | u8 | 34.95 (30) | f 20.08 | 33.28 | 195 (23.0 %) | 230 / 605 / 12 |
| < 10 viruses (350) | FAIR2PLUS | 49.21 (50) | f 34.90 | 49.00 | 0 | 343 / 0 / 7 |
| | u8 | 32.38 (32) | f 13.11 | 30.77 | 23 (6.6 %) | 40 / 306 / 4 |

- Paired, DOWN starts 9.94 f earlier overall (5.07 f at ≥ 10 viruses, 21.78 f in the endgame).
- GO → lock excludes the 63-71 pills whose search started before the spawn.

### 3.3 Where the pills land (each cell: == copro final / non-final published answer / hybrid / LATEGUARD-frozen)

| stratum | n | FAIR2PLUS on V11 | u8 on V11 | FAIR2PLUS on A16 | u8 on A16 |
|---|---|---|---|---|---|
| all pills | 1,197 | 1,145 / 52 / 0 / 17 | 1,138 / 59 / 0 / 16 | 1,141 / 56 / 0 / 21 | 1,135 / 62 / 0 / 19 |
| ≥ 10 viruses | 847 | 808 / 39 / 0 / 6 | 807 / 40 / 0 / 7 | 808 / 39 / 0 / 6 | 805 / 42 / 0 / 9 |
| < 10 viruses | 350 | 337 / 13 / 0 / 11 | 331 / 19 / 0 / 9 | 333 / 17 / 0 / 15 | 330 / 20 / 0 / 10 |
| tuck pills | 63 / 66 | 16 / 47 / 0 / 13 | 12 / 51 / 0 / 9 | 15 / 51 / 0 / 17 | 12 / 54 / 0 / 12 |
| non-tuck pills | 1,134 / 1,131 | 1,129 / 5 / 0 / 4 | 1,126 / 8 / 0 / 7 | 1,126 / 5 / 0 / 4 | 1,123 / 8 / 0 / 7 |
| right after garbage | 83 | 82 / 1 / 0 / 0 | 82 / 1 / 0 / 0 | 82 / 1 / 0 / 0 | 82 / 1 / 0 / 0 |

- **Tuck pills already land off the final in today's cart** (47 of 63). A tuck final is only delivered at DONE, and
  at ≥ 10 viruses FAIR2PLUS has usually slammed on the earlier answer by then. What u8 adds is the same loss in the
  endgame, where FAIR2PLUS used to wait.
- **The exposure is the late final** (V11; `tools/u8slam/late_finals.py`):

| the final becomes the standing answer | pills (tuck) | FAIR2PLUS == final | u8 == final |
|---|---|---|---|
| with the first publish, or ≤ 4 f after it | 1,039 (0) | 1,039 | 1,039 |
| 4-16 f after the first publish | 88 (2) | 85 | 84 |
| > 16 f after, ≥ 10 viruses | 50 (48) | 11 | 11 |
| > 16 f after, < 10 viruses | 20 (13) | 10 | **4** |

- The pills whose landing changed (V11: 9; all in REPLAYS.txt with their DOWN and lock frames):
  - final → earlier published answer, endgame: m2g2 p76, p82, p99 and m1g2 p106 (tucks); m1g1 p127, m4g1 p124,
    m5g2 p158 (a late non-tuck final, refused by LATEGUARD once the pill is descending);
  - final → earlier published answer at exactly 10 viruses: m4g1 p90;
  - gained: m4g1 p118 (FAIR2PLUS froze on an earlier answer; u8 landed the final).
  - A16: 7 lost (G2 p79, m1g2 p58 at 14-15 viruses; m4g1 p90; m1g2 p96, p106, m2g2 p99 tucks; m4g1 p124), the same
    1 gained.
- These pills lock 2 to 56 f sooner. Whether the earlier answer is a worse move is not something a per-pill replay
  can price.

### 3.4 Which immediate does what (one-variable carts, V11; A16 agrees)

| cart | lock, all pills | ≥ 10 viruses | < 10 viruses | == final | disarmed |
|---|---|---|---|---|---|
| k8 (KOPEN 8, KEND 255) | −2.69 [−3.26, −2.12] | −3.74 | −0.13 [−0.36, +0.09] | 1,144 (1 lost) | 195 |
| e8 (KOPEN 32, KEND 8) | −4.88 [−5.41, −4.35] | +0.00 (847 of 847 identical) | −16.71 [−17.76, −15.65] | 1,139 (7 lost, 1 gained) | 133 |
| u8 (both) | −7.57 [−8.29, −6.85] | −3.74 | −16.83 | 1,138 (8 lost, 1 gained) | 218 |

- The two cuts are additive and do not touch each other's phase. Two thirds of the gain and 7 of the 8 lost finals
  come from `K_END`.

### 3.5 The disarm side effect (descriptive: this split is on a post-treatment state)
- A pill whose predecessor locks while its search is still running starts with `SLAM_ARM` = 0 and waits for DONE.
  u8 slams earlier, so this happens twice as often: 109 → 218 pills on V11, 106 → 220 on A16.
- At ≥ 10 viruses on V11: the 637 pills armed in both carts lock 7.81 f sooner; the 101 pills that u8 newly disarms
  lock **23.46 f later**; 100 of the 115 pills that lock later under u8 are these. That is why the ≥ 10-virus gain
  is −3.74 f and not −7.8 f.
- In the endgame a disarmed pill costs nothing against FAIR2PLUS, which waits for DONE there anyway (23 pills,
  difference 0.00 f).
- The disarm follows a stability slam, not DONE: after a pill that descended on the stability rule the next pill is
  disarmed on 214 of 900 pills under u8 (107 of 658 under FAIR2PLUS); after a DONE descent, 1 of 269.

## 4. Simulator vs cart
STEER14's arms: `S14_d4_k32` → `S14_d4_u8` for V11, `S14_d16_k32` → `S14_d16_u8` for A16.

| quantity | STEER14 model (V11 / A16) | cart replays (V11 / A16) | agree? |
|---|---|---|---|
| GO → lock, endgame pills | 49.5 → 31.6 f / 51.6 → 32.1 f | 48.96 → 30.85 f / 48.64 → 30.52 f | **yes** (−17.9 / −19.5 vs −18.1 / −18.1) |
| GO → lock, all pills | 43.0 → 33.1 f / 43.6 → 33.4 f | 40.70 → 32.66 f / 40.58 → 32.58 f | yes after the pill mix: the model's games are 44 % endgame pills, this corpus is 29 % |
| tempo per pill | −9.76 f / −10.08 f | −7.57 f / −7.54 f; **−9.49 f / −9.12 f** reweighted to the model's endgame share (43.9 % / 41.2 %) | **yes** (within 1 f) |
| disarmed pills | 9.0 → 17.1 % / 9.5 → 18.6 % | 9.1 → 18.2 % / 8.9 → 18.4 % | **yes** |
| DOWN on DONE / stability / never | 50 / 48 / 2 → 18 / 81 / 1 % | 43 / 55 / 1 → 23 / 76 / 1 % | direction and size yes; shares differ with the pill mix |
| landed on the final | 99.0 → 98.7 % (endgame 98.3 → 97.8 %) | all 95.66 → 95.07 %; non-tuck 99.56 → 99.29 %; endgame 96.29 → 94.57 % | **partly** (below) |
| LATEGUARD refusals | 0.005 → 0.007 per pill | frozen pills 17 → 16 / 21 → 19 | no rise seen |

- **Agrees:** the size of the tempo gain, where it comes from (the endgame), and the doubling of the disarm rate.
- **Agrees on non-tuck pills:** the landing cost is 0.3 pp in both.
- **Does not agree, as STEER14 warned: tucks.** The model has none, so its 99 % is a statement about non-tuck pills.
  On the cart 5 % of pills carry a tuck final, today's cart already lands only a quarter of them, and u8 loses the
  endgame ones. The endgame landed-on-final drop is 1.7 pp on V11 (6 net pills of 350) and 0.9 pp on A16 (3 net),
  against the model's 0.5 pp.
- **PRESTART and pre-commit rotation, also not modelled:** nothing shows up. Post-garbage pills land identically
  (82 of 83 in every cart) and gain 1.4-1.8 f; there are no hybrids.

**The steer model on the same pills** (`tools/u8slam/model_vs_cart.py`; `steer_model.execute(slam=...)` wrapped as
`steer14_slamcal.model_pill`, with each cart's constants, the replay's own schedule, DONE, GO and `SLAM_ARM`; V11):

| | FAIR2PLUS (the validated point) | u8 |
|---|---|---|
| DOWN start, model == cart | 99.1 % | 43.8 % (mean +1.05 f) |
| lock frame, model == cart / within 3 f | 93.9 % / 99.5 % | 53.9 % / 96.0 % (mean +0.59 f) |
| landing, model == cart | 1,122 of 1,126 | 1,129 of 1,134 |

- Paired change u8 − FAIR2PLUS on the same 1,122 pills: cart −8.05 f, model −7.20 f. **The model under-predicts the
  gain by 0.85 f per pill**, uniformly across strata.
- It predicts 8 of the cart's 9 landing changes, pill for pill.
- Where the error is (REPLAYS.txt, section C): on 438 pills the model starts DOWN exactly 2 f late. On 412 of them
  the cart starts DOWN on the frame after its last lateral move. With a 16 f window the stability clock decides the DOWN frame; with a 4 f
  window the end of steering does, and the model's steering ends one TAP period later than the cart's. This part of
  the model was never exercised at KOPEN 32. It is an observation from the traces, not a traced-down model bug.

## 5. What this means for the candidate
- The execution half of STEER14's u8 claim holds on the real cart, slightly conservatively. Its race value
  (+8.5 pp vs dr. lulu in the model) rests on that tempo and is not re-measured here.
- These flags cannot keep the endgame DONE-wait for tuck finals only: the driver reads the tuck descriptor from the
  mailbox at DONE and has nothing earlier to tell a tuck pill by. The measured trade stands as it is: −16.8 f per
  endgame pill, for 6 of the 20 endgame pills with a late final.
- The newly disarmed pills cost u8 2.8 f per ≥ 10-virus pill against FAIR2PLUS (101 pills × 23.46 f over 847). The
  disarm rule is the next tempo lever in this cart. It is a safety rule (DRSLAM_MATURE), so it goes to the simulator
  first.

## 6. Not verified here
- **Nothing ran on a MiSTer.** No rbf, no silicon, no couch. bluemage and rivalmage were not touched.
- **No game outcomes.** Every case starts from the silicon board of that pill (chained only across the spawn /
  prestart edge), so a changed landing never reaches a later board. The replays measure tempo and execution, not
  what the 6 lost finals or the extra tempo do to a game.
- **The copro under more aborts.** Under u8 twice as many pills (18 %) lock while the search is still running, and
  the cart then aborts it at the next edge (DRABORTSTALE). The replay serves the next search from a clean co-sim
  timeline. Silicon has run this path at today's 9 %; whether the publish timing of a search started over an
  aborted one matches the clean timeline at 18 % is a co-sim or soak question.
- **The model comparison in section 4** uses STEER14's published aggregates against a corpus with a different pill
  mix; only the reweighted tempo row and the per-pill table are like for like.
- **The press-cadence count on the traces** has no mutant behind it (the TAP gate does).
- **Intervals** treat pills as the unit. Pills within a game share a `SLAM_ARM` chain; the game-cluster bootstrap in
  3.1 is the conservative reading, and with 12 games it is itself rough.
- No CvC freeze soak. The driver differs in two immediates and the NMI census is unchanged, but a soak is what
  finds freezes.

## Files
- **Cart:** `tools/u8slam/build_carts.sh`, `gates_cart.sh` → `experiments/u8slam/GATES_CART.txt`; test arms
  `couch_fair_A_lgp_row2_u8` in `tests/test_gravity_fidelity.py`, `tests/test_lgprestart.py`.
- **Replays:** `tools/u8slam/replay_batch.sh` (waits on `PAUSE_ALL` before every run), `analyze.py`,
  `late_finals.py`, `model_vs_cart.py`, `report.sh` → `experiments/u8slam/REPLAYS.txt`, `pills_{v11,a16}.jsonl`,
  `model_pills_{v11,a16}.jsonl`.
- **Outside git** (dr_mario_rl): carts `tmp/u8slam/carts/` (u8 1ebd386e, k8 4b53df67, e8 1792aecf), runs
  `tmp/u8slam/execfid/runs/` (96 traces), `tmp/u8slam/STATUS.txt`.
