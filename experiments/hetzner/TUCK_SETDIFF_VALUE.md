# Are the firmware scanner's tuck picks worse, or merely different?

**Neither. They are SYSTEMATICALLY BETTER — and that redirects the whole tuck
program away from the scanner.**

## Method

RTL-mirror ruler (`mirrored_leaf.choose_root_with_tucks_mirrored`), spent only
on decisions where the two candidate sets plausibly disagree. Both sets scored
by the SAME ruler on the SAME board with the SAME pill pair; only the vocabulary
differs, so every number is a paired within-decision difference.

θ needs no re-scoring: the gate is `val < best_base_val + θ` (`mirrored_leaf.py:171`),
so a tuck fires at θ iff its **margin over base ≥ θ**. One scoring pass covers
every θ.

⚠ The fast njit ruler was **rejected** — it failed its sign gate 9/10 — and is
used ONLY as a nominator to choose which decisions the mirror adjudicates. An
audit sample of nominator-concordant decisions bounds false negatives:
**7 audited, 0 missed.**

## Result — 175 mirror-scored discordant decisions (277 seen, seeds 7000-7003)

| θ | PY fires | FW fires | mean(FW−PY) | median | FW better | PY better | sign test |
|---|---------|----------|-------------|--------|-----------|-----------|-----------|
| 150 | 7 | 26 | **+202.90** | +245 | 26 | 5 | **p = 0.0002** |
| 250 | **0** | 16 | **+348.69** | +347 | 16 | 0 | **p < 0.0001** |

## Three answers

**1. WORSE or DIFFERENT? Neither — BETTER, decisively.** The firmware's set
contains a materially better best-tuck on the decisions where the sets diverge.
At θ=250 the Python enumerator finds **nothing at all** that clears the bar while
the firmware finds 16 tucks averaging +348.

**2. The horizontal skew is the mechanism — with the sign INVERTED.** FW winners
are **25 H / 1 V** at θ=150 and **15 H / 1 V** at θ=250. The horizontals the
firmware uniquely enumerates are exactly where the value is. The 71-75%
horizontal skew is not a defect signature; it is the firmware finding valuable
horizontal tucks the Python enumerator misses.

**3. Tightening θ is NOT the fix — it makes the gap WORSE.** Going 150 → 250
widens the mean advantage (+203 → +349) and zeroes the Python side. Any plan to
recover arm D by raising θ toward the offline 250 should be dropped.

## ⚠ A prediction of mine this REFUTES

I previously flagged that FW-only candidates sit **shallower** (rows 8-12) than
RS-only (rows 13-15) and reasoned that "a scanner finding shallower tucks is
finding worse ones by construction." **That was wrong.** The firmware reaches
shallower AND scores higher, so **margin and depth pull apart** — depth is not a
proxy for value here. Do not use resting-row depth as a quality heuristic.

## GO/NO-GO with mechanism

**The scanner's VOCABULARY is not the blocker.** It is better than the proof
enumerator's on exactly the decisions that differ. So arm D's 0% RTL clear rate
must originate **downstream of candidate generation** — in selection, in
executor coherence, or in the root-placement overwrite. That is where to look
next, and it is a much smaller search than redesigning the scan.

## Scope

Best-in-set under one eval. This does NOT test the firmware's own
selection/scoring rule, nor execution — the two remaining downstream suspects.
n=175 discordant decisions from 4 games; decisions within a game are not
independent, so treat the p-values as strong directional evidence rather than
exact.

Rig: `tuck_setdiff_value.py --discordant` · raw: `results/tuck_setdiff_mirror.json`
