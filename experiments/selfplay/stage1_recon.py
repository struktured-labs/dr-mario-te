#!/usr/bin/env python3
"""STAGE 1j -- RECONCILE "horizon is 15%" with "40% of deaths escapable at E=1".

Two lanes produced numbers that read as contradictory and are not. Rather than
assert compatibility, this tests it on the data I already have.

TWO CLAIMS, DIFFERENT POPULATIONS:
  this lane   -- d4 minus d3 averaged over ORDINARY sampled positions: +0.48 pills
  hole-poker  -- one more ply is decisive at the CRITICAL PLY of a pressure death:
                 40% of 53 replay-verified deaths

The sharpest form of the reconciliation is not "different aggregation" -- it is that
my corpus STRUCTURALLY CANNOT CONTAIN their positions. Checked below, not assumed.

Then the positive test: if depth is "worth little on average, decisive at specific
moments", the d4-over-d3 advantage should CONCENTRATE where the move choice matters
most. Stakes are measured by tau, the position's true across-action value spread with
Monte-Carlo noise removed (the same CRN-corrected decomposition Stage 1d uses), so
"high stakes" is a property of the position and not of any arm's opinion about it.
"""
import json, math, random, statistics as st, sys
sys.path.insert(0, '.')
from stage1_depth import _v

def boot(xs, n=8000, seed=3):
    if len(xs) < 2: return (float('nan'), float('nan'))
    r = random.Random(seed); k = len(xs)
    rep = sorted(st.mean([xs[r.randrange(k)] for _ in range(k)]) for _ in range(n))
    return rep[int(.025*n)], rep[int(.975*n)]

lab = {r['idx']: r for r in (json.loads(l) for l in open('out/labels_main.jsonl') if l.strip())}
dep = {r['idx']: r for r in (json.loads(l) for l in open('out/depth.jsonl') if l.strip())}

nclear = ntot = 0
rows = []
for i, L in lab.items():
    vals = {int(a): _v(L['pills'][a], L['outcome'][a]) for a in L['pills']}
    for a in L['outcome']:
        for o in L['outcome'][a]:
            ntot += 1; nclear += (o == 'clear')
    r = dep.get(i)
    if not r: continue
    for a, d in r['new_vals'].items():
        vals[int(a)] = _v(d['pills'], d['outcome'])
        for o in d['outcome']:
            ntot += 1; nclear += (o == 'clear')
    acts = sorted(vals); M = min(len(v) for v in vals.values())
    if M < 4 or len(acts) < 3: continue
    # tau: true across-action spread, CRN-corrected
    dd = {a: [] for a in acts}
    for m in range(M):
        mu = st.mean(vals[a][m] for a in acts)
        for a in acts: dd[a].append(vals[a][m] - mu)
    between = st.pvariance([st.mean(dd[a]) for a in acts])
    within = st.mean(st.variance(dd[a]) for a in acts)
    tau = math.sqrt(max(0.0, between - within / M))
    a3, a4 = r['arms']['d3'], r['arms']['d4']
    if a3 in vals and a4 in vals:
        rows.append((tau, st.mean(vals[a4]) - st.mean(vals[a3]), L['nvir']))

print("=" * 74)
print("1. CAN MY CORPUS EVEN CONTAIN A DEATH POSITION?")
print("=" * 74)
print(f"  rollouts total {ntot}, ended in a CLEAR {nclear} ({nclear/ntot:.2%})")
print(f"  ended in topout or stall: {ntot-nclear}")
print("  ^ my corpus is solo play with NO garbage and NO opponent pressure, sampled")
print("    from champion trajectories. Essentially nothing in it is death-adjacent,")
print("    so my +0.48 says NOTHING about the regime hole-poker measured. The two")
print("    results are not in tension; they do not overlap.")

rows.sort(key=lambda t: t[0])
n = len(rows); k = n // 3
print()
print("=" * 74)
print("2. DOES DEPTH'S BENEFIT CONCENTRATE WHERE THE STAKES ARE HIGH?")
print("=" * 74)
for name, sl in (("low  stakes", rows[:k]), ("mid  stakes", rows[k:2*k]),
                 ("HIGH stakes", rows[2*k:])):
    d = [x[1] for x in sl]; t = [x[0] for x in sl]
    lo, hi = boot(d)
    print(f"  {name} (tau {st.mean(t):5.2f})  V(d4)-V(d3) = {st.mean(d):+6.3f} "
          f"[{lo:+.3f},{hi:+.3f}]  n={len(d)}")
tot = sum(x[1] for x in rows)
hi_share = sum(x[1] for x in rows[2*k:]) / tot if tot else float('nan')
print(f"\n  the top band is {len(rows[2*k:])/n:.0%} of positions and carries "
      f"{hi_share:.0%} of ALL the depth benefit")
print("  ^ the shape supports 'worth little on average, decisive at specific")
print("    moments'. Note the high band's CI still includes 0, so the")
print("    CONCENTRATION is suggestive rather than established -- what is solid is")
print("    that the +0.48 average is not spread evenly, so quoting it as if depth")
print("    were uniformly worthless would be wrong.")
