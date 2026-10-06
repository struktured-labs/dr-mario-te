# RESULT (2026-10-03): the P2 post-spawn SETTLE, the gravity pin hiding in it, and the fair cart

Branch `claude/settle` (on PR #30's `claude/late-flip`). Everything here is measured, in Mesen on the real carts and
under py65 on the real emitted driver bytes; every number has its run file in this folder.

## 1. Verdict

- **The shipped settle hides a gravity pin, and the pin is a fairness defect.** freeze_pending pins P2's speed counter
  (`$0392 := 0`) on every hook of the settle. The settle is `DELAY2 = 15` hooks = 7.5 f; it was sized "~3 frames" under
  the retired 5-hooks/frame assumption.
  - Unmodified game: the counter reads 0,0,1,2,3… from the spawn frame, G0 = 1 (2,000+ pills, LOW/MED/HI).
  - Shipped carts: 0,0,1,1,1,1,1,1,2…, G0 = 6. That is 5 frames of P2 gravity held on every settle-path pill, at every
    level and speed.
  - It applies to every couch / CvC cart with the settle, ANTIBODY included.
- **What the settle itself protects (the data the upload is built from) needs one NMI, not seven.**
  - Mid-round spawns: the upload is byte-final at the edge hook. That held on 926/926 stock uploads, after clears,
    multi-line clears / cascades, garbage drops and on tall boards.
  - Round starts: the pre-throw edge needs the next NMI (75/80; the other 5 had identical colours).
  - Worst case: 2 hooks.
- **`DRSETTLE=3` + a readiness guard** (no upload while `p2_nextAction == sendPill`) uploads at the next NMI.
  - The upload is identical to what the 15-hook settle would send: 962/962 checked.
  - GO comes 6 f earlier and the pin becomes a no-op. With `DRSETTLEPIN=0` the pin is gone.
  - Tempo: paired over 70 identical-landing pills, edge→lock is **−5.90 f/pill**.
- **But the fair settle alone regresses G2's tall endgame**: hybrids 1 → 14.
  - The pinned settle was also PROPH's free-move window.
  - Fixed by **`DRPROPHFIRST`** (D): on a PROPH-armed pill still on its spawn row, PROPH's ledge escape runs before
    the rotation pre-phase until the commit window opens. That is the shipped carts' input ORDER, under live gravity.
  - G2 with D: landing == final 100 (464a4b75: 99), hybrids 1 (1), regret 17.2 (17.1).
  - G3: identical (0/86 landings differ).
  - G4: == final 131 (131), hybrids 0 (0), == silicon 117 (115); 2 landings differ, net equal.
- **Fair couch candidate:** 464a4b75 + `DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1`, md5 `dbbb5007`. Kit:
  `dr_mario_rl/tmp/couch_kit/fair_20261003/`. **NOT deployed.**

## 2. What DELAY2 protects (Mesen, real carts; `MESEN_SETTLE_CORPUS.txt`)

**Instrument:** `tools/settle/settle_probe.lua`.
- It snapshots the upload-source RAM at the driver's own hook entry ($FF54, i.e. exactly what the driver reads):
  `$0500-$057F`, `$0381/$0382`, `$039A/$039B`, `$038A/$038B`, SEED2.
- It encodes that RAM like handle(2). The self-check is exact: 0 mismatches on 1,006 + 965 settle uploads.
- For each pill it finds the earliest hook after the edge from which the encoding equals the bytes actually
  uploaded.

**Corpus** (garbage pokes = the review lane's `$0318`/`$0329` method; a Lua copro = 1-ply colour greedy + 15%
random placements, so boards get tall):

| | settle uploads | mid-round stable at the edge hook | round-start stable at hook 2 | after garbage | after a clear | multi-line / cascade | height ≥ 14 |
|---|---|---|---|---|---|---|---|
| stock (464a4b75, 387bb7bd, + tempo arm) | 1,006 | **926 / 926** | 75 / 80 (5 at hook 0, identical colours) | 107 | 270 | 23 | 508 |
| fair `DRSETTLE=3` (couch + CvC + tempo) | 965 | 883 / 883 | 81 / 82 | 100 | 276 | 17 | 523 |

**Why round starts need more than the edge hook.**
- Level init calls generateNextPill (Y = $0F) before the first throw, so the stock Y test fires a PRE-THROW edge.
- The throw (generateNextPill again: capsule ← preview, preview ← reserve) lands 1-2 NMIs later.
- In Mesen it landed before the next NMI every time (160 round starts). The 9/28 spawnedge run saw it one frame later
  on 3/56.
- The readiness guard covers both cases. The py65 gate reproduces the 2-frame throw: the `noguard` mutant uploads the
  wrong pill (KILLED).

**Copy-back race (why N = 3, not 1).**
- `currentP_toP2` copies `$80-$AF → $0380-$03AF` in ascending order. Y (+$06) is copied before speedUps (+$0A) and
  the preview (+$1A/$1B).
- An NMI that lands inside that window would fire the edge on a half-copied state.
- Interrupted main-loop PCs:
  - couch: the idle loop at 59,973/59,995 NMIs;
  - CvC (whose P1 native AI hooks steal main-loop time): ~120/59,995 mid-work, 6 of them inside currentP_toP1's copy.
- None was inside currentP_toP2 at a P2 edge in this corpus, but the mechanism is real.
- One NMI later the copy is done: the census leaves the main loop ≥ 2k cycles per frame, and the rest of the copy
  needs ≤ 770.
- The 7/04 commit (32c306c8) recorded "preview stale ~1-in-10 spawns" at the edge, under that day's heavier hooks.

**The fair upload equals the stock one.**
- On the flag-on carts the probe also compares each upload with the snapshot a 15-hook settle would have used:
  **962 / 962 equal**, 0 different; 3 pills had already locked by then.

## 3. The gravity pin (fairness)

| condition | G0 (frames of gravity not counted since spawn) | n |
|---|---|---|
| unmodified drmario.nes, 2P, L11 MED / HI, no input until the first drop | **1** | 815 + 934 (+ 274 smoke) per seat |
| shipped couch 464a4b75 / CvC 387bb7bd, mid-round settle pills | **6** | 383 / 454 |
| shipped, round-start pills (the pin overlaps the pre-throw frame) | 5 | 9 / 70 |
| shipped, DRPRESTART-owned pills (they skip the settle) | 1 | 99 |
| fair `DRSETTLE=3` (pin kept or removed: identical runs) | 1 | 392 / 546 |

- CvC G0 = 7 (14 pills) and fair-CvC G0 = 2 (32 pills) are LAG frames: the counter repeats a value mid-trace. The P1
  native AI's ~18k-cycle hooks steal the main loop. That stalls both seats; it is not the pin.
- **The pin's effect by speed** (real driver bytes under py65, `PIN_EFFECT_TABLE.txt`; Mesen-confirmed at MED):
  - always **5 frames per pill** for thr ≥ 1;
  - rows held = 5 / (thr + 1).

| speed / speedUps (every 10 pills) | thr | frames held | rows of reach per pill |
|---|---|---|---|
| L11 = L15 = L20 MED, start (su 0) | 19 | 5 | **0.25** |
| MED after ~100 pills (su 10) | 9 | 5 | 0.50 |
| MED su 20 / 30 / 40 / 49 | 5 / 4 / 2 / 1 | 5 | 0.83 / 1.00 / 1.67 / 2.50 |
| HI start (su 0) / su 10 / su 30 / su 40 | 13 / 6 / 3 / 1 | 5 | 0.36 / 0.71 / 1.25 / 2.50 |
| HI su 49 (thr 0: a pin cannot stop a drop) | 0 | 0 | 0 |
| LOW start | 39 | 5 | 0.12 |

- Levels ≤ 20 share the MED schedule; level only matters above 20.
- On the couch (L11 MED, ~70-150 P2 pills a game, su 0→~15): **0.25-0.6 rows of extra reach on ~85-90% of pills**.
  The prestart-owned pills after a human garbage release were never pinned.
- **What the pin was worth on G2** (arm (c): no pin, settle kept at 15): landing == final 99 → 95, hybrids 1 → 0,
  regret 17.1 → 18.8. The answer then comes 5 f later relative to gravity.

**Why nothing caught it:**
- `tests/test_driver_fidelity.py` (the 7/19 audit) asserted the settle pin as "the one deployed in-window pin, ~3 f
  inside the ~20 f spawn window". Its mock reloads the drop timer every frame, but the ROM's counter is CUMULATIVE.
- That file is not in `run_cart_gates.sh`, and 6/41 of its byte goldens have rotted (identical on PR #30's head).
- `gate_tap_interface.py`'s world rewrites `$0392` from its own copy every frame, so it cannot see a driver store.

**The gate that now prevents it: `tests/test_gravity_fidelity.py`**, in `tools/gate/run_cart_gates.sh`, ~10 s.
- It runs the real driver under py65 against a ROM-rule world whose state lives in the game's own RAM bytes.
- It replays the recorded pads on the same world with NO driver, and FAILS on any frame where the two differ (P2
  nextAction, Y, X, rotation, speed counter, horVelocity, pill counter, board).
- Coverage, with zero activity counted as a FAIL: round starts (throw 1-3 frames late), garbage releases, stale-DONE
  edges, tall throats, LOW/MED/HI × speedUps 0-49.
- It also checks UPLOAD correctness: the first upload after a pill's edge must carry that pill.
- Results:
  - the fair couch/CvC and D builds PASS;
  - 464a4b75 / 387bb7bd are KILLED at frame 3-5 (driver `$0392` stores);
  - the `noguard` mutant is KILLED (wrong-pill round-start uploads).
- 20k-frame run: `GATE_GRAVITY_FIDELITY.txt`.

**Audit of every driver store into game RAM** (`AUDIT_ROM_WRITES.txt`; CFG-reachable from the hook entry, on the
IR captured from the emitter):
- On the couch AND CvC carts, the only live P2 gravity/position store is `fp_p2: STA $0392` (the settle pin). The
  rest are P2 pad bytes `$F6/$F8`.
- The CvC adds autonav level writes (menus only) and the P1 native AI's in-NMI evaluate/undo on P1's board.
- The non-ROTFIX/FREEZE-cart pins and act_p1's GRAV_P1 stores are dead code on these carts.
- The DRPENDBOUND stale-DONE path stays bounded by DELAY2, so it is the same window.

## 4. DRSETTLE (flag block in patch_cartridge_copro.py)

- `DRSETTLE=N` (default 15 = byte-identical). It loads DELAY2 ← N at the P2 edge; N = 3 uploads at hook 2 (the next
  NMI).
  - N ≠ 15 also emits the READINESS GUARD in handle(2)'s `_start`: `LDA $0397 / CMP #6 / BNE go / JMP done`.
  - The test-only mutant `DRSETTLE_MUT=noguard` is gated.
- `DRSETTLEPIN=0` (default 1). freeze_pending emits no P2 pin. At N = 3 the pin only covers the edge NMI, where the
  counter is already 0, so pin-kept and pin-removed Mesen runs are pill-for-pill identical.
- **Frames:**
  - GO: hook 14 → 2 = **−6 f** (314/314 at dgo = 2; stale-ARMED edges wait for the old DONE, as before).
  - Gravity start: −5 f (G0 6 → 1).
  - Answer relative to gravity: −1 f.
  - Tempo, paired over 70 pills with identical landings (`MESEN_SETTLE_CORPUS.txt` tempo runs, all slam-bound):
    (b) −5.90 f/pill; (c) no pin, settle 15: −0.73.

## 5. The tall-board regression and the fair ledge fixes (G2/G3/G4 banked copro timelines, fw 1488e158)

**Harness:** `tools/lateflip/run_lateflip.sh` + `tools/settle/replay_eval.py`. The case files are byte-identical to the
late-flip lane's. Each fix is its own default-off flag:
- A `DRPROPHHOLD`: PROPH pulses through the MIN_THINK hold.
- B `DRDISTROW`: when no row below the span is empty, the DISTGATE budget = min(7, (thr − $0392)/2).
- C `DRLEDGECOMMIT`: PROPH-armed pills skip MIN_THINK.
- D `DRPROPHFIRST`: PROPH's escape runs before the rotation pre-phase while on the spawn row and before the commit
  window.

| arm (fair settle + …) | G2 == final | G2 hybrids | G2 regret (scored) | G2 landings ≠ 464 | G3 ≠ 464 | G4 == final / hybrids / ≠ 464 |
|---|---|---|---|---|---|---|
| **464a4b75** | 99 | 1 | 17.1 (115) | — | — | 131 / 0 / — |
| (b) nothing | 92 | 14 | 19.2 (100) | 17 | 0 | 131 / 0 / 2 |
| (c) no pin, settle 15 (not fair-settle) | 95 | 0 | 18.8 (116) | 5 | 0 | 130 / 0 / 1 |
| A | 98 | 4 | 17.2 (112) | 4 | 0 | 131 / 0 / 2 |
| B | 98 | 4 | 17.3 (111) | 6 | 0 | 131 / 0 / 2 |
| C | 92 | 13 | 19.0 (101) | 16 | 0 | 131 / 0 / 2 |
| AB | 98 | 5 | 17.3 | 5 | 0 | 131 / 0 / 2 |
| BC = ABC | 98 | 3 | 22.2 (113) | 5 | 0 | 131 / 0 / 2 |
| B on the stock settle | 99 | 2 | 17.3 | 1 | 0 | 131 / 0 / 0 |
| **D** | **100** | **1** | **17.2 (115)** | **1** (p98: lands on the copro final) | **0** | **131 / 0 / 2** (== silicon 117 vs 115) |
| DB | 100 | 2 | 17.3 | 2 | | |

**The G4 pair** that every fair variant changes is an earlier-answer effect:
- p11 now lands on the final / python / silicon answer;
- p123 lands on silicon's intermediate instead of the final.

**Mechanism** (p108 frame trace, `TRACE` lines in the replay logs):
- **Stock:** PROPH presses at f1/3/5/7 inside the pinned settle (gravity counter frozen at 1) carry the capsule col 3→6.
  The answer arrives at f9 and lands on the final.
- **Fair, no fix:**
  1. The answer is published at f3, so PROPH stops.
  2. The rotation pre-phase spends the TAP slots.
  3. MIN_THINK withholds lateral moves until f8.
  4. DISTGATE's budget is 0 on a ledge.
  5. The capsule locks in the spawn column at the f11 tick.
- **D:** PROPH presses at f1/3/5/7 (4, as stock; commit f10), under live gravity.

**PROPH window, measured** (17 PROPH-armed G2 pills):

| arm | first valid publication | commit | PROPH presses (before publication / before commit) | gravity counter first ≥ 2 |
|---|---|---|---|---|
| 464 | f9 | f14 | 4 | f8 |
| plain fair | f3 | f8 | 1 | f3 |
| (c) | f9 | f14 | 4 | f3 |
| D | | f10 | 4 before the commit | f3 |

**Certification of D** (the couch candidate):
- gravity-fidelity gate PASS (`couch_fair_D` arm);
- Mesen corpus on the D cart (60k frames, garbage pokes):
  - G0 = 1 on **528/528** pills;
  - upload == the 15-hook upload on **422/422** settle pills;
  - mid-round uploads final at the edge hook 411/411; round starts at hook 2 (10/11).
- Tempo, paired over 70/70 identical-landing pills: **−5.90 f/pill**.
- negative controls 8/8;
- `run_cart_gates.sh` ALL PASS;
- `test_lateguard_census_cut.py` PASS with `LGCUT_OVERLAY=DRSETTLE=3,DRSETTLEPIN=0,DRPROPHFIRST=1`;
- static census worst admissible frame **27,752 / 29,780** (margin 2,028; 464a4b75: 27,704 / 2,076);
- TAP interface gate PASS (40k frames, 0 violations; `GATE_TAP_INTERFACE_LEDGE.txt`);
- Mesen NMI max **12,644** (couch churn + pokes / 30 f; over29780 0, nested 0, absorbed 0, REFUTE 0; fair base 12,572, 464a4b75 run 11,459).

## 6. Gates for the fair settle itself (`GATE_*_SETTLE.txt`)

- **Negative controls** (`tools/settle/build_settle_carts.sh`): with every new flag at its default AND set
  explicitly to its default, c960dd49, fd08d7a3, 464a4b75, 3b8737a9 and 387bb7bd rebuild byte-identically. 8/8.
- **TAP interface:** couch and CvC, stock and fair, 40k frames each: 0 violations. Mutant `everyframe` KILLED.
- **Static NMI census** (`tools/nmi126/census.py`):
  - fair couch worst admissible 27,676 (margin 2,104), vs stock 27,704 / 2,076;
  - fair CvC per-hook bounds −8 to −25 cyc vs stock.
- **Mesen NMI max** (`tools/lateflip/run_nmi.sh`, the review lane's settings): over29780 = 0, nested = 0,
  absorbed = 0 on both.
  - fair couch, churn + pokes / 30 f: 12,572 (shipped CH run: 11,459);
  - fair CvC: 21,297 (shipped 21,092).
- **`test_lateguard_census_cut.py`:** PASS on the fair image (`LGCUT_OVERLAY` added to the test for this).
- **`run_cart_gates.sh`:** ALL PASS, including the new gravity gate.

## 7. Pricing (sent to the steer-sim lane for STEER8b)

Frames are mine (main-loop frame k after the spawn pass); the sim's ≈ +1.

| arm | G0 | answer frame | mask T_LAT (mask G0) | tempo / pill | PROPH window |
|---|---|---|---|---|---|
| (a) 464a4b75 | 0 | 0 | 0 | 0 | ends at the first publication ≈ f9, 4 taps, gravity frozen until f8 |
| (b) plain fair | −5 | −6 | −6 (−5) | −6 slam-bound / −5 gravity-bound (measured −5.90) | ends ≈ f3, 1 tap |
| (c) no pin, settle 15 | −5 | 0 | 0 (−5) | 0 slam-bound / −5 gravity-bound (measured −0.73) | ≈ f9, 4 taps, live gravity |
| D (fair + DRPROPHFIRST) | −5 | −6 | −6 (−5) | ≈ (b) on non-PROPH pills | [F0, min(GO + 6 f, leaves the spawn row, DONE)), before rotation: 4 taps, commit ≈ f10 |

**Two model corrections the sim needs:**
1. PROPH ends at the FIRST VALID PUBLICATION (not at the first lateral / t_act). Then MIN_THINK withholds lateral
   moves and DISTGATE clamps a ledge capsule to budget 0.
2. The deployed DRREACH mask bakes in T_LAT 19 / G0 8. A fair cart needs a mask refit: T_LAT 13, G0 3, and PROPH
   ending at p_end.

## 8. MIN_THINK (recommendation, not built)

From the fw-lane co-sim timelines of hex **a1ef31c8** (ROOTORD), P(the final answer is already published at the
commit gate):

| gate | G2 | G3 | G4 |
|---|---|---|---|
| 2 f | 11% | 1% | 1% |
| 3 f | 64% | 55% | 54% |
| **4 f** | **85%** | **84%** | **84%** |
| 6 f (today) | 91% | 86% | 91% |
| 8 f | 96% | 86% | 93% |

- **Recommend `DRMINTHINK=8` (4 f) paired with a1ef31c8:**
  - −2 f of live-gravity latency, worth ≈ −2.2 pp tap-out on STEER7's faster-side slope;
  - final-at-commit falls only 1-6 pp; LATEGUARD bounds a late change.
- Not below 8: at 6 hooks it collapses to 54-64%.
- Not with fw 1488e158: 60-66% at today's gate.
- Note: D's PROPH-first window ends at the commit window, so MIN_THINK 8 cuts PROPH to 3 taps. Re-run the G2 replay
  with the pair before shipping it.

## 9. Side findings (not the settle's; logged for their owners)

- **DRPRESTART projection:** on 4-8% of prestart-owned pills, the projected upload ≠ the board the capsule landed in
  (8/100 stock, 4/78 fair; `LOCK_MISMATCH` lines).
- **Stale-DONE dead-pill upload:**
  - In the py65 world, a search that DONEs in the clear window after its capsule locked re-uploads the dead pill.
  - The next pill then waits for that search's DONE.
  - This is a pre-existing path, independent of the settle (the gate counts these uploads and does not fail on them).
- **CvC lag:** the P1 native AI's ~18k-cycle hooks cost main-loop frames for both seats (G0 7 / 2 above).
- **`tests/test_driver_fidelity.py`:** 6/41 byte goldens stale on PR #30's head; its pin exemption is corrected in
  text.

## Reproduce

```
tools/settle/build_settle_carts.sh tmp/carts                 # carts + the 8 negative controls
tools/gate/run_cart_gates.sh                                  # incl. tests/test_gravity_fidelity.py
python tests/test_gravity_fidelity.py --frames 20000 --seed 11
python tools/settle/pin_effect_table.py couch_464a4b75 cvc_387bb7bd couch_fair
python tools/settle/audit_rom_writes.py experiments/lateflip/couch_c960dd49_flags.json TAG [K=V ...]
ST_SETTLE=15 ST_HUMAN=1 ST_SEED=11 ST_POKE_EVERY=500 tools/settle/run_probe.sh TAG cart.nes tools/settle/settle_probe.lua 60000
BS_SPEED=1 tools/settle/run_probe.sh TAG drmario.nes tools/settle/base_gravity_probe.lua 60000
tools/lateflip/run_lateflip.sh G2_TAG cart.nes tmp/settle/cases/cases_G2.lua 20000; python tools/settle/replay_eval.py tmp/lateflip 464 TAG
```
