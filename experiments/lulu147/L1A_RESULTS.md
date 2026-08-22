# L1a RESULTS — champion tempo under pressure

Lane: lulu-147. Run 2026-08-21 EDT. Rig: `experiments/lulu147/l1a_tempo.py`.
Raw output: `L1A_OUTPUT.txt`.

**ZERO NEW COMPUTE.** Every number is a re-reading of per-seed rows that existing runs
already wrote to `dr-mario-qa-wt/experiments/eval47/results/`. The simulator was not executed.

## G0 — outcome-plausibility gate: **PASS 7/7**

Recovered rows reproduce every published headline: drip ctrl 115/120 and arm 119/120 won;
bursty v1.1 arm dies-ahead 9 (the published 7.5%); lulu arm 90/120 won, dies-ahead 17;
lulu ctrl dies-ahead 41; and the derived lulu clear rate equals the stored `summary.clear1`
to machine precision. The artifacts are what they claim.

## ★★★ THE HEADLINE — and a CORRECTION to the number now in circulation

My first pass quoted the **wins-only** median (96 → 127 pills, +32%). The pre-registration
required a survivorship check, and **the check moved the number.** Two independent
estimators agree and both say the wins-only figure **understates** the tempo tax:

| stream | cleared | wins-only MED | Kaplan-Meier MED | **ALL-GAMES MED** | **min** | ALL p75 |
|---|---|---|---|---|---|---|
| clean (blunder corpus, n=250) | 250/250 | 91 | 91 | **91** | **3.8** | 105 |
| canonical drip | 119/120 | 96 | 96 | **96** | **4.0** | 110 |
| bursty v1.1 | 100/120 | 128 | 136 | **136** | **5.7** | 222 |
| **lulu-fitted (POOLED)** | **90/120** | 127 | 151 | **152** | **6.3** | **299** |

> ★ **QUOTE THIS: median time-to-clear 96 → 152 pills, +57% (vs clean 91, +67%).
> At the project's 2.5 s/pill constant, 4.0 min → 6.3 min.**
> Her one filmed race win ran **~190 s ≈ 3.2 min**.

**Why the all-games column is the right one, and why it needs no censoring model.**
"Pills by which 50% of ALL games have cleared" is well defined whenever the clear rate
exceeds 50%, and it requires **no** claim that a topped-out game would have cleared later.
The KM column (which does make that assumption) lands at 151 against the assumption-free
152 — they agree, so the estimator choice is not load-bearing. The wins-only column is a
**floor**: it silently drops the 30 games that never cleared at all.

⚠ **`ALL p75 = 299` for the lulu stream is the most alarming cell in the table.** The rig
caps at 300 placements. **A quarter of games under her pressure effectively never finish.**

⚠ **Caveats unchanged and still mandatory** ([[caveat-next-to-data-not-number]]): her 3.2 min
is **n=1** and includes non-play frames; our side is a **solo rig with injected garbage, not
a VS board**; 2.5 s/pill is a project constant, not a measurement of this build. The
comparison is an anchor, not a finding.

## ★ Prediction outcomes (pre-registered in `PREREG_L1.md` §3)

- **P1 — CONFIRMED, and by more than predicted.** Predicted median ≥120 under lulu pressure;
  observed 152 all-games (127 wins-only). The unflattering branch (~96 ⇒ "pressure does not
  tax tempo") is firmly excluded.
- **P2 — CONSISTENT but NOT ESTABLISHED.** Her ~3.2 min vs our 6.3 min points the predicted
  way, but n=1 on her side cannot establish it. Needs L1b.
- **P3 — UNTESTED. Blocked, not answered.** See below.
- **P4 — not yet run** (her sending split).

## ★★ L1a(3) IS BLOCKED — and the reason is a rig defect worth fixing

The volley-stratified hazard cannot be computed from stored artifacts. **The rows are
per-GAME aggregates**: `garbage_injected` is a total, and the placement index of each volley
received is **never serialized**. So "is failure clustered in the placements right after a
volley lands?" — the question that separates an *attack-response* defect from a plain
*cumulative-height* one — needs a rig instrumentation change plus a re-run, i.e. **compute**.

⇒ **P3 is deferred, and the attack-response story remains an assumption.** This matters
beyond L1: `lulu_proxy/striker_model.py`'s whole design is a height-gated *release* model,
and nothing on disk confirms that failure actually concentrates after volleys. Recommended
one-line fix when compute returns: have `pressure_rig.play()` append the placement index to
a `volley_pills: []` list on each injection.

## ★★ L1a(2) — how it loses, and why the cap=LOSS ruling is now empirically vindicated

| stream | lost | topout | stall | dies-ahead | med viruses left | med pills at loss |
|---|---|---|---|---|---|---|
| canonical drip | 1 | 0 | 1 | 0 | — | 300 |
| bursty v1.1 | 20 | 11 | 9 | 9 | 3.0 | 290 |
| **lulu-fitted** | **30** | **18** | **12** | **17** | **2.0** | 272 |

**When it loses under her pressure it dies with a median of TWO viruses left.** 17 of its 18
topouts are dies-ahead. That is not a play-quality deficit; it is a build that gets to the
brink and cannot close.

> ★★ **12 of the 30 losses are STALLS — games that hit the 300-placement cap.** That is
> **10% of all games** where the scoring convention alone decides the answer:
> `cap = LOSS` (signed off) scores them 0, `h2h_vs.py:218`'s `0.5` would hand the champion
> six free half-points per 120 games. The ruling was made on principle before this number
> existed; the data now backs it. **This is also a concrete reason old h2h numbers must
> never be pooled with new race-endpoint numbers.**

## Scope (rule 10)

Solo pressure-rig numbers. **There is no race and no opponent in any of them.** They license
tempo claims only — never a win rate against dr. lulu, and never a claim that the champion
"would" win a race.
