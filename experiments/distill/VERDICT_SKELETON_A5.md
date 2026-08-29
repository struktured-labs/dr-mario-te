# A5 / PHASE 1 VERDICT — STRUCTURE, WRITTEN BEFORE THE NUMBERS EXIST

⚠ **This is the skeleton, not the verdict.** Committed while PHASE 1 is still
running so the framing cannot be chosen after seeing the result. Every `<...>`
is filled from a command's output, not from recollection.

**R28 timing proof at commit**: PHASE 1 incomplete, `fit2` has never emitted a
`REGISTERED VERDICT` line, no census-enlarged fit exists.

---

## 0. STAGE COMPLETE ≠ VERDICT — say which, in the heading

⚠ **A segment's ETA was delivered to the owner as the verdict's** ("around
5 am" for what was only the held arm ending). The `fit2` completeness gate
already enforces the distinction in code — it prints
`*** NOT A VERDICT — BANK INCOMPLETE ***` and exits 4 — **and the prose must
match the gate.**

| what happened | what it is called | may it be quoted? |
|---|---|---|
| PHASE 1 (held census) finishes | **STAGE COMPLETE — L20 held arm** | ❌ no number from it |
| reserve census finishes | **STAGE COMPLETE — reserve census** | ❌ |
| `fit2` prints `REGISTERED VERDICT` on a complete bank | **THE VERDICT** | ✅ |
| L11M instrument arm | **its own arm, own bars** | ✅ (already read) |

**Never put a stage-complete time and the word "verdict" in the same sentence.**
An ETA is always quoted "at the observed rate" and re-derived at report time
(`scratch/eta.py`), never repeated from an earlier message.

---

## 1. R81 EXECUTOR CAVEAT — ITS OWN SENTENCE, NOT A FOOTNOTE

> **The M1 rig is the SOFTWARE executor.** `oracle_arm.py` contains zero
> `exec_mode` occurrences — there is no firmware executor on the path any M1
> game took. **Every death-class claim below inherits this.**

| stratum | n topouts | median viruses left | ≤3 | ≥20 (silicon-like) |
|---|---|---|---|---|
| L11M (E-M1a's) | 63 | 2 | 77.8% | 7.9% |
| L20 (this fit's) | 254 | 9 | 28.7% | 35.0% |
| real-firmware ref | | 35-36 | 1.7-2.6% | |
| software-lab ref | | 2 | 59.6% | |

**E-M1a's 63/63 catch and 191-ply median lead describe the LAST-VIRUS death
class, not the midgame class the silicon exhibits.** M0 is unaffected (banked
silicon loss corpus, not a lab rig).

## 2. THE L11M RETRACTION — stated where the finding was made

"L11M not distillable" was **wrong** and is retracted: n=55 gave headroom
−0.057; the completed arm at n=531 gives **+0.209 (USABLE)**, comparable to
L20's +0.200. Decomposition (n vs population) travels with it, and so does the
inheritance: **it establishes distillability in the death window OF
software-executor last-virus deaths**, not in the midgame class.

## 3. THE FIT — three ways, against the bars AS SIGNED

Bars unchanged: **GO ≥0.129 with clustered CI LB >0.099; KILL if UB <0.099.**
Gating arm = **pooled census**; base-only = continuity check; all three reported
with the class-composition table beside them.

| arm | n held-danger | capture | CI | verdict |
|---|---|---|---|---|
| P poststrat-pooled (GATES) | `<...>` | `<...>` | `<...>` | `<...>` |
| S1 pooled unweighted (CO-GATES) | `<...>` | `<...>` | `<...>` | `<...>` |
| S2 base-only (continuity) | `<...>` | `<...>` | `<...>` | — |
| D census-only (diagnostic) | `<...>` | `<...>` | `<...>` | — |
| F frozen pre-A5 guard | `<...>` | `<...>` | `<...>` | — |

**⚠ READ AGAINST 0.37, NOT 1.0 (R72).** The teacher reproduces only **36.7%**
of its own verdicts across independent fork halves. No agreement figure here
gets read against perfect imitation.

**Power, stated as power (R47):** `<...>`% for a KILL at the true-effect values
that matter — not as bare n.

## 4. THE DEATH-CLASS DIAGNOSTIC — reported, never gating

Read at full n **whichever way it falls** (pre-committed; the partial reading
was withheld under R82 and declared as withheld).

| death class of source game | n | capture | CI | dose |
|---|---|---|---|---|
| last-virus (≤3) | `<...>` | `<...>` | `<...>` | `<...>` |
| mid (4-19) | `<...>` | `<...>` | `<...>` | `<...>` |
| **silicon-like (≥20)** | `<...>` | `<...>` | `<...>` | `<...>` |
| no-topout | `<...>` | `<...>` | `<...>` | `<...>` |

⚠ Conditions on an outcome the deployed guard cannot see. **Diagnostic only.**

## 5. WHAT THIS VERDICT DOES NOT LICENSE

- **No silicon claim**, on two independent legs: the L20→L11-MED regime gap and
  the software-executor→real-firmware death-class gap.
- A **BETWEEN** at the enlarged n is a pre-registered **STOP**, not a third
  back-fill.
- PHASE 2 (333 core-h) is **conditional on a KILL** — on GO or BETWEEN its
  necessity gets argued, not assumed.

## 6. COST — count the blanks and say what was counted

Report **games, core-hours, wall-clock, and EUR actual**, each with **how many
rows carried the value and how many were blank**. A total over a
sometimes-populated field is a lower bound wearing a total's clothing.
