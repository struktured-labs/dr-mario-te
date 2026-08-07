# Portfolio Verdict — round ending 2026-08-06

Triage of 5 parallel threads in `experiments/portfolio/*/`. One additional directory
(`learned-eval/`) was found with no `REPORT.md` — data collected, never written up; flagged
separately below, not scored as a sixth verdict.

**Score: 1 ALIVE (endgame-policy), 4 DEAD (attack-timing, failure-objective, opponent-aware,
depth4-transfer).** All 4 dead threads were killed by their own cheapest-test-first gate; none
needed the expensive escalation to prove the negative, though 2 of the 4 (attack-timing,
opponent-aware) ran a confirmatory escalation anyway and the direction only sharpened — the
gate is calibrated correctly, not systematically missing real effects (see §3).

---

## 1. Survivors, ranked by expected value per unit of compute

Only one thread survived. Ranking is trivial but the cost/value breakdown matters for whether
to spend on it next round.

### #1 — endgame-policy: champion self-seals its own virus targets (47.5% of games, n=200)

- **What it costs to reach a shippable answer, in stages, each individually cheap:**
  1. Implement one new root-only eval term (`g_virus_seal`, same architectural slot as
     `g_stranded` — non-leaf, root-candidates-only scan, ~28 candidates/decision, per
     `SILICON_PLAN.md`'s existing pattern). This is code, not compute — hours, not machine-time.
  2. Offline paired-seed A/B vs the wt=0/ws=20 control, no pressure (cheap, ~minutes, reuses
     `seal_probe.py`'s harness).
  3. Re-run under `eval47/bursty_model.py`'s v1.1 human-cadence pressure — **this is the step
     that actually matters**, since the human's own failure (film review) happened under
     incoming volleys, not in the solo/no-pressure environment this thread measured. Still
     cheap (~20 min per arm, per failure-objective's own throughput numbers on the same rig).
  4. Only a winning dose goes through the Verilator co-sim farm bit-exactness gate before any
     RTL/firmware work — this is the expensive, cross-team-dependent step (cosim-farm thread is
     still building the farm). Everything before it is machine-time the owner doesn't have to
     watch.
- **What it's worth if true:** this is the only thread this round that ties a champion defect
  to a *named, previously human-observed* failure mode (`FILM_REVIEW_20260804_SCORECARD.md`,
  struktured's m4 endgame: 8 self-seals in one contested close). It is also the only thread that
  identifies a genuinely **new axis** the champion's eval does not currently price at all — see
  §3, this is why failure-objective's coordinate scan over *existing* terms came back flat.
  Realistic upside is modest (0.63 events/game, most self-resolve — 66.7% reopen before game
  end, only 14/126×200 cells stay sealed at game end) but the mechanism plausibly compounds
  under the `dr-mario-eval47-stranded-win`-documented dies-ahead disease (~70% of deaths are
  at-the-doorstep per `BURSTY_V1_RESULTS.md`).
- **Verdict on pursuing:** yes, next round, but gate spend at each stage — a WASH at stage 2/3
  (offline, no-pressure or with-pressure A/B) should stop it there per the same discipline this
  round's dead threads used, before touching the cosim farm.

No other candidate from this round qualifies as a survivor. Everything else is DEAD (§2).

---

## 2. Dead threads — permanent negatives, do not re-run

State these as settled facts for future sessions; re-running the same test is a compute leak.

- **attack-timing — DEAD.** Holding a ready ROM-true attack (up to K pills, gated on opponent
  column height) **never** beats cashing in immediately against the strand180_20 champion, and
  gets **monotonically worse** the more license it's given (threshold=8 small/non-sig,
  threshold=11 large and significant at every K). Confirmed at n=60 on the mildest surviving
  arm: 28.3% winrate, margin −4.43 [−5.59,−3.25], CI nowhere near zero. **Mechanism**: holding
  doesn't re-time damage, it suppresses it — holder's total attacks sent drop ~30% because the
  board keeps moving under the held structure (occlusion/burial/opportunity-cost), not because
  the ranking of "when to cash in" is wrong. **Killed by the cheap gate**: the n=20, 6-arm sweep
  already had every arm ≤50%, four of six with CIs excluding zero — n=60 only sharpened an
  already-decided answer.

- **failure-objective — DEAD, but caveated.** A 6-point local coordinate scan (ws∈{10,40} vs
  champion 20; R_BURIED, R_SETUP at 0.5×/2×) around the champion's coefficients under bursty
  v1.1 pressure found **no point that materially beats the champion's bad-end rate** — every
  arm WASH at n=40 paired seeds (CIs 15–55 points wide, straddling zero). Corroborates the
  independent prior `REACTIVE_MODE_RESULTS.md` (temporary ws elevation to 40/60 under the older
  v1 model also failed). **This closes "reweight the existing terms," not "find any survival
  lever"** — the full 6D CMA-ES the task originally specified was *not* run (deliberately, per
  the cheap-gate-first rule), so "champion is provably coefficient-optimal" is **not** what was
  shown; "no easy win from nudging ws/R_BURIED/R_SETUP individually" is. Do not re-run these
  exact 6 arms; a genuinely different axis (see §1, §3) is the correct next probe, not a wider
  version of this one.

- **opponent-aware — DEAD.** The one-weight term `k·opp_danger·cells` (opponent spawn-lane
  fullness gating the candidate's own matched-cell/attack-channel score), swept k∈{3,7,15,30,60}
  against a bit-exact k=0 null (200/200 selfcheck), never beat 50% winrate; the sole
  positive-point-estimate arm (k=3, 52.5% at n=20) collapsed to 50.8% [44.5,57.8] on a disjoint
  fresh-seed n=64 confirmatory run — **confirmed noise, not a gradient**. Doses beyond k=3
  trend consistently worse on both win rate and the candidate's own attack output (k=60: 5.88
  vs reference 7.95). This is now the **third** independent confirmation of
  `dr-mario-selfplay-vs-negative.md`'s "speed beats aggression, 40+ candidates, zero VS wins"
  (joined by attack-timing above). **Open discrepancy, not a re-run target**: this thread used
  the brief's literal plain-root-search champion definition (`ab47.py::_choose_base`), not the
  actually-shipped `strand180_20` chain+stranded decider — flagged explicitly by the thread
  itself as untested against the real silicon champion, but the thread's own author judged this
  not economical as a "kill test" (it would be new spend, not a cheap re-check).

- **depth4-transfer — DEAD.** Re-mined the existing 1809-row d4-vs-d3 disagreement corpus (zero
  new simulation) for a single-position structural signature separating "d4's move proved
  better" from "d3's move proved better." Best held-out AUC across logreg/tree/forest and a
  4-point noise-margin sweep: **0.578**, always below the 0.60 kill line. The literal mechanism
  named in the task ("d4 keeps a column shorter/open") scored **exactly chance** (AUC 0.500).
  Closes task #22: d4's edge is not just sequential (already known, `depth4/README.md` Phase 3,
  Wilcoxon p=0.389 at the game level) — it is **statistically invisible in a 30-feature
  single-position space**, so it cannot be distilled into a cheap d3 eval term this way. Do not
  re-attempt single-position feature engineering on this corpus; a sequence/trajectory-level
  classifier is the only thing this result leaves open, and the thread itself recommends against
  chasing it, since the underlying game-level rescue effect isn't even confirmed net-positive.

---

## 3. Cross-thread connections

- **failure-objective × endgame-policy — the flat coordinate scan is EXPLAINED by the seal
  defect, not contradicted by it.** failure-objective scanned `ws`, `R_BURIED`, `R_SETUP` —
  all *existing* terms — and found no reweighting improves bad-end rate. endgame-policy shows
  *why*: the champion's search has no term at all for "does this placement cover my own
  remaining virus," and `g_stranded` (the very term failure-objective was scanning) provably
  cannot substitute — a covering cell one row above a virus can have a same-colour neighbour
  elsewhere on the board and score **zero** stranded-cost while still sealing the virus
  underneath it (endgame-policy report, mechanism section). A coordinate scan over an
  eval's existing axes cannot find a fix that lives on a missing axis. This means the natural
  next move is not "widen the failure-objective sweep" (would waste compute repeating a search
  that structurally cannot see the defect) but "build the seal-aware term, then re-ask
  failure-objective's exact question (bad-end rate under bursty v1.1) with the new axis
  included." That is a stronger, cheaper-to-justify follow-up than either thread proposed in
  isolation.

- **attack-timing × opponent-aware — two independent confirmations of the same "don't deviate
  from greedy" law, via unrelated mechanisms.** attack-timing deviates on *when* to cash in an
  attack; opponent-aware deviates on *how much* to weight attacking based on opponent state.
  Both fail for related-but-distinct reasons (attack-timing: held structure decays under a
  moving board; opponent-aware: juicing the term chases rare high-danger states at the expense
  of the common case). Combined with the pre-existing `dr-mario-selfplay-vs-negative.md` (40+
  candidates, zero wins), this is now a 3-for-3 pattern specifically for VS-side ad hoc
  deviations from this champion's tuned greedy policy. Future VS-improvement threads should
  treat "add a heuristic on top of the greedy champion" as a class with a demonstrated near-zero
  hit rate, and look for structurally different levers (search depth, information, or — per §4
  Q3 below — whether the offline harness generating all three of these negatives is even
  measuring the right thing).

- **The gate calibration itself is a finding.** Both attack-timing and opponent-aware ran a
  cheap n=20 pass, escalated the one/few interesting-looking arms, and in *both* cases the
  escalation sharpened the existing direction rather than reversing it (attack-timing:
  37.5%→28.3%, more negative; opponent-aware: 52.5%→50.8%, converged to the null). Zero
  reversals across two independent escalations this round is weak but real evidence the
  portfolio's "cheap pass, escalate only survivors" discipline is not silently discarding real
  positive effects at n=20 — worth remembering next time a thread is tempted to skip the cheap
  gate "to save time."

---

## 4. Next round — three questions (not perturbations)

Given what this round closed off (reweighting existing terms: dead; attack-timing/aggression
heuristics on top of greedy: dead ×3; single-position distillation of d4's edge: dead), the
next round should not hill-climb around this champion's existing parametrization. Three
questions that could be wrong in interesting ways, and that lean on machine time over the
owner's own attention:

1. **Finish and validate the orphaned `learned-eval` thread — is the hand eval leaving real
   value on the table, or is a low linear-R² misleading?** It already ran (n=2200 positions,
   L11, real trajectories, d3/d4-labeled, gate-checked 100/100) but was never written up. A
   quick pass over its own output (`ceiling_positions.json`) during this triage found the
   **hand eval's Pearson correlation with the d3/d4 search-value labels is only 0.10 / 0.06**
   — essentially no linear relationship — while **Spearman rank correlation is 0.59 / 0.52**,
   moderate. That combination is the interesting-if-true case the thread's own docstring names
   as the kill condition's opposite: if R²/rank-correlation were ~0.9+, a learned eval would
   have no headroom; instead there appears to be a lot of headroom on an absolute-value basis,
   while the champion still makes roughly-sane relative choices (which is consistent with it
   working as an argmax-only ranker). This is unverified by me and not this triage's job to
   finish, but it means the thread should **not** be left orphaned — closing it out (a
   held-out train/eval split + an actual small NNUE fit, not just a correlation check) is cheap
   relative to its potential payoff (a structurally different eval paradigm, not a coefficient
   nudge) and the expensive data-collection half is already paid for.

2. **Generalize the self-seal defect to a "color-reachability blind spot" — is sealing a
   narrow instance of a bigger problem?** endgame-policy found the champion covers its own
   virus targets; it did not ask whether the champion also has no notion of *which colors are
   still reachable soon* (e.g., stalling because the one remaining virus's color hasn't
   appeared in N pills, independent of any seal event). This is mineable from existing corpora
   the same way depth4-transfer re-mined its own (zero new simulation for a first pass): pull
   the champion's own solo trajectories, and test whether "target-color pill scarcity" predicts
   stall/loss independent of the seal-event label. If it does, that is a second, larger missing
   axis worth pricing; if it doesn't, that's a cheap, clean kill of a hypothesis nobody's asked
   yet — not a re-test of anything above.

3. **Does the offline VS harness's win-rate conclusion even transfer to RTL, in aggregate — not
   per-move?** Every VS-side negative this round (attack-timing, opponent-aware) and the prior
   `dr-mario-selfplay-vs-negative.md` corpus rest entirely on `vs_harness.play_match`, the
   offline Python simulator. The standing rule (`CANDIDATE_TIER3.md` §10) is that this
   simulator agrees with real RTL on individual move choice only ~13% of the time — but nobody
   has checked whether the **aggregate win-rate direction** (as opposed to per-move identity)
   these threads report is trustworthy at all against real silicon. This is a foundational
   methodology question, not a hill-climb: once the cosim farm (cosim-farm thread) is usable,
   take one already-built, already-negative offline comparison — attack-timing's
   `HoldingDecider` at (threshold=11, K=1) is the cheapest, since its code and paired seeds
   already exist — and run a modest paired sample through the farm. Two genuinely different
   outcomes are both valuable: confirms the offline VS harness's aggregate-rate conclusions are
   trustworthy (rescues this round's negatives, and the older 40+-candidate corpus, as real
   findings rather than simulator artifacts), or shows they are not (which would mean this
   portfolio needs a standing caveat on every VS-derived DEAD verdict to date, a much bigger
   deal than any single thread's result).

---

## Provenance

- Thread reports read in full: `attack-timing/REPORT.md`, `failure-objective/REPORT.md`,
  `endgame-policy/REPORT.md`, `opponent-aware/REPORT.md`, `depth4-transfer/REPORT.md`.
- `learned-eval/` inspected directly (`ceiling_test.py`, `run_full.log`,
  `ceiling_positions.json`) — no `REPORT.md` present; the Pearson/Spearman numbers in §4 Q1
  were computed fresh during this triage from that thread's own output, not copied from a
  report, and should be treated as a preliminary spot-check, not a validated result.
