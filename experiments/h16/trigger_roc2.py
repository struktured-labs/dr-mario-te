"""trigger_roc2.py — H16 design round 2: spawn-lane / death-window triggers.

Round 1 (trigger_roc.py) measured: maxh saturates at L20 (0.74-0.82 fire on
healthy plies at h0=12) — a height trigger is not a trigger at the home
regime.  Round 2 evaluates the spawn-lane family, which is the game's actual
top-out mechanism (games end when the spawn is blocked):

  T_dsh(t):    d_spawn_h >= t                  (current board, cols 3/4)
  T_mindsh(t): min over legal candidates of child d_spawn_h >= t
               ("the window is closing": EVERY placement leaves the spawn
               lane at >= t — the E=1 mechanism of the depth-4 memo)
  x vir>=9 variants (excluding H12's endgame-gate territory)

Catch = fire rate on the 274 claim states (rollout-changeable death-gateway
states, registered claim rule).  Specificity = fire rate on cleared-game
plies of the 1,500-game state bank.  Lead-time = fire rate at k plies before
death in topout games.
"""
import base64
import glob
import gzip
import json
import os

import numpy as np

LAB = os.path.expanduser(
    "~/projects/dr-mario-labels146-wt/experiments/labels146/garbage/out/labels")
BANK = os.path.expanduser(
    "~/projects/dr-mario-champ145-wt/experiments/champ145/out/states")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

NCELL = 128
CLAIM_CHAMP_MAX, CLAIM_DELTA_MIN = 5, 3

DSH_GRID = (12, 13, 14, 15)
MINDSH_GRID = (9, 10, 11, 12, 13)


def col_heights(flat_c1):
    occ = np.asarray(flat_c1[:NCELL]).reshape(16, 8) != 0
    return np.where(occ.any(axis=0), 16 - np.argmax(occ, axis=0), 0)


def nes_planes(nes):
    """Raw NES bytes -> flat colour plane (occupancy only; colours unused)."""
    c = np.zeros(NCELL, dtype=np.int8)
    for i, v in enumerate(nes):
        if v not in (0xFF, 0x00):
            c[i] = (v & 0x3) + 1
    return c


def load_label_states():
    rows = []
    for p in sorted(glob.glob(os.path.join(LAB, "*.jsonl.gz"))):
        with gzip.open(p, "rt") as fh:
            d = json.loads(fh.readline())
        champ = next(c for c in d["cands"] if d["champ_slot"] in c["slots"])
        best = max(d["cands"], key=lambda c: sum(c["surv"]))
        cs, bs = sum(champ["surv"]), sum(best["surv"])
        claim = cs <= CLAIM_CHAMP_MAX and bs - cs >= CLAIM_DELTA_MIN
        # child d_spawn_h per dedup'd candidate, from the stored planes
        cdshs = []
        for c in d["cands"]:
            raw = base64.b64decode(c["planes"])
            hs = col_heights(np.frombuffer(raw[:NCELL], dtype=np.int8))
            cdshs.append(int(max(hs[3], hs[4])))
        if "nes" in d:
            hs = col_heights(nes_planes(d["nes"]))
            dsh = int(max(hs[3], hs[4]))
            vir = sum(1 for v in d["nes"] if (v >> 4) == 0xD)
        else:
            dsh, vir = int(d["dsh"]), int(d["vir"])
        rows.append({"id": d["id"], "stratum": d["stratum"],
                     "k": d.get("k"), "claim": claim, "champ_surv": cs,
                     "dsh": dsh, "vir": vir, "mindsh": min(cdshs),
                     "n_cands": len(d["cands"])})
    return rows


def trig(row, kind, t):
    if kind == "dsh":
        return row["dsh"] >= t
    if kind == "mindsh":
        return row["mindsh"] >= t
    if kind == "dsh&vir":
        return row["dsh"] >= t and row["vir"] >= 9
    if kind == "mindsh&vir":
        return row["mindsh"] >= t and row["vir"] >= 9
    raise ValueError(kind)


def bank_iter():
    for p in sorted(glob.glob(os.path.join(BANK, "states_*.jsonl.gz"))):
        rows = []
        with gzip.open(p, "rt") as fh:
            for ln in fh:
                rows.append(json.loads(ln))
        yield rows[-1]["game"], rows[:-1]


def main():
    os.makedirs(OUT, exist_ok=True)
    lab = load_label_states()
    claims = [r for r in lab if r["claim"]]
    mid_healthy = [r for r in lab if r["stratum"] == "C"
                   and r["champ_surv"] >= 7]
    print(f"label states={len(lab)} claims={len(claims)} "
          f"C-mid healthy={len(mid_healthy)}")

    variants = ([("dsh", t) for t in DSH_GRID]
                + [("mindsh", t) for t in MINDSH_GRID]
                + [("dsh&vir", t) for t in DSH_GRID]
                + [("mindsh&vir", t) for t in MINDSH_GRID])

    # ---------------- state bank pass (fire rates + lead time) ----------
    kbins = [(1, 5), (6, 10), (11, 15), (16, 25), (26, 40)]
    stats = {v: {"fire": 0, "fire_clr": 0, "lead": {b: [0, 0] for b in kbins}}
             for v in variants}
    plies = plies_clr = 0
    plies_per_game = []
    for game, rows in bank_iter():
        cleared, topout = bool(game["won"]), bool(game["topout"])
        n = len(rows)
        plies_per_game.append(n)
        for i, row in enumerate(rows):
            plies += 1
            plies_clr += cleared
            cd = [x for x in row["cdsh"] if x >= 0]
            r = {"dsh": row["dsh"], "vir": row["vir"],
                 "mindsh": min(cd) if cd else 16}
            for v in variants:
                f = trig(r, *v)
                stats[v]["fire"] += f
                stats[v]["fire_clr"] += (f and cleared)
                if topout:
                    kk = n - i
                    for b in kbins:
                        if b[0] <= kk <= b[1]:
                            stats[v]["lead"][b][0] += f
                            stats[v]["lead"][b][1] += 1

    mean_plies = float(np.mean(plies_per_game))
    print(f"bank plies={plies} cleared-plies={plies_clr} "
          f"mean plies/game={mean_plies:.1f}\n")
    res = {"mean_plies": mean_plies, "variants": {}}
    hdr = (f"{'trigger':16s} {'fire_all':>8s} {'fire_clr':>8s} "
           f"{'catch':>6s} {'healthyC':>8s} " +
           " ".join(f"k{b[0]}-{b[1]}" for b in kbins))
    print(hdr)
    for v in variants:
        kind, t = v
        fire = stats[v]["fire"] / plies
        fire_clr = stats[v]["fire_clr"] / plies_clr
        catch = float(np.mean([trig(r, *v) for r in claims]))
        healthy = float(np.mean([trig(r, *v) for r in mid_healthy]))
        lt = [stats[v]["lead"][b] for b in kbins]
        lts = " ".join(f"{a/b:5.2f}" if b else "  -  " for a, b in lt)
        name = f"{kind}>={t}"
        print(f"{name:16s} {fire:8.4f} {fire_clr:8.4f} "
              f"{catch:6.3f} {healthy:8.3f} {lts}")
        res["variants"][name] = {
            "fire_all": round(fire, 4), "fire_cleared": round(fire_clr, 4),
            "catch_claims": round(catch, 4), "fire_mid_healthy": round(healthy, 4),
            "lead": {f"{b[0]}-{b[1]}": (round(a / c, 4) if c else None)
                     for b, (a, c) in zip(kbins, lt)},
            "fires_per_game": round(fire * mean_plies, 2)}

    # dedup width on claim states (drives forks/fire)
    ncands = [r["n_cands"] for r in claims]
    print(f"\ndedup candidate count on claim states: "
          f"median={np.median(ncands):.0f} p90={np.percentile(ncands,90):.0f}")
    res["claim_ncands_median"] = float(np.median(ncands))

    with open(os.path.join(OUT, "trigger_roc2.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote {os.path.join(OUT, 'trigger_roc2.json')}")


if __name__ == "__main__":
    main()
