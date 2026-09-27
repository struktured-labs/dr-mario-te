# RESULT — run 10, COMBINED arm (run of PREREG_COMBO.md).  ✅ PRIMARY LANDS.
2026-09-10/11. Pre-registration filed before the run; decision rule applied as written.

## PRIMARY — `wincombo` IS a genuine champion candidate
n = 2000 CRN-paired fresh seeds (63000..64998 + 27960..29958, both registered AT LAUNCH),
L20 drip, cap 600. Powered for +2.2pp; the pre-run prediction was +2.2pp.

| arm | clear | d | 95% CI | W | L | McNemar p | topout | stall |
|---|---|---|---|---|---|---|---|---|
| champion | 89.20% | — | — | — | — | — | 9.00% | 1.80% |
| **`wincombo`** (primary) | **91.40%** | **+2.20pp** | **[+0.4, +4.0]** | 183 | 139 | **0.01643** | **5.65%** | 2.95% |
| `winend8_48` (decomposition) | 90.80% | +1.60pp | [+0.2, +3.0] | 122 | 90 | 0.03300 | 7.25% | 1.95% |

`wincombo` = champion + `R_SPAWNCOL=2` + `R_ENDK=8, R_ENDH=48`.

## The mechanism endpoint is FAR stronger than the headline
**Top-out: 9.00% -> 5.65%, a 37% relative reduction, McNemar p = 0.00006** (champion-only 169 vs
arm-only 102). That is the term's OWN endpoint and it is two orders of magnitude more significant
than the clear-rate p — which is exactly the right shape for a real mechanism rather than a lucky
clear-rate draw. Top-out was ~76% of the champion's remaining failure.

⚠ **It trades stalls for top-outs: stall 1.80% -> 2.95%.** The arm is slower and safer. At cap 600
those stalls are GENUINE (no clear anywhere in this lane exceeds 426 pills), not censoring. Net is
clearly positive, but the trade must be stated, not buried.

## Additivity (pre-specified, cross-block ⇒ DIRECTIONAL ONLY)
`d(wincombo) +2.20` − `d(winend8_48) +1.60` = **+0.60pp** implied for the spawn-lane half, against
the **+1.12pp** `winsc2` measured on its own block. Directionally consistent, **sub-additive**.
⚠ Different seed blocks — never a significance claim. What it does say: **most of the win is the
endgame term**, and that matters for cost (see below).

## int16-wrap hazard — DISCHARGED for this exact arm
Re-measured on `wincombo`'s OWN board distribution (not the champion's): **880,678 real depth-2
leaves, range [-162, +7072], ZERO wraps, headroom 25,695** — slightly MORE than the champion's
25,577 on the same boards, because both new terms are NEGATIVE and the binding side is the positive
maximum. See [[dr-mario-int16-wrap-headroom]].

## ⚠⚠ THE REAL COST IS NOT ALMs — IT IS A PIPELINE STAGE
[[dr-mario-leaf-has-no-timing-budget]]: the shipped copro closes at **0.165 ns against a +0.10 ns
bar**, and placement-seed noise alone spans **0.076-0.380 ns**. `S_DONE2` is already a 10-term 16-bit
adder tree in ONE cycle and has been retimed once already. `wincombo` adds TWO terms (~1 more carry
level, ~0.3-0.6 ns) ⇒ **~5-9x the available headroom ⇒ it needs a THIRD pipeline stage**, which
costs a leaf cycle, which costs search throughput, which costs playing strength.
⇒ **Do not promote `wincombo` to silicon on the strength of this p-value alone.** Price the leaf
cycle first. And note the decomposition: `winend8_48` alone gives **+1.60 of the +2.20** with only
ONE added term — likely the better silicon trade.
⇒ And run 11 (`PREREG_SHAPE.md`) is testing whether pure RE-WEIGHTS, which cost **nothing** in
silicon, can reach the same place.

## Status
`wincombo` is the first candidate all session to clear a pre-registered bar. It is a **software
champion candidate**, not a ship decision. Owed next: the leaf-cycle price, and a fit on SEVERAL
placement seeds (one passing fit is an n=1 draw from a distribution wider than the margin).
