"""H13 pre-launch gates. Project standard: a gate must be shown to FAIL on
wrong inputs, not merely to pass on right ones
([[dr-mario-gate-standard-killed-mutants]]).

G0 EXTRACTION NO-OP  — H12Arm with the new `_gate` hook must reproduce the
   SEALED h12_arm.py (a pristine `git show 2b96cd3` copy) ACTION-SEQUENCE
   IDENTICALLY. This is the refactor's own gate, and it shares no code with the
   refactor because the sealed module is loaded separately by path.
G1 V1 IDENTITY       — H13Arm(gate_mode='v1') reproduces sealed H12
   action-for-action. This is the "gate-v2 off reproduces the sealed arm"
   claim, at the action-sequence standard the distill lane used.
G2 NOT INERT         — gate-v2 must measurably BIND: it must open on plies
   gate-v1 leaves closed, on real boards. An inert widening passes every
   equality test trivially and would price as free (rule 26).
G3 MUTANT KILL       — four deliberately wrong gates must each DIVERGE from
   gate-v2 in action sequence. Each mutant's PREDICATE is first shown to differ
   from gate-v2's on real plies, so a survivor is a real failure rather than an
   unkillable equivalent mutant.
G4 DETERMINISM       — same seed twice => identical result dict.

WHAT THESE GATES DO NOT COVER (rule 24 — the gap travels with the number):
they exercise the GATE PREDICATE and the action sequence it produces. They say
nothing about whether gate-v2's extra triggers IMPROVE play — that is the
endpoint's job — and nothing about the shuffled-null thinning, which is
inherited unchanged from H12.

An H12-class game is ~226 core-seconds, so this runs on a process pool; serial
it is a multi-hour job.
"""
import argparse
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def _load_sealed():
    path = os.path.join(HERE, "h12_arm_sealed.py")
    spec = importlib.util.spec_from_file_location("h12_arm_sealed", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["h12_arm_sealed"] = mod
    spec.loader.exec_module(mod)
    return mod.H12Arm


def _winit(thresh):
    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")
    _W.update(O=O, C=C, bmodel=bmodel, thresh=thresh, Sealed=_load_sealed())


def _play(item):
    """One work item -> (key, action tuple). `kind` selects the arm."""
    kind, seed = item
    O, C, bmodel, T = _W["O"], _W["C"], _W["bmodel"], _W["thresh"]
    from h12_arm import H12Arm
    from h13_arm import H13Arm, GateCensusArm

    if kind == "sealed":
        arm = _W["Sealed"](label_mode="true", tie_margin=0.5, provenance=False)
    elif kind == "hook":
        arm = H12Arm(label_mode="true", tie_margin=0.5, provenance=False)
    elif kind == "census":
        arm = GateCensusArm(thresholds=(T - 4, T, T + 4))
    else:                                   # a gate_mode name
        arm = H13Arm(gate_mode=kind, maxh_thresh=T, label_mode="true",
                     tie_margin=0.5, provenance=False)
    res = O.play_one(seed, arm, C, bmodel)
    acts = tuple(res.pop("_actions"))
    if kind == "census":
        return (kind, seed), {"rows": arm.rows}
    return (kind, seed), {"actions": acts, "res": res}


MUTANTS = ("m_inverted", "m_offby4_low", "m_offby4_high", "m_always")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20,
                    help="seeds for the G0/G1 identity gates")
    ap.add_argument("--mutant-seeds", type=int, default=6)
    ap.add_argument("--seed-start", type=int, default=41000)
    ap.add_argument("--thresh", type=int, default=13)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out", default="out/GATE_H13.json")
    a = ap.parse_args()

    seeds = list(range(a.seed_start, a.seed_start + a.seeds))
    mseeds = seeds[:a.mutant_seeds]
    items = ([("sealed", s) for s in seeds]
             + [("hook", s) for s in seeds]
             + [("v1", s) for s in seeds]
             + [("census", s) for s in mseeds]
             + [("v2", s) for s in mseeds]
             + [(m, s) for m in MUTANTS for s in mseeds])
    print(f"H13 GATES: {len(items)} games, {a.workers} workers, T={a.thresh}, "
          f"identity seeds {seeds[0]}..{seeds[-1]}, mutant seeds "
          f"{mseeds[0]}..{mseeds[-1]}", flush=True)

    t0 = time.monotonic()
    R = {}
    done = 0
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_winit,
                             initargs=(a.thresh,)) as ex:
        for key, val in ex.map(_play, items):
            R[key] = val
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{len(items)} "
                      f"{(time.monotonic()-t0)/60:.1f}min", flush=True)

    ok = True
    rep = {"thresh": a.thresh, "seeds": seeds, "mutant_seeds": mseeds}

    # ---- G0 / G1
    n0 = sum(R[("sealed", s)]["actions"] == R[("hook", s)]["actions"]
             for s in seeds)
    n1 = sum(R[("sealed", s)]["actions"] == R[("v1", s)]["actions"]
             for s in seeds)
    g0, g1 = n0 == len(seeds), n1 == len(seeds)
    print(f"\nG0 EXTRACTION NO-OP (hook == sealed h12, actions): "
          f"{n0}/{len(seeds)} {'PASS' if g0 else 'FAIL'}")
    print(f"G1 V1 IDENTITY (gate_mode=v1 == sealed h12, actions): "
          f"{n1}/{len(seeds)} {'PASS' if g1 else 'FAIL'}")
    rep["G0"] = {"pass": g0, "n": n0, "of": len(seeds)}
    rep["G1"] = {"pass": g1, "n": n1, "of": len(seeds)}
    ok &= g0 and g1

    # ---- G2 not inert, from the fork-free census
    rows = [r for s in mseeds for r in R[("census", s)]["rows"]]
    n = len(rows)
    T = a.thresh
    v1_on = sum(r["gate_v1"] for r in rows)
    v2_on = sum(r[f"gate_v2_t{T}"] for r in rows)
    extra = v2_on - v1_on
    g2 = n > 0 and extra > 0
    print(f"G2 NOT INERT: {n} plies | gate-v1 {v1_on} ({100*v1_on/n:.1f}%) | "
          f"gate-v2@T={T} {v2_on} ({100*v2_on/n:.1f}%) | v2-only {extra} "
          f"({100*extra/n:.1f}% of plies) {'PASS' if g2 else 'FAIL — inert'}")
    rep["G2"] = {"pass": g2, "plies": n, "v1_on": v1_on, "v2_on": v2_on,
                 "v2_only": extra}
    ok &= g2

    # ---- equivalence pre-check on the mutant PREDICATES
    def pred(mode, r):
        v1 = bool(r["gate_v1"])
        base = v1 or r["maxh"] >= T
        return {"v2": base, "m_inverted": not base,
                "m_offby4_low": v1 or r["maxh"] >= T - 4,
                "m_offby4_high": v1 or r["maxh"] >= T + 4,
                "m_always": True}[mode]

    print("  equivalence pre-check (mutant predicate differs from v2):")
    equiv = {}
    for m in MUTANTS:
        d = sum(pred(m, r) != pred("v2", r) for r in rows)
        equiv[m] = d
        ok &= d > 0
        print(f"    {m:16s} differs on {d:5d}/{n} plies"
              + ("" if d else "   <- EQUIVALENT, UNKILLABLE"))
    rep["equivalence_precheck"] = equiv

    # ---- G3 mutant kill, on action sequences
    g3 = True
    rep["G3"] = {}
    for m in MUTANTS:
        diff = sum(R[(m, s)]["actions"] != R[("v2", s)]["actions"]
                   for s in mseeds)
        killed = diff > 0
        g3 &= killed
        rep["G3"][m] = {"pass": killed, "diverged": diff, "of": len(mseeds)}
        print(f"G3 MUTANT {m:16s}: diverges on {diff}/{len(mseeds)} seeds "
              f"{'KILLED' if killed else 'SURVIVED — cases are vacuous'}")
    ok &= g3

    # ---- G4 determinism (v2 twice on one seed, in-process)
    _winit(a.thresh)
    _, d1 = _play(("v2", mseeds[0]))
    _, d2 = _play(("v2", mseeds[0]))
    g4 = d1 == d2
    print(f"G4 DETERMINISM: {'PASS' if g4 else 'FAIL'}")
    rep["G4"] = {"pass": g4}
    ok &= g4

    rep["overall"] = ok
    rep["elapsed_min"] = round((time.monotonic() - t0) / 60, 1)
    rep["not_covered"] = (
        "Exercises the gate predicate and the action sequence it produces. "
        "Says NOTHING about whether gate-v2's extra triggers improve play "
        "(endpoint's job), and nothing about the shuffled-null thinning, "
        "inherited unchanged from H12.")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(rep, open(a.out, "w"), indent=1)
    print(f"\nNOT COVERED: {rep['not_covered']}")
    print(f"elapsed {rep['elapsed_min']:.1f} min -> {a.out}")
    print("H13 GATES", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
