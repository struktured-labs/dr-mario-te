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
| 5b | ~~defence term gated on garbage: kills the family~~ | ⚠ **RETRACTED** — broken harness | replaced by 5b-R |
| 5b-R | defence term gated on incoming garbage | ⚠ **NARROW NEGATIVE** | ×2 moves only 0.95% of decisions, but the terms are **not** saturated (range 5.08%, 27% in danger) |
| 5b-R | self-play barely tops out | ★ **KEY** | **3.3%** of matches (was quoted 28% — floating-garbage artifact) → survival can't pay for itself in self-play |
| 5b-R | argmax sensitivity under re-weighting | ✅ **SUCCESS** (instrument) | survives the retraction; must state the harness rev it sampled |
| 5c | VS garbage channel | ⚠ **5 HARNESS DEFECTS**, all fixed | attack rate 1.12 → **7.02**/100 placements; `cells>=7` as *documented* was ROM-true all along |

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

## 5b. ⚠ RETRACTED 2026-08-01 — measured on a broken harness

> The 5b published on 2026-07-31 claimed the survival penalties were SATURATED and INERT,
> and that this "killed the whole family" of garbage-gated defence terms. **Both headline
> claims are false.** They were measured on a harness with five mechanics bugs that between
> them suppressed garbage ~6.7x and faked top-outs. Numbers withdrawn; replaced by 5b-R.
> The retraction is kept because the failure mode is the lesson: an argmax-sensitivity
> curve is only as good as the STATE DISTRIBUTION it is sampled over, and that distribution
> came from a game that was barely being played.

## 5b-R. ⚠ NARROW NEGATIVE — doubling the survival penalties is weak, but they are NOT inert

Re-run on the consolidated ROM-true harness
(`HARNESS_REV = vsharness-r1 / rom-attack-2026-08-01 (complete)`), 60 matches,
**12694 decisions**, L11, real NES capsule stream, shipped `winner` brain both sides:

| re-weighting | differs (all) | differs (danger, h≥12) | differs (just took garbage) |
|---|---|---|---|
| `spawn`×2 `toprisk`×2 (BRACE) | 0.95% | 4.69% | 1.13% |
| ×4 | 1.61% | 7.55% | 2.26% |
| ×8 | 2.11% | 9.49% | 2.71% |
| ×20 | **3.07%** | **14.24%** | **3.84%** |
| **0 — ablated** | **5.08%** | **27.02%** | **4.74%** |

★ **WHAT CHANGED, and it is not a detail.** On the broken harness the curve flattened at
×8 (×20 identical to ×8, decision for decision) and the full range was 1.19%. On correct
mechanics **there is no saturation** — authority keeps climbing to ×20 — and the dynamic
range is **5.08% overall and 27.02% in danger states**, roughly 5x and 2.6x the retracted
figures. "These constants barely arbitrate the argmax" was an artifact of a game with
almost no garbage in it.

WHAT SURVIVES, stated narrowly:
- **Doubling is a weak lever.** BRACE still moves only 0.95% of decisions, and only 1.13%
  of the decisions immediately after taking a release — the states such a term targets.
  So *that specific proposal* remains unpromising.
- **The family is NOT dead.** The retracted "kills the whole family" claim is withdrawn.
  Scaling continues to bite well past ×8, so a defence term with real authority is
  available to anyone who wants one — it just has to push much harder than ×2.

★ **THE DEEPER RESULT — why survival weighting does so little here.** On correct gravity,
self-play at L11 **almost never tops out: 2/60 = 3.3%** (the previously quoted 28% and 25%
were the floating-garbage defect). A term that trades efficiency for survival cannot pay
for itself in a distribution where nobody dies. This is a fact about the SELF-PLAY
DISTRIBUTION, not about the eval — and it points straight at why the user beats the AI:
**humans generate top-outs that self-play never produces.** Tuning survival against
self-play is measuring a rare event; the right instrument is human or adversarial play.

★ **INSTRUMENT (reusable, cheap): ARGMAX SENSITIVITY UNDER RE-WEIGHTING.** Replay real
decisions, re-run the same search with the proposed re-weighting, count how often the
CHOSEN MOVE changes. State frequency is only an upper bound; this measures the real
ceiling on a term's fire rate for one extra decider call per decision. It survives the
retraction intact — it was the state distribution that was wrong, not the method. ⚠ And
that is exactly its caveat: **always state the harness rev the curve was sampled under.**
`dr_mario_rl/tmp/vs_aware/rebaseline.py`.

## 5c. ⚠ HARNESS DEFECTS — five bugs in the VS garbage channel, all fixed 2026-08-01

★ The 5c published on 2026-07-31 said the `cells >= 7` trigger "OVER-fires on cascades".
**That was backwards** — cascades SHOULD fire (see 1 below), and as DOCUMENTED the proxy
was ROM-true all along: 99.9% precision, 100% recall over 6078 clears. The bug was in the
IMPLEMENTATION, not the documented rule.

Five defects, now consolidated into one rev-stamped harness with a test suite
(`tmp/vs_aware/vs_harness.py`, `test_vs_harness.py`, frozen rule `rom_attack_rule.py`):

1. **TRIGGER (opening-book, task #12).** `currentP_comboCounter` increments per matched run
   (game_logic.asm:1176/:1623), is never reset inside the cascade loop, and is consumed
   once from a SINGLE call site — `action_checkAttack` (:2859), a per-ACTION step, not per
   cascade step. **Runs from different cascade steps SUM: `[1,1]` attacks.** Confirmed on
   real hardware in Mesen (comboCounter 1→2 across two clear steps 37 frames apart,
   garbage delivered). The rule is `sum(steps) >= 2`. The step-local rule this project
   used had **14.9% recall**; the shipped `cells>=9` off-by-2 had **23.5%**.
2. **OFF-BY-2 (selfplay-opt).** vs_env's `cells` is `occupancy(before) − occupancy(after)`
   with the pill (+2) already placed, making its `>=7` test really `cleared >= 9`.
3. **PAYLOAD.** 2/3/4 tiles by accumulated `attackSize`, saturating at 4 — not a flat 2.
   Two attacks between a receiver's placements MERGE into one capped release.
4. **COLUMNS.** Size-2 start is `frameCounter & 3`, stride 4 → {0,4}/{1,5}/{2,6}/{3,7}.
   **Columns 0 and 4 are NOT immune** (verified twice in Mesen by pinning frameCounter), so
   "build through the immune columns" was never a real defence.
5. ★ **GRAVITY — garbage never fell.** `FaithfulBoard.resolve()` applies gravity only
   INSIDE its clear loop, so garbage forming no line was left FLOATING at row 0. Traced:
   receiver heights `[9,9,10,10,9,…]` → `[16,9,10,10,16,…]` with nine empty rows beneath.
   Column 4 is a spawn column, so a drop there read as an instantly blocked spawn.
   **This faked every top-out rate this project has quoted.** Settle first, then resolve.

Net effect on the game being simulated: attack rate **1.12 → 7.02 per 100 placements**,
match length 76 → 106 placements per player, top-out rate **28% → 3.3%**.

★ **RULE ADOPTED: no VS number without a `HARNESS_REV` stamp.** Three generations of
numbers exist in this record and only the stamp tells them apart. `rom_attack_rule.stamp()`
names any missing mechanic explicitly, so a half-upgraded harness cannot pass as complete.

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
