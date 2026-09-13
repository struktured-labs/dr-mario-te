# PRE-REG run 16 (2026-09-13, AT LAUNCH): holes80 vs holes80+maxh24 at L11. Owner hypothesis (4): "not defensive
enough for high columns". Evidence: run 11 maxh x2 alone: tap-out 11.0->9.0% (-18%), clear +1.5 (n.s.); toprisk x2 HURT;
convex height dead twice. Question: does maxh24 STACK on holes80? Baseline arm = winholes80 (the debut core), not the
old champion. L11 drip, cap 600, n=2000, DECLARED REUSE of streams 36734..40732 (consumed at L20; L11 = different games).
PRIMARY = paired tap-out, McNemar exact. p<0.05 and down => candidate for a free re-fit; else maxh stays 12.

## AMENDED AT LAUNCH (before any game): pressure model = BURSTY (owner fit), and a CALIBRATION arm added
Owner, tonight: "im still tapping it out, that should be nigh impossible for lvl 11 unless combo stomping is a
dominating strat." Offline L11 tap-out for holes80 = 1.0% under DRIP; couch tonight ~1-in-6. The gap IS the
pressure model. This run uses `bursty_model.fit_struktured_20260804()` — the burst model fit to the owner's own
sends — via worker3.py. Arms: `winner` (CALIBRATION: couch 5 tap-outs/11 games last night on this evaluator),
`winholes80` (couch ~1/6 tonight), `winholes80_maxh24` (hypothesis 4). If `winner` and `winholes80` land near
their couch rates, the rig is calibrated to the owner and every later result inherits that. PRIMARY unchanged:
paired tap-out, holes80 vs holes80+maxh24. Reactive-switch arm deliberately EXCLUDED: never tuned (all prior
uses reactive_k=0), so it would be a screen, not a test.
