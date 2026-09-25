# RESULT (2026-09-25): STEER3 — a human-rate tap cap (15 Hz) keeps ~3/4 of the tap-steering benefit

Pre-reg: `PREREG_STEER3.md` (committed `717a377` before any arm ran). Brain: fw540 + reach root (mask simulates the
same P). Couch steering on. Paired seed-bootstrap 95% CIs vs the current build (DAS + reach).
- Survival: gate (b), OWNER model, L11 MED, n=600.
- Race: vs_race lam 6, n=300, vs a 177-s human.

| steering | tap≤100 | Δ vs DAS | whole-game tap-out | Δ vs DAS | VS win δ2.65 | Δ vs DAS |
|---|---|---|---|---|---|---|
| DAS (P=∞): current CHAIN540 + REACH | 9.83% | — | 45.50% | — | 45.7% | — |
| P=2 (30 Hz, interface ceiling) | 6.33% | −3.50 [−5.83, −1.33] | 25.50% | −20.00 [−24.33, −16.00] | 75.7% | +30.0 [+24.0, +36.3] |
| P=3 (20 Hz) | 6.33% | −3.50 [−5.83, −1.33] | 28.33% | −17.17 [−21.17, −13.17] | — | — |
| **P=4 (15 Hz, elite hypertap)** | 7.00% | −2.83 [−5.17, −0.67] | 30.33% | **−15.17 [−19.17, −11.33]** | 67.7% | **+22.0 [+16.0, +28.0]** |
| P=5 (12 Hz) | 7.17% | −2.67 [−5.17, −0.33] | 31.00% | −14.50 [−18.50, −10.50] | — | — |

Share of the P=2 gain kept at P=4 (15 Hz): about 76–81% on tap-outs, 73% on race wins.

| endpoint | P=3 | P=4 | P=5 |
|---|---|---|---|
| tap≤100 | 100% | 81% | 76% |
| whole-game tap-out | 86% | 76% | 72% |
| VS race | — | 73% | — |

**Reading.**
- With the reach root on, early deaths are already low (9.8%), so tapping trims them only modestly (−3 pp at any
  P).
- The big effect is on long-game survival and race wins, and it degrades gently with the cap. Even 12 Hz (P=5)
  keeps −14.5 pp tap-out.
- The P=2/3 vs P=4/5 steps are within one CI of each other.
- Every P is significantly better than DAS on every endpoint.

**Declared.**
- P=2 here is period-based (the first press lands on the first steering frame), not STEER1's parity pulse.
- The DISTGATE budget scales with P.
- The race numbers are a stress read, as in STEER2: the race model's human never tops out.

Files: `steer_model.Steer(tap_period=P)`, `ReachAwareDecider(steer_kw=…)`, the `tap{P}_reach` arms,
`steer_race.py` TAP arg, `analyze_steer3.py`, and rows in `steer3/`.
