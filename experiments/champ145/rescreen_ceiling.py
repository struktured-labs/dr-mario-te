"""rescreen_ceiling.py — H13-v2 re-screen RECON HARDENING (2026-08-24,
champion task). Analysis only — zero new games, zero fresh seeds; extends
rescreen_discards.py (c0fe58b) over the same banked 1,500-game L20 corpus.

Question: is the sub-floor increment at T=13/12 a threshold accident, or is
the WHOLE gate-expansion family dose-starved at L20? The supremum of every
"OR another clause onto gate-v1" candidate is the ALWAYS-OPEN gate, so its
tie dose upper-bounds the increment ANY superset gate can deliver. Also
banks the game-level divergence ceiling: a paired A/B game can only go
discordant if the trt arm ever sees a v2-only tie ply, so
P(game has >= 1 v2-only tie) bounds the discordant-pair rate from above
(before theta acceptance thins it further).

Self-gates (before extension rows are trusted):
  1. REPRODUCE c0fe58b: the T=13 / T=12 rows must equal the committed
     out/rescreen_discards.json statistics exactly.
  2. Gate mutants from rescreen_discards.py re-run here (fire/threshold).
  3. always-open must open on EVERY ply, and increments must be monotone
     non-increasing in T; always >= every T row.
"""
import glob
import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GATE_DSPAWN_H, GATE_VIRUSES = 12, 8
THRESHOLDS = [10, 11, 12, 13, 14]


def v1(r):
    return r["dsh"] >= GATE_DSPAWN_H or r["vir"] <= GATE_VIRUSES


def v2(r, t):
    return r["maxh"] >= t or v1(r)


def self_gate():
    ply = {"dsh": 8, "vir": 30, "maxh": 13}
    assert not v1(ply), "v1 must miss the edge tower"
    assert v2(ply, 13), "v2@13 must fire on the edge tower"
    assert not v2({"dsh": 8, "vir": 30, "maxh": 12}, 13), "threshold inert"
    print("[self-gate] gate mutants killed")


def main():
    self_gate()
    files = sorted(glob.glob(os.path.join(HERE, "out", "states",
                                          "states_*.jsonl.gz")))
    assert len(files) == 1500, len(files)
    variants = {"v1": lambda r: v1(r)}
    for t in THRESHOLDS:
        variants[f"v2@{t}"] = (lambda tt: (lambda r: v2(r, tt)))(t)
    variants["always"] = lambda r: True

    tot = {k: {"open": 0, "tie": 0, "only_open": 0, "only_tie": 0,
               "tie_fail": 0, "games_with_only_tie": 0}
           for k in variants}
    n_ply = n_ply_fail = 0
    n_games = n_fail = 0
    for path in files:
        rows = []
        with gzip.open(path, "rt") as fh:
            for line in fh:
                rows.append(json.loads(line))
        game = rows[-1]["game"]
        n_games += 1
        failed = game["won"] == 0
        n_fail += int(failed)
        game_only_tie = {k: 0 for k in variants}
        for r in rows[:-1]:
            n_ply += 1
            n_ply_fail += int(failed)
            tie = r["tie_dedup"] > 1
            base = v1(r)
            for k, fn in variants.items():
                if not fn(r):
                    continue
                d = tot[k]
                d["open"] += 1
                d["tie"] += int(tie)
                if failed:
                    d["tie_fail"] += int(tie)
                if not base:
                    d["only_open"] += 1
                    if tie:
                        d["only_tie"] += 1
                        game_only_tie[k] += 1
        for k in variants:
            if game_only_tie[k] > 0:
                tot[k]["games_with_only_tie"] += 1

    # self-gate 3: always-open opens everywhere; monotone in T
    assert tot["always"]["open"] == n_ply, "always-open must fire every ply"
    incs = [tot[f"v2@{t}"]["only_tie"] for t in THRESHOLDS]
    assert all(a >= b for a, b in zip(incs, incs[1:])), incs
    assert tot["always"]["only_tie"] >= max(incs), "supremum violated"

    out = {"n_games": n_games, "n_fail_games": n_fail, "n_ply": n_ply,
           "n_ply_in_fail_games": n_ply_fail, "variants": {}}
    for k, d in tot.items():
        out["variants"][k] = {
            "open_rate": round(d["open"] / n_ply, 4),
            "tie_dose_of_all": round(d["tie"] / n_ply, 4),
            "increment_tie_over_v1": round(d["only_tie"] / n_ply, 4),
            "increment_tie_plies": d["only_tie"],
            "tie_dose_in_fail_games": round(d["tie_fail"]
                                            / max(1, n_ply_fail), 4),
            "games_with_v2only_tie": d["games_with_only_tie"],
            "divergence_ceiling": round(d["games_with_only_tie"]
                                        / n_games, 4),
        }

    # self-gate 1: reproduce the committed c0fe58b rows exactly
    with open(os.path.join(HERE, "out", "rescreen_discards.json")) as fh:
        prev = json.load(fh)
    for k in ("v1", "v2@13", "v2@12"):
        for col in ("open_rate", "tie_dose_of_all", "increment_tie_over_v1",
                    "tie_dose_in_fail_games"):
            a, b = out["variants"][k][col], prev["variants"][k][col]
            assert a == b, (k, col, a, b)
    print("[self-gate] c0fe58b rows reproduced exactly (v1, v2@13, v2@12)")

    dst = os.path.join(HERE, "out", "rescreen_ceiling.json")
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))
    print("RESCREEN_CEILING_OK")


if __name__ == "__main__":
    main()
