#!/usr/bin/env python3
"""G-IDENTITY (blocking) — PREREG_H12_SUBSTITUTION.md §2.1.

PASS requires BOTH:
  1. H12ArmWithBoards produces action sequences BYTE-IDENTICAL to sealed H12Arm
     on every gate seed;
  2. the margin-gate-off MUTANT FAILS that same check on >=1 seed.
A gate that has only ever passed is not a gate. Exit 0 only if both hold.

Also times the instrumented arm so the smoke can re-derive the per-seed rate
(rule 39: wall-clock is a property of THIS box, not of the algorithm).
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed-lo", type=int, default=70000)
    ap.add_argument("--level", type=int, default=20)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--model", default="lulu")
    ap.add_argument("--skip-mutant", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "gate_identity.json"))
    a = ap.parse_args()

    import oracle_arm as OA
    from h12_arm import H12Arm
    from h12_boards import H12ArmWithBoards, H12ArmMutantNoMargin

    C, bmodel = OA.init_rig(model=a.model, level=a.level)
    seeds = [a.seed_lo + 2 * i for i in range(a.seeds)]

    same = mut_diff = n_flips = n_planes = 0
    t_ins = 0.0
    rows = []
    for s in seeds:
        ref = OA.play_one(s, H12Arm(provenance=True), C, bmodel, a.max_pills)
        t0 = time.time()
        arm = H12ArmWithBoards(provenance=True)
        ins = OA.play_one(s, arm, C, bmodel, a.max_pills)
        dt = time.time() - t0
        t_ins += dt
        ident = ref["_actions"] == ins["_actions"]
        same += ident
        nf = len(arm.flip_log)
        npl = sum(1 for r in arm.flip_log if r.get("planes"))
        n_flips += nf; n_planes += npl
        md = None
        if not a.skip_mutant:
            m = OA.play_one(s, H12ArmMutantNoMargin(provenance=True), C, bmodel, a.max_pills)
            md = m["_actions"] != ref["_actions"]
            mut_diff += bool(md)
        rows.append(dict(seed=s, plies=ins["n_plies"], res=ins["res"], identical=ident,
                         mutant_differs=md, flips=nf, planes=npl, secs=round(dt, 1)))
        print(f"  seed {s}: plies={ins['n_plies']:3d} res={ins['res']:7s} "
              f"identical={ident} mutant_differs={md} flips={nf:2d} planes={npl:2d} "
              f"{dt:6.1f}s", flush=True)

    ok_id = same == len(seeds)
    ok_mut = a.skip_mutant or mut_diff > 0
    print(f"\nG-IDENTITY  instrumented == sealed on {same}/{len(seeds)}  "
          f"{'PASS' if ok_id else 'FAIL'}")
    if not a.skip_mutant:
        print(f"G-MUTANT    margin-off differs on {mut_diff}/{len(seeds)}  "
              f"{'PASS (gate can fail)' if ok_mut else 'FAIL - GATE IS BLIND, ALL DOWNSTREAM VOID'}")
    print(f"\nflips {n_flips} ({n_flips/len(seeds):.2f}/game), planes on {n_planes}")
    print(f"RATE (instrumented arm only): {t_ins/len(seeds):.1f} core-s/seed  "
          f"=> {t_ins/len(seeds)*200/3600:.2f} core-h per 200 games")
    json.dump(dict(seeds=seeds, level=a.level, max_pills=a.max_pills, model=a.model,
                   identical=same, mutant_differs=mut_diff, flips=n_flips,
                   with_planes=n_planes, secs_per_seed=t_ins/len(seeds), rows=rows,
                   verdict="PASS" if (ok_id and ok_mut) else "FAIL"),
              open(a.out, "w"), indent=1)
    sys.exit(0 if (ok_id and ok_mut) else 1)


if __name__ == "__main__":
    main()
