"""make_targets.py — PREREG_LABELS §2 pilot sampling rule, applied mechanically.

Writes out/targets.json: [{seed, ply, stratum, k, Hs}, ...].
S-death: first 12 topout games (seed asc, n_plies>=30), plies end-k,
k in {1,3,6,10,15,20}; k in {6,15} get Hs=[15,25,40], else [25].
S-clear: first 8 cleared games (seed asc, n_plies>=30); target ply = banked ply
nearest in (vir,dsh) L1 to the i-th S-death game's end-10 row (ties earliest).
"""
import json
import os

import labelcore as LC

KS = [1, 3, 6, 10, 15, 20]
DUAL_KS = {6, 15}
HS_DUAL = [15, 25, 40]
HS_ONE = [25]


def main():
    games = LC.bank_games()
    deaths = [g for g in games if g["res"] == "topout"
              and g["n_plies"] >= 30][:12]
    clears = [g for g in games if g["res"] == "clear"
              and g["n_plies"] >= 30][:8]
    assert len(deaths) == 12 and len(clears) == 8, (len(deaths), len(clears))

    targets = []
    anchor = []   # (vir,dsh) of each S-death game's end-10 row
    for g in deaths:
        rows, _ = LC.load_bank_game(g["seed"])
        for k in KS:
            ply = g["n_plies"] - k
            assert 0 <= ply < g["n_plies"]
            targets.append({"seed": g["seed"], "ply": ply, "stratum": "death",
                            "k": k,
                            "Hs": HS_DUAL if k in DUAL_KS else HS_ONE})
        r = rows[g["n_plies"] - 10]
        anchor.append((r["vir"], r["dsh"]))

    for i, g in enumerate(clears):
        rows, _ = LC.load_bank_game(g["seed"])
        av, ad = anchor[i]
        best = min(range(len(rows)),
                   key=lambda j: (abs(rows[j]["vir"] - av)
                                  + abs(rows[j]["dsh"] - ad), j))
        targets.append({"seed": g["seed"], "ply": best, "stratum": "clear",
                        "k": None, "Hs": HS_ONE})

    assert len(targets) == 80, len(targets)
    assert all(LC.SEED_LO <= t["seed"] <= LC.SEED_HI and t["seed"] % 2 == 0
               for t in targets)
    os.makedirs(os.path.join(LC.HERE, "out"), exist_ok=True)
    path = os.path.join(LC.HERE, "out", "targets.json")
    with open(path, "w") as fh:
        json.dump(targets, fh, indent=1)
    n_seeds = len({t["seed"] for t in targets})
    print(f"TARGETS_OK n={len(targets)} seeds={n_seeds} "
          f"death={sum(t['stratum'] == 'death' for t in targets)} "
          f"clear={sum(t['stratum'] == 'clear' for t in targets)}")


if __name__ == "__main__":
    main()
