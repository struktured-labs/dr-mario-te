"""First silicon-vs-Mesen divergence per pill (offset +1 f), with event classification."""
import load, collections, json, sys
OFF = 1
def events(seq):
    """seq: list of (f, pose) sorted; returns list of (f, kind) for orientation/col changes"""
    ev = []; prev = None
    for f, (hv, row, col, cols) in seq:
        if prev is not None:
            ph, pr, pc, pcols = prev
            if (hv, cols) != (ph, pcols): ev.append((f, "rot"))
            if col != pc: ev.append((f, "L" if col < pc else "R"))
        prev = (hv, row, col, cols)
    return ev

def analyse(game):
    T, land, inj = load.mesen(game); Q = load.cases(game); FI = load.fidelity(); MI = load.misses()
    out = []
    for p, tr in sorted(T.items()):
        q = Q.get(p)
        if not q: continue
        cur = tuple(q["cur"]); sf = load.sil_frames(q)
        mseq = [(d["f"], load.mpose(d, cur)) for d in tr]
        sseq = sorted((f - OFF, load.spose(s, cur)) for f, s in sf.items())
        lastf = tr[-1]["f"]
        sseq = [x for x in sseq if x[0] <= lastf + 2]
        md = dict(mseq); first = None
        for f, sp in sseq:
            mp = md.get(f)
            if mp is None: continue
            if (sp[0], sp[2], sp[3]) != (mp[0], mp[2], mp[3]):
                first = (f, sp, mp); break
        go = next((d["f"] - d["k"] for d in tr if d["k"] > 0), None)   # Mesen GO frame (k counts frames since GO)
        fi = FI.get((game, p), {}); mi = MI.get((game, p))
        out.append(dict(game=game, p=p, first=first, go=go, sil=fi.get("silicon"), mes=fi.get("mesen_fair"),
                        fin=fi.get("copro_final"), sil_only=(mi or {}).get("silicon_only"), label=(mi or {}).get("label"),
                        sev=events(sseq), mev=events(mseq), lastf=lastf))
    return out

if __name__ == "__main__":
    allr = []
    for g in load.GAMES: allr += analyse(g)
    json.dump(allr, open("diverge.json", "w"))
    so = [r for r in allr if r["sil_only"]]
    print("silicon-only:", len(so))
    c = collections.Counter()
    for r in so:
        if r["first"] is None: c["no-divergence-seen"] += 1; continue
        f, sp, mp = r["first"]
        kind = ("orient" if (sp[0], sp[3]) != (mp[0], mp[3]) else "") + ("col" if sp[2] != mp[2] else "")
        c[kind] += 1
    print(c)
    for r in so[:60]:
        f = r["first"]
        print(r["game"], r["p"], r["label"], "go", r["go"], "first", None if f is None else (f[0], f[1][0], f[1][2], f[2][0], f[2][2]),
              "| sil ev", r["sev"][:8], "| mes ev", r["mev"][:8])
