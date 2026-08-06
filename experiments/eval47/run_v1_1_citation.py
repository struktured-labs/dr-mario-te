#!/usr/bin/env python3
"""ITERATION 5 (task #60 follow-on, team-lead): citation-grade numbers under
the corrected bursty v1.1 pressure model. BURSTY_V1_RESULTS.md section 5
found v1 was pool-contaminated -- roughly half its 61 volleys were the AI
copro's own sending events, not struktured's, which pulled the fit toward
faster/more-reliable attack behavior than an honest human-only fit supports.
v1.1 (struktured-only separated stream, n=28 volleys) is now the source of
truth for ABSOLUTE rates; the paired tier CURVE from Iteration 4 is
unaffected (the same model applies to both sides of every paired arm, so
contamination cancels in a same-model comparison) but the silicon manifest
must cite v1.1's honest absolute numbers, not v1's superseded ones (control
dies-ahead 13.3%->7.5% per that section's own validity rerun).

Reuses run_bursty_v1_1_validity.py's build_v1_1() -- the documented single
source of truth for "what v1.1 is" (rebuilt in-process from bursty_model.
fit_struktured_20260804()'s live raw_events + fit_ensemble_source.
fit_per_player(), not a saved-JSON copy). bursty_model.py itself is NOT
imported directly here and NOT edited (reactive-mode owns it); the v1.1
model object comes from run_bursty_v1_1_validity.py's own reconstruction,
imported and called, not re-derived.

Arms: base32 / tier<=3 (translatable.tier_of, the task #67 knee) /
reachfull2 (the oracle) -- n=120 paired, same seeds, under bursty v1.1.
Three comparisons: tier<=3 vs base32 (the headline), reachfull2 vs base32
(context/ceiling), tier<=3 vs reachfull2 (does the tier-3==oracle
equivalence found under v1 still hold under v1.1 -- confirmed, not assumed).
"""
from __future__ import annotations
import sys
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reach_root_ab as AB
import run_tier_sweep as RTS
import run_bursty_v1_1_validity as V11

SEEDS = 120
WORKERS = 6
LEVEL = 11
TIER = 3   # the task #67 knee


def main():
    v1_1 = V11.build_v1_1()
    s = v1_1.fit_summary()
    print(f"=== bursty v1.1: n_volleys={s['n_volleys']} n_clears={s['n_clears']} "
          f"volley_size_mean={s['volley_size_mean']:.3f} "
          f"gap_mean={s['inter_volley_gap_mean_s']:.2f} "
          f"p_within_k={s['p_volley_within_k_by_clear_size']} ===", flush=True)
    # strip raw_events before pickling into worker processes -- same
    # convention reach_root_ab.py's own main() uses for the v1 object, and
    # run_bursty_v1_1_validity.py doesn't need since it only runs pressure_
    # rig.py's own arms; reach_root_ab.py's play() doesn't touch raw_events
    # either but stripping keeps worker IPC payloads small either way.
    if hasattr(v1_1, "meta") and "raw_events" in v1_1.meta:
        v1_1.meta = {k: v for k, v in v1_1.meta.items() if k != "raw_events"}

    print(f"=== ITERATION 5 citation gate, L{LEVEL}, n={SEEDS}, pressure=bursty v1.1, "
          f"arms=[base32, tier<={TIER}, reachfull2(oracle)] ===", flush=True)

    base32 = AB.run_arm(LEVEL, SEEDS, WORKERS, "base32", "bursty", v1_1)
    reachfull2 = AB.run_arm(LEVEL, SEEDS, WORKERS, "reachfull2", "bursty", v1_1)
    tier3 = RTS.run_tier_arm(LEVEL, SEEDS, WORKERS, TIER, "bursty", v1_1)

    print()
    s_tier_vs_base = AB.compare(base32, tier3, f"tier<={TIER} vs base32     (v1.1)")
    s_tier_vs_oracle = AB.compare(reachfull2, tier3, f"tier<={TIER} vs reachfull2(v1.1)")
    s_oracle_vs_base = AB.compare(base32, reachfull2, "reachfull2 vs base32  (v1.1, context)")

    n = SEEDS
    base_bad, base_da = s_tier_vs_base["bad_ends0"], s_tier_vs_base["dies_ahead0"]
    tier_bad, tier_da = s_tier_vs_base["bad_ends1"], s_tier_vs_base["dies_ahead1"]
    oracle_bad, oracle_da = s_oracle_vs_base["bad_ends1"], s_oracle_vs_base["dies_ahead1"]

    citation = (f"Under honest human cadence (bursty v1.1), tier-3 cuts bad-ends "
               f"{base_bad}/{n} ({base_bad/n:.1%}) -> {tier_bad}/{n} ({tier_bad/n:.1%}), "
               f"dies-ahead {base_da/n:.1%} -> {tier_da/n:.1%}.")
    print(f"\nCITATION LINE:\n{citation}")

    tier_eq_oracle = (s_tier_vs_oracle["bad_ends0"] == s_tier_vs_oracle["bad_ends1"]
                      and s_tier_vs_oracle["dies_ahead0"] == s_tier_vs_oracle["dies_ahead1"]
                      and s_tier_vs_oracle["mcnemar_disc"] == 0)
    print(f"tier<={TIER} == reachfull2 oracle under v1.1: "
          f"{'CONFIRMED' if tier_eq_oracle else 'DOES NOT HOLD -- see numbers above'} "
          f"(bad_ends {s_tier_vs_oracle['bad_ends0']} vs {s_tier_vs_oracle['bad_ends1']}, "
          f"mcnemar disc={s_tier_vs_oracle['mcnemar_disc']})")

    out = {"v1_1_fit_summary": s, "tier": TIER,
           "tier_vs_base32": s_tier_vs_base,
           "tier_vs_reachfull2": s_tier_vs_oracle,
           "reachfull2_vs_base32": s_oracle_vs_base,
           "citation_line": citation, "tier_eq_oracle": tier_eq_oracle,
           "raw": {"base32": [base32[x] for x in sorted(base32)],
                   "tier3": [tier3[x] for x in sorted(tier3)],
                   "reachfull2": [reachfull2[x] for x in sorted(reachfull2)]}}
    out_path = f"{HERE}/results/v1_1_citation_n120.json"
    with open(out_path, "w") as fh:
        json.dump(out, fh)
    print(f"\nwrote {out_path}")
    print("\nDONE")


if __name__ == "__main__":
    main()
