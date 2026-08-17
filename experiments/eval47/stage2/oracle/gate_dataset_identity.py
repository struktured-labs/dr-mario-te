#!/usr/bin/env python3
"""GATE: tie-event logging is causally inert.

The distillation dataset is only worth anything if the arm that produced it is
THE arm that was certified.  So this gate does not compare summary outcomes —
it compares the FULL ACTION SEQUENCE, ply by ply, between the sealed `H12Arm`
and the logging derivative `H12ArmDataset` on the same seeds.

A CHECK THAT CANNOT FAIL IS NOT A CHECK.  Two mutants run on the SAME seeds
through the SAME comparator:

  M1  perturb_first_tie=True  — exactly one decision changed, at the first tie
      ply.  This is the minimal perturbation the instrument could possibly
      introduce, so it is the right thing to prove detectable.
  M2  order_flip=True         — the champion's tie-resolution order reversed.

M1 can only diverge on a seed that HAS a tie ply, so its denominator is
tie-bearing seeds only.  The gate also fails if zero ties were observed at all:
otherwise a run with no tie plies would "pass" while exercising nothing.

Exit 0 = PASS.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def _winit(model):
    import oracle_arm as O
    C, bmodel = O.init_rig(model)
    _W.update(O=O, C=C, bmodel=bmodel)


KW = dict(label_mode="true", topk=4, horizon=15, provenance=True,
          future_mode="dist", fork_samples=5, tie_margin=0.5)


def _play(seed, arm):
    r = _W["O"].play_one(seed, arm, _W["C"], _W["bmodel"])
    return r, r["_actions"]


def _work(seed):
    import h12_arm as H
    import h12_arm_dataset as D

    r_seal, a_seal = _play(seed, H.H12Arm(**KW))
    arm_ds = D.H12ArmDataset(**KW)
    r_ds, a_ds = _play(seed, arm_ds)
    n_ties = len(arm_ds.tie_log)

    identical = (a_seal == a_ds
                 and r_seal["res"] == r_ds["res"]
                 and r_seal["pills"] == r_ds["pills"]
                 and r_seal["dies_ahead"] == r_ds["dies_ahead"]
                 and r_seal["flips"] == r_ds["flips"]
                 and r_seal["forks"] == r_ds["forks"])
    first_diff = None
    for i, (x, y) in enumerate(zip(a_seal, a_ds)):
        if x != y:
            first_diff = [i, int(x), int(y)]
            break

    _, a_m1 = _play(seed, D.H12ArmDataset(perturb_first_tie=True, **KW))
    _, a_m2 = _play(seed, D.H12ArmDataset(order_flip=True, **KW))
    return {"seed": seed, "identical": bool(identical), "first_diff": first_diff,
            "n_ties": n_ties, "n_plies": len(a_seal), "res": r_seal["res"],
            "flips": r_seal["flips"],
            "m1_diverged": bool(a_m1 != a_seal),
            "m2_diverged": bool(a_m2 != a_seal)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed-start", type=int, default=61000)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--model", default="lulu")
    ap.add_argument("--out", default=os.path.join(
        HERE, "out", "gate_dataset_identity.json"))
    a = ap.parse_args()

    from concurrent.futures import ProcessPoolExecutor
    seeds = list(range(a.seed_start, a.seed_start + a.seeds))
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_winit,
                             initargs=(a.model,)) as ex:
        for r in ex.map(_work, seeds):
            rows.append(r)
            print(f"  seed {r['seed']}: identical={r['identical']} "
                  f"ties={r['n_ties']} plies={r['n_plies']} "
                  f"flips={r['flips']} M1_div={r['m1_diverged']} "
                  f"M2_div={r['m2_diverged']}", flush=True)

    ok = True
    for r in rows:
        if not r["identical"]:
            ok = False
            print(f"FAIL seed {r['seed']}: first divergent ply "
                  f"{r['first_diff']}")
    ties_total = sum(r["n_ties"] for r in rows)
    m1_elig = sum(1 for r in rows if r["n_ties"] > 0)
    m1_div = sum(1 for r in rows if r["n_ties"] > 0 and r["m1_diverged"])
    m2_div = sum(1 for r in rows if r["m2_diverged"])
    if ties_total == 0:
        ok = False
        print("FAIL: zero tie plies observed — the gate exercised nothing")
    if m1_elig == 0 or m1_div <= m1_elig // 2:
        ok = False
        print(f"FAIL: M1 (perturb) diverged on only {m1_div}/{m1_elig} "
              f"tie-bearing seeds — the comparator cannot detect a change")
    if m2_div <= len(rows) // 2:
        ok = False
        print(f"FAIL: M2 (order_flip) diverged on only {m2_div}/{len(rows)}")

    doc = {"seeds": a.seeds, "seed_start": a.seed_start, "pass": bool(ok),
           "ties_total": ties_total, "m1_diverged": m1_div,
           "m1_eligible": m1_elig, "m2_diverged": m2_div,
           "n_seeds": len(rows), "rows": rows}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(doc, open(a.out, "w"), indent=1)
    print(f"\nidentical={sum(r['identical'] for r in rows)}/{len(rows)}  "
          f"ties_total={ties_total}  M1 {m1_div}/{m1_elig}  "
          f"M2 {m2_div}/{len(rows)}")
    print("GATE", "PASS" if ok else "FAIL", "->", a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
