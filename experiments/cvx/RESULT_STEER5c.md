# RESULT (2026-09-26): STEER5c — HSV512 holdout FAILS the bar; the early-death reduction REPLICATES on fresh seeds

Pre-reg: `PREREG_STEER5c.md` (committed `107ab24` before any 5c game).
- **Arm:** HSV leaf term at the RTL dose 512 (`cascade_leaf5b_x`), on the shipping REACH+TAP brain and steering.
- **PRIMARY:** the FRESH 464-stream block, paired vs the banked baseline control on the same seeds.

| endpoint (fresh block, n=464 paired) | baseline | hsv512 | paired Δ [95% CI] | bar | met? |
|---|---|---|---|---|---|
| tap≤100 | 4.96% | **2.37%** | **−2.59 [−4.96, −0.22]** | point < 0 | ✅ (CI also excludes 0) |
| whole-game tap-out | 27.37% | 25.22% | −2.16 [−7.33, **+3.23**] | upper CI ≤ +2 | ❌ |
| VS race win, δ 2.65 (n=300 fresh, paired) | 69.7% | 68.0% | −1.67 [**−8.33**, +4.67] | lower CI ≥ −2 | ❌ |
| VS race win, δ 2.0 | | | −2.67 [−9.33, +4.00] | (reported) | |

**Verdict: FAIL** on the pre-registered non-inferiority rules (tap-out and race).
- **The early-death reduction is confirmed.** −2.6 pp on fresh seeds, CI excluding 0: the post-hoc STEER5b signal
  was not a reuse artefact.
- **The two failed rules are width failures, as the prereg's power statement predicted:**
  - tap-out point estimate −2.2 with SE ≈ 2.7;
  - race SE ≈ 3.3 on n = 300, so "lower CI ≥ −2" needs a point estimate ≥ ≈ +4.5.
- **Race context:** hsv512 clears 71.0% vs 70.0% and taps out 28.7% vs 30.0%. It is a bit slower (median 214 s vs
  205 s) and sends a bit more (64.8 vs 59.8 tiles). There is no sign of a real race cost beyond noise, but no proof
  of non-inferiority either.

## Descriptive (NOT counted toward the pass)
- **Dose check, original 600 block:**
  - hsv512 tap≤100 −2.50 [−4.83, −0.17], tap-out −2.50 [−7.33, +2.33];
  - hsv540 there: −3.00 / −2.67.
  - ⇒ 512 ≈ 540.
- **Pooled 600 + 464** (n = 1064 paired; the 600 block is not independent of the selection):
  - tap≤100 −2.54 [−4.14, −0.85];
  - tap-out −2.35 [−5.73, +1.22].

## What would settle it (not run)
Non-inferiority at ±2 pp needs about 3–4× the sample:
- whole-game tap-out SE ≈ 1 pp → ~2,500 paired games;
- race SE ≈ 1 pp → ~3,000 race games.

Fresh streams are nearly exhausted (the registry's longest free runs are now ≤ 83 streams), so a larger
confirmation must reuse seeds, declared. The alternative is to accept tap≤100 as the primary on the owner's #1
metric (early tap-outs) with non-inferiority on the pooled data.

## RTL note (spec deferred, since the bar failed; recorded because it changes the cost picture)
LeafEval.sv already has a PRE-SCALED accumulator in the column walk: `matched60 += 48` per matched virus, which
enters S_DONE2 as `+ matched60_p` with no multiplier.
- **HSV folds into that path.** In `S_COLWALK`, on a virus cell with `wr_ < 9 && wc ∈ {3,4,5}`, add −512, a
  single-bit constant. The accumulator becomes signed, about 2 bits wider (range −13,824..+2,304).
- **No new combine input,** so no change to S_DONE2's adder tree. That is exactly what
  [[dr-mario-leaf-has-no-timing-budget]] prices as a new pipeline stage, and it is avoided here.
- **Delta path (CMD 6/7):** a non-clearing child never changes virus cells, so its HSV equals the parent's.
  - If the mini-colwalk's old and new phases apply the same per-virus rule, the −512s cancel and
    `base_matched + dd_matched` carries HSV for free.
  - Clearing children take the full NODE colwalk.
- **Expected impact:** a few ALMs plus a wider accumulator on a non-critical increment. Timing risk is low but
  NOT zero: one fit is n=1 at 0.076–0.380 ns seed noise.

Files: `analyze_steer5c.py`; rows in `steer5/c_remote/` (fresh gate b + both race arms) and `steer5/c_local/`
(600-block).
