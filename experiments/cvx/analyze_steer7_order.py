"""STEER7 desk lever 4 (root ordering): how early is the FINAL answer published under alternative root orders?
Reads steer7_anytime.py v2 rows (per-root act / val / leaves / depth-2 key / ply-2 leaves, in FIRMWARE order).

Orders compared (the argmax is the same in all of them; only WHEN it is published changes):
  fw      today's firmware: roots by descending Pass-0 key (ply-1 imm + leaf)
  d2      a two-pass search: ply-2 for EVERY root first (cost: sum(1 + m2) extra leaves up front, conservatively not
          reused), then roots by descending depth-2 estimate (imm1 + leaf1 + (best ply-2 key - leaf1)/2 + root terms)
  oracle  the final answer first (a lower bound on any ordering)

  python analyze_steer7_order.py steer7/anytime_10games_v2.jsonl
"""
import sys, json
import numpy as np

CLK_PER_LEAF = 1849.0
FRAME_CLK = 85.909e6 / 60.0988
TS = (1.5, 3.0, 6.0, 9.0, 12.5)


def publishes(order, r, start):
    """[(time_f, act)] in the given processing order; running best replaces on strictly greater val."""
    out = []; best = None; cum = start
    for j in order:
        cum += r["roots_leaves"][j]
        if best is None or r["roots_val"][j] > best:
            best = r["roots_val"][j]; out.append((cum * CLK_PER_LEAF / FRAME_CLK, r["roots_act"][j]))
    return out


def at(pubs, t):
    a = None
    for tf, act in pubs:
        if tf <= t:
            a = act
    return a


def main(path):
    R0 = [json.loads(l) for l in open(path)]
    R0 = [r for r in R0 if "roots_act" in r]
    for label, R in (("all decisions", R0), ("endgame 1-4 viruses", [r for r in R0 if r["nv"] <= 4]),
                     ("5-12 viruses", [r for r in R0 if 5 <= r["nv"] <= 12])):
        print(f"[{label}]"); one(R)


def one(R):
    res = {k: {t: [] for t in TS} for k in ("fw", "d2", "oracle")}
    stab = {k: [] for k in res}
    for r in R:
        n = len(r["roots_act"]); fw = list(range(n))
        d2 = sorted(fw, key=lambda j: -r["roots_d2"][j])                 # stable: ties keep the firmware order
        fin = publishes(fw, r, r["pass0"])[-1][1]
        jf = next(j for j in fw if r["roots_act"][j] == fin)
        orc = [jf] + [j for j in fw if j != jf]
        pre = sum(1 + m for m in r["roots_m2"])
        for k, (order, start) in {"fw": (fw, r["pass0"]), "d2": (d2, r["pass0"] + pre), "oracle": (orc, r["pass0"])}.items():
            p = publishes(order, r, start)
            fk = p[-1][1]                                   # == fin except exact-value ties (first in order wins)
            stab[k].append(next(tf for tf, a in p if a == fk))
            for t in TS:
                res[k][t].append(at(p, t) == fk)
    print(f"boards {len(R)}")
    for k in res:
        s = np.array(stab[k])
        print(f"  {k:6s} final answer first published: median GO + {np.median(s):.1f} f, p75 {np.percentile(s, 75):.1f}, "
              f"p90 {np.percentile(s, 90):.1f}   P(final) at GO + " +
              "  ".join(f"{t:g} f: {100 * np.mean(res[k][t]):.1f}%" for t in TS))


if __name__ == "__main__":
    main(sys.argv[1])
