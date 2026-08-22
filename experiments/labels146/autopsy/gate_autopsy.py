#!/usr/bin/env python3
"""gate_autopsy.py — the kills that must land BEFORE any autopsy label is read.

  G1  trace-anchored replay, bit-exact on known census failures (§1)
  G2  M-STALE — the same replay with one action swapped MUST abort (liveness)
  G3  G-FORK-INDEP — deepcopy cursor independence, both directions (A1.3)
  G4  G-DOSE-LIVE + M-INERT — the corrected dose must vary, the ORIGINAL
      registered dose must be flat (proves the vacuity, not asserts it)
  G5  determinism — labeling one state twice is byte-identical

Prints GATES_OK only if every one passes.  Exit nonzero otherwise.
"""
import copy
import hashlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autopsycore as AC   # noqa: E402

OUT = os.path.join(HERE, "out")
# Known census failures, both in the NODE's half — their record hashes are what
# out/gate_provenance.json matched against the census-era gate.
GATE_SEEDS = [33269, 33754]


def census_row(seed):
    """Regenerate one census row with the census's own code path."""
    import adversary_harness as AH
    r = AH.play_seed(seed)
    return {"seed": seed, "result": r["result"], "pills": r["pills"],
            "viruses_left": r["viruses_left"], "dies_ahead": r["dies_ahead"],
            "n_moves": len(r["trace"]),
            "trace": [[int(i), int(a)] for i, a in r["trace"]]}


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    import adversary_harness as AH
    AH._lazy()
    C, _bmodel = AC.init_rig()
    report = {}
    rows = {}

    # ---------------------------------------------------------------- G1
    for seed in GATE_SEEDS:
        row = census_row(seed)
        rows[seed] = row
        n = 0
        gen = AC.replay_census_game(seed, C, row)
        try:
            while True:
                next(gen)
                n += 1
        except StopIteration:
            pass
        assert n == row["n_moves"], (seed, n, row["n_moves"])
        print(f"  G1 seed {seed:6d} {row['result']:6s} {row['n_moves']:3d} plies "
              f"vl={row['viruses_left']} — trace + terminal gate PASS", flush=True)
    report["G1"] = {"seeds": GATE_SEEDS, "pass": True}

    # ---------------------------------------------------------------- G2
    kills = []
    for seed in GATE_SEEDS:
        row = rows[seed]
        skip = max(0, row["n_moves"] // 2)
        try:
            gen = AC.replay_census_game(seed, C, row, mutate_skip_ply=skip)
            while True:
                next(gen)
        except AC.ReplayMismatch as exc:
            kills.append({"seed": seed, "skip_ply": skip, "raised": str(exc)[:120]})
            print(f"  G2 seed {seed:6d} M-STALE KILLED at ply {skip}", flush=True)
            continue
        except StopIteration:
            pass
        sys.exit(f"G2 FAIL: M-stale at ply {skip} of seed {seed} did NOT abort "
                 f"— the replay gate cannot fail, so its passes mean nothing")
    report["G2"] = {"kills": kills, "pass": True}

    # ---------------------------------------------------------------- G3
    seed = GATE_SEEDS[0]
    env = AC.make_clean_env(seed)
    for i, a in rows[seed]["trace"][:12]:
        AC._advance_clean(env, int(a))
    a1, b1 = copy.deepcopy(env), copy.deepcopy(env)
    pa = [(p.a, p.b) for p in (a1._rand_pill() for _ in range(6))]
    pb = [(p.a, p.b) for p in (b1._rand_pill() for _ in range(6))]
    same_unswapped = (pa == pb)
    c1 = copy.deepcopy(env)
    AC._swap_stream(c1, 12345)
    pc = [(p.a, p.b) for p in (c1._rand_pill() for _ in range(6))]
    differs_swapped = (pc != pa)
    print(f"  G3 fork independence: unswapped clones agree={same_unswapped} "
          f"swapped clone differs={differs_swapped}", flush=True)
    if not same_unswapped:
        sys.exit("G3 FAIL: two clones of the same env drew DIFFERENT capsules "
                 "unswapped — the cursor is not deepcopy-clean")
    if not differs_swapped:
        sys.exit("G3 FAIL: the swapped clone drew the SAME capsules — A1.1's "
                 "stream swap does nothing")
    report["G3"] = {"same_unswapped": same_unswapped,
                    "differs_swapped": differs_swapped, "pass": True}

    # ---------------------------------------------------------------- G4
    # 20 states: 10 from each gate seed, spread back from the anchor ply.
    live_spread, inert_spread, n_states = 0, 0, 0
    detail = []
    for seed in GATE_SEEDS:
        row = rows[seed]
        end = row["n_moves"] - 1
        want = sorted({max(0, end - k) for k in (1, 2, 3, 4, 6, 8, 10, 14, 18, 24)})
        H = AC.H_STALL if row["result"] == "stall" else AC.H_TOPOUT
        for ply, env, vals, a in AC.replay_census_game(seed, C, row, want_plies=set(want)):
            n_states += 1
            live = AC.label_state(env, C, seed, ply, H, clair=False, swap=True)
            inert = AC.label_state(env, C, seed, ply, H, clair=False, swap=False)
            key = "clear" if row["result"] == "stall" else "surv"
            lv = sum(1 for e in live if 0 < sum(e[key]) < AC.N_SAMPLES)
            iv = sum(1 for e in inert if 0 < sum(e[key]) < AC.N_SAMPLES)
            live_spread += lv
            inert_spread += iv
            detail.append({"seed": seed, "ply": ply, "n_cand": len(live),
                           "live_varying": lv, "inert_varying": iv})
            if iv:
                sys.exit(f"G4 FAIL / A1 WITHDRAWN: the ORIGINAL registered dose "
                         f"showed spread ({iv} candidates at seed {seed} ply "
                         f"{ply}) — my inertness diagnosis is wrong")
    print(f"  G4 G-DOSE-LIVE: {live_spread} varying candidates over {n_states} "
          f"states (corrected dose)", flush=True)
    print(f"  G4 M-INERT   : {inert_spread} varying candidates — the ORIGINAL "
          f"registered dose is FLAT, vacuity proven", flush=True)
    if live_spread == 0:
        sys.exit("G4 FAIL (VOID V5): the corrected dose is ALSO flat — labels "
                 "carry no information in this regime")
    report["G4"] = {"n_states": n_states, "live_spread": live_spread,
                    "inert_spread": inert_spread, "detail": detail, "pass": True}

    # ---------------------------------------------------------------- G5
    seed = GATE_SEEDS[0]
    row = rows[seed]
    ply_t = row["n_moves"] - 6
    digs = []
    for _ in range(2):
        for ply, env, vals, a in AC.replay_census_game(seed, C, row, want_plies={ply_t}):
            ents = AC.label_state(env, C, seed, ply, AC.H_TOPOUT)
            blob = json.dumps([{k: v for k, v in e.items() if k != "planes"}
                               for e in ents], sort_keys=True)
            digs.append(hashlib.sha256(blob.encode()).hexdigest())
    if digs[0] != digs[1]:
        sys.exit("G5 FAIL: labeling the same state twice differs")
    print(f"  G5 determinism: {digs[0][:16]} == {digs[1][:16]}", flush=True)
    report["G5"] = {"digest": digs[0], "pass": True}

    report["elapsed_s"] = round(time.time() - t0, 1)
    with open(os.path.join(OUT, "gate_autopsy.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nGATES_OK  ({report['elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()
