# RESULT (2026-09-25, Claude): couch-death forensics, 9/25 morning G2 (CHAIN540 core + couch TE cart, AI = P2)

**Question.** The AI tapped out at 22 viruses (owner at 21) after its virus count sat at 22 for 36 s. Did it die
because (A) steering: silicon did not put pills where the brain chose; (B) the brain itself chose the
fatal placements under the owner's garbage; or (C) something else?

## Verdict: MIXED, and the fatal end is the DRIVER, not the brain (n = 1 death)
- **The 36-second stall (k=26–38, 13 placements) is the brain's own play.** 11 of 13 placements match the
  sim brain exactly. It kept clearing junk while cols 4–6 stood at 12–14 over buried viruses. This is the known
  stall-with-tower archetype (B-flavoured).
- **The kill (k=39–50, the last 12 placements) is driver-side execution the sim cannot see.** Only 2 of 12
  match the brain:
  1. **k=39, SHORT-LANDING (clamp):** the brain wanted H col 5. With 1 free row the DISTGATE clamp held the
     pill in the spawn column, which raised col 3 to 13 (spawn lane 13/13).
  2. **k=41–43:** late flips and one different target, all ending on the left.
  3. **k=45, SHORT-LANDING (clamp):** the brain wanted V col 7 (the lowest column, 4 away). The pill was clamped
     to col 4, raising it to 15. From here every spawn sits on a throat ledge (first occupied row of col 4 = 1).
  4. **k=46–49, PROPH-ESCAPE ×4:** DRPROPH fired every time. It pulsed LEFT (the "deeper throat side"
     heuristic) at exactly 1 col / 2 frames (moves at f4/6/8), before the brain's answer (~f15–20). **In all four
     the brain's target was on the RIGHT** (H5, H6, H5, V7). The pills piled into cols 0–2, which went from
     11/13/12 to 16/15/14.
  5. **k=50:** no lateral move in 13 frames. It locked in the spawn cells, and the next spawn was blocked.
- **The owner's garbage was modest:** 7 volleys, 16 cells in 83 s (2,2,2,2,4,2,2). Two volleys landed in the
  final 15 s. Garbage shaped the board but decided none of the final placements.

## Gates
| gate | result |
|---|---|
| GATE 1a: reader P2 virus count vs on-screen counter | **14/14** frames, 287–367.5 s (32, 31, 31, 30, 28, 26, 24, 24, then 22 ×6) |
| GATE 1b: colours by eye | 3/3 frames (309.4, 349.0, 366.2 s), every overlaid R/Y/B + virus label correct |
| GATE 2: decider plumbing | **428/428** identical actions on 3 banked gate-(b) fw540 games, round-tripped through this reader's string encoding + board constructor (398 boards carried links) |
| mechanics cross-check (reader + tracking) | for **49 consecutive placements** (k=0–48), S_k + observed landing + faithful `resolve()` ⊆ S_{k+1} with **0 missing/changed cells**. The extra cells are exactly the garbage volleys. |
| link reading | 0 link-consistency violations on every pre-death board. Links matter: zeroing them changes 17/51 sim decisions. Silicon agrees with the sim **32/51 with read links vs 23/51 all-unlinked**, so the silicon brain uses links and the reading is right. |

## Counts
| window | MATCH | SHORT-LANDING (clamp) | PROPH-ESCAPE | LATE-FLIP | TUCK | OTHER |
|---|---|---|---|---|---|---|
| all 51 placements (285–368 s) | 32 | 3 (3) | 5 | 5 | 2 | 4 |
| last 25 (k=26–50) | 14 | 2 (2) | 4 | 2 | 0 | 3 |
| last 12 (k=39–50) | 2 | 2 (2) | 4 | 2 | 0 | 2 |
| clean placements (no PROPH trigger, straight drop) | 18/26 | | | | | |

Category definitions are in `classify_g2.py`:
- **TUCK:** the landing is not a straight-drop resting position. The pill slid under an overhang (cart DRTUCK=1),
  which is outside the sim decider's action space.
- **LATE-FLIP:** the capsule held the brain's exact target pose (orientation + column + colours) for 5–25 frames,
  then changed pose before locking. This matches the Aug exec-fidelity "mid-pill commit flip" class. Mechanism
  not resolved here: an anytime re-publish or a driver recommit.
- **PROPH-ESCAPE:** DRPROPH fired and the pill ended on the pulse side while the brain's target was on the other
  side.

## Timing measured from video (60 fps, frames after the preview change)
- **DRPROPH pulse:** moves at f3–4, f5–6, f7–8 in all 20 triggered placements with movement. That is the design's
  1 col / 2 f exactly. PROPH fired on 24 of 51 spawns (col 4 sat at height 15 for ~25 s mid-window).
- **Normal steering, no carry ever observed:**
  - First lateral move at median **f17** (range 15–25): the answer latency.
  - The next move comes after 16 f (fresh press + engage), then 6 f/col.
  - Gap histogram: 6 f ×10, 16 f ×7, other gaps scattered.

## Counterfactuals (owner's "DAS momentum" point + ROM $8DCF carry model)
Steering-time models:
- Driver without carry: first move ≈ f17, then 16 then 6 f/col.
- ROM carry: first move at (16 − v) f with v ∈ [10, 15], then 6 f/col.
- PROPH pulse: 1 col / 2 f.

Results per placement:
- **k=39 (2 cols) and k=45 (4 cols), the two clamp turning points.** Carry needs 7–12 f and 19–24 f. Without carry
  the driver needs ≈33 f and ≈45 f. The fall budget was about one row (~15–30 f), so **carry would plausibly have
  reached both targets. The driver as built could not.**
- **k=46–49, ledge spawns.** A throat-ledge capsule locks on its first blocked gravity tick, W ≈ 8–10 f
  (DRPROPH design notes).
  - Carry alone reaches only the 2-col targets (k=46, 48) and only if v = 15 (7 f).
  - **A PROPH pulse aimed at the brain's side would reach all four** (3, 5, 3, 7 f).
  - The heuristic direction (deeper of cols 3/4) sent all four LEFT against the brain.
- ⇒ **Concrete driver change the data points at:** take the PROPH pulse direction, and a DAS pre-hold through the
  lock, from the brain's plan for the NEXT pill. The previous search's ply-2 plan exists before the spawn.
  - On this death, 6 of the last 12 placements (k=39, 45, 46–49) were steered away from the brain by the two
    mechanisms such a change targets.
  - Caveats: the sim's choice at spawn stands in for the ply-2 plan, which was computed before the last garbage
    landed. Whether the game survives is not knowable from one death; the right side was itself tall (cols 5/6
    at 15/13).

## What this means for the couch-vs-sim tap-out gap
The sim assumes perfect steering, has no DRPROPH, and never clamps, so it cannot produce the k=39–50 sequence.
**This one death supports hypothesis A (steering / driver) over B (garbage) for the fatal part.** The stall
before it is the brain's own play. One death is n = 1. The instrument now exists to classify every future
recorded death the same way:

```
scan_frames.py VIDEO T0 DUR frames.jsonl
track.py frames.jsonl placements_raw.jsonl
analyze_g2.py run placements_raw.jsonl analysis.jsonl
classify_g2.py analysis.jsonl placements_raw.jsonl out.jsonl
```

Grid geometry is fitted to the 9/25 capture; re-verify GATE 1 on any new capture.

## Files
- `reader.py`: NES-pixel tile reader (colour / virus / link from corner notches), geometry fitted to this capture.
- `scan_frames.py`: ffmpeg rawvideo stream through the reader. Nothing is written but per-frame JSON (tmp/).
- `track.py`: spawn detection (preview change) and settled board. Pop tiles and the capsule are handled; the
  capsule is erased at spawn.
- `analyze_g2.py`: GATE 2, sim decider comparison, mechanics cross-check, timing, DISTGATE budget.
- `classify_g2.py`: categories and counterfactuals.
- `g2_placements.jsonl`: **the 51 banked cases.** Each has the settled board (colour/virus/link), pill, next pill,
  sim action, silicon landing, category, timing, PROPH state and garbage.

Private footage and every frame/crop stay in gitignored `tmp/couch_forensics/`.
