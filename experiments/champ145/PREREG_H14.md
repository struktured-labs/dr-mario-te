# PREREG_H14 — REGISTERED (2026-08-21, champion-145)

This registers PREREG_H14_DRAFT.md as amended by PREREG_H14_AMENDMENT1.md,
after team-lead sign-off with riders 1+2 (both carried verbatim in the
amendment). Timing proof for the commit message: out/endpoint/ contains ZERO
E1/E2 rows; the registered seed block 53100+ is untouched by any run.

## The registered H14a configuration (rule applied mechanically)

Final screen (n=1,500 games, 364,052 plies, out/screen_result.json,
ANALYZE_SCREEN_OK): tie_dedup_rate_of_all = 0.0257; theta_dose 0.0/0.5/1.0/
1.5/2.0 = 0.1877/0.1877/0.1932/0.1932/0.1986.

estimated_dose: eps 0.5 -> 2.57% | 1.0 -> 3.12% | 1.5 -> 3.12% | 2.0 -> 3.66%.
ALL are <= 4.0% and >= 2.0%  =>  **eps* = 2.0** (largest in window, per the
amendment's pre-stated rule; no discretion exercised).

H14a = H12Arm with topk=4, horizon=15, fork_samples=5, theta_margin=0.5,
future=dist, gate unchanged, **trigger_eps=2.0**. Control = the identical
arm at trigger_eps=0.0 (bit-identical to certified H12; G1 identity gate).

## Registered endpoint parameters (from the draft, finalized)

- Instrument: run_h14.py (sealed run_h12 lineage), level=20, max_pills=400,
  model=lulu (honest bursty), paired seeds, provenance ON.
- Primary: failure (topout|stall) rate, McNemar exact + seed-bootstrap CI.
  Champion-const lab baseline at these coordinates: **49.27%**
  (576 topout / 163 stall of 1,500). H12-arm baseline comes from the A/B's
  own control arm.
- N = 600 pairs = the first 600 eligible seeds of 53100-59999 minus the 20
  sileval seeds (list frozen in analyse_h14.py SILEVAL_EXCL). Interim look
  at 250 pairs is REPORT-ONLY. MDE: at base ~30-50% failure and discordance
  >= 0.20, ~6-8pp absolute at 80% power; the realized MDE is recomputed
  from realized discordance and stated in the verdict either way.
- Guard (L11 clear non-inferiority, margin -2.0pp; rider 1 promotion
  escalation at point estimate worse than -1.0pp): runs AFTER the primary,
  2,000 pairs, level=11 defaults, seeds = the NEXT 2,000 eligible of the
  same block (never pooled with primary).
- Verdict rule + VOID classes: analyse_h14.py (self-gated v1-v5), dose
  anchor on FULL-N flip RATES in [0.9,1.1] with registered auto-thinning
  re-run (keep = true_rate/mutant_rate, num/1000), mutant must not read GO.
- Chain: chain_endpoint.sh under systemd-run --user --unit
  drm-champ-endpoint, set -eo pipefail, marker-gated stages
  (G1 identity -> G2 not-inert -> E1 true -> E2 mutant [-> E2b thinned] ->
  verdict), per-seed atomic + resumable, runtime manifest frozen per outdir.

## Screen results archived with this registration

- lab_fail_rate 0.4927 | gate_open 0.5032 | tie_dedup_of_gated 0.0512 |
  strat: neardeath tie 0.0353 (107,896 plies), endgame tie 0.0708 (119,281).
- H14c flip screen (for the record; stays behind H14a): under the h12gate,
  dose 8 flips 1.85% (below the 2% floor), dose 16 flips 3.17%. Testable
  only at doses in the churn-wall zone; not funded this round.
