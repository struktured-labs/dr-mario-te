# Garbage-window compute — first increment spec (draft, gated on #126)

**Preconditions from #126 (this branch):** the hook budget is already spent —
the v6e prestart release-edge frame bounds at 27,960/29,780 host cycles and the
TCVC P1-search frame overruns outright. Therefore the first GW increment adds
**ZERO host-hook cycles**: all new computation is copro firmware, triggered by
mailbox state the driver already writes. This was also the gw-design
conclusion (host hook length unchanged; capability byte at init); #126 turns
it from a preference into a hard constraint.

## What computation runs in the window

The tie-only 2-candidate 1-ply deepening from the gw-design budget table
(`dr-mario-garbage-window-budget`): after DRPRESTART's release-edge GO (the
projected post-garbage board is already uploaded by the existing driver path),
the copro:

1. runs the normal depth-3 search on the projected board (existing behaviour,
   the prestart already buys this);
2. de-duplicates the top-2 candidates BY RESULTING BOARD (the 87%-degenerate
   double-capsule trap; pairing is adjacent variants 0↔1 / 2↔3, NEVER (v,v+2));
3. iff a genuine top-2 tie survives de-dup: deepens both candidates by one ply
   and re-ranks. Budget: base + deepening = 3.0×C fits 52.4% of releases at
   median cost (h-keyed; MiSTer 1.57× roomier).

No new driver bytes; one firmware capability byte read at init (θ-style core
artifact discipline, `dr-mario-theta-is-core-not-cart`).

## How results merge with the pre-drop plan

They don't merge — they REPLACE, atomically. The copro publishes (col, orient)
through the existing DONE/result mailbox contract; the driver's anytime path
already re-reads the live target every hook. Seqlock/atomicity: publish via
the existing single-byte orient sentinel (0xFF = not ready) — the pair-latch
defect is avoided because col is written before orient flips from 0xFF, and
the driver treats orient==0xFF as "hold". Plan-protection interaction
(`dr-mario-plan-protection`): the deepened result is a strict re-rank of the
same top-2, so it can only swap within the tie — no plan-abandonment pathway.
Pre-emption (second volley mid-window): existing PRE_ACT2 teardown abandons
whole; the firmware sees a fresh GO which resets the search. Unchanged.

## A/B endpoint + MDE (before any launch — label-budget rules)

- **Endpoint**: registered H12 endpoint (clear rate at FULL N with flip-rate
  anchors), NOT vibes; per `dr-mario-h12-endpoint-verdict`. Population:
  post-garbage plies with a surviving de-dup'd top-2 tie ≈ 0.48% of plies
  (~4× smaller than H12's 1.98% dose — POWER IS THE RISK, not budget).
- **Ordering control first** (the S0-B lesson): worst-legal < random < 0 on
  OUR population in OUR instrument before any verdict; no imported magnitude.
- **Argmax-flip precondition**: measure the deepening's flip rate on the tie
  population first (`dr-mario-spawn-lane-gate-probe`: <2% = untestable, stop).
- **MDE**: with dose ~0.48% of plies, a whole-game clear-rate MDE at H12's
  n=9,000-game scale is not plausible; the affordable design is the co-sim
  farm's conditional pricing (`effect = P(completes|h) × value(move|granted)`,
  common-mode prestart bias cancels, ~$4) stratified by h, THEN a full-N
  silicon A/B only if the conditional value is positive with the ordering
  control green.
- **Operating-point table, not AUC** (`dr-mario-auc-operating-point-law`).

## Explicitly deferred

- Any h≥14 story (needs a FASTER search, not more window — prestart shadow
  data: overruns 25-100% at h=13-16).
- Any host-side deadline computation (adds hook cycles; revisit only after
  the #126 enforcement lands and re-opens budget).
