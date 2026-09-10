# PRE-REGISTRATION — COMBINED endgame + spawn-lane arm vs CHAMPION
Registered 2026-09-10 AT LAUNCH, before any game of this run. Seeds registered in the same commit.

## Why a COMBINED arm rather than another single validation
Two leads survive screening, and they attack **different** failure paths:
- `winsc2` — spawn-lane clutter. Measured at **+1.12pp (n=800, p=0.47)** in run 06. Null at that
  size, but the pre-specified secondaries were all directionally consistent (topout 8.75->7.25%).
- `winend8_48` — late height. Screened at **+4.00pp (n=400, p=0.0166)** in run 09, the first arm to
  clear the pre-set +2.9pp max-of-5 inflation bar. Expected TRUE effect after the curse: **~+1.1pp**.

Validating either ALONE at n=800 has power to detect ~3.5pp and would therefore reproduce an
**uninterpretable null** — the exact trap run 06 fell into. Resolving a true +1.1pp alone needs
~7,900 seeds. If the two are real and roughly independent the combination is **~+2.2pp**, which
**n=2000 can resolve** (needed n ~1,984). That is the cheapest question that can actually be answered.

⚠ **A COMBINATION NEEDS ITS OWN CERTIFICATE** ([[dr-mario-combo-pairing-hazard]]). A positive result
here licenses `wincombo` and NOTHING ELSE — it does not retroactively license `winsc2` or
`winend8_48` as individual champions, and additivity is the assumption being TESTED, not used.

## Arms
- champion = `variant("winner")`.
- **`wincombo`** = winner + `R_SPAWNCOL=2` + `R_ENDK=8, R_ENDH=48`. **PRIMARY.**
- `winend8_48` = winner + the endgame term alone. Pre-specified decomposition arm: it says how much
  of any combined effect is the endgame half. NOT a champion claim on its own.

## Design
CRN-paired; identical seed => identical virus layout, pill stream and garbage. L20 drip, wt=0 ws=20,
**max_pills=600** (the fair cap; 300 censors 5.5pp of the clear label and 400 still censors 1.0pp).

## Seeds — n = 2000, two registered blocks, both FRESH
`63000..64998 step 2` (1000 streams, keys 31500..32499) and `27960..29958 step 2` (1000 streams,
keys 13980..14979). Both `--check` PASS. Disjoint from all 2,500 streams consumed by runs 01-09.
Registered in `tools/seed_registry.py` AT LAUNCH, not post-hoc.

## PRIMARY endpoint
Paired clear-rate difference, `wincombo` vs champion, **McNemar exact two-sided**. Powered for +2.2pp.
## SECONDARY (pre-specified)
topout% split; `winend8_48` vs champion; and the ADDITIVITY check —
`d(wincombo) - d(winend8_48)` versus the +1.12pp `winsc2` measured in run 06 on its own block
(⚠ cross-block, so directional only, never a significance claim).

## Decision rule, fixed now
- `p < 0.05` and positive => `wincombo` is a genuine champion candidate. Report effect + CI. It then
  owes an ALM-cost check; the int16-wrap hazard is already discharged for both terms
  ([[dr-mario-int16-wrap-headroom]] — both are NEGATIVE terms, which move the binding max DOWN).
- `p >= 0.05` => not a champion. Report the null with its CI. **This closes the whole
  endgame+spawn-lane family**, because a properly powered test of the best available combination
  came back empty. No re-slicing, no re-screening on this data.
- direction negative => report as harm, and the additivity assumption is refuted.

## Pre-committed
- Screen figures are max-of-N. `+4.00pp` is NOT the estimate and will not be quoted as one.
- Absolute clear% is not comparable across seed blocks; only the paired difference within this run is.
- This is the solitaire L20 lane on CPU. No live silicon exists; nothing here is a silicon or couch claim.
