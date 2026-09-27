"""gate_labels.py — PREREG_LABELS §6 gates + mutant kills, run BEFORE the
pilot harvest.  Exit 0 only if every gate passes AND every mutant dies.
"""
import json
import os
import sys

import labelcore as LC


def first_by_res(games, res, n):
    return [g for g in games if g["res"] == res][:n]


def main():
    C, bmodel = LC.init_rig()
    games = LC.bank_games()
    report = {}

    # G1 — replay positive control: one topout, one stall, one clear
    picks = (first_by_res(games, "topout", 1) + first_by_res(games, "stall", 1)
             + first_by_res(games, "clear", 1))
    assert len(picks) == 3
    for g in picks:
        rows, _ = LC.load_bank_game(g["seed"])
        gen = LC.replay_game(g["seed"], C, bmodel, rows)
        n = 0
        try:
            while True:
                next(gen)
                n += 1
        except StopIteration as stop:
            res = stop.value
        assert res == g["res"], (g["seed"], res, g["res"])
        assert n == g["n_plies"], (g["seed"], n, g["n_plies"])
        print(f"G1 replay OK seed={g['seed']} res={res} plies={n}",
              flush=True)
    report["G1"] = "PASS"

    # G2 — M-stale kill: a desynchronized replay MUST abort (gate liveness)
    g = picks[0]
    rows, _ = LC.load_bank_game(g["seed"])
    killed = False
    try:
        gen = LC.replay_game(g["seed"], C, bmodel, rows,
                             mutate_skip_ply=g["n_plies"] // 2)
        while True:
            next(gen)
    except LC.ReplayMismatch as e:
        killed = True
        print(f"G2 M-stale KILLED at {e.args[0][:3]}", flush=True)
    except StopIteration:
        pass
    assert killed, "M-stale SURVIVED — the replay gate cannot fail"
    report["G2_m_stale"] = "KILLED"

    # G3 — population mutant: dedup-off must GROW the candidate count.
    # The collapse is a DOUBLE-CAPSULE property (mirror orientations give the
    # same board => ratio ~2.0 on doubles, ~1.0 otherwise), so the assert is
    # per-double, not pooled (the original pooled 1.15 bar was mis-derived —
    # it depends on how many doubles luck into the probe set).
    with open(os.path.join(LC.HERE, "out", "targets.json")) as fh:
        targets = json.load(fh)
    assert len(targets) == 80, len(targets)
    by_seed = {}
    for t in targets:
        by_seed.setdefault(t["seed"], set()).add(t["ply"])
    probes, n_double = [], 0
    for seed in sorted(by_seed):
        rows, _ = LC.load_bank_game(seed)
        gen = LC.replay_game(seed, C, bmodel, rows)
        try:
            while True:
                ply, env, _v, _r = next(gen)
                if ply in by_seed[seed]:
                    dbl = int(env.cur.a) == int(env.cur.b)
                    nu = len(LC.enumerate_candidates(env, dedup=True))
                    ns = len(LC.enumerate_candidates(env, dedup=False))
                    probes.append((seed, ply, dbl, ns, nu))
                    n_double += dbl
        except StopIteration:
            pass
        if len(probes) >= 6 and n_double >= 1:
            break
    assert n_double >= 1, "no double-capsule probe found — population untested"
    for seed, ply, dbl, ns, nu in probes:
        r = ns / nu
        print(f"G3 probe seed={seed} ply={ply} double={dbl} "
              f"slots={ns} uniq={nu} ratio={r:.3f}", flush=True)
        if dbl:
            assert r >= 1.8, (seed, ply, r)
    tot_s = sum(p[3] for p in probes)
    tot_u = sum(p[4] for p in probes)
    assert tot_s > tot_u, "dedup-off did not grow the population"
    report["G3_m_dedup_off"] = {
        "probes": len(probes), "doubles": n_double,
        "pooled_ratio": round(tot_s / tot_u, 3), "verdict": "KILLED"}

    # G4 — CRN + determinism: labeling the same state twice is byte-identical
    # probe = a CLEAR-stratum state (mid-game, labels cannot be all-zero the
    # way an end-1 death ply legitimately can)
    tgt = next(t for t in targets if t["stratum"] == "clear")
    rows, _ = LC.load_bank_game(tgt["seed"])
    gen = LC.replay_game(tgt["seed"], C, bmodel, rows)
    env = None
    for ply, e, _v, _r in gen:
        if ply == tgt["ply"]:
            env = e
            break
    assert env is not None
    l1 = LC.label_state(env, C, bmodel, tgt["seed"], tgt["ply"], 2, 5)
    l2 = LC.label_state(env, C, bmodel, tgt["seed"], tgt["ply"], 2, 5)
    assert json.dumps(l1) == json.dumps(l2), "labeling not deterministic"
    assert any(any(e["surv"]) or any(e["prog"]) for e in l1), \
        "all-zero labels on probe state (not-inert check)"
    print(f"G4 determinism OK ({len(l1)} candidates, N=2, H=5)", flush=True)
    report["G4"] = "PASS"

    with open(os.path.join(LC.HERE, "out", "gate_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print("GATES_OK", flush=True)


if __name__ == "__main__":
    sys.exit(main())
