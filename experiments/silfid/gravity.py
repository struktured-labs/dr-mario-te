"""Gravity check: silicon frames-per-row (free fall, from the video) vs Mesen's (replay injects spu = p//10)."""
import load, collections
def steps(seq):
    """frames at which the row increases by exactly 1, before any slam (diff==1 runs ignored)"""
    rows = [(f, pose[1] + (1 if pose[0] == "V" else 0)) for f, pose in seq]   # V row = top cell; use bottom
    ch = [f for (f0, r0), (f, r) in zip(rows, rows[1:]) if r == r0 + 1 and f == f0 + 1]
    return ch
tot = collections.Counter(); bad = []
for g in load.GAMES:
    T, land, inj = load.mesen(g); Q = load.cases(g)
    for p, tr in sorted(T.items()):
        q = Q.get(p)
        if not q or not tr: continue
        cur = tuple(q["cur"])
        mseq = [(d["f"], load.mpose(d, cur)) for d in tr]
        sseq = sorted((f - 1, load.spose(s, cur)) for f, s in load.sil_frames(q).items())
        ms, ss = steps(mseq), steps(sseq)
        mi = [b - a for a, b in zip(ms, ms[1:])]; si = [b - a for a, b in zip(ss, ss[1:])]
        # modal free-fall interval (> 2 frames, i.e. not slam)
        mm = collections.Counter(x for x in mi if x > 2).most_common(1)
        sm = collections.Counter(x for x in si if x > 2).most_common(1)
        if not mm or not sm: continue
        tot[(mm[0][0] == sm[0][0])] += 1
        if mm[0][0] != sm[0][0]: bad.append((g, p, mm[0][0], sm[0][0], q["p"] // 10))
print(tot); print(bad[:40])
print()
by = collections.defaultdict(collections.Counter)
for g in load.GAMES:
    pass
import json
allp = collections.defaultdict(lambda: collections.Counter())
for g in load.GAMES:
    T, land, inj = load.mesen(g); Q = load.cases(g)
    for p, tr in sorted(T.items()):
        q = Q.get(p)
        if not q or not tr: continue
        cur = tuple(q["cur"])
        mseq = [(d["f"], load.mpose(d, cur)) for d in tr]
        sseq = sorted((f - 1, load.spose(s, cur)) for f, s in load.sil_frames(q).items())
        ms, ss = steps(mseq), steps(sseq)
        mi = [b - a for a, b in zip(ms, ms[1:])]; si = [b - a for a, b in zip(ss, ss[1:])]
        mm = collections.Counter(x for x in mi if x > 2).most_common(1)
        sm = collections.Counter(x for x in si if x > 2).most_common(1)
        if not mm or not sm: continue
        allp[g][(p % 10, "same" if mm[0][0] == sm[0][0] else ("sil_faster" if sm[0][0] < mm[0][0] else "sil_slower"))] += 1
for g, c in allp.items():
    print(g, " ".join(f"{m}:{c[(m,'same')]}/{c[(m,'sil_faster')]}/{c[(m,'sil_slower')]}" for m in range(10)))
