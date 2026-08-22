# Self-play VS negative — evidentiary audit and re-scope

Lane: lulu-147. Date: 2026-08-21 EDT. Paper audit of [[dr-mario-selfplay-vs-negative]] against
[[dr-mario-sample-size-audit]]'s standard. **No compute was launched.**

---

## 1. What the verdict actually is

"40+ candidates screened, 0 confirmed improvements over the shipped coef-winner", where the
objective was **VS head-to-head win rate between two deciders**.

## 2. Evidentiary weight — n, era, instruments

| axis | assessment |
|---|---|
| **era** | 2026-07-31 / 2026-08-01. **Post-discipline.** The sample-size audit's own bounding claim is that thin conclusions cluster in the *pre*-2026-07-16 negatives. This is not one of them. |
| **n** | Screens n=160 seeds; holdouts n=320-400 side-configurations. Not thin. |
| **blocking** | Tune and holdout seed blocks **disjoint and pre-declared** (e.g. tune 2000-2159, hold 40000-40319). This is the design the audit holds up as exemplary. |
| **unit of analysis** | Seed-paired, side-swapped, bootstrap CI over seeds. Satisfies the unit-of-analysis rule. |
| **validation chain** | Delta decider == canonical numba at all 31 weight sets (248 games, byte-identical) → `gate.py selfcheck` **18/18 mutants killed** → `gate.py rtl` 948 leaf + 4494 node + 4494 delta cases vs `LeafEval.sv` md5 94f84404. Null (winner vs winner) exactly 50.0%. **This is the strongest validation chain in the project.** |
| **coverage self-audit** | The memory contains its own coverage critique (six defensive knobs measured where the defended-against event never occurred) **and then re-ran them under `--rule rom` where it does occur — the null survived, and the motivating hypothesis was refuted rather than rescued.** A negative that survives the fix to its own strongest objection is unusually well-evidenced. |
| **multiplicity** | Handled explicitly: 30 arms at α=0.05 predicts 1.5 false positives, 2 observed, both sent to holdout, both failed. Dose-response was used as the triage rule and **correctly predicted which of the two would survive**. |

## 3. ★ Verdict: **STANDS-BUT-NARROW.**

> The self-play VS negative is one of the best-evidenced results in the program and it is **not**
> a candidate for the sample-size audit's re-test list: it is post-discipline, properly blocked,
> holdout-confirmed, multiplicity-aware, backed by an 18/18 killed-mutant gate and an
> RTL-bit-exact chain, and it survived the fix to its own most serious coverage objection when
> the defensive knobs were re-run under `--rule rom` and the null held. **What it does not
> support is the inference the lulu question invites.** Its scope is *"tuning these eval
> constants for win rate in decider-vs-decider self-play does not beat the shipped winner"* —
> and by its own text, both attack levers it swept (`R_VBONUS`, `R_CROSS`) are **simultaneity**
> levers, while **85% of real ROM attacks are cascade-formed**, so the cascade lever has never
> been tested at all and the owner's combo thesis is untouched. Two further scope limits matter
> here: the opponent was always another decider, never a human-shaped one, so nothing in it
> speaks to performance against dr. lulu; and its own conclusion that garbage **compresses**
> skill gaps by 19.2pp means the objective it optimised has a structurally lower ceiling than
> the solo one — which is a reason the lane paid poorly, not evidence that VS performance is
> not worth pursuing. **It should be re-scoped, not re-tested:** it closes *eval-constant tuning
> in self-play*, and it closes nothing about cascades, about human-shaped opponents, or about
> the race endpoint this lane proposes.

**Corroboration that the narrow reading is the right one:** `lnk1` — a *physics-fidelity* change
rather than an eval-constant change — later became the program's **first holdout-confirmed VS
win** at 60.2% [56.9, 63.4], passing every filter that killed the self-play candidates, with a
holdout *stronger* than its tuning block. So the VS objective was never inert; the **lever class**
was wrong. ★ And `lnk1` wins by clearing first in 99.2% of its wins, with garbage deciding 5 of
800 matches — which is the same conclusion this lane's gap analysis reaches from the other end:
**tempo, not attack.**

## 4. Consequences for the lulu line

- **Do not re-run the eval-constant sweep.** It is answered.
- **Do not read it as "VS is not worth measuring."** It says VS *tuning of those constants* did
  not pay. Nothing in it measured a race against a human model, because no such rig existed.
- **Two doors it leaves open** and this lane should record as open: (i) the **cascade lever**,
  blocked behind fixpoint physics; (ii) **physics-fidelity** changes, which is where the only
  confirmed VS win came from.
- **Import its methodology wholesale** into `VS_RACE_ENDPOINT.md`: disjoint pre-declared blocks,
  dose-response as the triage rule for screen hits, margin/win-rate sign disagreement as an
  artifact detector, `moved%` in every output, and a stamped `HARNESS_REV` on every row.
