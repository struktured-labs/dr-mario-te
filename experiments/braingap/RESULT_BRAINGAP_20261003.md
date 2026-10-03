# Brain gap: why the copro's final answer differs from the sim brain (2026-10-03)

**Question.** On couch G2 (10/03, ANTIBODY_DIST: fw 1488e158 + RTL `claude/dist-leaf` 3b164c7) the copro's final
answer matched the python sim brain (`cascade_leaf6_x.Leaf6Decider`, dist_target60 on ANTIBODY/HSV512) on only 87/116
boards. 8 of the misses are tuck commits. The other **21 were unexplained value differences**.

**Answer.** All 21 come from **one firmware root add-on that the sim models differently: the ply-1 excavation + hang
term (`eh_terms`, `D_AD`).**
- **R4 hang credit.** The firmware pays **40 + 20·gap per hovering half, and only in columns that hold a virus**. The
  sim pays a flat 40, in any column. This was a known caveat in `fast_rtl_x.py`: "NOT R4-refined in the python
  bridge".
- **The soft b1.** The firmware scores eh on a board it rebuilds in 6502 RAM: the root plus a straight drop, a
  targeted cap-1 clear and **one compact gravity**. Compact gravity drops every hovering half and ignores links. The sim
  scores eh on the link-aware fixpoint child, which is the same board the engine scores.
  - The two boards differ **only on clearing roots**: 63 of 69 clearing roots on the 21 boards, and 0 non-clearing
    roots.
  - On **57 of those 63**, the soft board carries **less** hang credit.

Moving those two switches from python to firmware semantics reproduces silicon on **21/21**. Reverting either one in
the firmware model breaks the match on **16/21** (R4) and **13/21** (soft b1).

None of the candidate causes the brief listed explains any of the 21. Each was tested both ways: added to the python
model, and reverted in the firmware model.
- **int16 wrap / saturation and the HSV/DIST fold.** The RTL-exact twin equals python on 21/21. Reverting the wrap in
  the firmware model never changes its answer.
- **Expected-third / ply-3 fallback.** The per-root best2 is identical between the firmware model and py65.
- **Tie-break order:** 0/21.
- **REACH mask.** The python mask equals the firmware's R_FLT/ROK on 335/335 couch boards.
- **DRCHAIN / DRSTRAND.** Per-root imm1 and strand are identical.
- **matched60 / the leaf.** Per-root leaf1 is identical. The engine model also reproduces the co-sim.
- **DRVETO:** 0/21.
- **DIST.** Inactive: all 21 boards had 15 or more viruses.

## Instruments (all new, `experiments/braingap/`)

| tool | what it is | validation |
|---|---|---|
| `rtlengine_braingap_20261003.py` | The shipped fw logic under py65, from the reset stub through search, tuck and DONE. Every engine command is answered by the sim's own RTL-gated node (`_expand_chain` link-aware fixpoint, `_leafv_ship` + HSV512 + DIST wrapped together, chain bonus, CMD-8 strand). | The delta build's md5 is **1488e1583ab7ad8b2011d4c136926faf** (= shipped). The non-delta build is run, as fwlib does. Whole-decision final == Verilator co-sim on **331/335** boards (G2 113/116, G3 86/86, G4 132/133). All 4 misses are tuck-extension commits that py65 made and the co-sim did not (G2 p7, p8, p101; G4 p105). |
| `py65run_braingap_20261003.py` | Runs py65 on the exact cart-upload bytes from the co-sim timelines, using the DEBUG_VAL1 ring for per-root components. | Main-search final == co-sim on **326/326** non-tuck boards. |
| `mirror_braingap_20261003.py` | A pure-python switchable root search: python semantics ↔ firmware semantics, one feature at a time. | FW mode == py65 per root (V1, I1, L1, B2, AD, strand, veto, evaluation order) on 610/610 roots of the 21. PY mode == Leaf6Decider 21/21. |
| `cascade_leaf6fw_braingap_20261003.py` | **`Leaf6FwDecider`**: the same switches in numba. This is the sim-brain fix. | All switches **off == Leaf6Decider on 335/335**. All switches **on: per-root V1 == py65 on 9,689/9,689 roots** (G2 3,119, G3 2,580, G4 3,990). Final == co-sim **326/326** (python mask or firmware mask). |
| `compare_ / validate_ / cases_ / impact_ / simboards_ / g2replay_braingap_20261003.py` | Attribution, validation, banked cases, the sim-board impact estimate, and the G2 counterfactual rerun. | |

The engine conclusion follows: python's leaf/node arithmetic plus the firmware's search logic reproduces the real
RTL's answers. **The gap is the root-search structure, not LeafEval.**

## Per-cause table

Buckets come from the switch tests (`cases_braingap_20261003.jsonl`):
- **R4-hang:** python + hang alone reproduces silicon, and the firmware without hang does not.
- **soft-b1:** the same test for the soft board.
- **either:** either switch alone reproduces silicon.
- **joint:** neither works alone, both together do.

| cause | G2 (of 21) | G3 (of 7) | G4 (of 7) | which side is right | fix |
|---|---|---|---|---|---|
| **R4 hang credit**, alone | 5 (+3 either) | 4 | 5 | **Firmware = shipped design.** `build_copro_d3` sets HANG_DEPTH_PROP / W_HANG_GAP 20 / HANG_VIRUS_COL_ONLY deliberately ("R4 … -> copro_rom.hex"). The sim's flat 40 is a documented simplification (`fast_rtl_x.py:774`). The te diagnostic `experiments/tuck_v3/test_firmware_decider.py` already recorded "a 50-point gap". | **Sim:** model R4 (`hang=1`). R4 has **never** been A/B'd in the sim, because the sim never had it. Run that A/B before keeping or dropping it on silicon. |
| **soft b1**, alone | 2 (+3 either) | 2 | 1 | **The sim matches intent; the firmware deviates.** eh is defined on "the resolved ply-1 board b1". The 6502 re-derivation (soft land + targeted cap-1 + compact gravity) dates from the weekend-era resolve. After DRFIX / link engine it no longer equals the engine's own b1. On clearing roots it drops every hovering half, so the hang credit for "the delayed drop when its partner clears" vanishes exactly when a clear happens. | **Sim now:** model it (`ehb1=1`), so verdicts are about silicon's brain. **Firmware candidate** (report, don't fix: fw lane): score eh on the true b1 (link-aware gravity in the 6502 rebuild, or an engine-side scan). Gate it with a sim A/B of `ehb1=0` vs `ehb1=1` at `hang=1`. |
| **R4 + soft b1, jointly** (neither alone) | 11 | 0 | 1 | as above | both switches |
| **Tie-break order** (firmware: descending Pass-0 key, first max; python: enumeration) | 0 | 1 (p67, exact tie) | 0 | Neither. It only matters on exact ties. | **Sim:** `order=1`, trivial. |
| DRVETO, eh skip on no-legal-ply-2, int16 wrap, REACH mask, DRCHAIN/DRSTRAND, ply-3 fallback, matched60/HSV/DIST | 0 | 0 | 0 | Firmware = intent. The sim lacks VETO and the skip, but they never decide a couch board. | Include them in the faithful sim for exactness (`Leaf6FwDecider` does). |
| (tuck commits, out of scope) | 8 | 1 | 0 | fw lane (DRTUCKREACH / DRTUCKLIVE) | |

**Python margins on the 21:**
- Median 63, minimum 5 (under the python model, python's pick minus silicon's pick).
- The firmware model's margin for silicon's pick: median 90, range 6–255.

**Direction on G2:**
- In **16/21**, python's pick clears cells and silicon's pick does not. The reverse happens 0 times.
- On G3 and G4 it is mixed: 2 vs 1 and 1 vs 4. On G4 the virus-column-only rule cuts python's hang credit, and
  silicon clears instead.

**Why G2 is hit hardest (measured, not mechanism).** G2 boards carry 1.08 matching-colour hovering halves per board,
and 78% have at least one. The other boards carry far fewer:

| boards | matching-colour hovering halves per board | share with ≥ 1 |
|---|---|---|
| G2 | 1.08 | 78% |
| G3 | 0.16 | 16% |
| G4 | 0.19 | 19% |
| sim, python play | 0.36 | 29% |
| sim, silicon-faithful play | 0.22 | 19% |

Both causes act only through hovering halves. The sim does **not** show silicon's brain making more of them (19% vs
29%, n = 12 games each, no outcome claim), so G2's hang richness is not explained here.

## Impact on general sim boards (task 3)

Sim boards are gate-(b) games vs owner-0804, s6_dist_target60 steering, seeds 36734 + 2i, 12 games each. A
"divergent" decision is one where python's pick differs from silicon-faithful (all switches on).

| corpus | divergent decisions | R4 alone moves | soft b1 alone moves | VETO / wrap / order | EH-only fix == silicon |
|---|---|---|---|---|---|
| python brain playing (2,179 decisions) | **114 (5.2%)** | 4.5% | 1.4% | 1 / 1 / 4 boards | 2,174/2,179 |
| silicon-faithful brain playing (2,111 decisions) | **116 (5.5%)** | 4.3% | 1.1% | 0 / 0 / 3 boards (+1 ehnp) | 2,107/2,111 |
| couch 10/03, real silicon play (326 non-tuck) | **35 (10.7%)**: G2 19.4%, G3 8.2%, G4 5.3% | | | | 325/326 |

**By phase:**

| | python-play boards | silicon-faithful-play boards |
|---|---|---|
| max height ≤ 9 | 3.5% (10/285) | 5.7% (29/512) |
| max height 10–11 | 4.3% | 3.4% |
| max height 12–13 | 5.1% | 4.8% |
| max height 14–16 | **6.8%** (50/730) | **8.9%** (41/460) |
| 0–4 viruses | 5.0% | **7.0%** (54/766) |
| 5–8 viruses | **6.5%** | 4.3% |
| 9–16 viruses | 5.7% | 4.2% |
| 17–32 viruses | 4.6% | 5.8% |
| 33+ viruses | 3.2% | 3.8% |

**The gap concentrates on the tallest boards and in the endgame, and scales with hovering halves.**

**Which brain clears on the divergent decisions:**

| corpus | python's pick clears cells | silicon's pick clears cells | viruses cleared at once (python vs silicon) |
|---|---|---|---|
| python-play | 24 | 25 | 18 vs 11 |
| silicon-play | 34 | **14** | 24 vs **5** |

**Combined:** where they disagree, silicon's brain takes the immediate clear less often, and clears 16 viruses
against python's 42 over 230 divergent decisions. G2 is the extreme case: 16/21 declined.

**What this means for past verdicts:**
- Every sim result used Leaf6Decider or its ancestors (base hang, eh on the link-aware b1) in **both** arms: STEER1–7,
  DOSE, OPP1, holes80/winner, and the late-flip regret column. So their deltas describe a brain that picks
  differently from silicon on ≈ 5% of decisions, and ≈ 7–19% on tall, hang-rich boards.
- **Most exposed:** anything that interacts with the eh terms or with clearing on hang-rich boards.
  - STEER6e `s6e_fin` gated w_excav / w_hang. Silicon's eh is stronger: R4 inflates it, and the soft b1 removes it
    from clearing roots.
  - The DIST60 endgame term competes with eh.
- The pure-arithmetic gates (twin, wrap headroom, mask) stand.
- A quantitative re-verdict needs the A/B rerun with `Leaf6FwDecider`. It was not run here (box saturated, by
  instruction).

**The G2 counterfactual changes** (`g2replay_braingap_20261003.txt`, `g2replay_steer_braingap_20261003.txt`):

| replay of the observed capsules + garbage | python brain | silicon-faithful brain |
|---|---|---|
| brain-only, perfect execution, from p0 | CLEAR at p114 | **alive at p115, 5 viruses, max height 10** (not a clear) |
| steering model, 20 latency seeds, from p0 | CLEAR 20/20 | alive 19/20 (5 viruses), **TOPOUT 1/20** (p96) |
| steering model from p31 | alive 20/20, 5–6 viruses | alive 20/20, 3 viruses |

- "The brain alone clears the board" was a property of the python brain.
- Silicon's own brain, executed perfectly, still survives the observed sequence. So "G2's tap-out = execution" holds,
  but the clear does not.

## Recommended fixes
1. **Sim (now):** score sim verdicts with `Leaf6FwDecider` (all switches on). It is value-exact against the shipped
   firmware on 9,689 roots and costs about the same as Leaf6Decider.
   - The minimum fix is the eh switches (`hang`, `ehb1`, `ehnp`): 2,174/2,179 sim boards and 325/326 couch boards.
   - Re-score the late-flip regret and `steer_churn` with it too: they use the python evaluator.
2. **Re-run the decisive A/Bs on the faithful brain** when the box frees up. Priority order:
   - (a) python vs faithful, for tap-out and race;
   - (b) faithful with R4 vs flat hang (`hang` 1/0);
   - (c) faithful with `ehb1=0` (eh on the true b1, i.e. a firmware fix) vs 1;
   - (d) the STEER6/6e verdicts.
3. **Firmware (report to the fw lane; not fixed here):** `eh_terms` scores a stale soft b1.
   - On clearing roots it compact-drops every hovering half, so the hang credit disappears exactly when a clear makes
     the drop real.
   - Whether to change it depends on 2(c). A 6502 link-aware rebuild costs cycles. An engine-side eh scan costs RTL.
4. **Instrument caveat:** the py65 + RTL-faithful engine does not reproduce the co-sim's **tuck extension** on 4/335
   boards. The main search is exact. Engine semantics for the tuck path's soft-injected boards are unverified, so use
   the Verilator co-sim for tuck questions.

## Reproduce (nice 19; numba cache `h16 tmp/braingap/nbcache`; te tree `dr-mario-braingap-wt` @ 395973c5)

```
TL=/home/struktured/projects/dr-mario-lateflip-wt/experiments/lateflip/pubtrace_G2_fw1488e158.jsonl
python rtlengine_braingap_20261003.py                                  # delta image md5 == 1488e158
python py65run_braingap_20261003.py $TL py65_G2_braingap_20261003.jsonl --debug --workers 2   # (G3, G4 alike)
python compare_braingap_20261003.py G2 cmp_G2_braingap_20261003.jsonl 20 28 31 ...   # mirror switch attribution
python validate_fwvariant_braingap_20261003.py OUT.jsonl G2 G3 G4     # numba decider vs py65 roots + co-sim
python cases_braingap_20261003.py cases_braingap_20261003.jsonl        # the 35 banked divergent cases
python simboards_braingap_20261003.py 12 36734 simboards_braingap_20261003.jsonl [fw]
python impact_braingap_20261003.py simboards_braingap_20261003.jsonl impact_sim_braingap_20261003.jsonl
python g2replay_braingap_20261003.py g2replay_braingap_20261003.txt [--steer 20 0 31]
```
Use in a sim: `cascade_leaf6fw_braingap_20261003.Leaf6FwDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2,
mode="dist_target", W=60, vk=4)` is a drop-in for `Leaf6Decider`. `sw=` takes a dict of the switches, all on by
default.
