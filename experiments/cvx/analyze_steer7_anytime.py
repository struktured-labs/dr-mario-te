"""STEER7 desk analysis: summarise steer7_anytime.py rows (the firmware's anytime publish trajectory on real boards).

  python analyze_steer7_anytime.py steer7/anytime_10games.jsonl
"""
import sys, json
import numpy as np

CLK_PER_LEAF = 1849.0
FRAME_CLK = 85.909e6 / 60.0988
F = lambda leaves: np.asarray(leaves, float) * CLK_PER_LEAF / FRAME_CLK
TS = (1.5, 3.0, 6.0, 9.0, 12.5, 20.0)           # frames after GO; couch MIN_THINK = 12 hooks = 6 f


def best_at(r, t):
    """Running best (action) published at t frames after GO, or None (mailbox still $FF)."""
    a = None
    for leaves, act in r["pubs"]:
        if F(leaves) <= t:
            a = act
    return a


def q(x, ps=(50, 75, 90, 95)):
    x = np.asarray(x, float)
    return " ".join(f"p{p} {np.percentile(x, p):.1f}" for p in ps) + f" mean {x.mean():.1f}"


def block(R, label):
    print(f"\n[{label}] boards {len(R)}")
    if not R:
        return
    tot = np.array([r["total"] for r in R])
    print(f"  leaves/search: median {np.median(tot):,.0f} (pass0 {np.median([r['pass0'] for r in R]):.0f}, ply2 "
          f"{np.median([r['ply2'] for r in R]):,.0f}, ply3 {np.median([r['ply3'] for r in R]):,.0f}; ply3 share "
          f"{sum(r['ply3'] for r in R) / tot.sum():.3f}); roots {np.median([r['roots'] for r in R]):.0f}")
    print(f"  GO->DONE frames (x {CLK_PER_LEAF:.0f} clk/leaf): {q(F(tot))}")
    print(f"  first publish f: {q(F([r['first_pub'] for r in R]))}")
    print(f"  FINAL answer first published at f: {q(F([r['stab'] for r in R]))}   (fraction of search: median "
          f"{np.median([r['stab'] / r['total'] for r in R]):.2f})")
    print(f"  publishes/search {q([r['npub'] for r in R])}; final answer's position in the processing order "
          f"(0 = first root) {q([r['final_rank'] for r in R])}")
    for t in TS:
        acts = [best_at(r, t) for r in R]
        same = np.mean([a == r["final"] for a, r in zip(acts, R)])
        same_o = np.mean([a is not None and a // 8 == r["final"] // 8 for a, r in zip(acts, R)])
        none = np.mean([a is None for a in acts])
        done = np.mean([F(r["total"]) <= t for r in R])
        print(f"  t = GO + {t:4.1f} f: running best == final {100 * same:5.1f}%  same orient {100 * same_o:5.1f}%  "
              f"no publish yet {100 * none:4.1f}%  search DONE {100 * done:5.1f}%")


if __name__ == "__main__":
    R = [json.loads(l) for l in open(sys.argv[1])]
    print(f"rows {len(R)}; final == Leaf6Decider.choose on {sum(r['final'] == r['ref'] for r in R)}")
    block(R, "all decisions")
    for lo, hi, name in ((0, 4, "1-4 viruses (dist_target active)"), (5, 12, "5-12 viruses"), (13, 24, "13-24 viruses"),
                         (25, 99, "25+ viruses")):
        block([r for r in R if lo <= r["nv"] <= hi], name)
