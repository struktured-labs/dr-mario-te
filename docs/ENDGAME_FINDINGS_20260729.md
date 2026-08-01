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
| 4 | endgame-gated planner | ⚠ **REAL BUT MARGINAL — DO NOT BUILD** | −6% on uniform capsules, only **−1.4% on the REAL NES stream** |
| 5 | anti-seal move filter | ❌ **FAILURE** | clear 100→93%, p/v 4.44→**6.55**, 82 worse |
| 5 | cascade override (cheap version) | ❌ **WASH** | median +0.0 pills, 30/28, fires 1.0/game |
| 5 | blanket plan-avoidance filter | ❌ **FAILURE** (earlier) | +6.98 pills, CI excludes any gain |
| 5 | NES-pill eval retune | ❌ **HOLDOUT NEGATIVE** | tuning block was a seed artefact |
| — | goal-metric h2h | ⚠ **INCONCLUSIVE** | 53.6% finishes-first (n=300), ≈chance |
| — | MiSTer silicon A/B | ⚠ **BLOCKED** | autonav dead; known-good cart unrebuildable |
| 5b | defence term gated on incoming garbage | ❌❌ **STANDING NEGATIVE — kills the whole family** | doubling `spawn`+`toprisk` moves the argmax **0 / 102** times in the target states |
| 5b | argmax sensitivity under re-weighting | ✅ **SUCCESS** (instrument) | measures a term's real fire-rate ceiling before it is built |
| 5c | VS garbage trigger (`cells>=7`) | ⚠ **HARNESS DEFECT** | 83% false positives *and* misses real doubles (off-by-2) |

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
failure. ### ⚠ …AND THEN THE NES CAPSULE STREAM SHRANK IT (2026-07-30)

Every number above uses the simulator's IID-**uniform** capsule draw. The NES does not:
mod-9 additive walk off a 16-bit LFSR, strong adjacent correlation, heavy tail on waiting
for a SPECIFIC capsule. A planner is the single thing most likely to be flattered by a
uniform stream, because it reasons about capsule AVAILABILITY.

| stream | planner | clear | med pills | endgame p/v |
|---|---|---|---|---|
| uniform | off → ON | 100% → 99.3% | 91.5 → 90.0 | 4.40 → 4.13 (**−6%**) |
| **real NES** | off → ON | 96.7% → **97.3%** | 99.5 → **98.0** | 5.02 → **4.95 (−1.4%)** |

Still POSITIVE on the real stream — clear +0.6pp, 1.5 pills faster — but the endgame gain
is **4x smaller**. That does not justify a 6502 firmware port.

★ Note the baselines: the real stream is genuinely HARDER (endgame 5.02 vs 4.40; clear
96.7% vs 100%). **Every offline figure in this document is from an easier game than the
hardware actually plays.**

★★ **THE GENERAL LESSON, now twice-proven** (NES-pill eval retune, and this): validate on
the REAL capsule stream before building anything. Uniform draws flatter every
capsule-dependent strategy, and both the h2h and held-out gauntlets above ran on uniform —
so passing them proves less than it appears.

**NET: the only change that survives every test is the pair-latch fix.** It is an EXECUTION
defect measured on the real RTL, so it is independent of capsule modelling entirely.

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

## 5b. ❌❌ STANDING NEGATIVE — the eval's SURVIVAL side cannot be steered (2026-07-31)

★ **Kills the whole future family of "add a defence term when garbage is incoming".** Not
one proposal — the family. Anything of that shape scales `spawn` and/or `toprisk`, and
those two penalties **do not move the argmax**.

Measured by re-running the *same* depth-3 search with the eval re-weighted and diffing the
chosen move, over 9107 decisions of self-play VS (L11, real NES capsule stream, shipped
`winner` brain both sides):

| re-weighting | move differs, ALL decisions | move differs, garbage inbound |
|---|---|---|
| `spawn` 150→300, `toprisk` 90→180 | 29 / 9107 = **0.32%** | **0 / 102** |

Zero, in exactly the states the term is designed for. Then the full scaling sweep (3026
decisions, 279 of them with spawn-lane h≥12) shows this is not a matter of nudging harder:

| scale | move differs (all) | move differs (danger, h≥12) |
|---|---|---|
| ×2 | 0.40% | 2.87% |
| ×4 | 0.96% | 7.53% |
| ×8 | 1.06% | 8.24% |
| ×20 | **1.06%** | **8.24%** |
| **0 — ablated entirely** | **1.19%** | **10.39%** |

★ Two independent facts kill the family. **Up-scaling saturates at ×8** — ×20 is identical
to ×8 down to the decision, so there is no "push harder" left to buy. And the **entire
dynamic range of both penalties, from ablated to ×20, is 1.19% of decisions**. The depth-3
search is already playing the survival move; these constants barely arbitrate the argmax.

⚠ Read this precisely: low argmax authority is **not** "no value". 1.19% is ~1.8 moves a
match, and those may be exactly the moves that avert a top-out. The claim is directional —
you cannot buy *more* safety by scaling these up, whether or not they already earn their
keep. Corollary: **we have no working headroom lever**; if the AI must play safer it cannot
be asked to via these constants, and a garbage-gated version of them is dead before build.

★ **INSTRUMENT (reusable, cheap): ARGMAX SENSITIVITY UNDER RE-WEIGHTING.** Before building
any gated/conditional eval term, replay real decisions and count how often the proposed
re-weighting actually *changes the chosen move*. State frequency is only an upper bound —
this measures the real ceiling on the term's fire rate, costs one extra decider call per
decision, and refutes dead ideas in minutes instead of a build. It is what turned this
candidate around before a line of RTL was written.
`dr_mario_rl/tmp/vs_aware/size2.py`, `saturation.py`.

## 5c. ⚠ HARNESS DEFECT — the VS garbage trigger fires on the wrong events

`tmp/champion/vs_env.py` detects an attack with `cells >= 7`, documented as a near-perfect
proxy for a 2-simultaneous-line clear. It is wrong in **both directions at once**:

- **OVER-fires.** `FaithfulBoard.resolve()` loops clear→gravity→clear and sums cells across
  steps, so a *cascade of single-line clears* reaches the threshold. Audited every positive
  over 12 matches: **83% are false**, and the dominant signature is `(1, 1)` — clear a line,
  gravity, clear another. Sequential, not simultaneous; sends nothing.
- **UNDER-fires (off-by-2, found by selfplay-opt).** Its `cells` is
  `occupancy(before) − occupancy(after)`, but `env.step` places the pill (**+2 cells**)
  before resolving. The delta is `cleared − 2`, so `>= 7` really demands **9** cleared
  cells — while a genuine L-shaped double is 7. Real doubles land silently.

Consequence: VS self-play has been running with a garbage channel keyed to the wrong
events, so its top-out rate and any win-rate tuned against it are measurements of a
different game. Line-accurate replacement counts **distinct maximal runs ≥ 4 per clear
step**: `dr_mario_rl/tmp/vs_aware/attack.py`; audit `check_proxy2.py`.

⚠ **PENDING ROM-RULE CONFIRMATION.** "Truth" above means *≥2 runs cleared in one step*,
which is `MECHANICS_NES.md`'s wording — **not** a citation of the ROM's send routine, and
that doc's own evidence does not support it: `probe_attack.lua`'s log shows `single` clears
producing 14–34 changed P2 cells, the same range as `double`, with changes in columns 0 and
4 that the same doc calls garbage-**immune**. That is P2 redraw, not garbage. If the ROM
counts cascade-formed lines, `attack.py` under-fires, the old proxy was accidentally closer,
and the inbound-garbage regime grows ~6x. Owned by task #12; freeze one shared trigger.

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
