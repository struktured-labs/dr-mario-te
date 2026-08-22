# VS-RACE — a registered endpoint for "does it beat dr. lulu"

Lane: lulu-147. Date: 2026-08-21 EDT. **Specification. Not built, not run.**

The program's problem is not that its VS numbers are wrong. It is that **it has never measured a
race against a human-shaped opponent.** This document specifies the endpoint that would.

---

## 1. Why a new endpoint rather than a new arm on an old one

| existing rig | has a race? | has a human model? | verdict |
|---|---|---|---|
| `pressure_rig.py` (drip / bursty / lulu) | **NO** — one board, no opponent clock; in bursty mode the *AI's own clear* stands in for the opponent's (`pressure_rig.py:222-240`) | yes (fitted) | measures survival, cannot produce a win rate |
| `lulu_proxy/striker_model.py` | **NO** — banks and releases against the defender's height; still one board | yes (fitted + timed) | best pressure instrument in the tree; still not a race |
| `vs_harness.py` (r1) / `h2h_vs.py` | **YES** — real clear-first / topout / cap, side-swapped | **NO** — the opponent is always another decider | measures eval-vs-eval, not human-vs-AI |

**The endpoint is the missing cell of that table.** No code change to either family is enough;
the two must be crossed.

---

## 2. Definitions — fixed before any run

### 2.1 Outcome (the part the owner cares about most)

For the champion (`C`) against the modelled opponent (`L`), per seed:

| outcome | condition | scored |
|---|---|---|
| **WIN** | `C` reaches 0 viruses strictly before `L` | 1.0 |
| **LOSS (raced)** | `L` reaches 0 viruses first | 0.0 |
| **LOSS (killed)** | `C` tops out or has no legal move | 0.0 |
| **WIN (kill)** | `L` tops out first | 1.0 |
| **LOSS (cap)** | neither finishes by the placement cap | **0.0** |

★★ **`survive-but-slower` is a LOSS, and so is the cap.** This is the single most important
definitional choice in the document and it is a deliberate break with the incumbent rigs.
`vs_env_exact.play_match` scores a cap as `winner = -1` and `h2h_vs.py:218` converts it to
**0.5**. That is correct for an eval-vs-eval A/B where a draw is genuinely uninformative; it is
**wrong here**, because against a real human a game that never ends is a game you did not win.
Scoring caps at 0.5 would let a stalling arm buy half a point per hung game.

**Reported alongside the win rate, never folded into it:** `win_race`, `win_kill`, `loss_race`,
`loss_kill`, `loss_cap` as five separate counts. If `loss_cap` is more than ~2% the cap is
distorting the endpoint and the number is not shippable.

### 2.2 Primary endpoint

**`P(C beats L)` over held-out seeds, side-swapped, with a seed-clustered bootstrap CI.**
Unit of analysis = **the seed** ([[dr-mario-sample-size-audit]]'s unit-of-analysis rule).

### 2.3 Secondaries (pre-registered, reported always, never promoted to primary)

- `pills_to_clear` **distribution** for `C` — p10/p25/median/p75/p90, not just a mean delta.
  ★ This does not exist anywhere in the tree today and is the cheapest thing on this list.
- `dies_ahead` rate (topout with ≤12 viruses left) — the incumbent metric, retained for
  continuity with `pressure_rig`, explicitly **demoted to secondary**.
- volleys received per placement (survival-normalised — the raw count is a survival artifact,
  per [[dr-mario-vs-stance-mechanism]]).
- margin (`viruses_L − viruses_C`) at termination.

★ **Margin/win-rate sign disagreement is a pre-registered artifact detector**
([[dr-mario-selfplay-vs-negative]]): if win rate moves up while margin moves down, the result is
presumed noise regardless of its CI.

---

## 3. Arm (a) — `L` = lulu-parameterized pressure + clock

The opponent is not a decider and not a garbage schedule. It is a **two-part model**:

**(i) A CLOCK.** `L` clears viruses at a fitted rate drawn per-seed from a *distribution*, not a
constant — a constant-rate opponent makes every match a threshold test on a single number and
destroys the variance structure that makes seeds informative. Parameterized as pills-to-clear
(the unit both sides share) with a spread taken from her footage; **on 12:38 of footage this is
the weakest-identified parameter in the whole endpoint** and it gets a sensitivity sweep, not a
point estimate (§6).

**(ii) A VOLLEY PROCESS.** Reuse `striker_model.py` unchanged where possible — it already fires
on a *sender clear* event and banks/releases on the defender's scaffold height, and it carries
its own killed-mutant gates. Feed it her **sending** fit once `PRESSURE_MODEL_PLAN.md` §3(a)
lands; until then, her pooled fit **with a scope label on every number**.

**Coupling — the property that makes this a race rather than two solos.** `L`'s clock advances
her viruses down; her clears are what *generate* her volleys; and `C`'s volleys must be able to
**slow her down or kill her**, or `C` can never win by attacking and the endpoint silently
re-encodes the "AI never attacks" assumption as a rule. `L` therefore needs a **damage response**
— a fitted or assumed penalty to her clock per volley received. On current footage this is
**assumed, not fitted**, and it is declared as such in §6.

**Garbage mechanics:** use `rom_attack_rule.garbage_columns` — the stamped, ROM-true path.
⚠ **`vs_env_exact.py:46` hard-codes `GARBAGE_PAIRS = ((1,5),(2,6),(3,7))` with the comment
"columns 0 and 4 are immune", which `rom_attack_rule.py:172` explicitly refutes.** Two
incompatible garbage models are live in the tree and `h2h_vs.py` uses the wrong one. The new rig
must import `rom_attack_rule` and **stamp `HARNESS_REV`**; harness identity has already moved a
result by ~5 points on identical seeds.

---

## 4. Arm (b) — `L` = real dr. lulu on silicon (the couch protocol)

The eventual ground truth. Design constraints, stated now so arm (a) is built to be falsifiable
by it:

- **Seeds are not controllable across the couch.** The cart's seed is deterministic on boot, so
  the protocol must **log** the seed rather than assign it, and arm (a)'s comparison set must be
  drawn to match the observed distribution — not the reverse.
- **n is brutally limited.** A couch session is ~10-20 matches. At n=15 the binomial half-width
  is roughly ±25pp. **Arm (b) can refute a strong claim from arm (a); it cannot confirm a
  marginal one.** Plan it as a falsification gate, not as an estimate.
- **Record every session** (capture pipeline), with the OBS filename template naming the actual
  opponent, so every couch match also becomes footage that improves the model.
- **Pre-commit the prediction.** Before the session, arm (a) emits a predicted win rate and its
  CI. The session either falls inside it or does not. This is the only way a 15-match set carries
  information.

---

## 5. ★ What the lab CAN and CANNOT claim (rule 10)

**CAN claim, once arm (a) exists and its gates pass:**
- "Against a lulu-parameterized opponent model, build X wins `p%` [CI] of held-out seeds."
- "Change Y moves that number by `d` [CI]" — *provided* Y moves ≥ ~20% of seeds; a near-inert
  knob gives a deceptively **tight** CI because most paired diffs are exactly zero, and a tight
  CI at 51% can mean "barely tested", not "precisely measured as good".
- Distributional tempo claims, once the distribution is reported.

**CANNOT claim, ever, on arm (a) alone:**
- "Build X beats dr. lulu." Arm (a) is a **model of her**, fitted to 12:38 of footage from one
  night, pooled, with no aim, no phase, and an **assumed** damage response. It licenses claims
  about the *model*, not about the person. This distinction must survive into every headline —
  it is exactly the distinction [[dr-mario-lulu-fit-is-pooled]] found the program already
  failing to make once.
- Any transfer to silicon. Execution defects that lose pills mid-match are invisible to this
  endpoint by construction, and they are ranked HIGH in the north-star memory.

**CANNOT claim today, before arm (a) exists:**
- ⚠ **Any VS win rate against dr. lulu whatsoever.** `dies_ahead 14.2%` on `pressure_rig` is a
  *solo survival* statistic on a board with no opponent. It has been the closest thing we have,
  and it is not a win rate.

**Known asymmetries that must be controlled or declared:**
- **First-mover.** `vs_harness.play_match` alternates with player 0 always first and does **not**
  correct for it; `h2h_vs.py` corrects by **side swap** (every seed played both ways, scored
  `(win_as_P0 + win_as_P1)/2`). ★ **Arm (a) cannot side-swap** — the opponent is a model, not an
  arm, so there is no symmetric configuration to swap into. First-mover must therefore be
  **measured** (run the model in both positions, report the delta) and **declared as a bias**,
  not silently cancelled.
- **Garbage phase keying.** `frame_counter = seed * 7919 + volley_ordinal` keys columns per
  (seed, ordinal) so ablating one volley cannot reshuffle another's. Preserve this; it is what
  makes ablations interpretable.
- **Garbage compresses skill gaps** — it takes 19.2pp [−25.5,−13.0] off the stronger eval's edge,
  and flips 37.2% of matches between *identical* evals ([[dr-mario-garbage-power-bias]]).
  ⇒ **This endpoint has a structurally lower ceiling and higher variance than a solo one.**
  Power it accordingly (§6) and never compare its effect sizes to solo effect sizes.

---

## 6. Gates, controls, and honest weak points

**Gates (all pre-registered; a failure blocks the number, not just annotates it):**
- **G1 null** — `C` vs a copy of `C` promoted to opponent = 50.0%. ⚠ Note this gate is *weak*:
  with identical arms and a side swap it is 50.0% **by construction** and cannot detect a broken
  rule; it catches plumbing only. Do not treat passing it as evidence the rule is right.
- **G2 not-inert** — the arm must move ≥20% of seeds. Report `moved%` in every output; "moved 0%
  of seeds with attack rates identical to 4 significant figures" is the diagnostic that caught a
  candidate built byte-identical to its own reference.
- **G3 zero-pressure control** — with `L`'s volleys severed, the endpoint must collapse to a pure
  pills-to-clear race, and the observed win rate must match the one predicted from the two
  clock distributions. If it does not, the race loop is wrong.
- **G4 volume-matched blind** — `L`'s *timing* must beat `build_blind_schedule` at her exact
  volume. Without this, any result is a volume result wearing a timing label.
- **G5 harness stamp** — every row carries `HARNESS_REV`; results are never compared across revs.
- **G6 determinism** — replay a sample of seeds; byte-identical.

**Power.** Given the compression above, plan n on the assumption that effects are small.
n=400 side-configurations gives roughly ±5pp on a win rate — adequate for a 10pp effect, not for
a 3pp one. Tune and holdout blocks are **disjoint and declared before the run**; every apparent
win in the self-play lane died on a fresh block, and seed-block artifacts were the *default*
there, not the exception.

**★ The three weak points, named rather than buried:**
1. **`L`'s clock distribution is fitted to essentially one observed clear.** It gets a
   **sensitivity sweep** across a plausible range, and the headline is reported as a *curve over
   her assumed speed*, not a single win rate. If the win rate is flat across the sweep the
   endpoint is robust; if it swings, the endpoint is measuring our assumption about her.
2. **`L`'s damage response is assumed.** Same treatment: sweep it, report the surface.
3. **A model of a person is not the person.** §5.

---

## 7. Build order

1. **Pills-to-clear distribution reporting** in `pressure_rig.compare()` and `ab47.compare()`.
   Zero new compute — the per-seed rows are already on disk. Unblocks every tempo claim and
   makes the §6 sensitivity sweep interpretable.
2. **`vs_race.py`** — the two-clock loop, `rom_attack_rule` columns, stamped `HARNESS_REV`,
   G1/G2/G3/G6 wired from the first commit rather than retrofitted.
3. **G4** + the striker fed by her fit.
4. Her **sending** fit swapped in (`PRESSURE_MODEL_PLAN.md` §3a).
5. The sensitivity surface, then a pre-committed prediction for a couch session.
