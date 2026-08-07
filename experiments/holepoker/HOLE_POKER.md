# THE HOLE POKER — deep adversarial search against the strand20 champion

Tier 4 of the adversarial program. Everything here runs in the **offline python
simulator**, which disagrees with real RTL on ~87% of base-search MOVES
(`CANDIDATE_TIER3.md` §10). **Every claim below is a SIMULATOR claim until it is
replayed through the Verilator co-sim.** Named validation targets are in §8.

---

## TL;DR

1. **The champion has no solo pill-stream holes.** 1200 games at L15-L20: **zero
   topouts.** On 21 real positions with the stack already at row 2-3, exhaustive
   IDA* **proves** no killing pill sequence of length ≤5 exists.
2. **The real m3 silicon death was neither myopia nor an already-lost position.**
   The eval had a survivable move at all six commits and exhaustive search shows
   every one was survivable — **execution**, confirming `VERDICT.md`'s H1 by
   forward search rather than by ranking argument.
3. **🚨 The VS harness manufactured its own kills.** `vs_env_exact` garbage tiles
   never fell — they floated at row 0, and column 3 is a garbage column, so
   **31.7% of deliveries topped the receiver out instantly** on any board. Fixed
   upstream. With gravity correct: **beam 0/40, control 0/40.** *Every* VS number
   I ever reported (32%, 26.7%, 7.1%) was that artifact. Blast radius audited:
   only this lane and `h2h_vs --rule exact`; every other lane has its own
   gravity-correct injection.
4. **THE REAL ANSWER, on deaths that actually happen** — 480 games across two
   doses and two levels, **53 deaths**, all replay-verified. **75% are
   dies-ahead**, independently reproducing the field disease. Escape depths:
   **E=1 for 21/53 = 40% [28-53%] — depth-4 dodges those. E≤3 for 53%.**
   The other 42% need E≥5 or are unavoidable. The E=1 share is stable at 33-43%
   across a 4.6x swing in death rate, so it is not a single-setting artifact.
5. **So: depth AND eval, roughly half each.** Depth-4 is worth ~40% of pressure
   deaths — a real, sizeable, testable prize. It is *not* the whole disease.

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
| **G2 admissibility** | does `h` ever exceed true plies-to-death? | **PASS** — 10 killing lines, 32 states, **0 violations** (§7) |
| **G3a positive control** | can the search find kills at all? | **PASS** — K=1 in 6 calls, K=3 in 84 calls on boards built near death |
| **G4 replay gate** | does every reported hole reproduce from its saved state? | **PASS after a FAIL** — it caught BOTH defects. Pressure deaths: **19/19 reproduce, 16/16 escapes survive** |
| **G5 memo integrity** | can the persistent store change an answer? | **PASS** — 60 positions, round-trip + reopen + key hygiene, 0 disagreements |
| **G6 garbage gravity** | does a delivery top out a healthy board? | **PASS after a FAIL** — 19/60 pre-fix, **0/60 post-fix** (§4a) |

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
badly-built adversary understated the champion's VS vulnerability 5x.

---

## 4. VS — the harness manufactured its own kills

Two independent defects, both found by replay, both in the shared substrate.

### 4a. Garbage tiles never fell (the fatal one)
`vs_env_exact._drop_garbage` wrote two tiles into ROW 0 and called `resolve()`
to "settle" them. But `FaithfulBoard.resolve()` applies gravity **only after a
clear** — freshly dropped garbage rarely completes a line, so the loop exits
immediately and the tiles were left **floating at row 0 over empty space,
permanently**.

`spawn_blocked()` is `any(color[0,c] for c in (3,4))`, and `GARBAGE_PAIRS`
contains column 3. So **one third of all deliveries topped the receiver out
instantly** — on any board, at any height, with a full set of legal moves.

| | one delivery onto a healthy fresh L11 board |
|---|---|
| before fix | topped out **19/60 = 31.7%** |
| after fix | **0/60** |

A single tile on a *completely empty* board reported `spawn_blocked() == True`.

**Effect on my results — total:**

| harness | deep-search beam | champion-in-adversary-seat control |
|---|---|---|
| broken | 8/30 = 26.7% | 7/30 = 23.3% |
| **fixed (n=40)** | **0/40 = 0.0%** | **0/40 = 0.0%** |

**Not one genuine kill survived.** Every VS number this lane ever produced —
32%, 26.7%, 7.1% — was the artifact. Strike all of them.

**Blast radius, audited rather than assumed** (`grep -rl vs_env_exact`, plus who
defines their own injection): only this lane and `h2h_vs.py --rule exact`.
`adversary`, `adversary_t3`, `pressure_rig`, `bursty_model`, `reach_root_ab` and
`cascade_probe` each carry their own gravity-correct `drop_garbage`, and
`h2h_vs` defaults to `rule="rom"`. `pressure_rig` even comments the exact cause —
that lane already knew. Fixed upstream in `vs_env_exact`; gate
`test_garbage_gravity.py`.

`FaithfulBoard.resolve()` itself is deliberately unchanged: solo play never
inserts an unsupported cell and every solo result depends on its behaviour. The
rule it implies is the durable one — **anything that writes a cell not at its
resting position must call `_apply_gravity()` itself.**

### 4b. Deepcopy shared one pill cursor
`NesPillSource.attach` installed `env._rand_pill = lambda: ...`; `copy.deepcopy`
treats functions as atomic, so every cloned branch drew from **one advancing
cursor** and siblings stole each other's capsules. 14 of 16 "kills" would not
replay. Fixed upstream with a `_PillDraw` callable object; gate
`test_deepcopy_pillshare.py`.

**It was deterministic run-to-run** — I re-ran the beam twice and got
byte-identical action paths, which read as proof of correctness. *Determinism is
not validity: a deterministic bug reproduces perfectly.* Only an independent
replay from the stored `(seed, path)` could see it.

### What the corrected null does and does not mean
0/40 does not say the champion is unkillable. It says **my adversary's attack
channel was the binding constraint**: it can only send garbage by landing double
clears, which it manages ~1.6 times a match — far below human cadence. The
regimes that actually kill this champion deliver garbage on a human-like
schedule, which is §4c.

### 4c. PRESSURE — where the deaths are real

Driving the project's own gravity-correct drip injection (`pressure_rig`
semantics: k=2 halves every 5 placements after ply 20), L11, n=160 games:

| outcome | n |
|---|---|
| deaths | **19 (11.9%)** |
| clears | 125 |
| stalls | 16 |

**15 of 19 deaths (79%) are DIES-AHEAD** (≤12 viruses left) — this lane
independently reproduces the field disease that the other four lanes converged
on, using different code and a different pressure model.

**Why this counterfactual is clean where the VS one was not:**
`_inject_garbage` seeds its RNG on `(seed, pills_placed)`, so the garbage
schedule is **exogenous** — it depends on the ply index, never on what the
champion played. Changing one champion move leaves the entire future garbage
stream identical, so the comparison isolates the move. In the VS rig the
champion's own clears fed the opponent, so any deviation also changed the
pressure, and an "escape" was partly the adversary going quiet.

**Both gates pass: 19/19 deaths reproduce exactly on independent replay, and
16/16 claimed escapes survive independent replay.**

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

## 6. Hole taxonomy — escape depth on real pressure deaths

For each death: what is the smallest number of plies past the champion's 3-ply
horizon at which **one** different move survives past the fatal ply?

### Pooled — 480 games, 3 configurations, 53 deaths

| E | deaths | search depth that dodges it | feasible? |
|---|---|---|---|
| **1** | **21** | **depth 4** | **yes** |
| 2 | 2 | depth 5 | plausibly |
| 3 | 5 | depth 6 | unlikely |
| 4 | 3 | depth 7 | no |
| 5 | 5 | depth 8 | no |
| 6 | 2 | depth 9 | no |
| 7 | 1 | depth 10 | no |
| 8 | 2 | depth 11 | no |
| none in 8 plies | 12 | — already lost | — |

* **E=1: 21/53 = 40%**, 95% CI **[28%, 53%]** — one extra ply recovers two fifths
  of all pressure deaths.
* **E≤3: 28/53 = 53%**, 95% CI **[40%, 66%]**.
* **E≥5 or no escape: 22/53 = 42%** — no feasible search reaches these.

### It holds across dose and level

| config | games | deaths | dies-ahead | E=1 | E≤3 |
|---|---|---|---|---|---|
| L11 k2/p5/after20 | 160 | 19 (11.9%) | 15 | 7 (37%) | 9 |
| L11 k2/p8/after25 | 160 | 6 (3.8%) | 5 | 2 (33%) | 3 |
| L17 k2/p5/after20 | 160 | 28 (17.5%) | 20 | 12 (43%) | 16 |
| **pooled** | **480** | **53** | **40 (75%)** | **21 (40%)** | **28 (53%)** |

The E=1 share is stable at 33-43% across a 4.6x swing in death rate, two doses
and two levels — so it is not an artifact of one pressure setting.

**75% of deaths are dies-ahead**, independently reproducing the field disease
with different code and a different pressure model from the other four lanes.

### Mechanism mix (pooled)
`garbage_flood` dominates (32), then `spawn_congestion` (10),
`colour_starvation` (8), `forced_overstack` (3). Consistent with the dies-ahead
framing: the champion is not out-played positionally, it is buried while banking
clearing progress.

### The champion's mistake, in plain language
At E=1 the pattern is consistent: **with garbage arriving, the champion takes the
placement that maximises clearing progress and lets the reachable headroom in the
spawn lane collapse to a single column. Its horizon ends exactly one placement
before that column closes, so the move that strands it still looks free.** One
more ply makes the closure visible and a different column wins. For this two
fifths of deaths it is genuinely a horizon problem.

The E≥5 group is a different animal: those boards were committed five to eight
placements before the end and no endgame move recovers them. That is the
risk-neutrality the other lanes named — an eval-term problem.

### Two methodological notes
**Why drip and not bursty.** The bursty model's volleys are keyed on the
champion's own clear size, so changing a champion move changes the future
pressure — the same contamination that made the VS escapes meaningless. Drip is
keyed on `(seed, ply)` only, so the garbage stream is exogenous and the
comparison isolates the move. Exogeneity is a requirement here, not a preference.

**Classifier caveat.** A death-by-delivery ply has a legal-move count of 0 *by
definition*; feeding that to the mechanism classifier made `forced_overstack`
fire on every kill until I measured it on the last ply with a real count.

## 7. G2 — admissibility of the bound

`h` is the single load-bearing assumption behind every negative here: IDA* starts
at `h` and prunes on it, so if `h` ever *overstates* the distance to death, real
kills are skipped and "no hole within K" is worthless.

Both intended test sources produced no test cases — the death corpus had **zero
topouts**, and the taxonomy found **zero killing lines**. Both are findings, but
neither tests `h`. So deaths were manufactured: randomised near-death boards,
kills found by IDA*, and `h` checked at every state of every killing line against
the placements that actually remained (`g2_admissibility.py`, results in
`results/g2_admissibility.json`).

**Result: PASS.** 30 manufactured near-death boards produced **10 killing lines**
(depths 2, 3, 4), **32 states checked, 0 violations** — `h` never once exceeded
the placements that actually remained.

Analytically the bound is a **proof**, not a hypothesis: a topout needs row 0 of
a spawn column filled (a no-legal-move needs every column to row ≤1, hence the
−1); one placement adds ≤2 cells to one column; clears and gravity only ever
*raise* the top-occupied row.

### ⚠ Scope: the bound is SOLO-ONLY and is invalid under garbage
The proof assumes cells enter the board only via placements. **VS garbage is
inserted directly at row 0, and column 3 is not immune** (`GARBAGE_PAIRS =
(1,5),(2,6),(3,7)`; only columns 0 and 4 are immune). One garbage drop can
therefore top a board out from *any* height, and `h` collapses. Pruning a
garbage-exposed search with it would silently discard real kills.

Audited: `h_lower_bound` prunes only in `poker.SoloPoker`, and serves as a
survival certificate in `m3_counterfactual.survivable` — whose replays are
garbage-free by construction (the Q1 continuity check proves no garbage arrived
between the six commits). `vs_poker` and `vs_escape` use `spawn_top` for beam
*ranking* only and never prune on it, so **no VS result depends on the bound.**
The constraint is now recorded in the function's docstring.

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
2. **The seven E=1 pressure deaths** (`results/pressure_escape.json`, filter
   `E == 1`). These are the ENTIRE depth-4 argument and they are cheap to check:
   one RTL decision per position. If the RTL leaf already prefers the escaping
   alternative, the depth prize shrinks; if it agrees with the fast sim, depth-4
   is worth ~37% of pressure deaths. This matters more than usual because the
   co-sim lane measured RTL agreement at **88% near death** vs 100% mid-game —
   this is exactly the divergent regime.
3. **The exact-safe positions** (`results/exact_solo.json`, 21 boards at
   `spawn_top` 2-3). Spot-check that the RTL's committed placement matches the
   sim's on a handful; the "proved safe to depth 5" claim inherits whatever the
   move-level disagreement is.

---

## 9. Honest read: depth or eval?

**Both, and roughly half each — which is a different answer from the one I gave
before the harness was fixed, and the change came from better data, not a better
argument.**

* **Depth-4 is worth ~40% of pressure deaths** (21 of 53 at E=1, 95% CI 28-53%), and depth-6
  about 53%. That is a real, sizeable, testable prize. It should be weighed
  against the measured d4 cost of 22.9x (`dr-mario-depth4-memo`) — but "depth
  buys nothing" is now refuted on the deaths that actually occur.
* **The other ~42% need E≥5 or have no escape at all.** Those were decided five
  to eight placements before the end, and no feasible search depth reaches them.
  This is the same place the other four lanes landed — risk-neutrality near an
  absorbing state — and it is an eval-term problem: something that prices
  collapsing spawn-lane headroom while garbage is arriving.
* **Solo needs neither.** Zero topouts in 1200 games, and exhaustive proof that
  no ≤5-pill stream kills it from the worst real positions.

So the recommendation is narrow and specific: **a depth-4 search would recover
about two fifths of pressure deaths, and a survival term is needed for the rest.**
Neither alone closes the disease.

### What I got wrong, and why it matters for how this is read
I previously reported "depth is NOT the lever" with E = 5,5,6,8 and no E≤4 case.
That was measured on VS kills that were **entirely fabricated by the garbage
gravity bug** — the champion was being tile-blocked, not out-played, so of course
no shallow escape existed. The number was confidently wrong in a way that pointed
at the more expensive fix. Both of tonight's defects had the same shape as the
three the lead catalogued: *the check couldn't see the fault because the check
shared the fault's assumption.* Nothing in the harness ever asserted that a
delivered tile ends up supported, or that a cloned state owns its own RNG.

### Limits, stated plainly
n=53 deaths across two doses and two levels — enough that the E=1 share is
stable (33-43%), not enough to split it by mechanism.

**The bursty human-fitted model cannot go through this instrument as it stands,**
and that is a real limit rather than an omission: its volleys key on the
champion's own clear size, so deviating the champion changes the future pressure
and the counterfactual stops isolating the move. Answering "does the E=1 share
survive human cadence" needs a bursty variant whose schedule is frozen per seed.
Worth building; not built.

All simulator-side, and the co-sim lane has since measured RTL agreement at
**88% near death** vs 100% mid-game — precisely this regime — so whether these
escapes exist on silicon is an open question, not a formality. The 21 E=1 deaths
are the ones to put through the co-sim first: they are the entire depth-4
argument and cost one RTL decision each.

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
| `vs_reproduce.py` | G4 replay gate + fluke check on the VS kills |
| `test_deepcopy_pillshare.py` | regression test for the deepcopy/pill-cursor defect |
| `m3_counterfactual.py` | the real silicon death analysis |
| `m3_margin.py` | prices the m3 blunders in pills of margin (null — see §5) |
| `pressure_escape.py` | **the real result** — escape depth on drip-pressure deaths |
| `memo_db.py` | persistent LMDB champion-move store on /mnt/data |
| `classify.py` / `mapelites.py` | behaviour descriptor + QD archive scaffolding |
| `test_garbage_gravity.py` | regression test for the floating-garbage defect |
| `test_memo_integrity.py` | G5 — the store never changes an answer |
| `death_corpus.py` | 1200-game solo death hunt |
| `sample_boards.py` | stratified real-position sampler |
| `gates.py`, `g2_admissibility.py` | G1/G2/G3 |
| `smoke_oracle.py` | G0 — oracle vs shipped decide path |

Results in `results/`; reproducers are the `col`/`vir`/`cur` fields carried
alongside every hole and every proved-safe position.
