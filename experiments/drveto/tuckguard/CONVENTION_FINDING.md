# The case-002 "disagreement" is a ROW-CONVENTION mismatch in the CHECKER, not a cart defect

Recomputed by the team lead from `pred_tg1v2.log`'s own logged boards, after proph-cvc's session
died (API safeguard error) mid-investigation.

Both logged cases: `approach=2 final=3 trow_board=1 need=3`, cart **VETOED** both.

| case | col-3 cells (top->bottom) | TOP-relative | FLOOR-relative | cart |
|---|---|---|---|---|
| 001 | 60 FF FF FF D0 D1 D1 FF D0 D2 FF D1 D1 D0 D0 D1 | have=2 -> VETO | have=0 -> VETO | VETOED |
| 002 | 61 FF FF FF FF D0 D1 D1 D0 D0 FF D1 D1 D2 D2 D0 | have=3 -> **ALLOW** | have=0 -> VETO | **VETOED** |

**Case 002 is DISCRIMINATING**: the two conventions predict opposite verdicts, and the cart matches
**FLOOR-relative**. Under floor-relative the cart agrees on both cases; only the top-relative reading
manufactures a disagreement.

This matches the emitted code directly: `LDA #15 / SEC / SBC W_TROW / STA TUCK_R2` — `TUCK_R2` is
**floor-relative** because `$0386` counts UP from the bottle floor. It is the same convention trap
that made the FIRST DISTGATE fail vacuously (hence the `DRDIST_FLOORREL` killed mutant).

⇒ **No defect in the shipped 6502 is demonstrated.** The apparent one was ours.
⚠ **n = 1 discriminating case**, and both logged cases share the same
`approach/final/trow` configuration — so this is one distinct geometry observed twice. The direction
is clear and it agrees with the code reading, but it is not yet a correctness verdict.
⇒ **Next**: log the cart's OWN `W_TROW` / `TUCK_R2` / `TG_OFF` so the convention is confirmed from the
cart rather than inferred, and raise the case count with varied geometries.
