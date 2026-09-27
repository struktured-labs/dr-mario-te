"""trigger_roc.py — H16 DESIGN-SIDE analysis (bank-only; nothing here is
evaluation evidence — REGISTRATION_H16.md carries the firewall statement).

Inputs (read-only, existing banks):
  1. garbage label bank  (labels-146 campaign, 1,344 states, voids attached):
     ~/projects/dr-mario-labels146-wt/experiments/labels146/garbage/out/labels/
     - A_* / B_*: silicon pre-death imports (have `nes` raw board)
     - C_*_k{8,12,16,20}: C-deep lab states from topout games (maxh/dsh/vir
       precomputed) — the death-path window; claims live here (269/1,200)
     - C_*_k{30,40,50}: mid-game states (champ_surv 7.75/8 — healthy-ish)
  2. champ145 state bank (1,500 champion-const L20 home-regime games, every
     ply: maxh/dsh/vir/margins + game result):
     ~/projects/dr-mario-champ145-wt/experiments/champ145/out/states/

Outputs (committed with the registration):
  out/trigger_roc.json + stdout table.

Questions answered, each mapped to a REGISTRATION_H16.md section:
  Q1 trigger ROC: for maxh>=h0 (and dsh>=12 / H12-gate for comparison):
     catch rate on claim states (by stratum and k), fire rate on healthy
     states (C-mid champ_surv>=7; cleared-game plies from the state bank).
  Q2 lead-time: fire rate at k plies before death in the 1,500-game bank's
     topout games (does the trigger open BEFORE the 6-10 ply lock-in?).
  Q3 rank/margin on claims: where does the rollout-best candidate sit in the
     H12 value ranking (sets k), and how large is the value gap (the H14a
     near-tie trigger eps=2.0 comparison).
  Q4 budget: fire rate x plies/game x forks/fire at the candidate (k,m).
"""
import glob
import gzip
import json
import os
from collections import defaultdict

import numpy as np

LAB = os.path.expanduser(
    "~/projects/dr-mario-labels146-wt/experiments/labels146/garbage/out/labels")
BANK = os.path.expanduser(
    "~/projects/dr-mario-champ145-wt/experiments/champ145/out/states")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

H0_GRID = (10, 11, 12, 13, 14)
CLAIM_CHAMP_MAX = 5          # PREREG_GARBAGE sec 5, verbatim
CLAIM_DELTA_MIN = 3


def nes_maxh_singles(nes):
    """(maxh, n_singles, vir) from a raw 128-byte NES board (row 0 = top)."""
    maxh, singles, vir = 0, 0, 0
    top = [16] * 8
    for i, v in enumerate(nes):
        if v in (0xFF, 0x00):
            continue
        r, c = divmod(i, 8)
        top[c] = min(top[c], r)
        hi = (v >> 4) & 0xF
        if hi == 0x8:
            singles += 1
        elif hi == 0xD:
            vir += 1
    maxh = max((16 - t) for t in top)
    return maxh, singles, vir


def load_labels():
    rows = []
    for p in sorted(glob.glob(os.path.join(LAB, "*.jsonl.gz"))):
        with gzip.open(p, "rt") as fh:
            d = json.loads(fh.readline())
        r = {"id": d["id"], "stratum": d["stratum"],
             "k": d.get("k"), "champ_slot": d["champ_slot"],
             "vals": d.get("vals") or d.get("champ_vals"),
             "cands": [{"rep_slot": c["rep_slot"], "slots": c["slots"],
                        "surv": sum(c["surv"])} for c in d["cands"]]}
        if "nes" in d:
            r["maxh"], r["singles"], r["vir"] = nes_maxh_singles(d["nes"])
            r["dsh"] = None      # derivable but unused for A/B
        else:
            r["maxh"], r["dsh"], r["vir"] = d["maxh"], d["dsh"], d["vir"]
            r["singles"] = None
        rows.append(r)
    return rows


def classify(r):
    """(champ_surv, best_surv, best_rep, claim?) under the registered rule."""
    champ = None
    for c in r["cands"]:
        if r["champ_slot"] in c["slots"]:
            champ = c
            break
    assert champ is not None, r["id"]
    best = max(r["cands"], key=lambda c: c["surv"])
    claim = (champ["surv"] <= CLAIM_CHAMP_MAX
             and best["surv"] - champ["surv"] >= CLAIM_DELTA_MIN)
    return champ["surv"], best["surv"], best["rep_slot"], claim


def value_rank_gap(r, best_rep):
    """Rank (1-based) of the claim's best candidate among dedup'd candidates
    ordered by H12 value, and the value gap champ_val - best_val."""
    vals = r["vals"]
    ents = sorted(r["cands"],
                  key=lambda c: -(vals[c["rep_slot"]]
                                  if vals[c["rep_slot"]] is not None
                                  else -1e18))
    rank = next(i + 1 for i, c in enumerate(ents) if c["rep_slot"] == best_rep)
    v_champ = vals[r["champ_slot"]]
    v_best = vals[best_rep]
    gap = (v_champ - v_best) if (v_champ is not None and v_best is not None) \
        else None
    return rank, gap


def bank_iter():
    for p in sorted(glob.glob(os.path.join(BANK, "states_*.jsonl.gz"))):
        rows = []
        with gzip.open(p, "rt") as fh:
            for ln in fh:
                rows.append(json.loads(ln))
        game = rows[-1]["game"]
        yield game, rows[:-1]


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {}

    # ---------------------------------------------------------- label bank
    lab = load_labels()
    strata = defaultdict(list)
    for r in lab:
        champ_surv, best_surv, best_rep, claim = classify(r)
        r["champ_surv"], r["best_surv"], r["claim"] = champ_surv, best_surv, claim
        r["best_rep"] = best_rep
        key = (r["stratum"] if r["stratum"] not in ("C", "Cdeep")
               else f"{r['stratum']}_k{r['k']}")
        strata[key].append(r)
    print("== label bank composition ==")
    for key in sorted(strata):
        rs = strata[key]
        nc = sum(r["claim"] for r in rs)
        print(f"  {key:10s} n={len(rs):4d} claims={nc:3d} "
              f"champ_surv_mean={np.mean([r['champ_surv'] for r in rs]):.2f}")
    res["composition"] = {k: {"n": len(v), "claims": sum(r["claim"] for r in v)}
                          for k, v in strata.items()}

    claims = [r for r in lab if r["claim"]]
    deep = [r for r in lab if r["stratum"] == "Cdeep"]
    mid_healthy = [r for r in lab if r["stratum"] == "C"
                   and r["champ_surv"] >= 7]

    # Q1: trigger ROC on the bank
    print("\n== Q1 trigger ROC (label bank) ==")
    roc = {}
    for h0 in H0_GRID:
        catch = np.mean([r["maxh"] >= h0 for r in claims])
        catch_deep = np.mean([r["maxh"] >= h0 for r in deep if r["claim"]])
        deathpath = np.mean([r["maxh"] >= h0 for r in deep])
        healthy = np.mean([r["maxh"] >= h0 for r in mid_healthy])
        roc[h0] = {"catch_claims": round(float(catch), 4),
                   "catch_deep_claims": round(float(catch_deep), 4),
                   "fire_deathpath_all": round(float(deathpath), 4),
                   "fire_mid_healthy": round(float(healthy), 4)}
        print(f"  maxh>={h0}: catch(all claims)={catch:.3f} "
              f"catch(Cdeep claims)={catch_deep:.3f} "
              f"fire(deathpath all)={deathpath:.3f} "
              f"fire(C-mid healthy)={healthy:.3f}")
    # old sensor + H12 gate for comparison (Cdeep has dsh)
    dsh_catch = np.mean([r["dsh"] >= 12 for r in claims if r["dsh"] is not None])
    h12gate_catch = np.mean([(r["dsh"] >= 12 or r["vir"] <= 8)
                             for r in claims if r["dsh"] is not None])
    print(f"  [cmp] dsh>=12 catch(Cdeep claims)={dsh_catch:.3f}; "
          f"H12 gate (dsh>=12|vir<=8) catch={h12gate_catch:.3f}")
    res["roc"] = roc
    res["cmp_dsh12_catch"] = round(float(dsh_catch), 4)
    res["cmp_h12gate_catch"] = round(float(h12gate_catch), 4)

    # contamination, where observable (A/B only)
    ab = [r for r in lab if r["stratum"] in ("A", "B")]
    print(f"  [A/B strata n={len(ab)}] singles median="
          f"{np.median([r['singles'] for r in ab]):.0f} "
          f"maxh median={np.median([r['maxh'] for r in ab]):.0f}")

    # Q3: rank / margin of the rollout-best candidate on claim states
    print("\n== Q3 value rank & gap of rollout-best on claim states ==")
    ranks, gaps = [], []
    for r in claims:
        rank, gap = value_rank_gap(r, r["best_rep"])
        ranks.append(rank)
        if gap is not None:
            gaps.append(gap)
    ranks = np.array(ranks)
    gaps = np.array(gaps)
    cov = {k: round(float(np.mean(ranks <= k)), 4) for k in (2, 3, 4, 5, 6, 8, 10)}
    print(f"  n_claims={len(ranks)}  rank<=k coverage: " +
          " ".join(f"k{k}:{v:.2f}" for k, v in cov.items()))
    print(f"  value gap champ-best: median={np.median(gaps):.0f} "
          f"p25={np.percentile(gaps,25):.0f} p75={np.percentile(gaps,75):.0f} "
          f"frac<=2.0 (H14a eps reach)={np.mean(gaps<=2.0):.4f}")
    res["rank_coverage"] = cov
    res["gap_median"] = float(np.median(gaps))
    res["gap_frac_le_eps2"] = float(np.mean(gaps <= 2.0))

    # ------------------------------------------------- champ145 state bank
    print("\n== Q1b/Q2/Q4: 1,500-game home-regime state bank ==")
    per_h0_fire = {h0: 0 for h0 in H0_GRID}
    per_h0_fire_cleared = {h0: 0 for h0 in H0_GRID}
    plies_total, plies_cleared = 0, 0
    n_games = n_cleared = n_topout = 0
    plies_per_game = []
    # lead-time: fire rate at k plies before the END of topout games
    kbins = [(1, 5), (6, 10), (11, 15), (16, 25), (26, 40)]
    lead = {h0: {b: [0, 0] for b in kbins} for h0 in H0_GRID}
    for game, rows in bank_iter():
        n_games += 1
        plies_per_game.append(game["n_plies"])
        cleared = bool(game["won"])
        n_cleared += cleared
        topout = bool(game["topout"])
        n_topout += topout
        n = len(rows)
        for i, row in enumerate(rows):
            plies_total += 1
            plies_cleared += cleared
            for h0 in H0_GRID:
                f = row["maxh"] >= h0
                per_h0_fire[h0] += f
                per_h0_fire_cleared[h0] += (f and cleared)
                if topout:
                    kk = n - i          # plies before death (1 = last)
                    for b in kbins:
                        if b[0] <= kk <= b[1]:
                            lead[h0][b][0] += f
                            lead[h0][b][1] += 1
    print(f"  games={n_games} cleared={n_cleared} topout={n_topout} "
          f"plies={plies_total} mean_plies/game={np.mean(plies_per_game):.1f}")
    res["bank_games"] = {"n": n_games, "cleared": n_cleared,
                         "topout": n_topout, "plies": plies_total,
                         "mean_plies": float(np.mean(plies_per_game))}
    res["fire"], res["lead"] = {}, {}
    for h0 in H0_GRID:
        fr = per_h0_fire[h0] / plies_total
        frc = (per_h0_fire_cleared[h0] / plies_cleared) if plies_cleared else 0
        lt = {f"{b[0]}-{b[1]}": (lead[h0][b][0] / lead[h0][b][1]
                                 if lead[h0][b][1] else None) for b in kbins}
        print(f"  maxh>={h0}: fire(all plies)={fr:.4f} "
              f"fire(cleared-game plies)={frc:.4f} "
              f"lead-time fire k-before-death: " +
              " ".join(f"[{k}]:{v:.2f}" for k, v in lt.items() if v is not None))
        res["fire"][h0] = {"all": round(float(fr), 4),
                           "cleared": round(float(frc), 4)}
        res["lead"][h0] = {k: (round(float(v), 4) if v is not None else None)
                           for k, v in lt.items()}

    # Q4 budget at the candidate config
    print("\n== Q4 budget (k=5 dedup cands x m=8 forks, H=25) ==")
    forks_per_fire = 5 * 8
    for h0 in (12, 13):
        fires_per_game = res["fire"][h0]["all"] * res["bank_games"]["mean_plies"]
        for tag, cps in (("blackmage-unloaded", 0.718),
                         ("redmage", 1.11), ("blackmage-load50", 1.917)):
            s_per_game = fires_per_game * forks_per_fire * cps
            print(f"  h0={h0} {tag}: fires/game={fires_per_game:.1f} "
                  f"extra {s_per_game/60:.1f} min/game "
                  f"600 B-games={600*s_per_game/3600:.0f} core-h")
        res.setdefault("budget", {})[h0] = {
            "fires_per_game": round(float(fires_per_game), 2),
            "forks_per_fire": forks_per_fire}

    with open(os.path.join(OUT, "trigger_roc.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'trigger_roc.json')}")


if __name__ == "__main__":
    main()
