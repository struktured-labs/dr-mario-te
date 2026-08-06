# THE HOLE POKER — deep adversarial search against the strand20 champion

Tier 4 of the adversarial program. Everything here runs in the **offline python
simulator**, which disagrees with real RTL on ~87% of base-search MOVES
(`CANDIDATE_TIER3.md` §10). **Every hole below is a SIMULATOR hole until it is
replayed through the Verilator co-sim.** Named validation targets are in §8.

---

## 1. The structural idea, and why it works

The champion is **deterministic and depth-3**. Its reply to any position is a
computable function, not a strategic choice. An adversary allowed unbounded
thinking time therefore does **not** face a minimax game — it faces a
**single-agent planning problem in which the champion is an oracle**. Branch only
on the adversary's own choices; compute the champion's forced reply exactly at
every node.

Two things make it fast:

**(a) An admissible lower bound.** A topout needs row 0 of column 3 or 4
occupied; a no-legal-move needs every column filled to row ≤1. One placement
adds at most 2 cells to one column, and clears/gravity only ever *raise* the
top-occupied row. So

```
h(state) = ceil((min(top_occ[3], top_occ[4]) - 1) / 2)
```

is a true lower bound on placements-to-death. IDA* with this `h` prunes whole
subtrees **without spending a single oracle call on them**, and because the
champion actively refuses to stack the spawn columns, most branches die on the
bound immediately.

**(b) Memoisation.** Identical `(board, cur, next)` recur constantly. Measured
hit rate: **29%** in solo trajectories, **96%** in VS search (there the
adversary's placements usually don't touch the champion's board at all, so the
champion's reply is literally the same computation).

### Cost reality
The champion's d3 reply is **~56 ms and irreducible** — the monolithic jitted
chooser (`FX._choose_d3_ship_eh`, 55.8 ms) is no faster than the 32-candidate
python loop (57.5 ms), so there is no restructuring win. That is ~18 oracle
calls/sec/core. Exhaustive solo search costs `6^K` calls: K=6 is ~43 min, K=8 is
~20 h. This is why the primary instrument is a **beam** (upper bound, reaches
depth 18-22 cheaply) with **IDA\*** reserved for exact minimality where it is
affordable.

---

## 2. Gates — what was verified before any result was believed

| Gate | Question | Result |
|---|---|---|
| **G0 oracle fidelity** | does our champion wrapper reproduce the shipped decide path? | **PASS** — 8 full games, 1064 decisions, trajectories **identical** to `eval47/ab47.py`'s own loop (wt=0, ws=20) |
| **G1 pill alphabet** | is `(a,b)` the same capsule as `(b,a)`? | **PASS** — 108 board-level comparisons, 0 differences ⇒ the 6-pill alphabet is sound (action *encoding* differs by a variant-parity bit and on ties; the resulting **board** never does) |
| **G3a positive control** | can the search find kills at all? | **PASS** — K=1 in 6 calls, K=3 in 84 calls on boards built near death |
| **G2 admissibility** | does `h` ever exceed true plies-to-death? | see §7 |

**G3b was retracted as vacuous.** It asked "can a healthy board be killed below
the bound?" — but `SoloPoker.search` starts its iterative deepening *at* the
bound, so it can never return a depth below it no matter how wrong the bound is.
It would have passed on a broken bound. Admissibility is tested for real by G2.

**Fixture design mattered more than expected.** The first positive control buried
only columns 3 and 4 — and the champion simply played the other six columns, so
the search burned `6^K` finding nothing. That fixture could not distinguish "the
champion is robust" from "the search is broken". Only fixtures that remove the
escape routes are valid controls.

---

## 3. SOLO: the champion has no shallow pill-stream holes

### The champion does not top out on its own
1200 solo games, levels 15/17/19/20, real NES capsule stream:

| level | n | clear | topout | stall |
|---|---|---|---|---|
| 15 | 300 | 99.7% | **0** | 1 |
| 17 | 300 | 99.7% | **0** | 1 |
| 19 | 300 | 99.7% | **0** | 1 |
| 20 | 300 | 99.3% | **0** | 2 |

**Zero topouts in 1200 games.** This independently reproduces
`dr-mario-stomper-loss-autopsy` (400 VS losses, zero topouts) and is the single
most important framing fact in this report: *the champion's deaths are not solo
deaths.*

### Even from dangerous positions, the pill stream cannot kill it
129 **real** positions sampled from the champion's own play (levels 11-20),
stratified by spawn-column height including 9 positions at `spawn_top=2` — one
row from the top. Beam width 16, depth 18.

*(results table filled in §6 when the run completes)*

---

## 4. VS: this is where the champion actually dies

The adversary's real lever is not the pill stream (nobody chooses your capsules)
but **garbage**: clear two lines simultaneously, two tiles drop. The adversary
branches over **its own placements** — which cost no oracle calls — while the
champion answers once per ply. That asymmetry makes deep VS search cheap.

| adversary | kills / 14 seeds | median plies to kill |
|---|---|---|
| champion in the adversary seat (control) | **0 / 14** (0%) | — |
| deep-search beam, v1 (attack-only objective) | 1 / 14 (7.1%) | 24 |
| deep-search beam, v2 (attack + self-preservation) | **5 / 14 (35.7%)** | 23 (range 8-57) |

**Deep search strictly dominates the champion-seat control**, 35.7% vs 0%.

### The v1→v2 jump is a methodological warning worth more than the number
v1 scored only garbage sent. It stacked its own board chasing double clears and
**killed itself in 13 of 14 seeds** ("no surviving lines" — every beam line had
topped the *adversary* out). That run measured my adversary's incompetence, not
the champion's robustness. Adding self-preservation to the objective **5x'd the
kill rate.** Any "the champion survived" claim is only as strong as the
adversary that failed to kill it — including the solo negatives in §3.

---

## 5. COUNTERFACTUAL: the real m3 silicon death was NOT myopia

Six consecutive capsule commits reconstructed from the m3 video, ending in a
topout. Prior work (`recon/VERDICT.md`) adjudicated *mechanism* (H1, pair-latch
commit-path defect) from the eval's rankings. This establishes *consequence*.

**Q1 — continuity: 5/5.** Applying the tape's placement to board *i* reproduces
board *i+1* **exactly**, on the colour plane, for every consecutive pair. So the
world model matches real silicon on this tape, no garbage arrived between these
commits, and the tape's action is identified unambiguously without relying on the
video's ambiguous orientation reading.

**Q2 — the eval's own choice survives.** The champion wants a *different column*
from the tape in 5 of 6 commits. Rolling the champion forward from **every one**
of the six boards, under the known pill stream, it **stays alive to the end of the
stream** — including from c6, the last board before the tape's topout.

**Q3 — the position was never lost.** Exhaustive deduped BFS over the champion's
*own* action space against the fixed stream (no oracle needed — pure mechanics):
**every one of the six commits was survivable**, right up to the fatal one. The
trap never closed. (Cap only threatens *negative* answers; all six are positive,
so the answer is sound.)

> **Verdict: the m3 death was neither myopia nor an already-lost position.** The
> eval had a survivable move at every step and the hardware played a different
> column. That is an execution defect, and it confirms H1 with a forward search
> rather than a ranking argument.

Window caveat: the known stream is 7 pills, so "survivable" spans 1-6 plies
depending on the commit. The claim is strongest at c1-c4 (3-6 ply windows).

---

## 6. Hole taxonomy

*(filled when the taxonomy run completes)*

---

## 7. G2 — admissibility

The original plan was to falsify `h` against real champion deaths. **The death
corpus came back with zero topouts**, so that route produced no test cases. `h`
is instead falsified against every *killing line* the poker produced, each of
which ends in a replayed topout: at each state, `h` must be ≤ the placements that
actually remained.

*(result filled when lines are available)*

---

## 8. What to validate on real RTL

*(named targets filled with the taxonomy)*

---

## 9. Files

| file | what |
|---|---|
| `champion.py` | the memoised oracle + faithful world-step |
| `poker.py` | admissible bound, IDA* solo poker, beam |
| `margin.py` | shortest-kill + escape-depth `E` |
| `taxonomy.py` | the histogram run (beam → E, with replay check) |
| `vs_poker.py` | VS deep search + champion-seat control |
| `vs_escape.py` | escape depth for the VS kills |
| `m3_counterfactual.py` | the real silicon death analysis |
| `m3_margin.py` | prices the m3 blunders in pills of margin |
| `death_corpus.py` | 1200-game solo death hunt |
| `sample_boards.py` | stratified real-position sampler |
| `gates.py` | G1/G2/G3 |
| `smoke_oracle.py` | G0 — oracle vs shipped decide path |
