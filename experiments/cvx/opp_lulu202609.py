"""dr. lulu opponent (STEER6 / OPP suite): her sends AS RECEIVED by ANTIBODY on the couch
(experiments/couch_forensics/lulu_fit_202609.json, RESULT_COUCH_LULU.md `d36dd4ad`; PROVISIONAL, n = 2 games).

Same form as OWNER-2026-09 (`opp_owner202609.Owner202609`): an independent renewal process of volleys in AI
placements (2.08 s per placement, the couch conversion), gaps resampled from her 59 measured inter-volley gaps,
size pmf {2: .783, 3: .033, 4: .167}, merged-double p .016. Her column split is not fitted, so the owner's is
reused. Her aggressive opening (first 30 s: 6 volleys/min, mean size 3.3) is NOT modelled: gate (b) delivers no
garbage before placement 25 (~52 s) on any profile.
"""
from __future__ import annotations
import json, os
from opp_owner202609 import Owner202609, S_PER_PLACEMENT

FIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "couch_forensics", "lulu_fit_202609.json")


class Lulu202609(Owner202609):
    name = "lulu202609"

    def __init__(self, fit_path=FIT):
        d = json.load(open(fit_path))
        self.gaps = [g / S_PER_PLACEMENT for g in d["inter_volley_gap_s"]["samples"]]
        pmf = {int(k): v for k, v in d["size_pmf"].items() if k.isdigit()}
        tot = sum(pmf.values())
        self.sizes = sorted(pmf); self.cum = []
        acc = 0.0
        for s in self.sizes:
            acc += pmf[s] / tot; self.cum.append(acc)
        self.p_double = float(d["p_merged_double"])
        self.reset(0)

    def reset(self, seed):
        import random
        self.rng = random.Random(seed * 7727 + 99147)       # own stream, independent of OWNER-2026-09's
        self.next_at = None
        self.nvol = 0; self.cells = 0


def make():
    return Lulu202609()
