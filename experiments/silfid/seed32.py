"""silfid: per-game seed-class verdict over all 32 behaviour classes (seed bits 1,3,4,5,7; bit 0 = 1).
Does ONE class explain most of a game's silicon-only residual? -> seed32_20261006.{txt,json}"""
import json, os, collections, load, score
G = ["m1g1", "m1g2", "m1g4", "m2g2", "m2g3"]
SEEDS = [1, 25, 11, 9, 3, 17, 19, 27, 153, 145, 155, 147, 161, 33, 35, 41, 43, 49, 51, 57, 59, 129, 131, 137, 139, 163,
         169, 171, 177, 179, 185, 187]
RUNS = "/home/struktured/projects/dr_mario_rl/tmp/silfid/mesen/runs"
MI = load.misses()
SO = {k for k, m in MI.items() if m.get("silicon_only")}
summ = json.load(open("/home/struktured/projects/dr-mario-h16-wt/experiments/silfid/summary_silfid_20261006.json"))
resid = {tuple(x) for x in summ["residual"]["pills"]}
out = {"classes_done": [], "per_game": {}}
lines = []
for g in G:
    so_g = {p for (gg, p) in SO if gg == g}; res_g = {p for (gg, p) in resid if gg == g}
    rows = []
    for s in SEEDS:
        t = f"seed{s}_{g}"; lp = os.path.join(RUNS, t, f"lateflip_{t}.log")
        if not os.path.exists(lp) or "SUMMARY" not in open(lp).read():
            continue
        r = score.score(g, t)
        rows.append((s, r["so_reproduced"], len(set(r["so_pills"]) & res_g), r["eq_sil"], r["n"], r["so_pills"]))
        if s not in out["classes_done"]: out["classes_done"].append(s)
    rows.sort(key=lambda x: -x[1])
    best = rows[0] if rows else None
    out["per_game"][g] = dict(silicon_only=len(so_g), residual77_in_game=len(res_g),
                              best=dict(seed=best[0], reproduced=best[1], of_residual=best[2], eq_sil=best[3]) if best else None,
                              classes=[dict(seed=a, reproduced=b, of_residual=c, eq_sil=d) for a, b, c, d, n, ps in rows],
                              union=len({p for r in rows for p in r[5]}))
    lines.append(f"{g}: silicon-only {len(so_g)}, of which in the 77-residual {len(res_g)}; best class s{best[0]} reproduces "
                 f"{best[1]} ({best[2]} of the residual); eq_sil {best[3]}/{best[4]}; union over {len(rows)} classes "
                 f"{out['per_game'][g]['union']}; 2nd best {rows[1][1] if len(rows) > 1 else '-'}" if best else f"{g}: none")
txt = "\n".join(lines) + f"\nclasses done: {len(out['classes_done'])}/32\n"
print(txt)
open("/home/struktured/projects/dr-mario-h16-wt/experiments/silfid/seed32_20261006.txt", "w").write(txt)
json.dump(out, open("/home/struktured/projects/dr-mario-h16-wt/experiments/silfid/seed32_20261006.json", "w"), indent=1)
