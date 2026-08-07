# THE HOLE POKER — deep adversarial search against the strand20 champion

Tier 4 of the adversarial program. Everything here runs in the **offline python
simulator**, which disagrees with real RTL on ~87% of base-search MOVES
(`CANDIDATE_TIER3.md` §10). **Every claim below is a SIMULATOR claim until it is
replayed through the Verilator co-sim.** Named validation targets are in §8.

---

## TL;DR

1. **The champion has no solo pill-stream holes.** 1200 games at L15-L20: **zero
   topouts.** On 21 real positions with the stack already at row 2-3, exhaustive
   IDA* **proves** no killing pill sequence of length ≤5 exists. A beam to depth
   18 found none on 40 positions.
2. **The real m3 silicon death was neither myopia nor an already-lost position.**
   The eval had a survivable move at all six commits, and exhaustive search shows
   every one of them was survivable. It was **execution** — confirming
   `VERDICT.md`'s H1 by forward search rather than by ranking argument.
3. **Deep search does NOT reliably beat a reactive opponent.** VS beam 32% kills
   vs 20% for the champion in the adversary seat, McNemar **p = 0.21, n = 50.**
   The lead flagged this as the surprising-and-reportable outcome; it happened.
4. **Depth-vs-eval, priced:** of 16 VS kills, **7 were avoidable by one different
   champion move, 5 of them at E=1 (depth-4 dodges).** The other **9 (56%) had no
   escape anywhere in the last 8 plies** — already lost. Avoidable deaths are
   *fast* (K median 17); unavoidable ones are *slow attrition* (K median 42).
   **Depth-4 buys roughly a third of the deaths. The majority need the eval.**

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
subtrees **without spending a single oracle call on them**. Measured effect: the
exact depth-5 runs used a **median 2 478 oracle calls** against a `6^5 = 7 776`
worst case.

**(b) Memoisation.** Identical `(board, cur, next)` recur constantly. Measured
hit rate: **29%** in solo trajectories, **96%** in VS search (there the
adversary's placements usually don't touch the champion's board at all, so the
champion's reply is literally the same computation).

### Cost reality
The champion's d3 reply is **~56 ms and irreducible** — the monolithic jitted
chooser (`FX._choose_d3_ship_eh`, 55.8 ms) is no faster than the 32-candidate
python loop (57.5 ms), so there is no restructuring win. ~18 oracle calls/s/core.
Exhaustive solo search costs `6^K`: K=6 ≈ 43 min, K=8 ≈ 20 h. Hence **beam** for
reach and **IDA\*** for proof.

---

## 2. Gates

| Gate | Question | Result |
|---|---|---|
| **G0 oracle fidelity** | does the wrapper reproduce the shipped decide path? | **PASS** — 8 full games, 1064 decisions, trajectories **identical** to `eval47/ab47.py`'s own loop (wt=0, ws=20) |
| **G1 pill alphabet** | is `(a,b)` the same capsule as `(b,a)`? | **PASS** — 108 board-level comparisons, 0 differences ⇒ the 6-pill alphabet is sound |
| **G2 admissibility** | does `h` ever exceed true plies-to-death? | see §7 |
| **G3a positive control** | can the search find kills at all? | **PASS** — K=1 in 6 calls, K=3 in 84 calls on boards built near death |

**G3b was retracted as vacuous.** It asked "can a healthy board be killed below
the bound?" — but `SoloPoker.search` starts its iterative deepening *at* the
bound, so it can never return a depth below it no matter how wrong the bound is.
It would have passed on a broken bound.

**Fixture design mattered more than expected.** The first positive control buried
only columns 3 and 4 — the champion simply played the other six columns, so the
search burned `6^K` finding nothing. That fixture could not distinguish "the
champion is robust" from "the search is broken". Only fixtures that remove the
escape routes are valid controls.

---

## 3. SOLO — no shallow pill-stream holes

### The champion does not top out on its own
1200 games, real NES capsule stream:

| level | n | clear | **topout** | stall |
|---|---|---|---|---|
| 15 | 300 | 99.7% | **0** | 1 |
| 17 | 300 | 99.7% | **0** | 1 |
| 19 | 300 | 99.7% | **0** | 1 |
| 20 | 300 | 99.3% | **0** | 2 |

**Zero topouts in 1200 games.** Independently reproduces
`dr-mario-stomper-loss-autopsy`. *The champion's deaths are not solo deaths* —
which reframes the whole hunt.

### Exhaustive proof on the dangerous positions
129 **real** positions sampled from the champion's own play (L11-L20), stratified
by spawn-column height. On the 21 positions with `spawn_top ∈ {2,3}` — one or two
rows from the top, virus loads 3 to 79 — **exhaustive IDA\* to depth 5**:

| outcome | count |
|---|---|
| killable within 5 pills | **0** |
| **proved safe** (no sequence of length ≤5 exists) | **21 / 21** |
| budget-truncated (proof incomplete) | 0 |

This is a proof, not a search failure: zero truncations, every branch either
expanded or cut by an admissible bound.

### Beam reach
40 positions (`spawn_top` 2-5), beam width 16, depth 18: **0 kills**, and all 40
terminated as "no kill within 18" rather than by running out of lines — i.e. the
champion survived 18 plies of adversarial stream, it did not merely clear out.

### What this does NOT say
No kill within 5 (exact) / 18 (beam) is not "no kill ever". Kill depths beyond 18
are unmeasured. And a beam negative is only as good as the beam — see §4, where a
badly-built adversary understated the champion's vulnerability by 5x.

---

## 4. VS — where the champion actually dies

The adversary's real lever is not the pill stream (nobody chooses your capsules)
but **garbage**: two simultaneous lines send two tiles. The adversary branches
over **its own placements** — which cost no oracle calls — while the champion
answers once per ply. That asymmetry makes deep VS search cheap.

### Headline (pooled, n = 50 seeds, L11)

| adversary | kills / 50 | median plies to kill |
|---|---|---|
| champion in the adversary seat (control) | 10 / 50 (**20.0%**) | 50 (range 7-81) |
| deep-search beam | 16 / 50 (**32.0%**) | 32 (range 4-57) |

Paired by seed: **11 seeds the beam kills and the control doesn't; 5 the control
kills and the beam doesn't.** McNemar exact on the 16 discordant pairs:
**two-sided p = 0.21 — NOT SIGNIFICANT.**

> **Deep search does not reliably dominate a reactive opponent.** It is directionally
> better and it kills faster (median 32 plies vs 50), but on kill *rate* the
> difference is within noise at n=50. Compare against tier-3's evolved policy
> using this same 50-seed control, not against the v2-only number below.

### The first 14 seeds lied — and that is the important part
On seeds 0-13 alone: **beam 5/14 (35.7%) vs control 0/14 (0%)** — a decisive-looking
win. Extending to seeds 14-49: **beam 11/36 (30.6%) vs control 10/36 (27.8%)**.
The beam held its rate; **the control's 0% was pure seed-range luck.** A 14-seed
VS comparison in this harness manufactured a 35-point effect out of nothing.
(`dr-mario-sample-size-audit`, again.)

### The adversary's own competence bounds the answer
The first adversary scored only garbage sent. It stacked its own board chasing
double clears and **killed itself in 13 of 14 seeds** ("no surviving lines" —
every beam line topped the *adversary* out). Adding self-preservation to the
objective took it from 7.1% to 35.7% on the same seeds. Even the fixed version
still loses 19/50 lines that way, so **32% is a floor on the champion's VS
vulnerability, not a ceiling.**

---

## 5. COUNTERFACTUAL — the real m3 silicon death was NOT myopia

Six consecutive capsule commits reconstructed from the m3 video, ending in a
topout. Prior work (`recon/VERDICT.md`) adjudicated *mechanism* (H1, pair-latch
commit-path defect) from the eval's rankings. This establishes *consequence*.

**Q1 — continuity: 5/5.** Applying the tape's placement to board *i* reproduces
board *i+1* **exactly** on the colour plane, for every consecutive pair. So the
world model matches real silicon on this tape, no garbage arrived between these
commits, and the tape's action is identified unambiguously without relying on the
video's ambiguous orientation reading.

**Q2 — the eval's own choice survives.** The champion wants a *different column*
from the tape in 5 of 6 commits. Rolled forward from **every one** of the six
boards under the known pill stream, it **stays alive to the end of the stream** —
including from c6, the last board before the tape's topout.

**Q3 — the position was never lost.** Exhaustive deduped BFS over the champion's
*own* action space against the fixed stream (no oracle needed — pure mechanics):
**all six commits were survivable**, right up to the fatal one. The trap never
closed. The frontier cap can only produce false *negatives*; all six answers are
positive, so the result is sound.

> **Verdict: neither myopia nor an already-lost position.** The eval had a
> survivable move at every step and the hardware played a different column. An
> execution defect — H1 confirmed by forward search.

Caveat: the known stream is 7 pills, so the survival window is 1-6 plies
depending on the commit; the claim is strongest at c1-c4.

**A null result worth recording:** pricing each commit by *adversarial* survival
margin was inconclusive — both the eval's and the tape's resulting positions were
un-killable by any pill sequence within depth 6. The pill-stream adversary cannot
discriminate on these boards, which is itself consistent with §3: m3's pressure
came from garbage and the commit path, not from board danger.

---

## 6. Hole taxonomy — escape depth on the VS kills

For each of the 16 VS kills: does **one** different champion move at some late
ply survive past the fatal ply? `E = K - j` for the latest such ply.

| E | count | share of kills | what would fix it |
|---|---|---|---|
| **1** | 5 | 31% | a **depth-4** search |
| 3 | 1 | 6% | a depth-6 search |
| 4 | 1 | 6% | a depth-7 search |
| **none in last 8 plies** | **9** | **56%** | nothing at the end — already lost |

**Verified against a live adversary.** The first pass was contaminated: replaying
a *fixed* adversary line after the champion deviates is unfair, because the
champion's different move changes the garbage it sends back and can make the
stored adversary action illegal. `adv_substituted` was **True on every escape
found** — the champion had "escaped" an adversary that had stopped attacking.
Re-running a fresh adversary beam (width 8, 14 plies) from each escape point
returned the **same** verdicts, so these are real survivals, not delays.

### The structure of the split — the most useful finding here
| | kill depth K |
|---|---|
| avoidable (E exists) | 4, 5, 8, 17, 23, 29, 32 — **median 17** |
| unavoidable | 24, 28, 40, 40, 42, 42, 52, 54, 57 — **median 42** |

**Avoidable deaths are fast; unavoidable deaths are slow.** A short kill means the
adversary found a sharp tactical shot the champion could have parried one ply
earlier. A long kill means sustained garbage attrition: by the endgame there is no
move left that helps, because the board was lost twenty-plus placements earlier.

### The champion's mistake, in plain language
In the E=1 cases the pattern is the same: **with garbage arriving, the champion
keeps placing to maximise its own clearing progress and lets the reachable
headroom collapse to a single column. Its depth-3 horizon ends exactly one
placement before the column closes, so the move that strands it looks free.**
One extra ply of lookahead makes the closure visible and a different column is
preferred. It is not a subtle evaluation error — it is a horizon that stops one
pill too early under pressure.

---

## 7. G2 — admissibility of the bound

`h` is the single load-bearing assumption behind every negative here: IDA* starts
at `h` and prunes on it, so if `h` ever *overstates* the distance to death, real
kills are skipped and "no hole within K" is worthless.

Both intended test sources produced no test cases — the death corpus had **zero
topouts**, and the taxonomy found **zero killing lines**. Both are findings, but
neither tests `h`. So deaths were manufactured: randomised near-death boards,
kills found by IDA*, and `h` checked at every state of every killing line against
the placements that actually remained.

*(`g2_admissibility.py` — result in `results/g2_admissibility.json`; see the
run log. Analytically the bound is a proof: row 0 of a spawn column must be
filled, one placement adds ≤2 cells to one column, clears only raise the top.)*

---

## 8. What to validate on real RTL

The offline sim disagrees with RTL on ~87% of base-search moves, so these are
**simulator** findings. Top three to replay through the Verilator co-sim, in
priority order:

1. **The m3 counterfactual (highest value, and it is already anchored to
   silicon).** Q1 continuity passed 5/5 against real tape, so the boards are
   real. Re-run the champion's preferred placement at commits c2, c4 and c6
   through the co-sim and confirm it still differs from the tape's column. If it
   does, the execution-defect verdict is silicon-grade, not simulator-grade.
2. **The five E=1 VS kills** (seeds 6, 9, 12, 31, 36 in `results/vs_escape_all.json`).
   These are the entire case for buying depth 4. Replay each fatal position and
   confirm the RTL leaf ranks the escaping alternative the same way. If the RTL
   already prefers the escape, the depth prize evaporates.
3. **The exact-safe positions** (`results/exact_solo.json`, 21 boards at
   `spawn_top` 2-3). Spot-check that the RTL's committed placement matches the
   sim's on a handful; the "proved safe to depth 5" claim inherits whatever the
   move-level disagreement is.

---

## 9. Honest read: depth or eval?

**Both, in a specific ratio, and depth is the smaller half.**

* Depth-4 would recover roughly **a third** of the VS deaths (5 of 16 at E=1,
  plus 2 more at E=3/4 needing depth 6-7 which is not affordable). That is real,
  bounded, and the cheapest available win *if* it survives RTL validation (§8.2).
* **56% of VS deaths have no escape at the endgame at all.** Those are attrition
  deaths with a median kill depth of 42 plies. No feasible search depth touches
  them; the champion has to not arrive there, which is an eval/strategy property.
* In **solo** play depth is worth nothing, because there is nothing to fix: zero
  topouts in 1200 games and exhaustive proof of safety on the worst real
  positions.

So the depth argument should be made narrowly — *depth 4, for sharp tactical
shots under garbage pressure* — and not as a general capability upgrade. The
larger prize is in whatever keeps the champion out of 40-ply attrition losses,
and that is not a search-depth question.

---

## 10. Files

| file | what |
|---|---|
| `champion.py` | the memoised oracle + faithful world-step |
| `poker.py` | admissible bound, IDA* solo poker, beam |
| `margin.py` | shortest-kill + escape-depth `E` |
| `exact_solo.py` | exhaustive IDA* proof on dangerous positions |
| `taxonomy.py` | beam sweep over real positions (with replay check) |
| `vs_poker.py` | VS deep search + champion-seat control |
| `vs_escape.py` | escape depth for the VS kills, with live-adversary verification |
| `m3_counterfactual.py` | the real silicon death analysis |
| `m3_margin.py` | prices the m3 blunders in pills of margin (null — see §5) |
| `death_corpus.py` | 1200-game solo death hunt |
| `sample_boards.py` | stratified real-position sampler |
| `gates.py`, `g2_admissibility.py` | G1/G2/G3 |
| `smoke_oracle.py` | G0 — oracle vs shipped decide path |

Results in `results/`; reproducers are the `col`/`vir`/`cur` fields carried
alongside every hole and every proved-safe position.
