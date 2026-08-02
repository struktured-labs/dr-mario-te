#!/usr/bin/env python3
"""Does garbage DECIDE anything? A direct causal test, not a comparison of two win rates.

CONTEXT: winner-vs-r47 scores 78.3% [73.3,83.3] with garbage ON and 79.6% [74.6,84.2] with
it OFF. Those CIs overlap almost entirely, which HINTS that garbage is inert -- but two
overlapping interval estimates are weak evidence, and a lopsided matchup could hide an
effect that matters between near-equal arms.

THIS IS THE DIRECT TEST. Everything downstream of the seed is deterministic, so the same
(seed, swap) can be replayed with garbage ON and OFF and the two outcomes compared
match-by-match. That measures the quantity we actually care about:

    P(garbage changes who wins)

which no comparison of aggregates can give you. Run for a LOPSIDED matchup (winner vs r47)
and an EVEN one (winner vs itself), because the even matchup is where a small perturbation
has the most room to flip an outcome.

★ CAVEAT TO CARRY INTO ANY CONCLUSION: the attack rate is a property of the POLICY, not of
the game. Our brain makes 0.80 doubles per 100 placements (task#62 measured 0.98 for this
arm; pro humans 1.18). "Garbage rarely decides" is therefore partly endogenous -- it is a
statement about how seldom THIS policy attacks, not proof that VS play cannot be won by
attacking. It does mean a search that scores VS win rate has almost no attacking gradient
to climb.
"""
from __future__ import annotations
import sys, os, json, argparse
from concurrent.futures import ProcessPoolExecutor

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from h2h_vs import WINNER, R47, ARMS, boot_ci, _play
from sweep_knobs import _dec, _warm


def _one(job):
    seed, swap, cand, ref, cfg = job
    c = _dec(cand, cfg["topk2"]); r_ = _dec(ref, cfg["topk2"])
    f = lambda d: (lambda b, cu, nx: d.choose(b, cu, nx))
    a, b = (c, r_) if not swap else (r_, c)
    side = 0 if not swap else 1
    out = {}
    for gb in (True, False):
        c2 = dict(cfg); c2["garbage"] = gb; c2["nes_pills"] = True
        r = _play(c2, seed, f(a), f(b))
        atk = r.get("attacks_sent") or r.get("attacks") or [0, 0]
        out["on" if gb else "off"] = (r["winner"], r["reason"], sum(atk), r["pills"][side])
    return seed, swap, side, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--seed0", type=int, default=400)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--cand", default="winner")
    ap.add_argument("--ref", default="r47")
    ap.add_argument("--rule", default="rom", choices=("rom", "exact"))
    a = ap.parse_args()

    cfg = {"level": a.level, "max_pills": 300, "chain_mode": "first", "topk2": 8,
           "rule": a.rule, "nes_pills": True}
    cand = ARMS[a.cand]; ref = ARMS[a.ref]
    jobs = [(s, sw, cand, ref, cfg)
            for s in range(a.seed0, a.seed0 + a.seeds) for sw in (0, 1)]

    with ProcessPoolExecutor(max_workers=a.workers, initializer=_warm, initargs=(8,)) as ex:
        rows = list(ex.map(_one, jobs, chunksize=2))

    flips = 0; any_atk = 0; flip_when_atk = 0; pill_diff = 0
    for seed, swap, side, o in rows:
        won_on = o["on"][0] == side
        won_off = o["off"][0] == side
        if won_on != won_off:
            flips += 1
        if o["on"][2] > 0:
            any_atk += 1
            if won_on != won_off:
                flip_when_atk += 1
        pill_diff += abs(o["on"][3] - o["off"][3])

    n = len(rows)
    lo, hi = boot_ci([1.0 if (o["on"][0] == side) != (o["off"][0] == side) else 0.0
                      for _s, _w, side, o in rows])

    # ★ THE STATISTIC THAT ACTUALLY DECIDES THE QUESTION. A high flip rate says garbage is
    # POWERFUL; it does not say garbage FAVOURS either arm. Flips can be symmetric noise --
    # and in a self-vs-self run they must be, by construction. What matters for tuning is
    # whether garbage SHIFTS THE MEAN, so pair ON against OFF per (seed,swap) and bootstrap
    # the DIFFERENCE. Comparing two separately-computed CIs (as I first did) cannot do this.
    diff = [(1.0 if o["on"][0] == side else 0.0) - (1.0 if o["off"][0] == side else 0.0)
            for _s, _w, side, o in rows]
    dlo, dhi = boot_ci(diff)
    dmean = sum(diff) / len(diff)
    print(f"GARBAGE IMPACT  L{a.level}  {a.cand} vs {a.ref}  real NES capsules")
    print(f"  {n} matches replayed identically with garbage ON and OFF")
    print()
    print(f"  matches where garbage CHANGED THE WINNER : {flips}/{n} = {flips/n:.1%}"
          f"   95% CI [{lo:.1%}, {hi:.1%}]")
    print(f"  matches with >=1 attack landed            : {any_atk}/{n} = {any_atk/n:.1%}")
    if any_atk:
        print(f"  ...of those, garbage flipped the winner  : {flip_when_atk}/{any_atk} "
              f"= {flip_when_atk/any_atk:.1%}")
    print(f"  mean |pill-count change| from garbage     : {pill_diff/n:.2f} placements")
    print()
    print(f"  PAIRED shift in candidate win rate, ON - OFF : {dmean:+.1%}"
          f"   95% CI [{dlo:+.1%}, {dhi:+.1%}]")
    print()
    if dlo <= 0 <= dhi:
        print("  => garbage is POWERFUL but UNBIASED for this matchup: it flips outcomes,")
        print("     yet does not favour either arm, so it adds VARIANCE to the h2h without")
        print("     moving the mean. Tuning against VS win rate then pays the variance cost")
        print("     of garbage while getting no new gradient from it.")
    else:
        print("  => garbage SHIFTS the matchup. VS win rate is genuinely a different")
        print("     objective from the solo race here.")


if __name__ == "__main__":
    main()
