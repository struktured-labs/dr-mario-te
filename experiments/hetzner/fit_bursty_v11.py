#!/usr/bin/env python3
"""fit_bursty_v11.py -- fit bursty v1.1 ONCE (locally, where the footage lives)
and pickle the fitted model for the remote node.

WHY NOT FIT ON THE REMOTE. `BurstyPressureModel.fit_struktured_20260804()` reads
1fps JPEG frames and a `vision.py` calibrated against them -- gigabytes of media
that has no business on a compute node. Shipping the FITTED OBJECT instead is
both cheaper and better provenance: both nodes then provably use the same model
rather than two independent re-fits that are merely supposed to agree.

Pickle is the right format here even though the class has `to_json`: there is no
loader for that JSON (BURSTY_V1_RESULTS.md §5 says so), and `pressure_rig.run_arm`
already pickles this exact object to its worker processes via `initargs` -- so
pickling is a path the model is known to survive, not a new assumption.

`meta['raw_events']` is stripped before pickling: it is a heavy per-frame ledger
the sampler never reads (run_bursty_v1_1_validity.py strips it for the same
reason). The fit summary is printed and stored alongside so the remote can assert
it got the model it expected.

Usage: fit_bursty_v11.py --out bursty_v1_1.pkl
"""
from __future__ import annotations

import sys
import json
import pickle
import argparse

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (QA + "/eval47", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bursty_model as BM          # noqa: E402
import fit_ensemble_source as FE   # noqa: E402


def build_v1_1():
    m_v1 = BM.fit_struktured_20260804()
    raw = m_v1.meta["raw_events"]
    all_volleys, all_clears = [], []
    for _mid, res in raw.items():
        all_volleys.extend(res["volleys"])
        all_clears.extend(res["clears"])
    return FE.fit_per_player(all_volleys, all_clears, m_v1.n_matches, "P1",
                             dict(BM.DEFAULT_OPPONENT_OF))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="bursty_v1_1.pkl")
    a = ap.parse_args()

    m = build_v1_1()
    s = m.fit_summary()
    print(f"n_volleys={s['n_volleys']} n_clears={s['n_clears']} "
          f"volley_size_mean={s['volley_size_mean']:.3f} "
          f"gap_mean={s['inter_volley_gap_mean_s']:.2f}")
    print(f"p_by_clear_size={s['p_volley_within_k_by_clear_size']}")

    # v1.1 is the struktured-ONLY fit. v1 (the contaminated pool, ~half AI
    # copro) has 61 volleys / 188 clears. If those numbers show up here we are
    # about to ship the wrong pressure model.
    if int(s["n_volleys"]) != 28 or int(s["n_clears"]) != 89:
        sys.exit(f"REFUSING TO SHIP: expected v1.1 (28 volleys / 89 clears), got "
                 f"{s['n_volleys']} / {s['n_clears']} -- this looks like "
                 f"CONTAMINATED v1, not the human-only fit")

    if isinstance(getattr(m, "meta", None), dict):
        m.meta.pop("raw_events", None)     # heavy, unused by the sampler

    with open(a.out, "wb") as f:
        pickle.dump(m, f, protocol=4)
    with open(a.out + ".summary.json", "w") as f:
        json.dump(s, f, indent=2, default=str)
    print(f"wrote {a.out} (+ .summary.json)")


if __name__ == "__main__":
    main()
