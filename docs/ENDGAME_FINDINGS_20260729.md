# Endgame findings — 2026-07-28/29

Durable record of a measurement session whose scripts live in gitignored `tmp/`. Numbers
here so they survive the machine. Every figure is paired-seed unless stated.

**The user's observation that started it**, after a Pocket game against the AI:
> *"it didn't lose the race per se, it just lost a huge EDGE and barely won where as it
> should have crushed me"* … *"slowness here means its bad decision making, not reaction
> time"* … *"it needs to focus on clearing the junk around last two viruses … you kind of
> need to clear the junk **adjacent** to the virus first, not directly on top"*

All three turned out to be correct and measurable.

---

## SCOREBOARD

Every idea tried this session, tagged. Failures are kept deliberately — the negatives here
cost real hours and re-deriving them would cost the same again.

| # | idea | verdict | number |
|---|---|---|---|
| 2 | pair-latch fix (driver) | ✅ **SUCCESS** | endgame p/v 8.93 → 4.49 (**−50%**) |
| 3 | 6-constant eval re-tune | ❌ **RETRACTED** — failed cross-level validation | h2h **43.2% @L17, 45.6% @L20** (loses) |
| 3 | `W_POLL` 6→12 alone | ⚠ **UNVALIDATED** — same tuning, same doubt | −9.4% on one block; not confirmed |
| 3 | 10-constant re-tune | ❌ **RETRACTED** — contradicts the 6-constant optimum | noise-dominated objective |
| 1 | scoring on pills-per-virus by regime | ✅ **SUCCESS** (method) | unblocked every result below |
| 6 | tuck enumerator + gravity model | ✅ **SUCCESS** (tool) | 18.1% availability proven, 0 physics cost |
| 7 | meatfighter source review | ✅ **SUCCESS** (corrected our docs) | threat HIGH → MODERATE |
| 4 | endgame-gated planner | ✅✅ **SUCCESS — PASSED THE FULL GAUNTLET** | h2h wins 4/4 levels (52.6/53.3/**62.1**/53.2%); 3/3 held-out blocks −11 to −18% |
| 5 | anti-seal move filter | ❌ **FAILURE** | clear 100→93%, p/v 4.44→**6.55**, 82 worse |
| 5 | cascade override (cheap version) | ❌ **WASH** | median +0.0 pills, 30/28, fires 1.0/game |
| 5 | blanket plan-avoidance filter | ❌ **FAILURE** (earlier) | +6.98 pills, CI excludes any gain |
| 5 | NES-pill eval retune | ❌ **HOLDOUT NEGATIVE** | tuning block was a seed artefact |
| — | goal-metric h2h | ⚠ **INCONCLUSIVE** | 53.6% finishes-first (n=300), ≈chance |
| — | MiSTer silicon A/B | ⚠ **BLOCKED** | autonav dead; known-good cart unrebuildable |

**Process failures worth naming too** (mine, all caught before they shipped):
- ❌ characterised the latch defect from **synthetic** boards (8.3%) — real boards say 23.2%
- ❌ claimed the planner "grows with difficulty" from an **n=60** run; n=120 killed the trend
- ❌ `cascade_probe.py` had no `if __name__` guard, so importing it silently re-ran the probe
  and two "override" results were void
- ❌ emitted a 6502 branch that **infinite-looped** for virus counts < 10 (i.e. every endgame)
- ❌ patched the 1P return instead of the 2P one, so a fix verified as "not working" was
  actually never being called
- ❌ drew a conclusion from a **failed build** whose md5 came back empty

---

## 1. ✅ The metric was wrong all along

Solo **clear rate is at a 100% ceiling** — the shipped brain clears 100% of seeds at L11,
L14, L17 *and* L20. Every A/B scored on clear rate was therefore a forced wash, which is why
the planner looked worthless for weeks.

The metric that works is **pills spent per virus cleared, split by regime**:

| regime | shipped cost |
|---|---|
| opening (vc>32) | 1.28 p/v |
| mid (9-32) | 1.79 p/v |
| **endgame (vc<=8)** | **4.49 p/v** |

The endgame is **3.5x more expensive per virus** than the opening. That is the "gave back a
huge edge" shape, quantified.

## 2. ✅ SUCCESS — pair-latch defect (execution), worth −50%

The cart commits ORIENT from a ~5-frame partial search but COLUMN from the converged search,
so it plays a pair depth-3 never scored. Measured on the real RTL via Verilator co-sim
(`fpga/copro/sim_orient_trace.cpp`, 69 real L11 positions):

| regime | orient disagreement |
|---|---|
| opening | 12.5% |
| mid | 16.7% |
| **endgame** | **39.1%** |

Full-game cost at those measured rates (n=120):

| | clean | with latch |
|---|---|---|
| clear rate | 100% | 84.2% |
| median pills | 90 | 122 |
| endgame p/v | 4.49 | **8.93** |

⚠ An earlier synthetic-board run said 8.3% disagreement — an artefact of `_rand_board`.
**Never characterise this defect from synthetic positions.**

★ Fix is one build flag (`DRRECOMMIT_NOFREEZE=1`), already built and reproducible
(`romgen` tag `latch-converged`, md5 `e8578322`). Not silicon-tested — the MiSTer autonav
rig is blocked separately.

## 3. ❌ RETRACTED — the eval re-tune does NOT hold up

Coordinate descent on the endgame objective, **6 constants**, held-out block (seeds 9000+):

| | shipped | re-tuned |
|---|---|---|
| endgame p/v | 4.850 | **3.593 (−26%)** |
| clear rate | 98.3% | **100%** |

`{vrdy 8, buried 40, rdyext 12, setup 32, matched 56, poll 16}` — vrdy and setup unchanged.

### ★ RETRACTION (same session, further validation)

That −26% was **one favourable holdout block** and does not survive scrutiny. Four
independent checks all point the other way:

| check | result |
|---|---|
| h2h vs shipped, L11 (n=396) | 53.0% finishes-first — ≈ chance |
| h2h vs shipped, L14 (n=147) | 54.4% |
| **h2h vs shipped, L17 (n=146)** | **43.2% — LOSES** |
| **h2h vs shipped, L20 (n=147)** | **45.6% — LOSES** |
| real NES capsule stream | **NO IMPROVEMENT — keep the coef-opt winner** |

**The two optimiser runs contradict each other.** 6-constant found
`{vrdy 8, buried 40, rdyext 12, matched 56, poll 16}`; 10-constant found
`{vrdy 12, buried 56, rdyext 8, matched 48, poll 10}` — nearly opposite on every term.
Two searches on one objective landing on contradictory optima is the signature of a
**noise-dominated objective**, not a real gradient.

**Why −26% looked so good:** the shipped baseline scores 4.850 on that block but 4.452 on
another and 4.14 in the h2h. I quoted the block with the worst baseline, which flattered
the delta. Effect size is unstable across seed blocks; the sign is not reliable across
levels.

✅ **One genuine finding survives it:** the 10-constant run left **all four shape terms at
their shipped values** (`maxh 12, holes 20, toprisk 90, spawn 150`). They had never been
tuned by anything, and it turns out they did not need to be.

★ **`poll` (pollution) had NEVER been tuned** by any prior optimisation. It is the only term
that models junk *blocking a virus's completion line* — exactly the user's insight. Alone,
`W_POLL 6 -> 12` is worth −9.4% endgame (held out at seeds 5000+: 4.44 -> 4.10) and 12 is a
genuine optimum (8: 4.60, 10: 4.25, 12: 4.07, 14: 4.19). **Jointly the optimum is 16, not
12** — individually-optimal != jointly-optimal, which is why single-constant sweeps mislead.

## 4. ✅ SUCCESS — the endgame-gated planner (CANCELLED, then UN-CANCELLED)

| W_POLL | planner | endgame p/v |
|---|---|---|
| 6 | off | 4.38 |
| 6 | ON | 4.03 (planner worth **+0.34**) |
| 12 | off | 4.10 |
| 12 | ON | 4.09 (planner worth **+0.01**) |

At `W_POLL=12` the planner appears redundant — which is why it was cancelled.

### ★ UN-CANCELLED

That cancellation rested on `W_POLL=12`, which is part of the retracted tuning above. At the
**shipped** constants the planner is the better-supported change of the two:

| level | endgame p/v | change |
|---|---|---|
| L11 | 4.49 → 3.88 | **−13.6%** |
| L14 | 4.30 → 3.90 | −9.3% |
| L17 | 4.39 → 4.27 | −2.7% |
| L20 | 4.97 → 4.37 | −12.1% |

**Improvement at every level, same direction**, opening and mid untouched, firing 2.2
moves/game — versus an eval re-tune that outright loses at two of four levels. Consistency
across levels is the discriminator, and the planner has it.

### ★★ THE GAUNTLET — the planner PASSES the test that killed the eval re-tune

Same protocol, applied honestly to the surviving candidate rather than stopping at the
single-arm conversion metric that made the re-tune look good.

**Head-to-head vs shipped, "champion finishes first":**

| level | planner | eval re-tune (for contrast) |
|---|---|---|
| L11 | 52.6% | 53.0% |
| L14 | 53.3% | 54.4% |
| **L17** | **62.1%** | **43.2% ❌ LOST** |
| L20 | 53.2% | **45.6% ❌ LOST** |

**Wins 4/4, and is strongest exactly where the re-tune collapsed.**

**Three INDEPENDENT held-out seed blocks (endgame pills-per-virus):**

| block | shipped → planner | change |
|---|---|---|
| 3000 | 4.31 → 3.54 | **−17.9%** |
| 6000 | 4.87 → 4.08 | −16.2% |
| 12000 | 4.25 → 3.77 | −11.3% |

All three improve; opening and mid untouched in every one. Compare the re-tune: one
flattering block, contradictory optima between two optimiser runs, and a NES-capsule-stream
failure. **This is the champion-path eval-side change.** Firmware only (~10 KB free in
`copro_rom.hex`), no ALM, no re-fit.

## 5. ❌ FAILURES worth keeping

- **Anti-seal move filter — REFUTED.** Penalising placements that cover a virus's completing
  cell: clear 100% -> 93%, endgame p/v 4.44 -> 6.55, 17 better / 82 worse. Fired **21.8
  moves/game** — the trigger was far too loose.
- **Cascade override — WASH.** cap-1 vs resolve-to-fixpoint argmax differ on 2.8% of
  decisions and the cascade choice clears more 72:6 — but requiring "strictly more" leaves
  ~1.3% = **1.0 move/game**, and n=120 gives median +0.0 pills, 30/28. ⚠ This refutes only
  the CHEAP version; a genuinely cascade-aware depth-3 search is untested and links are not
  representable in the 3-bit RTL cell encoding.
- **NES-pill eval retune — HOLDOUT NEGATIVE.** Re-tuning against the real capsule generator
  does not beat the coef-opt winner. The tuning block looked decisive and was a seed-block
  artefact.

★ **PATTERN, now three-for-three: fire rate predicts soundness.** 21.8 moves/game (refuted),
2.8/game (refuted), 1.0/game (wash), **2.2/game (works)**. Any override that wants to
second-guess the search on more than a few moves a game has been wrong every time.

## 6. ✅ SUCCESS (tool) / ⚠ UNBUILT — tucks: availability confirmed, executor-limited

`tmp/tuck/tuck_enum.py` (independent re-implementation of meatfighter's reachability BFS,
plus a gravity-constrained mode). 778 real L11 positions:

- gravity costs **zero** placements at every drop period a real L11 game runs (P=20..10)
- positions with a tuck killing a virus **no straight drop can reach: 18.1%**
- …**currently emittable by our driver: 2.7%**
- **88.4%** of those viruses are *geometrically* tuck-only (sealed under a ledge), not colour luck
- the shipped eval prefers the tuck in **80.9%** of unique-virus positions

⚠ Contradicts the standing "tucks are 1.43x endgame-only" framing: yield concentrates in
**mid**-game (24.2%), endgame is weakest (7.7%). Different denominators, opposite shape.

## 7. ✅ SUCCESS (correction) — meatfighter does NOT play under gravity

`DrMarioAI.java`: `stallDrop()` writes `FRAMES_UNTIL_DROP=0xFF` **every frame** while moving,
and capsule x/y/orientation are written straight into RAM. He resolves clears to fixpoint
(`while(removeConnections()) dropUnsupported();`) with full link state — physics we lack —
but his agent is not constrained by the falling-piece clock. Threat re-rated HIGH -> MODERATE.
Scope our own fairness claim to the anytime/human configuration: **our freeze carts do pin
gravity too**, at the same `$0312`. We never write capsule position/orientation (verified).

---

## Where this leaves the champion path

| change | endgame conversion | status | cost |
|---|---|---|---|
| **latch fix** | 8.93 → 4.49 (**−50%**) | ✅ measured on real RTL, mechanism-verified | one build flag, built |
| **endgame planner** | −2.7% to −13.6%, all 4 levels | ✅ consistent, un-cancelled | 6502 firmware, ~10 KB free, no ALM |
| ~~eval re-tune~~ | ~~−26%~~ | ❌ **RETRACTED** — loses at L17/L20, fails NES stream | — |

★ The latch fix is independent of all eval tuning — it is an execution defect measured on
the RTL itself, so nothing above weakens it.

⚠ The goal-metric h2h is **weak so far**: champion finishes first on 53.6% of decided seeds
(n=300) — barely above chance, and measured on the pre-6-constant arm. Being re-run at n=400
with the real champion constants. Until that lands, "champion level" is a claim about solo
efficiency, not about winning races.
