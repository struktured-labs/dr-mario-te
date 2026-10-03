# RESULT (2026-10-03, Claude): 10/03 match-1 G2. The AI tapped out at 10 viruses because silicon did not execute the brain's moves.

- **Build:** ANTIBODY_DIST. Above 4 viruses DIST is off, so this is ANTIBODY's midgame. AI = P2.
- **Video:** `/mnt/data/Videos/2026-10-03 08-26-24.mkv`, scanned 182–456 s at 60 fps with `geom_dist60_20261003.json`.
- **Tracker:** the hidden-spawn tracker. Mechanics gate **114/114** explained (107 exact, 7 garbage).
- **STUDY pause:** 314.65–394.2 s, excluded. The capsule spawned at the pause is landed after it.
- **Size:** 116 placements (p0–p115), about 185 s of board time.

## Verdict
**The cause is execution (the cart's answer and steering), not brain choice and not garbage.**

**Brain-only replays survive.** The sim brain was given the same 116 capsules and the same received garbage cells:

| replay | start | result at p115 |
|---|---|---|
| brain alone, perfect execution | p0 | **CLEARS the board at p114** |
| | p31 | alive, 6 viruses |
| | p59 | alive, 9 viruses |
| | p90 | alive, 10 viruses (one column reaches 16) |
| | p96 | alive, 9 viruses |
| shipping-driver model, 20 latency seeds (tap-2, DISTGATE clamps, PROPH; no answer churn) | p0 | **20/20 clear** |
| | p31 / p59 / p90 | 20/20 alive |

Source: `g2_counterfactual_dist60_20261003.py` → `.txt`.

**Silicon matched the brain on only 77/116 placements (66%).** The other games that day:

| game | silicon == brain |
|---|---|
| G1 | 81% |
| G2 | **66%** |
| G3 | 90% |
| G4 | 88% |

- **G2 misses:** OTHER 22, LATE-FLIP 11, SHORT-LANDING 5 (4 with a DISTGATE clamp), TUCK 1.
- **Board height:** 85 of 116 G2 pills were played with max height ≥ 12. LATE-FLIPs by game: G2 11, G3 2, G4 1, G1 0.

## Timeline (per-pill evidence in `cases_g2_dist60_20261003.jsonl`)
**1. Opening, p0–p22.** Five high viruses sat in the HSV region (cols 3–5, rows < 9). They were gone by p22 (222.8 s,
36 s into the game). **HSV had nothing to act on for the rest of the game.**

**2. The tower starts at p31 (241.4 s) with a silicon LATE-FLIP.**
- The brain chose H4 RY at row 11, low.
- Silicon held that pose for 19 frames, then stepped right twice, rotated, flipped back, and locked **H5 YR at row 5**
  on top of column 6's stack.
- That hung a pill over an empty column 5: its height jumped from 4 to 11 with a cavity underneath.
- Columns 5–6 stayed at 11–12 from then on. Column 4 joined them at p62 (11) and reached 13–14 by p80 and p97.

**3. The stall at 15 viruses, p59–p106 (48 pills).**
- On 43 of the 48 pills no allowed move cleared any virus with the actual capsule.
- The viruses left were sealed. Column 6 was a stack of viruses with gaps between them (B7, Y9, R11, R12, Y13), and
  the B at row 7 was capped by two reds, as in the owner's study screenshot. Others were deep in columns 0–3.
- Silicon == brain on only 29/48 pills here.

**4. The kill, p97–p102 (424.9–428.3 s).**
- The brain chose the 1-wide column-3 well three times running: a vertical drop to row 11 at p97, p98 and p99.
- Silicon:
  - p97, OTHER: went straight to column 1;
  - p98, LATE-FLIP: reached vertical in column 3 at f17, flipped to horizontal at f23, landed H1 at row 2;
  - p99, LATE-FLIP: reached vertical in column 3 at f17, flipped at f26, landed **H3 at row 2**, capping the well with
    nothing under it.
- The spawn lane went to 14. From p100, PROPH's trigger held on every pill and the pills went into columns 0–2 at rows 0–1.
- The AI then cleared 5 viruses on the right (p106–p111).
- **p115:** SHORT-LANDING with a DISTGATE clamp, locked in the spawn cells at row 0. Top-out at 10 viruses (HUD).

**Garbage was minor.** The owner sent 8 volleys × 2 cells = 16 cells (fixed tracker). None of them raised the tower,
and none landed in the kill sequence p97–p102.

## Tower-building decisions by the brain itself (term decomposition)
Only 5 of the sim brain's own choices would raise max(h4, h5) to ≥ 11 (`(2)` in the `.txt`). Chosen − best
non-raising move:

| pills | what the brain wanted | terms for | terms against | silicon |
|---|---|---|---|---|
| p0, p2 | clear the high spawn-column viruses at the start | **HSV +256** | | did it (legitimate) |
| p84, p87, p94 | stack on the column-5 pile at rows 1–2 | **EXCAV +112 / +288 / +288**, CHAIN +68 | LEAF −83 / −306 / −197 | did NOT execute these (OTHER) |

- **The late tower-stacking urge is the root EXCAV term again:** 24·min(run,3)² for a same-colour run on top of a
  buried virus. It is the same term the endgame analysis found paying the bot not to finish
  (`RESULT_COUCH_DIST60.md`).
- It did not kill G2, but it is the brain-side term pushing the spawn region up when execution is shaky.

## The late flips: what they are not (`(3)` in the `.txt`)
- The flipped final pose is NOT explained by:
  - the brain searching the PREVIEW pill (1/11);
  - cur and nxt swapped (0/11);
  - the live capsule's pre-flip cells counted as board (1/11).
- **On the tall board** (p98, p99, p111–113) the capsule holds the brain's target from about f17. It flips at f22–26,
  6–9 frames after the first gravity drop. Those are the classic LATE-FLIP / answer-churn signs.
- **OTHER** (22): in 12 of them the first lateral move went to the opposite side from the brain's target. The cart's
  answer differed from the start, which looks like a different board or input to the copro. PROPH's trigger held only at
  p80 and from p100 on.
- **Not caused by same-colour capsules.** Across all four 10/03 games, misses run 21% after a same-colour previous
  capsule vs 19% otherwise.
- **The mechanism is unresolved from video.**
  - Next step: a cart-side trace of the driver's target register on these boards, e.g. a Mesen replay of the
    p96–p99 boards.
  - This failure class is **not in the steering sim**. That is consistent with the STEER1/2 finding that the couch
    tap-out gap is steering.

## Compared with the prior middle-tower deaths
| death | what happened | same as 10/03 G2? |
|---|---|---|
| 9/26 TAP AM-G1/G2 (`RESULT_COUCH_TAP.md`) | Brain-built towers on 7 high spawn-column viruses that were never cleared; silicon matched the brain 80–85%. **This is the archetype HSV was built to fix.** | No. G2's HSV region was empty from 36 s; the tower started with a silicon flip; the brain alone clears. |
| 9/25 CHAIN540 G2 (`RESULT_COUCH_G2.md`) | Brain stall with a tower (11/13 match), then a driver-side kill (clamps + PROPH; 2/12 match in the last 12). | **Same family:** stall plus a driver kill. But the driver failure is mostly LATE-FLIP / answer churn rather than PROPH / clamp, and here the tower itself was seeded by a flip. |
| 9/27 HSV M1-G3 near-tap-out (`RESULT_COUCH_HSV.md`) | A high virus sealed by execution slips (a short landing and a tuck) plus garbage. | Same flavour: execution slips seed the structure. |

- ⇒ **This is a NEW instance of the execution-fidelity problem on tall boards, not the HSV archetype.** HSV did its
  job: the high centre viruses were gone in 36 s.
- **What the brain would have needed: nothing, given faithful execution.**
- **What would make it robust:**
  1. fix or trace the late-flip / off-target answers on tall boards;
  2. secondarily, drop or gate the root EXCAV pile credit, which pulls the spawn region up.
- All of this is n = 1 death and PROVISIONAL.

## Files
- `cases_g2_dist60_20261003.jsonl`: 116 placements. Board, heights, silicon pose, brain pose, category, trajectory
  lateral frames, mechanics, garbage received, act-stall flag, per-action values and PV term splits.
- `cases_cat_dist60_20261003.jsonl`: categories for all four 10/03 games (371 placements).
- `rawh_dist60_20261003_G1.jsonl`, `rawh_dist60_20261003_G2.jsonl`.
- `g2_tapout_dist60_20261003.py`, `g2_counterfactual_dist60_20261003.py` (+ `.txt` output),
  `categories_dist60_20261003.py`.
