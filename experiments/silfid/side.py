import load, sys
g, p = sys.argv[1], int(sys.argv[2]); tag = sys.argv[3] if len(sys.argv) > 3 else f"ctl_{g}_D"
import os
T = {}
for ln in open(f"/home/struktured/projects/dr_mario_rl/tmp/silfid/mesen/runs/{tag}/lateflip_{tag}.log", errors="replace"):
    if ln.startswith(f"T p{p} "):
        m = load.TRE.match(ln); d = dict(zip(load.KEYS, [int(x, 16) if k in ("proph","pad","held","f8") else int(x) for k, x in zip(load.KEYS, m.groups())]))
        T[d["f"]] = d
q = load.cases(g)[p]; cur = tuple(q["cur"]); sf = load.sil_frames(q)
pt = load.pubtrace(g)[p]
print(g, p, "cur", cur, "pubs", [(t, a) for t, c, o, a in pt["pubs"]], "done", pt["done_f"], "final", pt["final"], "sil", q["actual_action"])
for f in range(1, max(T) + 1 if T else 30):
    d = T.get(f); s = sf.get(f + 1)
    mp = load.mpose(d, cur) if d else None
    print(f"f{f:2d} mes {mp} k={d['k'] if d else ''} tgt={d['tc'] if d else ''},{d['to'] if d else ''} mb={d['mbc'] if d else ''},{d['mbo'] if d else ''} lg={d['lgc'] if d else ''},{d['lgl'] if d else ''} eff={d['eff'] if d else ''} bud={d['bud'] if d else ''} pad={d['pad'] if d else 0:02X} | sil {load.spose(s, cur) if s else None}")
