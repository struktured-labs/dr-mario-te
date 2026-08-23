#!/usr/bin/env python3
"""score_e1b.py -- E1b (near-death survival), paired ship vs slice.

Readable from the banked artifacts WITHOUT catching a match ending: a side is
NEAR-DEATH while it has occupied cells in playfield rows 0-2 (the prereg's key).
An EXCURSION is a contiguous run of such samples inside one match.
  survived : occ_top3 returns to 0 later in the SAME match
  died     : the match ends while the side is still above the line
Excursions still open at the end of the cycle are censored, not scored.
"""
import sys, collections
import scan_winner as S

def occ(win, b, n=3):
    return sum(1 for r in range(n) for c in range(8) if win[b + r*8 + c] != 0xFF)

def segments(samples):
    """match segments as (start,end) index pairs, end exclusive."""
    b = [0] + S.boundaries(samples) + [len(samples)]
    return [(b[i], b[i+1]) for i in range(len(b)-1)]

def score(rows):
    out = collections.defaultdict(lambda: collections.Counter())
    for (seed, arm), samples in rows.items():
        for (a, z) in segments(samples):
            closed = z < len(samples)          # segment ended inside the cycle
            for side, board in (("P1", 0x400), ("P2", 0x500)):
                o = [occ(s["win"], board) for s in samples[a:z]]
                i = 0
                while i < len(o):
                    if o[i] == 0: i += 1; continue
                    j = i
                    while j < len(o) and o[j] > 0: j += 1
                    if j < len(o):                       # came back below the line
                        out[(seed, arm, side)]["survived"] += 1
                    elif closed:                          # match ended still above
                        out[(seed, arm, side)]["died"] += 1
                    else:
                        out[(seed, arm, side)]["censored"] += 1
                    i = j
    return out

def main(cache):
    rows = S.load(cache)
    sc = score(rows)
    for side in ("P1", "P2"):
        print(f"\n=== E1b  side {side} ===")
        tot = collections.Counter()
        per_arm = {"ship": collections.Counter(), "slice": collections.Counter()}
        for (seed, arm, s), c in sc.items():
            if s != side: continue
            tot.update(c); per_arm[arm].update(c)
        for arm in ("ship", "slice"):
            c = per_arm[arm]; n = c["survived"] + c["died"]
            r = 100*c["survived"]/n if n else float("nan")
            print(f"  {arm:5s} excursions={n:5d}  survived={c['survived']:5d}  died={c['died']:4d}  survival={r:5.1f}%  (censored {c['censored']})")
        # paired: seeds present in BOTH arms
        seeds = {sd for (sd, a, s) in sc if s == side and a == "ship"} & \
                {sd for (sd, a, s) in sc if s == side and a == "slice"}
        d_ship = d_slice = 0; n_ship = n_slice = 0
        for sd in seeds:
            a = sc[(sd, "ship", side)]; b = sc[(sd, "slice", side)]
            d_ship += a["survived"]; n_ship += a["survived"] + a["died"]
            d_slice += b["survived"]; n_slice += b["survived"] + b["died"]
        print(f"  PAIRED on {len(seeds)} seeds:  ship {100*d_ship/max(n_ship,1):5.1f}% ({n_ship})   "
              f"slice {100*d_slice/max(n_slice,1):5.1f}% ({n_slice})")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tmp_analysis/popA.pkl")
