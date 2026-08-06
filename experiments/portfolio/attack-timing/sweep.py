#!/usr/bin/env python3
"""Paired seed-swapped VS sweep: HoldingDecider(threshold, K) vs the plain
champion (strand180_20). Mirrors h2h_vs.py's stats (seed-level pairing, side
swap, bootstrap CI over seeds) but drives vs_harness.play_match directly
since h2h_vs.py's ARMS/_mk machinery only builds constant-dict deciders, not
a stateful wrapper like HoldingDecider.

K=0 is the champion vs itself and is NOT run here -- by construction with
identical arms every seed scores exactly 0.5 (h2h_vs.py's own documented
sanity fact), so it's the analytic 50% baseline, not something to spend
matches measuring.
"""
from __future__ import annotations
import sys, os, json, time, argparse, random
import statistics as st
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src", ROOT + "/tmp/vs_aware"):
    if p not in sys.path:
        sys.path.insert(0, p)

import vs_harness as H
sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments")
import h2h_vs as hv  # reuse boot_ci / attacks_sent, do not re-derive the stats

_CFG = {}


class _B:
    def __init__(self, fn):
        self._fn = fn

    def choose(self, b, c, n):
        return self._fn(b, c, n)


def _init(cfg):
    global _CFG
    import fast_rtl_x as F
    import cascade_chain_x as C
    F.warmup_delta(topk2=cfg.get("topk2", 8))
    C.warmup_chain(topk2=cfg.get("topk2", 8))
    _CFG = cfg


def _one(job):
    from hold_decider import make_champion, make_holder
    seed, swap = job
    cfg = _CFG
    holder = make_holder(cfg["threshold"], cfg["K"], topk2=cfg["topk2"])
    champ = make_champion(topk2=cfg["topk2"])
    f_hold = lambda b, c, n, opp: holder.choose(b, c, n, opp)
    f_champ = H.blind(_B(lambda b, c, n: champ.choose(b, c, n)))
    dec0, dec1 = (f_hold, f_champ) if not swap else (f_champ, f_hold)
    r = H.play_match(seed, dec0, dec1, level=cfg["level"], max_pills=cfg["max_pills"],
                     nes_pills=True, garbage=True)
    side = 0 if not swap else 1
    win = 1.0 if r["winner"] == side else (0.0 if r["winner"] >= 0 else 0.5)
    margin = r["margin"] if side == 0 else -r["margin"]
    sent_c, sent_r = hv.attacks_sent(r, side), hv.attacks_sent(r, 1 - side)
    return {"seed": seed, "swap": swap, "win": win, "margin": margin,
            "reason": r["reason"], "draw": r["winner"] < 0,
            "atk_cand": sent_c, "atk_ref": sent_r,
            "held": holder.stats["held"],
            "cashed_vulnerable": holder.stats["cashed_vulnerable"],
            "cashed_forced": holder.stats["cashed_forced"]}


def run_arm(threshold, K, seeds, workers, level, max_pills, topk2):
    cfg = {"threshold": threshold, "K": K, "level": level, "max_pills": max_pills,
           "topk2": topk2}
    jobs = [(s, sw) for s in seeds for sw in (0, 1)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(cfg,)) as ex:
        rows = list(ex.map(_one, jobs, chunksize=1))
    dt = time.time() - t0

    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["seed"], []).append(r)
    wr_seed = [sum(x["win"] for x in rs) / len(rs) for rs in by_seed.values()]
    mg_seed = [sum(x["margin"] for x in rs) / len(rs) for rs in by_seed.values()]
    lo, hi = hv.boot_ci(wr_seed)
    mlo, mhi = hv.boot_ci(mg_seed)
    dec = [w for w in wr_seed if w != 0.5]
    decisive = len(dec) / len(wr_seed) if wr_seed else float("nan")
    wr_dec = (sum(dec) / len(dec)) if dec else float("nan")
    n_held = sum(r["held"] for r in rows if r["swap"] == 0)
    n_vuln = sum(r["cashed_vulnerable"] for r in rows if r["swap"] == 0)
    n_forced = sum(r["cashed_forced"] for r in rows if r["swap"] == 0)
    return {
        "threshold": threshold, "K": K,
        "n_seeds": len(by_seed), "n_matches": len(rows),
        "winrate": sum(wr_seed) / len(wr_seed), "wr_lo": lo, "wr_hi": hi,
        "margin": st.mean(mg_seed), "mg_lo": mlo, "mg_hi": mhi,
        "draws": sum(1 for r in rows if r["draw"]),
        "atk_cand": sum(r["atk_cand"] for r in rows) / len(rows),
        "atk_ref": sum(r["atk_ref"] for r in rows) / len(rows),
        "decisive": decisive, "wr_decisive": wr_dec,
        "held_per_match": n_held / (len(rows) / 2), "vuln_cashes": n_vuln,
        "forced_cashes": n_forced,
        "sec_per_match": dt / len(rows) * workers, "wall_s": dt,
    }


def fmt(r):
    return (f"thr={r['threshold']:<3} K={r['K']}  winrate {r['winrate']:6.1%}  "
            f"95% CI [{r['wr_lo']:.1%}, {r['wr_hi']:.1%}]  margin {r['margin']:+5.2f} "
            f"[{r['mg_lo']:+.2f},{r['mg_hi']:+.2f}]  n={r['n_seeds']}  "
            f"held/match {r['held_per_match']:.2f}  vuln_cash {r['vuln_cashes']} "
            f"forced_cash {r['forced_cashes']}  atk {r['atk_cand']:.2f}v{r['atk_ref']:.2f}  "
            f"moved {r['decisive']:.0%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresholds", default="8,11", help="comma list of opponent-height thresholds")
    ap.add_argument("--Ks", default="1,2,3", help="comma list of hold budgets")
    ap.add_argument("--seed0", type=int, default=500)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--topk2", type=int, default=8)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    thresholds = [int(x) for x in a.thresholds.split(",")]
    Ks = [int(x) for x in a.Ks.split(",")]
    seeds = list(range(a.seed0, a.seed0 + a.seeds))

    print(f"attack-timing sweep: seeds {a.seed0}..{a.seed0+a.seeds-1} (n={a.seeds}), "
          f"thresholds={thresholds}, Ks={Ks}, workers={a.workers}")
    results = []
    for thr in thresholds:
        for K in Ks:
            r = run_arm(thr, K, seeds, a.workers, a.level, a.max_pills, a.topk2)
            results.append(r)
            print(fmt(r), flush=True)
    if a.out:
        json.dump(results, open(a.out, "w"), indent=2)
        print("wrote", a.out)


if __name__ == "__main__":
    main()
