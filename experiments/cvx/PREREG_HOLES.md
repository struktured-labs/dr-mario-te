# PRE-REGISTRATION — `winw_holes_40` confirmation + dose probe. AT LAUNCH 2026-09-11.

## Why this run exists, stated honestly
Run 12's PRIMARY (`winshape` = HOLES 20->40 **and** POLL 6->12) **landed**: +2.50pp, 95% CI
[+0.8,+4.2], p=0.0055, n=2000. Under `PREREG_WINSHAPE.md` that makes `winshape` a genuine candidate.
**But its pre-specified decomposition arm did BETTER:** `winw_holes_40` (the holes change ALONE)
scored **+3.40pp, CI [+1.6,+5.2], p=0.000179**, topout 8.95% -> 5.55%.
⇒ The POLL half is a DRAG, not a contributor.

⚠ `PREREG_WINSHAPE.md` explicitly said the decomposition arm is "NOT a champion claim on its own",
and picking it now is selecting on outcome WITHIN that run. **So it does not inherit run 12's
p-value.** This run exists to give it its own clean test on FRESH seeds. Run 12's +3.40pp is NOT
the estimate; this run is.

## Arms
- champion `variant("winner")`.
- **`winw_holes_40`** = champion + `R_HOLES 20 -> 40`. **PRIMARY.**
- `winholes80` = champion + `R_HOLES 20 -> 80`. Pre-specified DOSE probe: run 11's gradient was
  monotone (10 -> -4.00, 20 -> 0, 40 -> +4.25), so the optimum may lie past x2. NOT a champion claim.

## ★ Both arms are FREE in silicon — verified, not assumed
`20 = 10100b`, `40 = 101000b`, `80 = 1010000b` — **all popcount 2**, so the RTL shift-add multiplier
costs exactly what ships today. No new term, no extra carry level, **no third pipeline stage**.
(`60 = 111100b` is popcount 4 and would cost more, which is why the ladder skips it.)
This is the decisive advantage over `wincombo` (+2.20pp), which adds TWO terms to a combine with
~0.065 ns of headroom and therefore owes a leaf cycle ([[dr-mario-leaf-has-no-timing-budget]]).

## Design
CRN-paired, L20 drip, **cap 600**. n = **1518** fresh streams across five registered blocks
(26280..26958, 60348..60998, 51468..52098, 15464..15998, 65000..65534), all `--check` PASS, all
disjoint from the ~7,300 streams consumed by runs 01-12. n=1518 detects ~2.8pp; the effect under
test is ~+3.4pp. The seed space is fragmenting, which is itself a reason not to over-run this.

## PRIMARY / SECONDARY
PRIMARY: paired clear-rate, `winw_holes_40` vs champion, McNemar exact two-sided.
SECONDARY: topout% split (the mechanism endpoint), stall%, and whether `winholes80` beats
`winw_holes_40` (dose direction only).

## Decision rule, fixed now
- `p < 0.05` positive => `winw_holes_40` is a genuine, **zero-silicon-cost** champion candidate:
  ONE constant doubled. Then re-measure int16 on real leaves and it is a ship conversation.
- `p >= 0.05` => not confirmed; run 12's +3.40pp was selection-on-outcome and is withdrawn.
- `winholes80` cannot become the champion off this run either — if it wins it needs its own test.

## Pre-committed
- int16: raising a NEGATIVE weight moves the binding POSITIVE maximum DOWN => safer, but re-measure.
- Score against the CHAMPION, never a target. Solitaire L20 lane on CPU; no silicon claim.
