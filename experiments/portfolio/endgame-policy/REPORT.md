# endgame-policy: does the champion self-seal its own last targets, like struktured does?

> ## ⛔ SUPERSEDED 2026-08-07 — the "ALIVE" verdict below did NOT survive follow-up.
> **The measurement in this file is correct and reproduced. Its interpretation was wrong.**
> Self-sealing is real, replicates out-of-sample (0.790 seals/game on the disjoint seed
> block 0-199 vs the 0.630 here), and is **NOT A DEFECT**. Do not build a seal penalty.
>
> - **It costs nothing.** All 126 seals in this corpus RESOLVED: 84 re-opened and **42 ended
>   with the virus cleared WHILE STILL COVERED** — a seal blocks only the VERTICAL route,
>   and the virus's own row still matches. The single non-win here (seed 1103) had **zero**
>   seals. The "§Verdict" claim that `g_stranded` misses a live defect confuses a *pattern*
>   with a *blocker*.
> - **Pricing it makes the champion worse, monotonically in how often the term fires**
>   (n=200 paired, bursty v1.1): 2.43% fire → +4 bad-ends; 7.99% → +16, **McNemar p=0.0113**;
>   ungated 22.3% → **152/200 bad-ends vs the champion's 39/200**. Neither veto rescued a
>   single clean-stream seed.
> - **The "Next step" prescribed at the bottom of this file (`g_virus_seal`) was built and
>   is refuted.** Its colour-reachability generalisation is strictly worse still.
>
> Evidence: `experiments/selfseal/` (commits `3da54df`, `a24e27c`, `e97f60d`, `1bbffe3`).
> Method note carried forward: **fire rate = (gate hit rate) × (predicate hit rate | gated)**;
> report both, and treat an arm changing <~2-3% of decisions as *not testable*, never as a null.

**Date:** 2026-08-06 · **Thread:** endgame-policy (portfolio) · **Simulator:** python
`FaithfulDrMarioEnv` via `eval47/ab47.py`'s exact `_choose_base` (wt=0, ws=20 —
`fast_rtl_x.variant("winner")` leaf + `terms47.g_stranded` root-only, the shipped
strand20 decide path), real NES pill stream (`NesPillSource`), L11, n=200 seeds.
**This is an offline python harness, not RTL** — see Caveats.

## Hypothesis (falsifiable)

The champion commits the same endgame error the film review measured on the
human (`FILM_REVIEW_20260804_SCORECARD.md`, `player_styles/struktured.md`):
covering its own remaining virus targets with non-matching material while
closing out a game, rather than only under external (garbage) pressure. If the
champion essentially never does this in solo play, the human's failure mode is
not shared and this line of inquiry is dead. If it does, a concrete, nameable
defect exists with a ready-made implementation slot (the existing `g_stranded`
root-only eval-term architecture).

## Operational definition (SEAL EVENT)

While `virus_count() <= 6` after a placement resolves (post cascade/gravity),
for every remaining virus cell `i` at `(r,c)` with `r>0`: let `j=i-8` (the cell
directly above, same column). If `col[j]` is occupied by non-virus material
whose colour differs from the virus's own colour, the virus is COVERED. A SEAL
event fires on the OPEN→COVERED transition (re-covering after a re-open counts
again, matching the human case study's "sealed four separate times"). A
RE-OPEN event fires on COVERED→OPEN while the virus is still present. Because
this is a solo env (no second board, no incoming volleys), every seal counted
is by construction self-inflicted — there is no "AI volleys" bucket to net out
against, unlike the human's two-player 21-total/8-self split.

## Method

`seal_probe.py` reuses `ab47.py::_choose_base` and its imports **verbatim**
(same `fast_rtl_x`/`root_search`/`terms47` calls, same board convention:
128-byte row-major `idx=r*8+c`, row 0 = top, colours 1-based, `vir` 1/0 flag)
— no new decision logic, only instrumentation bolted onto the existing play
loop via `FB.from_board(env.board)` diffs before/after each `env.step()`. This
is the same harness the #47 stranded-half work already trusts for measuring
this exact decider (`dr-mario-eval47-stranded-win` memory; `SILICON_PLAN.md`
cites `eval47/ab47.py` as its own fast reference decider), so no new
move-selection code was written for this probe — only new instrumentation.

Cheapest-kill pass: n=8 smoke test first (0.71 seals/game, 4/7 endgame games
with >=1 seal) — did not kill the hypothesis, so proceeded to the full n=200
run per task spec, 4 workers, ~8 min wall time, well inside the box's OOM
history threshold (peak ~9.8GB total python RSS system-wide, most of it other
threads' processes).

## Results (n=200 seeds, L11, real NES pill stream)

| metric | value |
|---|---|
| games reaching endgame (vc<=6) | 200/200 (100%) |
| games won (full clear) | 199/200 (99.5%) |
| total seal events | 126 |
| seal events per endgame game | **0.630/game, 95% CI [0.525, 0.740]** (bootstrap, n=10000) |
| games with >=1 seal event | **95/200 (47.5%)** |
| per-game seal count distribution | 0: 105, 1: 68, 2: 23, 3: 4 |
| total re-open events | 84 (66.7% of seals eventually reopen before game end) |
| re-open count distribution | 0: 131, 1: 55, 2: 13, 3: 1 |
| virus cells still sealed at game end | 14 (across all 200 games) |
| a single virus resealed >1x in one game | 2/200 games (max 2 reseals on one virus; human case had one virus sealed 4x) |
| median pill index first reaching vc<=6 | 67 (mean total game length 93.7 pills — a short, ~27-pill endgame window on average) |

Example (seed 1017, won, 100 pills): two seal events at pill 82 (cell 124
covered by cell 116) and pill 83 (cell 126 covered by cell 118), both later
re-opened (pills 83 and 87) before the game cleared — the same
seal-then-reopen-then-clear cycle the human case study described, compressed
into a couple of pills instead of tens of seconds.

## Verdict: ALIVE  ⛔ **OVERTURNED — see the banner at the top of this file**

The champion is not immune to this error. It self-seals at a small but
non-trivial, CI-excludes-zero rate (0.63/game) and does so in **nearly half
of all games (47.5%, n=200)** — even in a solo, zero-external-pressure
environment where it wins 99.5% of the time. This is a materially smaller
magnitude than struktured's single m4 endgame (8 self-seals in one contested
~90-second close, under incoming AI volleys) but the mechanism is structurally
the same: the champion's own root search — which already prices "wasted
material" generically via `g_stranded` (ws=20) — does not price "did this
placement cover my own remaining virus" specifically, and `g_stranded` cannot
substitute for that: a covering cell one row above a virus can have a
same-colour neighbour elsewhere on the board and score zero stranded-cost
while still sealing the virus underneath it. The two metrics measure different
things (`dr-mario-eval47-stranded-win` memory: `g_stranded` cut the *general*
wasted-pill count 10.8→4.2; this probe shows a *virus-specific* burial pattern
survives that cut untouched).

The magnitude gap vs. the human is expected and not disqualifying: this probe
has zero incoming pressure and a short endgame window (median 27 pills from
vc<=6 to game end), whereas struktured's m4 endgame was a long, adversarial
siege. The `BURSTY_V1_RESULTS.md` finding that ws=20 "helps but does not cure"
dies-*ahead* deaths under pressure (7.5% honest v1.1 rate, ~70% of deaths at
the doorstep) is consistent with self-sealing being a live contributing
mechanism that this pressure-free probe only shows the floor of.

## Caveats (per portfolio rules)

- **Python offline harness, not RTL.** `_choose_base` here is byte-for-byte
  the same code `ab47.py` uses (verified by direct reuse, not reimplementation),
  and that harness is the one the #47 stranded-half work itself was gated and
  shipped on (`SILICON_PLAN.md`, `dr-mario-eval47-stranded-win` memory) — so
  this is not an unrelated-simulator claim, it measures the actual decider
  design. But per the standing rule (py65/python agrees with real RTL on
  ~13% of base-search moves in the adversarial CANDIDATE_TIER3 measurement),
  any prescription built on this finding (a new eval term) must go through
  the Verilator co-sim farm before being treated as validated for silicon.
- **No incoming garbage modeled.** This measures self-sealing under IDEAL
  conditions. `pressure_rig.py`'s bursty-v1.1 model exists and is the natural
  next instrument: rerun this same seal probe with bursty pressure on to see
  whether self-seal rate/severity rises when the AI is under real volley
  pressure (where struktured's own case study lives).
- **Conservative metric.** "Covered directly above, one cell" is a narrower
  definition than the human film review's manual, whole-board frame reading
  (which also counted lateral/partial burial via reinforcement, e.g. the m1
  case's compound self+AI seal). This probe's numbers should be read as a
  **lower bound**.
- **n=1 on the human side.** struktured's 8-self-seal count is one recorded
  endgame (m4), not a rate with its own CI — the comparison here is
  qualitative (same defect class exists) not a paired statistical test against
  a human population.

## Next step (not executed this pass — orthogonal thread's call)  ⛔ **EXECUTED AND REFUTED**

> The `g_virus_seal` term proposed below was built exactly as specified (root-only, gated on
> low virus count), A/B'd paired-seed against wt=0/ws=20 on the clean stream AND under
> bursty-v1.1 pressure, across a dose sweep and an ungated maximum-fire arm. **It loses on
> both streams at every dose.** See the banner at the top; do not re-propose it.

If this line is picked up: add a root-only `g_virus_seal` term parallel to
`g_stranded` (same eval-term slot per `SILICON_PLAN.md`'s architecture:
non-leaf, root-candidates-only scan, ~28 candidates/decision) that penalizes
placements creating a NEW seal event on a virus when `virus_count<=6`,
A/B it offline paired-seed against the wt=0/ws=20 control first (cheap), then
under bursty-v1.1 pressure (where the human's failure actually lives), and
only then take a winning dose through the cosim farm bit-exactness gate before
any RTL/firmware work — per the standing rule that this offline environment
does not predict silicon move choice on its own.

## Artifacts

- `seal_probe.py` — instrumented champion play loop + seal/reopen detector
  (verbatim `_choose_base` reuse from `eval47/ab47.py`)
- `smoke.json` — n=8 cheap-kill smoke test (did not kill the hypothesis)
- `seal_probe_n200.json` — full n=200 run, per-seed rows + all seal/reopen
  event lists
- `run_n200.log` — driver log for the n=200 run
