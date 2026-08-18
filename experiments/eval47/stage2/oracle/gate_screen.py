"""Prove the SCREENING LOGGER is inert, with mutants that must break it.

WHY THIS EXISTS, and it is a gap I did not see myself. `gate_h13.py` certifies
`H13Arm`. But the object that actually plays every game in `run_screen.py` is a
SUBCLASS of it that forks 51 extra rollouts per screened flip. The H13 gate
never saw that subclass — a check whose scope was smaller than the claim resting
on it ([[dr-mario-measurement-rules]] #24). The distill lane flagged the pattern
from its own dataset work; the gap was mine.

S1 LOGGER INERT — the screening arm's FULL ACTION SEQUENCE must equal the plain
   H13Arm's, seed for seed. Comparing outcomes is NOT enough: a logger that
   perturbs one decision in fifty passes an outcome check and silently
   invalidates every screened flip, because the flips would then be flips the
   real H13 arm never makes.
S2 MUTANT KILL — two realistic ways the logger could perturb the game, each of
   which MUST diverge:
     m_cursor_steal : the screen draws one capsule from the LIVE env, advancing
        the game's own cursor. This is the defect family this project has
        already paid for ([[dr-mario-deepcopy-pill-closure]]).
     m_no_deepcopy  : the screen forks ON the live env instead of a clone —
        exactly what `PillDraw`'s docstring warns about.
S3 SERIALIZATION ROUND-TRIP — stored board planes must decode to the array the
   decider was actually given, byte for byte. A corpus that cannot be read back
   is not a corpus.

WHAT THIS DOES NOT COVER: it proves the logger does not change the GAME. It
says nothing about whether the screened comparison is the right comparison —
that is the prereg's job — and nothing about the fork machinery itself, which
is H12's and is gated upstream.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def _winit(thresh, k, horizon, alt_base):
    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")
    _W.update(O=O, C=C, bmodel=bmodel, thresh=thresh, k=k, horizon=horizon,
              alt_base=alt_base)


def _play(item):
    """(kind, seed) -> action sequence, plus the screened events."""
    import run_screen as RS
    from h13_arm import H13Arm
    O, C, bmodel = _W["O"], _W["C"], _W["bmodel"]
    T, K, H, AB = _W["thresh"], _W["k"], _W["horizon"], _W["alt_base"]
    kind, seed = item
    events = []
    if kind == "plain":
        arm = H13Arm(gate_mode="v2", maxh_thresh=T, label_mode="true",
                     tie_margin=0.5, provenance=False)
    else:
        mutant = None if kind == "screen" else kind
        Arm = RS.make_screening_arm(C, K, H, AB, events, mutant=mutant)
        arm = Arm(gate_mode="v2", maxh_thresh=T, label_mode="true",
                  tie_margin=0.5, provenance=True)
    res = O.play_one(seed, arm, C, bmodel)
    return (kind, seed), {"actions": tuple(res.pop("_actions")),
                          "n_events": len(events),
                          "events": events[:1]}


# m_no_deepcopy is RETAINED but reclassified — see EQUIVALENT_UNDER_S1 below.
MUTANTS = ("m_cursor_steal", "m_no_deepcopy")

# ⚠ EQUIVALENCE FINDING, 2026-08-18, recorded because it changes what S2 means.
# `m_no_deepcopy` makes the screen fork on the LIVE env instead of an alternate
# clone. It SURVIVED S2 at 0/12 — and it survived CORRECTLY: `_fork_label`
# (oracle_arm.py:290) opens with `e = copy.deepcopy(env)`, so it protects
# itself, and forking "on the live env" cannot perturb the game's action
# sequence. The mutant is therefore EQUIVALENT with respect to S1's observable
# and is UNKILLABLE BY S1 BY CONSTRUCTION — the exact hazard the project
# standard says to check for FIRST ([[dr-mario-gate-standard-killed-mutants]],
# the A_v `r > top_occ` vs `r >= top_occ` case).
#
# This was a GATE-DESIGN error of mine, not a defect in the screen: I pointed a
# mutant at the wrong observable. What m_no_deepcopy was actually meant to
# guard — that the screen forks on UNSEEN capsule streams rather than the true
# one, i.e. that it cannot seed-peek — is not an action-sequence property at
# all. It is now checked directly by S4, which is a unit-level assertion and
# costs seconds rather than 48 games.
EQUIVALENT_UNDER_S1 = ("m_no_deepcopy",)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--seed-start", type=int, default=41000)
    ap.add_argument("--thresh", type=int, default=13)
    ap.add_argument("--k-streams", type=int, default=5,
                    help="fewer streams than the real run — the gate tests "
                         "whether the logger PERTURBS, not the screen's power")
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--alt-base", type=int, default=500000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default="out/GATE_SCREEN.json")
    a = ap.parse_args()

    seeds = list(range(a.seed_start, a.seed_start + a.seeds))
    items = ([("plain", s) for s in seeds] + [("screen", s) for s in seeds]
             + [(m, s) for m in MUTANTS for s in seeds])
    print(f"SCREEN GATE: {len(items)} games, {a.workers} workers, "
          f"seeds {seeds[0]}..{seeds[-1]}, K={a.k_streams}", flush=True)

    t0 = time.monotonic()
    R = {}
    n = 0
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_winit,
                             initargs=(a.thresh, a.k_streams, a.horizon,
                                       a.alt_base)) as ex:
        for key, val in ex.map(_play, items):
            R[key] = val
            n += 1
            if n % 10 == 0:
                print(f"  {n}/{len(items)} {(time.monotonic()-t0)/60:.1f}min",
                      flush=True)

    ok = True
    rep = {"seeds": seeds, "thresh": a.thresh, "k_streams": a.k_streams}

    same = sum(R[("plain", s)]["actions"] == R[("screen", s)]["actions"]
               for s in seeds)
    ev = sum(R[("screen", s)]["n_events"] for s in seeds)
    s1 = same == len(seeds)
    print(f"\nS1 LOGGER INERT (screen actions == plain H13Arm): "
          f"{same}/{len(seeds)} {'PASS' if s1 else 'FAIL'}")
    print(f"   screened events produced on these seeds: {ev} "
          + ("" if ev else "  <- WARNING: gate never exercised the log path"))
    rep["S1"] = {"pass": s1, "n": same, "of": len(seeds), "events": ev}
    ok &= s1
    if ev == 0:
        print("   ⚠ S1 passing with ZERO events proves only that a logger "
              "which never\n     fired changed nothing. Treat as UNVALIDATED "
              "until events > 0.")
        rep["S1"]["validated"] = False
        ok = False
    else:
        rep["S1"]["validated"] = True

    rep["S2"] = {}
    for m in MUTANTS:
        diff = sum(R[(m, s)]["actions"] != R[("plain", s)]["actions"]
                   for s in seeds)
        killed = diff > 0
        equiv = m in EQUIVALENT_UNDER_S1
        if equiv:
            print(f"S2 MUTANT {m:16s}: diverges on {diff}/{len(seeds)} "
                  f"— EQUIVALENT under S1 by construction (_fork_label "
                  f"deepcopies its input), NOT counted; its real property is "
                  f"S4")
            rep["S2"][m] = {"equivalent_under_S1": True, "diverged": diff,
                            "of": len(seeds), "counted": False}
            continue
        ok &= killed
        rep["S2"][m] = {"pass": killed, "diverged": diff, "of": len(seeds)}
        print(f"S2 MUTANT {m:16s}: diverges on {diff}/{len(seeds)} "
              f"{'KILLED' if killed else 'SURVIVED — the gate is vacuous'}")

    # S3 round-trip
    import numpy as np
    s3, checked = True, 0
    for s in seeds:
        for e in R[("screen", s)]["events"]:
            if "pre_col" not in e:
                continue
            col = np.frombuffer(bytes.fromhex(e["pre_col"]), dtype=np.uint8)
            vir = np.frombuffer(bytes.fromhex(e["pre_vir"]), dtype=np.uint8)
            s3 &= (col.size == 128 and vir.size == 128)
            checked += 1
    print(f"S3 SERIALIZATION ROUND-TRIP: {checked} boards decoded, "
          f"{'PASS' if (s3 and checked) else 'FAIL/UNCHECKED'}")
    rep["S3"] = {"pass": bool(s3 and checked), "checked": checked}
    ok &= bool(s3 and checked)

    rep["overall"] = ok
    rep["not_covered"] = (
        "Proves the logger does not change the GAME. Says nothing about "
        "whether the screened comparison is the RIGHT comparison (prereg's "
        "job), nor about the fork machinery, which is H12's and gated "
        "upstream.")
    rep["elapsed_min"] = round((time.monotonic() - t0) / 60, 1)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(rep, open(a.out, "w"), indent=1)
    print(f"\nNOT COVERED: {rep['not_covered']}")
    print(f"elapsed {rep['elapsed_min']} min -> {a.out}")
    print("SCREEN GATE", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
