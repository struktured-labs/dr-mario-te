#!/usr/bin/env python3
"""GATE 1 - THE OFF-IDENTITY GATE, IN BOTH DIRECTIONS.

This project has shipped a "fix" that was vacuously inert.  An identity gate
that only checks "OFF == champion" cannot distinguish a correctly-wired arm from
an arm that is never consulted.  So this gate has four parts and the last three
exist purely to make the first one capable of failing.

  G1a OFF-IDENTITY   Delta tables zeroed -> the arm must reproduce
                     pressure_rig.play() / p0_ab.play_one(forced=False)
                     EXACTLY: same per-ply action sequence, same res, pills,
                     garbage, dies_ahead.  Both pressure models.
  G1b MUTANT: TIE-BREAK FLIP.  Same zero Delta, but the argmax scans the
                     champion's enumeration order REVERSED.  This changes
                     nothing except how ties are resolved - 36% of decisions.
                     It MUST break G1a.  If it does not, G1a is not sensitive
                     to the decision path and is worthless.
  G1c MUTANT: SIGN-FLIPPED / SHUFFLED tables.  Must break G1a.
  G1d LIVENESS.      The real term ON must differ from the champion on >= 1
                     seed and must record flips > 0.  An arm that is inert is
                     not testable and the rollout would be a null by
                     construction.
  G1e PRUNE EXACTNESS.  The exact-bound pruning (skip candidates that cannot
                     win under any Delta) must give a byte-identical action
                     sequence to scoring every candidate.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import arm_lut as AL  # noqa: E402

OUT = os.path.join(HERE, "out")
SEEDS = [2, 3, 4, 5, 6, 7, 20000, 20001, 20002, 20003, 20004, 20005]


def _init(model):
    import pressure_rig as PR
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                    "jointdig"))
    import p0_ab as P
    obj = P.load_lulu() if model == "lulu" else None
    PR._init(11, 0, 20, model_kind=("bursty" if model == "lulu" else "drip"),
             bursty_model_obj=obj)
    return PR, P


def ref_row(PR, P, seed):
    """The champion, via the two independent existing entry points."""
    a = PR.play(seed)
    b = P.play_one(seed, forced=False)
    for k in ("seed", "won", "topout", "pills"):
        assert a[k] == b[k], ("rig disagreement", seed, k, a[k], b[k])
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    a = ap.parse_args()
    seeds = SEEDS[:a.seeds]
    lut = AL.load_recommended()
    res = {"model": lut.name, "seeds": seeds, "per_model": {}}
    ok_all = True

    for model in ("lulu", "drip"):
        PR, P = _init(model)
        rep = {}

        # ---------------- G1a OFF-identity -------------------------------
        off = 0
        mism = []
        for s in seeds:
            ref = ref_row(PR, P, s)
            arm = AL.Arm(lut=lut.zeroed(), prune=False)
            got = AL.play_one(s, arm)
            same = all(ref[k] == got[k] for k in
                       ("seed", "res", "won", "topout", "pills", "garbage",
                        "dies_ahead"))
            if same:
                off += 1
            else:
                mism.append({"seed": s, "ref": {k: ref[k] for k in ref},
                             "got": {k: got[k] for k in got if k != "_actions"}})
            assert arm.stats["flips"] == 0, "zero Delta produced a flip"
        rep["G1a_off_identity_pass"] = off
        rep["G1a_n"] = len(seeds)
        rep["G1a_mismatches"] = mism
        rep["G1a"] = bool(off == len(seeds))

        # G1a-strict: identical PER-PLY ACTION sequence vs a champion replay
        # (outcome equality alone could hide a compensating divergence).
        champ_arm = AL.Arm(lut=None)
        act_same = 0
        for s in seeds:
            ca = AL.Arm(lut=None)
            r0 = AL.play_one(s, ca)
            oa = AL.Arm(lut=lut.zeroed(), prune=False)
            r1 = AL.play_one(s, oa)
            if r0["_actions"] == r1["_actions"]:
                act_same += 1
        rep["G1a_action_sequence_identical"] = act_same
        rep["G1a_strict"] = bool(act_same == len(seeds))

        # ---------------- G1b tie-break-flip mutant ----------------------
        diff = 0
        for s in seeds:
            arm = AL.Arm(lut=lut.zeroed(), prune=False, tiebreak_flip=True)
            got = AL.play_one(s, arm)
            ref = ref_row(PR, P, s)
            if any(ref[k] != got[k] for k in ("res", "pills", "garbage")):
                diff += 1
        rep["G1b_tiebreak_mutant_differs_on"] = diff
        rep["G1b"] = bool(diff >= 1)

        # ---------------- G1c sign-flip / shuffle mutants ----------------
        for tag, m in (("signflip", lut.sign_flipped()),
                       ("shuftable", lut.shuffled_tables())):
            d = 0
            for s in seeds:
                arm = AL.Arm(lut=m, prune=False)
                got = AL.play_one(s, arm)
                ref = ref_row(PR, P, s)
                if any(ref[k] != got[k] for k in ("res", "pills", "garbage")):
                    d += 1
            rep[f"G1c_{tag}_differs_on"] = d
        rep["G1c"] = bool(rep["G1c_signflip_differs_on"] >= 1
                          and rep["G1c_shuftable_differs_on"] >= 1)

        # ---------------- G1d liveness -----------------------------------
        live, tot_flips, tot_plies = 0, 0, 0
        for s in seeds:
            arm = AL.Arm(lut=lut, prune=True)
            got = AL.play_one(s, arm)
            ref = ref_row(PR, P, s)
            tot_flips += arm.stats["flips"]
            tot_plies += arm.stats["plies"]
            if any(ref[k] != got[k] for k in ("res", "pills", "garbage")):
                live += 1
        rep["G1d_treatment_differs_on"] = live
        rep["G1d_flips"] = tot_flips
        rep["G1d_plies"] = tot_plies
        rep["G1d_flip_rate"] = tot_flips / max(1, tot_plies)
        rep["G1d"] = bool(live >= 1 and tot_flips > 0)

        # ---------------- G1e prune exactness ----------------------------
        same = 0
        for s in seeds:
            a1 = AL.Arm(lut=lut, prune=True)
            a2 = AL.Arm(lut=lut, prune=False)
            r1 = AL.play_one(s, a1)
            r2 = AL.play_one(s, a2)
            if r1["_actions"] == r2["_actions"]:
                same += 1
        rep["G1e_prune_exact_on"] = same
        rep["G1e"] = bool(same == len(seeds))

        rep["pass"] = all(rep[k] for k in
                          ("G1a", "G1a_strict", "G1b", "G1c", "G1d", "G1e"))
        ok_all = ok_all and rep["pass"]
        res["per_model"][model] = rep
        print(f"[{model}] G1a OFF-identity {rep['G1a_off_identity_pass']}/"
              f"{len(seeds)} (action-seq {act_same}/{len(seeds)})  "
              f"G1b tiebreak-mutant differs {rep['G1b_tiebreak_mutant_differs_on']}  "
              f"G1c signflip {rep['G1c_signflip_differs_on']} shuffle "
              f"{rep['G1c_shuftable_differs_on']}  "
              f"G1d live {rep['G1d_treatment_differs_on']} flips {tot_flips}/"
              f"{tot_plies} ({rep['G1d_flip_rate']*100:.2f}%)  "
              f"G1e prune-exact {same}/{len(seeds)}  -> "
              f"{'PASS' if rep['pass'] else 'FAIL'}", flush=True)

    res["pass"] = bool(ok_all)
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "gate1_identity.json"), "w"),
              indent=1, default=str)
    print(f"GATE 1: {'PASS' if ok_all else 'FAIL'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
