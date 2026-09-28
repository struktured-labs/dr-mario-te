# STEER6 phase 1: prior art for "build toward a clear" (2026-09-27)

**The target:** a STUCK virus is one with no clearing move for many pills.
- In the couch lulu G1 stall, a yellow at (8, 2) sat under the stack `r b y b r b r y`. It had a clearing move on
  only 2 of 102 pills, and the fix needed cols 3–4 to fill up to row 9.
- In match-1 G3, a yellow at (8, 3) was walled in. No candidate cleared it for 88 pills.
- The couch forensics conclusion: the missing capability is valuing PROGRESS toward the clear, not the clear itself.

**The shipping leaf** (ANTIBODY = `winner` coefficients + CHAIN540 + STRAND20 + HSV512, `fast_rtl_x._eval_rtl`):
`5000 −12·maxh −20·holes −90·toprisk −150·spawn +32·setup +48·matched −48·buried +8·rdy_ext +8·vrdy −6·pollution`,
plus −512·HSV and the chain/strand root terms.

## What already measures "readiness" or "access", and why none of it sees progress toward a stuck virus

| prior art | what it computes (per virus unless noted) | status | why it is blind to the stuck case / how a new term differs |
|---|---|---|---|
| **vrdy** (`tests/test_vrdy.py`, NES 6502 primitive; RTL `+8·vrdy`) | same-colour contiguous run through the virus VERTICALLY, Σ run² | shipped (8) | Vertical only, and only CONTIGUOUS same-colour cells count. Under a mixed stack (`r b y b r b r y`) the run is 1 and stays 1: no gradient. |
| **rdy_ext** (`tests/test_readiness_ext.py`; RTL S_HRUN/HSPAN/VRUN/VSPAN, `+8·rdy_ext`) | max over axes of run², counted only if that axis's **span** (same colour OR empty, stopping at the first different colour) ≥ 4 | shipped (8) | **(1)** An empty cell counts as "available" whether or not anything supports it: gravity is ignored. **(2)** Empty cells earn nothing; only a contiguous same-colour run does. **(3)** One wrong-colour cell zeroes the axis. **Measured on the couch boards** (`cases_lulu_20260927.jsonl`, virus (8, 2), k80–k181): hq = 1 and vq = 4 (one yellow pill half sits directly on it; span ≥ 4 below). So rdy_ext = **4 on every pill for 100 pills**. It jumps to 9 only at k182, one pill before the clear. **Zero gradient.** A **clearing-distance** term charges each empty window cell `1 + (empty cells beneath it)`, so it falls by one per support cell built, exactly where rdy_ext is flat. |
| **readiness (rg)** (`tests/test_readiness_rg.py`, `g_readiness`) | max(h, v) run², no span test | older NES primitive, superseded by rdy_ext | Same blindness, and it doesn't even check that the line can reach 4. |
| **setup** (RTL S_SETUP_H/V, `+32`) | +1 per 3-in-a-row (h or v) touching a same-colour virus | shipped | Rewards the LAST step before a clear (3 same-colour cells adjacent). Nothing before that, so it cannot pull support-building 5–10 pills ahead. |
| **matched** (LeafEval `matched60`, `+48` per virus) | the non-virus run directly above the virus is the same colour | shipped | A vertical "capped by the right colour" bonus. No horizontal notion, no support notion. |
| **buried** (`−48`, colour-aware exemption, nearest-2 cap) | filled cells above each virus, excluding a same-colour run directly above it | shipped at the coef-opt optimum | Prices COVER. Raising it is **harmful twice**: run 17 (48 → 96: tap-out 13.0 → 21.7%) and STEER5 BUR35 / RB35 (spawn-col burial and R_BURIED in cols 3–5: +5.8 … +25.7 pp tap-out). The failure mechanism: **it makes the brain avoid covering viruses, so it contorts while garbage rains**, and garbage buries the virus anyway. "Don't cover" is a different objective from "build the support that unlocks it". A clearing-distance term must not become a cover price in disguise (below). |
| **pollution** (`−6` per cell) | wrong-colour non-virus cells anywhere in the virus's row or column | shipped | Global and flat. It weakly penalises putting wrong colours in the target row. It is also a tiny cover price and has no support gradient. |
| **ACC35** (`s5_acc60` / `s5_acc180`, STEER5) | +W per spawn-col virus that is ACCESSIBLE NOW: the column above is empty or same-colour, or a side slot is droppable and supported | **failed** (+2.8 pp tap-out at 60; **+7.0 [+2.0, +12.0]** at 180) | **Binary** and **present-tense**: it rewards KEEPING access, i.e. not covering. That is the burial price with the sign flipped, and it fails the same way. It gives no credit for moving a sealed virus from "10 cells away" to "3 cells away". |
| **HSV512** (shipping, STEER5b–5d) | −512 per virus in cols 3–5, rows < 9 | **shipped**, works (tap≤100 −2.3 pp) | A static **priority** on WHICH viruses to clear. It says nothing about HOW. When no clear is within the depth-3 horizon it is constant across candidates, so it can't steer. Widening it to cols 2–6 changes 3 of 102 lulu-G1 choices and doesn't shorten the stall (couch forensics). |
| **Stall breaker** (`cascade_dig_x`, STALLBREAK1, 9/25) | DIG MODE when ≥ S placements pass without a virus clear AND the spawn lane is ≥ H. Levers: chain dose 0, a root spawn-height penalty, a **root virus-clear bonus** | **failed** (Δ tap-out +0.17 … +1.33; all/all_early cost race −3/−4 pp; churn 10 fixed / 18 new) | **(1)** Its levers are reactive PRIORITIES: pay more for a clear, pay more for height. A virus-clear bonus is worthless when no clearing move exists within reach, which is exactly the stuck case. **(2)** The trigger (no-clear streak AND a tall lane) missed 6 of 14 deaths: fast deaths where the bot kept clearing while the lane was 13–15. **(3)** Lesson carried forward: report fixed/new on base failure seeds, because a stronger rescue mode mostly churns a chaotic trajectory. |
| **Dig census** (`census_reach2.py`, 9/13) | classifies endgame viruses as drop-reachable / tuckable (side cell open under an overhang) / BURIED (every neighbour occupied) | diagnosis | On failed endgame boards 79% of remaining viruses are BURIED and 98% of failed endgame plies hold one. The endgame is a dig. It is a **classifier, not a gradient**: "buried" is one bucket whether it is 2 or 12 cells from a clear. A clearing distance is the graded version of this census. |
| **Tuck** (cart DRTUCK v1 + DRTUCKGUARD veto) | ACTION-space extension: slide under an overhang into the cell beside a virus; the guard vetoes tucks with no fall budget | shipped on the cart; **absent from the sim brain** | Orthogonal: it makes more cells REACHABLE, not more boards valuable. Silicon dug out match-1 G3 with 5 tucks (k79–84) the sim cannot represent. A distance term in the sim will treat under-overhang cells as unreachable (∞) where silicon might tuck. That is a known sim-to-silicon gap in the conservative direction. |
| **Chain search horizon** (depth 3: 2 known pills + an expectation over the 3rd) | — | shipped | Any unlock that needs more than 2–3 pills of building is beyond the search. The leaf is the only place a far-away clear can register, so the new capability has to live in the LEAF (or change the search, candidate c). |

## What a new term must do that none of the above does
1. **Graded and monotone in progress.** Each support cell built lowers the cost by one, and nothing happens only at
   the finish line (setup, matched, ACC35 are finish-line terms).
2. **Gravity-aware.** A cell counts as fillable only when something can rest there. Otherwise it costs its support
   gap; rdy_ext ignores support.
3. **Min over routes (windows and axes).** Covering a virus vertically must NOT raise the cost if a horizontal route
   remains, and vice versa. Otherwise it degenerates into the burial price that failed three times.
4. **Scoped to STUCK viruses** (the ones with no clearing move), not every virus every ply. Early game every virus
   is "a few cells away", and a global distance term would be a second, redundant readiness term whose dose would
   compete with clearing. Scoping options: the last K viruses, or firmware-flagged targets, or a board-stall
   trigger (see phase 3).
5. **RTL shape.** LeafEval already walks each virus's row and column (S_HRUN_L … S_VSPAN_D) and each column's top
   (S_COLWALK). A window-based distance is a few more per-virus states using the per-column top rows. That is
   sequential cycles, not combinational depth, but it costs leaf latency. The cheapest variant takes one
   firmware-supplied TARGET descriptor (row, window columns, colour) per decision; its RTL cost is ~3 column-top
   compares plus 3 colour checks.

**Regression trace (for phase 3).** A naive horizontal clearing distance on the same boards: Σ over the window's
empty cells of `1 + support gap`; a wrong-colour cell or an under-overhang cell makes that window infeasible.
- It reads **12–19 through k80–k176**, then **6 → 4 → 2** at k182–k184.
- It is NOT monotone during the stall. The AI kept building cols 3–5 up and then clearing its own support, because
  it cleared other viruses there.
- So the distance term would have had something to say: "don't dismantle cols 3–5 below row 9".
- The same trace also shows the cost: honouring it means holding the spawn columns at height ~8, which is the
  spawn-lane risk every height term fights. Dose and scope matter (phase 3).

Next: phase 2 sizes how often this happens in sim (`MEASURE_STEER6.md`).
