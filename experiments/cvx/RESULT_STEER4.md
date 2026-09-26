# RESULT (2026-09-26): STEER4 — no board-shape lever passes under the real regime; the k61 mask fix HURTS

Pre-reg: `PREREG_STEER4.md` (committed `0bed528` before any arm ran).
- **Baseline:** the shipping couch build in sim. fw540 + the `reach_fw_tap(tap=2)` mask, with unified DRTAPP=2 steering
  (`Steer(tap_unified=True)`, consistent with the mask on 100% of candidates for pill < 300).
- **Instrument:** gate (b), OWNER model, L11 MED, n=600 paired seeds 36734.. step 2. Seed-bootstrap 95% CIs vs baseline.
- **Pass bar:** one primary CI entirely below 0 AND the other primary's upper CI ≤ +1 pp.

| arm | lever (firmware-only?) | tap≤100 | Δ tap≤100 | tap-out | Δ tap-out | win | verdict |
|---|---|---|---|---|---|---|---|
| base | shipping REACH+TAP | 6.17% | — | 26.33% | — | 73.7% | — |
| (1a) sv180 | spawn-col virus priority +180/virus (YES: LEV_RVV + LIVE) | 4.17% | −2.00 [−4.50, +0.50] | 24.50% | −1.83 [−6.83, +2.83] | 75.5% | fail |
| (1b) sv540 | same, +540/virus (YES) | 5.33% | −0.83 [−3.33, +1.67] | 29.67% | +3.33 [−1.67, +8.17] | 70.3% | fail |
| (2a) sp100 | spawn-lane height, ungated, 100/row > 10 (YES: LEV_RVC + LIVE) | 7.00% | +0.83 [−1.67, +3.33] | 30.17% | +3.83 [−0.83, +8.50] | 69.8% | fail |
| (2b) sp300 | same, 300/row | 11.50% | **+5.33 [+2.33, +8.33]** | 36.33% | **+10.00 [+5.00, +15.00]** | 63.7% | **fail: HARMS** |
| (3) rot2 | mask +2 f rotation conservatism, the k61 fix (YES: mask constant) | 6.50% | +0.33 [−0.50, +1.17] | 29.00% | **+2.67 [+0.83, +4.67]** | 71.0% | **fail: HARMS** |
| (4) combo | sv180 + rot2 (by the pre-registered rule) | 4.50% | −1.67 [−4.33, +0.83] | 25.17% | −1.17 [−6.00, +3.67] | 74.8% | fail |

No arm passes, so there is no VS-race secondary and no holdout.

**Reading.**
- **The k61 fix is a net loss.** +2 rotation frames masks enough extra candidates that the brain builds worse
  boards: off-target placements 0.84 → 0.77%, but PROPH firings 3.38 → 3.75% and tap-out +2.7 pp. The one
  rotation/gravity miss seen on silicon is rarer than the cost of avoiding it. **Keep the shipping mask
  constants.**
- **The spawn-lane height penalty (the ungated sb_spawn term) is harmful, and dose-dependent.** At 300/row, tap-out
  is +10 pp, PROPH firing goes to 4.70%, and the median death comes at pill 138 vs 175. Firmware-realisable, it
  can only see the placement when nothing clears. That steers the brain away from non-clearing spawn-lane moves,
  but not toward digging, the same "height is a symptom" lesson as maxh24/toprisk. **Closed.**
- **Spawn-column virus priority** is the only direction with negative point estimates, and only at the low dose
  (sv180: −2.0 tap≤100, −1.8 tap-out). It doesn't clear the bar, and the ×3 dose reverses on tap-out. Possibly a
  small real effect below this screen's resolution (n=600 resolves ~±2.5 pp on tap≤100 at a 6% base rate). It is
  not a build candidate.
- **The baseline itself:** under REACH+TAP, execution is nearly faithful in sim. The driver overrides the brain on
  just 0.84% of placements, so what remains is the brain's board shape. Cheap root-term shaping doesn't move it.
  The couch forensics point the same way. The remaining lever is the evaluator/search (burial and virus
  accessibility inside the leaf), not a root add-on.

**Declared.**
- Reused seeds (the block shared with STEER1–3).
- Arms (1)/(2) are FIRMWARE PROXIES. The exact versions (region virus counts and child spawn height after clears)
  need an RTL read-back of the resolved child and were not tested.
- The race human never tops out.

**Files:**
- Model: `steer_model.Steer(tap_unified=…)`, `reach_fw_tap.reach_mask_fw(rot_margin=…)`, `cascade_shape_x.py`.
- Validation and runners: `reach_fw_tap_validate.py`, `steer_run.py` arms `s4_*`, `vs_race.py` arms `s4_*`
  (prepared, not run), `analyze_steer4.py`.
- Rows: `steer4/{local,remote}/`.
