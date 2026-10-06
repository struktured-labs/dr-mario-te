"""Slam (fast-drop) onset: silicon vs Mesen per pill -> a proxy for the frame the cart saw DONE."""
import load, collections, sys
def bottom_rows(seq):
    return [(f, pose[1] + (1 if pose[0] == "V" else 0)) for f, pose in seq]
def slam_onset(seq):
    r = bottom_rows(seq)
    for i in range(len(r) - 3):
        (f0, a), (f1, b), (f2, c), (f3, d) = r[i:i + 4]
        if f3 - f0 <= 4 and d - a >= 2 and f1 == f0 + 1 and f2 == f1 + 1 and f3 == f2 + 1:
            # first row increase in this burst
            j = i
            while j > 0 and r[j][1] == r[j - 1][1] and r[j][0] == r[j-1][0] + 1: j -= 1
            for k in range(i, i + 4):
                if r[k + 1][1] > r[k][1]: return r[k + 1][0]
    return None
res = collections.defaultdict(list)
MI = load.misses()
for g in load.GAMES:
    T, land, inj = load.mesen(g, tag=f"ctl_{g}_D") if False else load.mesen(g)
    Q = load.cases(g); FI = load.fidelity()
    for p, tr in T.items():
        q = Q.get(p)
        if not q: continue
        cur = tuple(q["cur"])
        ms = slam_onset([(d["f"], load.mpose(d, cur)) for d in tr])
        ss = slam_onset(sorted((f - 1, load.spose(s, cur)) for f, s in load.sil_frames(q).items()))
        if ms is None or ss is None: continue
        so = (MI.get((g, p)) or {}).get("silicon_only")
        grp = "silicon_only" if so else ("agree" if FI[(g, p)]["mesen_fair_eq_sil"] else "other")
        res[grp].append(ss - ms)
for grp, xs in res.items():
    c = collections.Counter(xs)
    print(grp, len(xs), sorted(c.items()))
