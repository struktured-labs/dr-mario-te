"""Infer silicon's speedUps per pill from its free-fall interval; compare with the replay's spu = p//10."""
import load, collections, re
from gravity import steps
fpr = {}   # spu -> frames per row (from Mesen)
data = []
for g in load.GAMES:
    T, land, inj = load.mesen(g); Q = load.cases(g)
    for p, tr in sorted(T.items()):
        q = Q.get(p)
        if not q or not tr: continue
        spu = int(re.search(r"spu=(\d+)", inj[p]).group(1))
        thr = max(d["grav"] for d in tr)
        fpr.setdefault(spu, collections.Counter())[thr + 1] += 1
        cur = tuple(q["cur"])
        sseq = sorted((f - 1, load.spose(s, cur)) for f, s in load.sil_frames(q).items())
        ss = steps(sseq); si = [b - a for a, b in zip(ss, ss[1:]) if b - a > 2]
        data.append((g, p, spu, si))
tab = {s: c.most_common(1)[0][0] for s, c in fpr.items()}
print("spu->frames/row:", sorted(tab.items()))
inv = collections.defaultdict(list)
for s, v in tab.items(): inv[v].append(s)
for g in load.GAMES:
    line = []
    for gg, p, spu, si in data:
        if gg != g or len(si) < 2: continue
        c = collections.Counter(si).most_common(1)[0]
        if c[1] < 2: continue
        sil_spus = inv.get(c[0], [])
        line.append((p, spu, c[0], tab.get(spu), min(sil_spus) if sil_spus else None, max(sil_spus) if sil_spus else None))
    # implied ROM pill counter: silicon spu range -> pill index range
    print(g, " ".join(f"p{p}:{a}/{b}" for p, s, a, b, lo, hi in line if a != b)[:1500])
