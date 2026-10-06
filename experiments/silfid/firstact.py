"""First-action timing: silicon vs Mesen (frames since spawn, silicon shifted by OFF), interval-censored for gaps."""
import load, collections, sys
OFF = 1
def first_change(seq, f0pose):
    """seq sorted (f, pose); returns (lo, hi): action happened in frames (lo, hi] w.r.t. visible frames"""
    last_same = None
    for f, pose in seq:
        same = (pose[0], pose[2], pose[3]) == (f0pose[0], f0pose[2], f0pose[3])
        if same: last_same = f
        else: return (last_same, f, pose)
    return (last_same, None, None)

res = collections.defaultdict(list)
for g in load.GAMES:
    T, land, inj = load.mesen(g); Q = load.cases(g); MI = load.misses(); FI = load.fidelity()
    for p, tr in sorted(T.items()):
        q = Q.get(p)
        if not q or not tr: continue
        cur = tuple(q["cur"])
        mseq = [(d["f"], load.mpose(d, cur)) for d in tr]
        sseq = sorted((f - OFF, load.spose(s, cur)) for f, s in load.sil_frames(q).items())
        sp0 = ("H", 0, 3, cur)
        ml, mh, mp = first_change(mseq, sp0)
        sl, sh, spp = first_change(sseq, sp0)
        mi = MI.get((g, p)); so = (mi or {}).get("silicon_only")
        fi = FI.get((g, p), {})
        grp = "silicon_only" if so else ("sil==mes" if fi.get("mesen_fair_eq_sil") else "other")
        if mh is None or sh is None: continue
        if sl is None or sh - sl > 1: continue            # need a tight silicon bracket
        res[grp].append((sh - mh, g, p))
for grp, xs in res.items():
    c = collections.Counter(d for d, g, p in xs)
    print(grp, len(xs), sorted(c.items()))

if __name__ == "__main__" and len(sys.argv) > 1:
    want = int(sys.argv[1])
    for grp, xs in res.items():
        for d, g, p in xs:
            if d != want: continue
            T, land, inj = load.mesen(g); Q = load.cases(g)
            q = Q[p]; cur = tuple(q["cur"]); tr = T[p]
            sf = load.sil_frames(q)
            print("==", grp, g, p, "d", d, "cur", cur)
            for dd in tr[:16]:
                s = sf.get(dd["f"] + OFF)
                print("  f%2d mes %s k=%d mb=%d,%d pad=%02X proph=%02X | sil %s" % (dd["f"], load.mpose(dd, cur), dd["k"], dd["mbc"], dd["mbo"], dd["pad"], dd["proph"], None if s is None else load.spose(s, cur)))
            break
