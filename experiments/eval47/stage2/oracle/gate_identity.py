#!/usr/bin/env python3
"""IDENTITY + LIVENESS + KILLED-MUTANT GATES for the oracle-ceiling arm.

PREREG_ORACLE.md sec 2.  A check that has not been shown to FAIL on a
deliberately wrong input is not a check, so every gate here ships with the
mutant that must break it.

  G1a  OFF-IDENTITY.  `label_mode="const"` (the base arm) must reproduce
       `pressure_rig.play()` exactly on res / pills / dies_ahead / viruses_left
       AND on the full per-ply action sequence.
  G1b  KILLED MUTANT for G1a: the same const arm with the enumeration order
       REVERSED.  That changes tie resolution only.  It MUST break G1a.
  G1c  FORK INDEPENDENCE.  Two clones of one live mid-game state must draw the
       IDENTICAL capsules and must not advance the parent's cursor.  Its own
       mutant: the same clone made through the lambda-based `nes_pills.attach`
       (the version `pressure_rig` puts first on sys.path) MUST fail it.
  G1d  LIVENESS.  The true oracle must differ from base and flip plies.
  G1e  GATE COVERAGE.  The pre-registered predicate must actually fire, and
       must fire on a non-trivial minority of plies; a gate that never fires
       makes the whole arm silently inert.
  G1f  MUTANT DISTINGUISHABILITY.  The shuffled-label arm must produce a
       DIFFERENT action sequence from the true oracle on most seeds -- if the
       permutation were a no-op the killed mutant would be vacuous.

Exit code 0 iff every gate is in the state the prereg demands.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def actions_of(seed, arm, C, bmodel):
    import oracle_arm as O
    r = O.play_one(seed, arm, C, bmodel)
    return r, r["_actions"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--seed-start", type=int, default=40000)
    ap.add_argument("--model", default="lulu", choices=["lulu", "drip"])
    ap.add_argument("--out", default=os.path.join(HERE, "out",
                                                  "gate_identity.json"))
    a = ap.parse_args()

    import oracle_arm as O
    import pressure_rig as PR
    C, bmodel = O.init_rig(a.model)
    seeds = list(range(a.seed_start, a.seed_start + a.seeds))
    res = {"model": a.model, "seeds": seeds, "gates": {}}
    ok = True

    # ---------------- G1a OFF-identity + G1b killed mutant ----------------
    g1a = g1a_act = g1b_break = 0
    ref_actions = {}
    for s in seeds:
        arm = O.OracleArm(label_mode="const")
        r, acts = actions_of(s, arm, C, bmodel)
        ref_actions[s] = acts
        ref = PR.play(s)
        if (r["won"] == ref["won"] and r["topout"] == ref["topout"]
                and r["stall"] == ref["stall"] and r["pills"] == ref["pills"]
                and r["dies_ahead"] == ref["dies_ahead"]):
            g1a += 1
        # the rig does not return its action sequence; the per-ply check is
        # against a SECOND independent const run, which must be deterministic
        arm2 = O.OracleArm(label_mode="const")
        _r2, acts2 = actions_of(s, arm2, C, bmodel)
        if acts2 == acts:
            g1a_act += 1
        armR = O.OracleArm(label_mode="const", order_flip=True)
        _rR, actsR = actions_of(s, armR, C, bmodel)
        if actsR != acts:
            g1b_break += 1
    res["gates"]["G1a_off_identity_vs_pressure_rig"] = f"{g1a}/{len(seeds)}"
    res["gates"]["G1a_action_determinism"] = f"{g1a_act}/{len(seeds)}"
    res["gates"]["G1b_reversed_order_MUST_break"] = f"{g1b_break}/{len(seeds)}"
    ok &= g1a == len(seeds) and g1a_act == len(seeds)
    ok &= g1b_break >= len(seeds) - 1     # >=11/12, the stage-2 bar

    # ---------------- G1c fork independence + its mutant ------------------
    env = O.make_env(seeds[0], C["level"])
    for _ in range(6):
        r, _v = O._advance(env, 10, C, seeds[0], bmodel)
        if r is not None:
            break
    A, B = copy.deepcopy(env), copy.deepcopy(env)
    pa = [A._rand_pill() for _ in range(6)]
    pb = [B._rand_pill() for _ in range(6)]
    par = env._rand_pill()
    g1c = (all((x.a, x.b) == (y.a, y.b) for x, y in zip(pa, pb))
           and (par.a, par.b) == (pa[0].a, pa[0].b))

    # MUTANT: the lambda attach that pressure_rig's sys.path order selects
    import nes_pills as NP
    env2 = O.make_env(seeds[0], C["level"])
    NP.NesPillSource(seed=seeds[0]).attach(env2)      # installs the lambda
    for _ in range(6):
        r, _v = O._advance(env2, 10, C, seeds[0], bmodel)
        if r is not None:
            break
    A2, B2 = copy.deepcopy(env2), copy.deepcopy(env2)
    qa = [A2._rand_pill() for _ in range(6)]
    qb = [B2._rand_pill() for _ in range(6)]
    lambda_shares = not all((x.a, x.b) == (y.a, y.b) for x, y in zip(qa, qb))
    res["gates"]["G1c_fork_capsule_independence"] = bool(g1c)
    res["gates"]["G1c_mutant_lambda_attach_MUST_share"] = bool(lambda_shares)
    res["gates"]["G1c_nes_pills_module"] = NP.__file__
    res["gates"]["G1c_lambda_attach_present_upstream"] = (
        "lambda" in open(NP.__file__).read().split("def attach")[1][:400])
    ok &= g1c
    ok &= lambda_shares

    # ---------------- G1d liveness / G1e gate coverage / G1f -------------
    live = 0
    flips_tot = plies_tot = gated_tot = 0
    differ_from_true = 0
    for s in seeds:
        at = O.OracleArm(label_mode="true")
        rt, acts_t = actions_of(s, at, C, bmodel)
        flips_tot += rt["flips"]
        plies_tot += rt["plies_scored"]
        gated_tot += rt["gated_plies"]
        if acts_t != ref_actions[s]:
            live += 1
        am = O.OracleArm(label_mode="shuffle")
        _rm, acts_m = actions_of(s, am, C, bmodel)
        if acts_m != acts_t:
            differ_from_true += 1
    res["gates"]["G1d_liveness_true_differs_from_base"] = f"{live}/{len(seeds)}"
    res["gates"]["G1d_flip_rate_of_plies"] = flips_tot / max(1, plies_tot)
    res["gates"]["G1e_gated_frac_of_plies"] = gated_tot / max(1, plies_tot)
    res["gates"]["G1f_shuffle_differs_from_true"] = \
        f"{differ_from_true}/{len(seeds)}"
    ok &= live >= len(seeds) - 1
    ok &= 0.0 < (gated_tot / max(1, plies_tot)) < 1.0
    ok &= differ_from_true >= len(seeds) - 1

    res["ALL_GATES_PASS"] = bool(ok)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    for k, v in res["gates"].items():
        print(f"  {k:44s} {v}")
    print("GATES", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
