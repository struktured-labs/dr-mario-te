"""Score a silfid Mesen replay: landing == silicon (canonical) overall / on the silicon-only set; GO-log stats."""
import load, sys, os, re, collections, json
S = "/home/struktured/projects/dr_mario_rl/tmp/silfid/mesen/runs"
def canon(a, cur):
    if a is None or a < 0: return None
    return (a // 16) * 16 + a % 8 if cur[0] == cur[1] else a
def lands(tag, root=S):
    path = os.path.join(root, tag, f"lateflip_{tag}.log")
    L = {}; gos = collections.Counter(); pre = []
    for ln in open(path, errors="replace"):
        if ln.startswith("LAND p"):
            m = re.match(r"LAND p(\d+) f=(\d+) x=(\d+) y=(\d+) rot=(\d+) action=(\d+)", ln)
            L[int(m.group(1))] = int(m.group(6))
        elif ln.startswith("GO n="):
            k = re.search(r"kind=(\w+) preempt=(\w+) prev_k=(-?\d+)", ln)
            gos[(k.group(1), k.group(2))] += 1
            if k.group(2) == "true": pre.append(ln.strip())
    return L, gos, pre
def score(game, tag, root=S, verbose=False):
    FI = load.fidelity(); MI = load.misses()
    L, gos, pre = lands(tag, root)
    n = eq = so_n = so_eq = fin = 0; changed = []
    for (g, p), f in FI.items():
        if g != game or p not in L: continue
        cur = f["cur"]; s = canon(f["silicon"], cur); m = canon(L[p], cur)
        n += 1; eq += (s == m); fin += (m == canon(f["copro_final"], cur))
        if (MI.get((g, p)) or {}).get("silicon_only"):
            so_n += 1; so_eq += (s == m)
            if s == m: changed.append(p)
    return dict(game=game, tag=tag, n=n, eq_sil=eq, eq_final=fin, so_n=so_n, so_reproduced=so_eq, so_pills=changed,
                gos=dict((f"{a}/{b}", v) for (a, b), v in gos.items()), preempts=pre)
if __name__ == "__main__":
    for spec in sys.argv[1:]:
        g, tag = spec.split(":")
        r = score(g, tag)
        print(json.dumps({k: v for k, v in r.items() if k != "preempts"}), "preempt lines:", r["preempts"][:5])
