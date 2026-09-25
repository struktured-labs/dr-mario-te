# PRE-REG (2026-09-25, before any STEER3 arm runs): does a HUMAN-RATE tap cap keep the tap-steering benefit?

**Owner fairness decision.** Tap-steering (a fresh press every P frames per column) vs DAS. P=2 is the interface
ceiling (30 Hz), P=4 is 15 Hz (about elite NES hypertapping), and P=6 would be DAS speed with no delay.

**Cells.** All use the new default brain (fw540 + reach root) with couch steering on
(`steer_model.Steer(proph="throat")`).
- Normal steering taps every P frames (`pulse=True, tap_period=P`), and DISTGATE is sized to the tap rate
  (2P hooks per column).
- The reach mask simulates the SAME P (`ReachAwareDecider(steer_kw={pulse, tap_period=P})`), so reachability
  matches the tap rate.
- The mask is the frame-sim (lenient) mask, as in the banked baseline.

Arms:
- **Baseline P=∞ (DAS):** CHAIN540 + reach, banked (STEER1 `reach`, survival; STEER2 `fw540_reach~steer`, race).
- **P = 2, 3, 4, 5:** survival gate (b), OWNER model, L11 MED, cap 600, n=600 paired seeds 36734.. step 2.
- **Race (if cheap):** vs_race lam 6, n=300 paired seeds 36734.. step 2, for P = 2 and P = 4, scored vs a 177-s
  human at δ 2.65 / 2.0.

**Endpoints.**
- tap≤100 and whole-game tap-out per P, paired vs the DAS + reach baseline, seed-bootstrap 95% CI.
- Race win, paired vs the baseline.
- **Benefit kept at P** = Δ(P)/Δ(P=2) on tap≤100 (the share of the 30 Hz gain a P-Hz cap keeps). Descriptive,
  for the owner; no pass/fail bar.

**G0 (done before any arm):** `tap_period=None` is unchanged.
- 4/4 vendored fingerprints.
- STEER1 couch md5 `ec5501cf`.
- STEER1 pulse and reach rows byte-identical.

**Declared.** P=2 here is period-based: the first press lands on the first steering frame. STEER1's arm-4 pulse was
parity-keyed. Same limits as STEER1/2.
