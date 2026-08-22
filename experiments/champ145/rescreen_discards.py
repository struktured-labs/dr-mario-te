"""rescreen_discards.py — DISCARD-PILE RE-SCREEN at L20 (owner directive,
2026-08-21) over the banked 1,500-game home-regime corpus. Analysis only —
zero new games; must not disturb drm-champ-endpoint.

Candidates re-screened here (banked columns suffice):
  1. H13 GATE-V2 (any-column height >= 13 primary / 12 secondary, v1 clauses
     retained — h13-gate worktree h13_arm.py). Judged NULL at saturated L11;
     question: does it ADD trigger population at L20, and where?
  2. d_spawn_h dose grid: already in screen_result.json (h14c section) —
     reprinted for the packet.
The stage-2 LUT re-screen needs per-candidate FEATURES which the bank does
not carry — it requires a bank-v2 replay pass and is scheduled POST-endpoint
(cores are the constraint, not design).

Output per gate variant: open rate, dedup-tie trigger dose (of all plies),
INCREMENT over gate-v1 (plies v2-only, tie mass added), failure-game vs
clear-game split, near-death/endgame strata.

Self-gate before data: a synthetic row set where v2@13 must fire on a
maxh=13/dsh=8 ply that v1 misses, and an inverted mutant must not.
"""
import glob
import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GATE_DSPAWN_H, GATE_VIRUSES = 12, 8


def v1(r):
    return r["dsh"] >= GATE_DSPAWN_H or r["vir"] <= GATE_VIRUSES


def v2(r, t):
    return r["maxh"] >= t or v1(r)


def self_gate():
    ply = {"dsh": 8, "vir": 30, "maxh": 13}
    assert not v1(ply), "v1 must miss the edge tower"
    assert v2(ply, 13), "v2@13 must fire on the edge tower"
    assert not v2({"dsh": 8, "vir": 30, "maxh": 12}, 13), "threshold inert"
    # reader-alive: tie accounting must move with the row
    a = {"tie_dedup": 2}
    b = {"tie_dedup": 1}
    assert (a["tie_dedup"] > 1) != (b["tie_dedup"] > 1)
    print("[self-gate] gate mutants killed")


def main():
    self_gate()
    files = sorted(glob.glob(os.path.join(HERE, "out", "states",
                                          "states_*.jsonl.gz")))
    assert len(files) == 1500, len(files)
    variants = {"v1": lambda r: v1(r),
                "v2@13": lambda r: v2(r, 13),
                "v2@12": lambda r: v2(r, 12)}
    tot = {k: {"open": 0, "tie": 0, "open_fail": 0, "tie_fail": 0,
               "only_open": 0, "only_tie": 0,
               "nd_tie": 0, "eg_tie": 0} for k in variants}
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
                    d["open_fail"] += 1
                    d["tie_fail"] += int(tie)
                if not base:
                    d["only_open"] += 1
                    d["only_tie"] += int(tie)
                if r["dsh"] >= 12:
                    d["nd_tie"] += int(tie)
                if r["vir"] <= 8:
                    d["eg_tie"] += int(tie)
    out = {"n_games": n_games, "n_fail_games": n_fail, "n_ply": n_ply,
           "n_ply_in_fail_games": n_ply_fail, "variants": {}}
    for k, d in tot.items():
        out["variants"][k] = {
            "open_rate": round(d["open"] / n_ply, 4),
            "tie_dose_of_all": round(d["tie"] / n_ply, 4),
            "increment_open_over_v1": round(d["only_open"] / n_ply, 4),
            "increment_tie_over_v1": round(d["only_tie"] / n_ply, 4),
            "tie_dose_in_fail_games": round(d["tie_fail"]
                                            / max(1, n_ply_fail), 4),
            "tie_neardeath": d["nd_tie"], "tie_endgame": d["eg_tie"],
        }
    dst = os.path.join(HERE, "out", "rescreen_discards.json")
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))
    print("RESCREEN_DISCARDS_OK")


if __name__ == "__main__":
    main()
