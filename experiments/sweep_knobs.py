#!/usr/bin/env python3
"""One-at-a-time sensitivity screen of the eval constants against VS WIN RATE.

WHY A SCREEN AND NOT GREEDY DESCENT FIRST: coordinate descent accepts the best-looking
candidate at every step, so with 30 candidates it accepts noise roughly as eagerly as
signal -- that is the machine that produced two retracted "wins" on this project. A
one-at-a-time screen against a FIXED reference measures each knob's own effect with a CI,
costs the same, and tells you which knobs matter at all before anything is stacked.

PRIOR: `vs_env.py`'s own docstring names the hypothesis -- spawn(-150) and toprisk(-90) are
the eval's two largest penalties and have ONLY ever been exercised against self-inflicted
stacking, never against incoming garbage. Those knobs get the widest grids.

The pool is built ONCE and candidates travel in the job, so numba warms up per worker per
RUN rather than per candidate.
"""
from __future__ import annotations
import sys, os, json, time, argparse, random
import statistics as st
from concurrent.futures import ProcessPoolExecutor

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from h2h_vs import WINNER, R47, boot_ci, _mk, _play, attacks_sent

# RTL-friendly values {4,6,8,12,16,24,32,48,60} where the constant lives on that grid.
# toprisk/spawn are structural penalties, not on the small grid -- swept wider because the
# VS hypothesis points at them. Anything that wins gets snapped + gate-checked afterwards.
GRID = {
    "vrdy":    [4, 12, 16, 24],
    "buried":  [24, 32, 60],
    "rdyext":  [4, 12, 16],
    "setup":   [16, 24, 48, 60],
    "matched": [32, 60],
    "poll":    [4, 12],
    "maxh":    [6, 24],
    "holes":   [12, 32],
    "toprisk": [45, 60, 120, 180],
    "spawn":   [100, 200, 250, 300],
}

_D = {}


def _warm(topk2):
    import fast_rtl_x as F
    F.warmup_delta(topk2=topk2)


def _dec(cand, topk2):
    """Cached decider. Delegates to h2h_vs._mk so the name->index mapping has exactly ONE
    definition -- a second copy here silently diverged once and invalidated a whole holdout
    run (see the warning on h2h_vs.idx_map)."""
    key = (tuple(sorted(cand.items())), topk2)
    d = _D.get(key)
    if d is None:
        d = _D[key] = _mk(cand, topk2)
    return d


def _one(job):
    seed, swap, cand, ref, cfg = job
    c = _dec(cand, cfg["topk2"]); r_ = _dec(ref, cfg["topk2"])
    f = lambda d: (lambda b, cu, nx: d.choose(b, cu, nx))
    a, b = (c, r_) if not swap else (r_, c)
    r = _play(cfg, seed, f(a), f(b))
    side = 0 if not swap else 1
    win = 1.0 if r["winner"] == side else (0.0 if r["winner"] >= 0 else 0.5)
    mg = r["margin"] if side == 0 else -r["margin"]
    # ★ DIES-AHEAD. mg is candidate-relative; positive = candidate has FEWER viruses,
    # i.e. was AHEAD. "Topped out while winning the virus race" = lost AND topout AND
    # ahead. This is the endpoint that separated arms at p=1.6e-4 where WIN RATE saw
    # nothing at p=0.19 -- and it is the failure the owner names in real play.
    # NOTE: this file has its OWN _one/evaluate and does NOT call h2h_vs.run(). Two
    # rigs for one measurement is the fragmentation that hid the garbage-gravity bug;
    # instrumenting h2h_vs alone silently produced a 3h run with no dies-ahead data.
    topped = r["reason"] == "topout"
    da_c = 1 if (win == 0.0 and topped and mg > 0) else 0
    da_r = 1 if (win == 1.0 and topped and mg < 0) else 0
    return (seed, win, mg, r["winner"] < 0,
            attacks_sent(r, side), attacks_sent(r, 1 - side), da_c, da_r)


def evaluate(ex, cand, ref, seeds, cfg):
    jobs = [(s, sw, cand, ref, cfg) for s in seeds for sw in (0, 1)]
    rows = list(ex.map(_one, jobs, chunksize=2))
    by = {}
    for seed, win, mg, draw, ac, ar, dc, dr in rows:
        by.setdefault(seed, []).append((win, mg, draw, ac, ar, dc, dr))
    wr = [sum(x[0] for x in v) / len(v) for v in by.values()]
    mg = [sum(x[1] for x in v) / len(v) for v in by.values()]
    lo, hi = boot_ci(wr)
    mlo, mhi = boot_ci(mg)
    return {"winrate": sum(wr) / len(wr), "wr_lo": lo, "wr_hi": hi,
            "margin": st.mean(mg), "mg_lo": mlo, "mg_hi": mhi,
            "n_seeds": len(by), "n_matches": len(rows),
            "draws": sum(1 for v in by.values() for x in v if x[2]),
            "atk_cand": st.mean([x[3] for v in by.values() for x in v]),
            "atk_ref": st.mean([x[4] for v in by.values() for x in v]),
            "da_cand": sum(x[5] for v in by.values() for x in v),
            "da_ref": sum(x[6] for v in by.values() for x in v)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=160)
    ap.add_argument("--seed0", type=int, default=400)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--uniform", action="store_true")
    ap.add_argument("--chain-mode", default="first")
    ap.add_argument("--topk2", type=int, default=8)
    ap.add_argument("--only", default=None, help="comma-separated knob subset")
    ap.add_argument("--rule", default="rom", choices=("rom", "exact"))
    ap.add_argument("--out", default="../tmp/selfplay/screen.jsonl")
    a = ap.parse_args()

    cfg = {"level": a.level, "max_pills": a.max_pills, "nes_pills": not a.uniform,
           "chain_mode": a.chain_mode, "topk2": a.topk2, "rule": a.rule,
           "garbage": True}
    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    ref = dict(WINNER)
    knobs = a.only.split(",") if a.only else list(GRID)
    out = os.path.abspath(os.path.join(HERE, a.out)) if not os.path.isabs(a.out) else a.out
    os.makedirs(os.path.dirname(out), exist_ok=True)

    cap = "UNIFORM" if a.uniform else "REAL NES"
    print(f"SCREEN vs WINNER  L{a.level}  {cap} capsules  chain={a.chain_mode}  "
          f"seeds {a.seed0}..{a.seed0+a.seeds-1}  ({a.seeds} seeds = {2*a.seeds} matches/eval)",
          flush=True)
    print(f"reference = WINNER {WINNER}", flush=True)
    print(flush=True)

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_warm,
                             initargs=(a.topk2,)) as ex:
        # null: candidate IS the reference -> must be exactly 50.0% / 0.00 by construction
        r = evaluate(ex, dict(WINNER), ref, seeds[:20], cfg)
        print(f"  {'NULL (winner)':<18} winrate {r['winrate']:6.1%}  margin {r['margin']:+6.2f}"
              f"   <- must be exactly 50.0% / +0.00", flush=True)
        print(flush=True)
        with open(out, "w") as fh:
            for knob in knobs:
                for v in GRID[knob]:
                    if v == ref[knob]:
                        continue
                    cand = dict(ref); cand[knob] = v
                    r = evaluate(ex, cand, ref, seeds, cfg)
                    r["knob"] = knob; r["value"] = v; r["base"] = ref[knob]
                    fh.write(json.dumps(r) + "\n"); fh.flush()
                    sig = "  <-- CI EXCLUDES 50%" if r["wr_lo"] > 0.5 else (
                          "  (worse)" if r["wr_hi"] < 0.5 else "")
                    print(f"  {knob:>8}={v:<4} winrate {r['winrate']:6.1%} "
                          f"[{r['wr_lo']:.1%},{r['wr_hi']:.1%}]   margin {r['margin']:+6.2f} "
                          f"[{r['mg_lo']:+.2f},{r['mg_hi']:+.2f}]  atk {r['atk_cand']:.2f}"
                          f"v{r['atk_ref']:.2f}  DA {r['da_cand']}v{r['da_ref']}{sig}", flush=True)
    print(f"\ndone in {(time.time()-t0)/60:.1f} min -> {out}", flush=True)


if __name__ == "__main__":
    main()
