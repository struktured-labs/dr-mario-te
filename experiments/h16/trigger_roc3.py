"""trigger_roc3.py — H16 design round 3: procedure + budget on the bank.

Round 2 fixed the trigger family (spawn-lane).  This round settles:
  A. PRIZE COVERAGE vs candidate width k: fraction of claim states where the
     value-top-k (dedup'd) contains ANY candidate with surv-champ >= 3
     (the claim needs a materially better move in the forked set, not THE
     argmax) — this is what k buys, not the argmax-rank of round 1.
  B. REDUCED-FORK PROCEDURES, simulated on the stored per-fork labels:
       P_full8 : all dedup cands x 8 forks, registered claim rule (reference)
       P_m5    : all cands x forks 0-4, rule champ<=3, delta>=2
       P_scr   : screen all cands with forks 0-1 (m=2), promote top-5 (+champ),
                 confirm on forks 2-7 (m=6), rule champ<=3, delta>=3
     For each: recovered-claim fraction, override-quality (chosen candidate's
     full-8 surv gain), false-override rate on healthy C-mid states, forks/fire.
  C. BUDGET with an adjudication COOLDOWN, simulated on the 1,500-game bank's
     ply sequences (A-arm trajectories; estimate only, stated in the reg):
     fire = dsh>=t AND (plies since last adjudication >= R OR dsh > dsh at
     last adjudication).  Adjudications/game for t in {13,14}, R in {1,5,8}.
  D. GAME-LEVEL OPPORTUNITY: fraction of topout games with >=1 trigger ply
     in the pre-lock-in window k in [10,25].
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


def load_label_states():
    rows = []
    for p in sorted(glob.glob(os.path.join(LAB, "*.jsonl.gz"))):
        with gzip.open(p, "rt") as fh:
            d = json.loads(fh.readline())
        vals = d.get("vals") or d.get("champ_vals")
        cands = []
        for c in d["cands"]:
            v = vals[c["rep_slot"]]
            cands.append({"rep": c["rep_slot"], "surv": list(c["surv"]),
                          "val": (v if v is not None else -1e18),
                          "is_champ": d["champ_slot"] in c["slots"]})
        if "nes" in d:
            occ = np.zeros(NCELL, dtype=bool)
            for i, v in enumerate(d["nes"]):
                occ[i] = v not in (0xFF, 0x00)
            occ = occ.reshape(16, 8)
            hs = np.where(occ.any(axis=0), 16 - np.argmax(occ, axis=0), 0)
            dsh = int(max(hs[3], hs[4]))
        else:
            dsh = int(d["dsh"])
        rows.append({"id": d["id"], "stratum": d["stratum"], "dsh": dsh,
                     "cands": cands})
    return rows


def surv_sum(c, lo, hi):
    return sum(c["surv"][lo:hi])


def full8(state):
    """Registered claim rule; returns chosen cand or None."""
    champ = next(c for c in state["cands"] if c["is_champ"])
    best = max(state["cands"], key=lambda c: (surv_sum(c, 0, 8), c["val"]))
    if surv_sum(champ, 0, 8) <= 5 and \
            surv_sum(best, 0, 8) - surv_sum(champ, 0, 8) >= 3:
        return best, champ
    return None, champ


def p_m5(state):
    champ = next(c for c in state["cands"] if c["is_champ"])
    best = max(state["cands"], key=lambda c: (surv_sum(c, 0, 5), c["val"]))
    if surv_sum(champ, 0, 5) <= 3 and \
            surv_sum(best, 0, 5) - surv_sum(champ, 0, 5) >= 2:
        return best, champ
    return None, champ


def p_scr(state, keep=5):
    champ = next(c for c in state["cands"] if c["is_champ"])
    ranked = sorted(state["cands"],
                    key=lambda c: (-surv_sum(c, 0, 2), -c["val"]))
    short = ranked[:keep]
    if champ not in short:
        short = short + [champ]
    best = max(short, key=lambda c: (surv_sum(c, 2, 8), c["val"]))
    if surv_sum(champ, 2, 8) <= 3 and \
            surv_sum(best, 2, 8) - surv_sum(champ, 2, 8) >= 3:
        return best, champ
    return None, champ


def main():
    os.makedirs(OUT, exist_ok=True)
    lab = load_label_states()
    res = {}

    claims, healthy = [], []
    for s in lab:
        got, champ = full8(s)
        s["claim"] = got is not None
        s["champ8"] = surv_sum(champ, 0, 8)
        (claims if s["claim"] else None) is not None and None
        if s["claim"]:
            claims.append(s)
        if s["stratum"] == "C" and s["champ8"] >= 7:
            healthy.append(s)
    print(f"states={len(lab)} claims={len(claims)} healthy={len(healthy)}")

    # A: prize coverage vs value-top-k width
    print("\n== A: claim coverage by value-top-k (ANY delta>=3 cand) ==")
    res["width_coverage"] = {}
    for k in (3, 5, 8, 12, 99):
        hit = 0
        for s in claims:
            champ8 = s["champ8"]
            topk = sorted(s["cands"], key=lambda c: -c["val"])[:k]
            if any(surv_sum(c, 0, 8) - champ8 >= 3 for c in topk):
                hit += 1
        cov = hit / len(claims)
        res["width_coverage"][k] = round(cov, 4)
        print(f"  k={k:2d}: {cov:.3f}")

    # B: procedures
    print("\n== B: reduced-fork procedures on the bank ==")
    res["procedures"] = {}
    W = float(np.median([len(s["cands"]) for s in lab]))
    for name, fn, forks_fire in (
            ("P_full8", full8, 8 * W),
            ("P_m5", p_m5, 5 * W),
            ("P_scr", p_scr, 2 * W + 6 * 6)):
        rec = qual = 0
        for s in claims:
            got, champ = fn(s)
            if got is not None:
                rec += 1
                if surv_sum(got, 0, 8) - s["champ8"] >= 3:
                    qual += 1
        fo = sum(fn(s)[0] is not None for s in healthy)
        # false-override on ALL non-claim states too
        fo_all = sum(fn(s)[0] is not None for s in lab if not s["claim"])
        res["procedures"][name] = {
            "recovered_of_claims": round(rec / len(claims), 4),
            "good_choice_of_recovered": round(qual / max(rec, 1), 4),
            "false_override_healthy": round(fo / len(healthy), 4),
            "false_override_nonclaim": round(fo_all / (len(lab) - len(claims)), 4),
            "forks_per_fire": round(forks_fire, 1)}
        print(f"  {name}: recovered={rec}/{len(claims)} "
              f"good-choice={qual}/{rec if rec else 1} "
              f"false-override healthy={fo}/{len(healthy)} "
              f"nonclaim={fo_all}/{len(lab)-len(claims)} "
              f"forks/fire~{forks_fire:.0f}")

    # C: cooldown budget + D: opportunity, on the state bank
    print("\n== C/D: cooldown budget + game-level opportunity ==")
    res["budget"] = {}
    res["opportunity"] = {}
    for t in (13, 14):
        adj = {R: [] for R in (1, 5, 8)}
        opp = opp_tot = 0
        for p in sorted(glob.glob(os.path.join(BANK, "states_*.jsonl.gz"))):
            rows = []
            with gzip.open(p, "rt") as fh:
                for ln in fh:
                    rows.append(json.loads(ln))
            game, rows = rows[-1]["game"], rows[:-1]
            n = len(rows)
            for R in adj:
                cnt, last_i, last_d = 0, -10**9, -1
                for i, row in enumerate(rows):
                    if row["dsh"] >= t and (i - last_i >= R
                                            or row["dsh"] > last_d):
                        cnt += 1
                        last_i, last_d = i, row["dsh"]
                adj[R].append(cnt)
            if game["topout"]:
                opp_tot += 1
                if any(r["dsh"] >= t for i, r in enumerate(rows)
                       if 10 <= n - i <= 25):
                    opp += 1
        res["opportunity"][t] = round(opp / opp_tot, 4)
        print(f"  dsh>={t}: topout games with a fire at k in [10,25]: "
              f"{opp}/{opp_tot} = {opp/opp_tot:.3f}")
        res["budget"][t] = {}
        for R, xs in adj.items():
            m, p90 = float(np.mean(xs)), float(np.percentile(xs, 90))
            res["budget"][t][R] = {"mean_adj_per_game": round(m, 2),
                                   "p90": round(p90, 1)}
            print(f"    cooldown R={R}: adjudications/game mean={m:.1f} "
                  f"p90={p90:.0f}")

    # cost table for the leading cells
    print("\n== cost table (cpu-s/fork anchors 0.718 / 1.11 / 1.917) ==")
    for t in (13, 14):
        for R in (5, 8):
            m = res["budget"][t][R]["mean_adj_per_game"]
            for pname in ("P_m5", "P_scr"):
                ff = res["procedures"][pname]["forks_per_fire"]
                for tag, cps in (("bm-unl", 0.718), ("rm", 1.11),
                                 ("bm-l50", 1.917)):
                    mins = m * ff * cps / 60
                    print(f"  dsh>={t} R={R} {pname} {tag}: "
                          f"{mins:.1f} min/game extra; "
                          f"600 B-games = {600*mins/60:.0f} core-h")

    with open(os.path.join(OUT, "trigger_roc3.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'trigger_roc3.json')}")


if __name__ == "__main__":
    main()
