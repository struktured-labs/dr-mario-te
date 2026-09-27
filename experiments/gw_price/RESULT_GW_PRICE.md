# GW increment pricing — RESULT: VOID (registered routing), with two structural findings

**2026-08-20.** Prereg `PREREG_GW_PRICE.md` (commit `859bcf9`, amendment `3fa911d`), both
pushed before their data existed. Precondition GO banked at `b3b264a` (flip rate 30.45 %
on de-dup'd ties, fresh block 52100–53099). Farm: 96 RTL games (fw s20b `e970e9ab`),
30.8 core-h; total lane spend ≈ 38 core-h — inside the ~40 core-h ($4-equivalent) budget.
$0 cash, all local.

## Verdict (the registered §6 router, unedited)

**VOID — "only 8 triggered seeds (<10)"** — and independently the ordering control is
not green on the registered metric. No salvage read is taken from any other column.

## Adjudication of the exact-zero table (team-lead directive)

- **Reader mutant KILLED** (`out/reader_mutant.txt`): a synthetic farm file with 2
  edited `viruses_cleared`/`won` rows moves d_vc to −1.75 CI (−4.38, 0.00) and d_won to
  −0.25 through the identical reader. The real zeros are DATA, not a constant-field bug.
- **The zeros are outcome saturation**: all 96 RTL games — every arm, every seed —
  ended `clear` with `viruses_cleared == start_viruses == 48`. On the registered
  outcome metrics (Δviruses_cleared, Δwon, Δdies_ahead) every paired delta is exactly 0
  by construction, so the worst/rand arms are pinned at 0 and the ordering gate
  (worst < rand < 0) is **structurally unsatisfiable in this regime**, not merely
  underpowered at this n.
- **Δpills** IS a registered secondary metric (§5), but the ordering control was
  registered on Δviruses_cleared only. The pills column (worst −49.25, deepen −15.5,
  rand +8.25; note NEGATIVE = fewer pills = faster) is not the predicted harm ordering
  in any orientation, is n≤8, and is dominated by one seed (52125: base ground 262
  pills; every perturbed arm finished in 133–283). Reported as exploratory,
  no verdict weight.
- **Mirror-mismatch routing** (question asked): per §4 a mismatch fires NO intervention
  in any arm — all arms play the identical RTL move at that ply — so the 6 events
  (6/113 = 5.3 % of tie plies, under the 10 % VOID bar) contaminate no arm's rows. The
  two affected seeds (52125, 52162) took their interventions at other plies (74, 107).

## Structural finding 1 — the farm's pressure regime cannot price this increment

Under bursty v1.1 (the honest human-only fit) at L11, the RTL champion cleared **96/96**
games. `value(move | granted)` on H12's registered endpoint (clear rate) is identically
zero in an instrument whose baseline never fails, at ANY n — so spending more seeds
cannot rescue this design, which is why no extension run was bought. The farm README's
own line ("a clean arm can only measure speed, never survival") turns out to apply to
the v1.1 bursty arm for the champion. Prior topout rates (POWER.txt 39 %/16.7 %) came
from harder/contaminated pressure fits and do not transfer.

## Structural finding 2 — mirror-vs-RTL fidelity is GAME-level, not move-level

Same harness, same seeds, same pressure; only the decider differs:

| decider | clear | topout | stall |
|---|---|---|---|
| champion MIRROR (prescreen, n=1000) | 81.0 % | 12.4 % | 6.6 % |
| — on the 32 N1 fire-seeds | 22/32 | 4/32 | 6/32 |
| **real RTL** (farm, n=96 incl. those seeds) | **96/96** | 0 | 0 |

The 100 %/50-board mid-game transfer result does not hold at game scope: per-move
divergence compounds (rep0-vs-RTL mismatch 5.3 % at flip plies), the mirror's games fork
away from the RTL's, and trigger yield realized 8/32 vs the mirror-predicted 32/32
(RTL fire rate 0.250/game on enriched seeds ≈ the unenriched mirror rate 0.293 —
enrichment washed out entirely). Corroborates [[dr-mario-cosim-farm]] "fidelity is
regime-dependent"; any future lane that pre-selects seeds by mirror play should expect
~no enrichment.

## MDE statement (registered §5)

Measured: dose 0.293 fires/game (mirror) / 0.250 (RTL, enriched); P(3.0×C ≤ W(h)) at
the observed trigger heights ≈ 0.78 (Pocket; MiSTer ≈ 1.0); d_won/trigger = 0 (saturated).
Projected full-N endpoint effect = **0.0 pp** vs MDE 0.84 pp. To fund the full A/B the
increment would need ≥ 3.7 pp clear-rate per trigger — impossible against a ~100 %-clear
baseline. **Recommendation: NO-GO on funding the full GW A/B from this evidence.** The
honest paths, if the owner wants the increment kept alive, are a re-registration in a
pressure regime where the champion actually fails (tier-3 adversary garbage channel, VS
pressure, or higher virus loads) — a NEW experiment, not an extension of this one — or
closing the lane on the converging evidence (this VOID + the ~4.5× tie-value-overstates-
outcome finding) that tie plies carry little outcome consequence.

## Process defect, disclosed

The chained unit's gate step crashed at import (`oracle_arm` imported before
`_boot_oracle()`), and `set -e` without `pipefail` let `tee` mask it — the farm ran
UNGATED at 09:26. Fixed (`gate_gw_price.py` import order; `chain_gw_farm.sh`
`set -eo pipefail`) and the full killed-mutant suite was run post-hoc on the unchanged
instrument (`out/gate_result.txt`); the timing violation of §7 ("gates before any real
farm row is read") is real and disclosed — the gates validate the instrument, and the
reader mutant above independently validates the one reading the verdict relied on.
