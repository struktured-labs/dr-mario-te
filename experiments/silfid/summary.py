"""silfid: the per-hypothesis tally of the 102 silicon-only misses -> summary_silfid_20261006.json"""
import json, os, collections
import load, score
G = ["m1g1", "m1g2", "m1g4", "m2g2", "m2g3"]
SEEDS = [1, 25, 11, 9, 3, 17, 19, 27, 153, 145, 155, 147]
RUNS = "/home/struktured/projects/dr_mario_rl/tmp/silfid/mesen/runs"
MI = load.misses()
SO = {(g, p) for (g, p), m in MI.items() if m.get("silicon_only")}
out = {"controls": {g: {k: score.score(g, f"ctl_{g}_D")[k] for k in ("n", "eq_sil", "eq_final")} for g in G}}
tags = collections.defaultdict(set)
for var, tag in [("shift1", "H2_shift+1"), ("shift-1", "H2_shift-1"), ("stale", "H2_stale_go_read"), ("spu2", "H6_spu+2")]:
    out[var] = {}
    for g in G:
        r = score.score(g, f"{var}_{g}"); out[var][g] = {k: r[k] for k in ("eq_sil", "eq_final", "so_reproduced", "so_pills", "gos")}
        tags[tag] |= {(g, p) for p in r["so_pills"]}
out["seed_classes"] = {}
best = {}
for s in SEEDS:
    for g in G:
        t = f"seed{s}_{g}"; lp = os.path.join(RUNS, t, f"lateflip_{t}.log")
        if not os.path.exists(lp) or "SUMMARY" not in open(lp).read():
            continue
        r = score.score(g, t)
        out["seed_classes"].setdefault(str(s), {})[g] = {k: r[k] for k in ("eq_sil", "eq_final", "so_reproduced", "so_pills")}
        tags["H5_seed_any_class"] |= {(g, p) for p in r["so_pills"]}
        if g not in best or r["so_reproduced"] > best[g][1]: best[g] = (s, r["so_reproduced"], r["so_pills"])
for g, (s, n, ps) in best.items(): tags["H5_seed_best_class"] |= {(g, p) for p in ps}
out["seed_best_class"] = {g: {"seed": s, "reproduced": n, "pills": ps} for g, (s, n, ps) in best.items()}
tags["PREV_TARGET_known_defect"] = {k for k in SO if MI[k]["label"] == "PREV-TARGET"}
tags["H2_any"] = tags["H2_shift+1"] | tags["H2_shift-1"] | tags["H2_stale_go_read"]
expl = tags["H2_any"] | tags["H6_spu+2"] | tags["H5_seed_best_class"] | tags["PREV_TARGET_known_defect"]
out["tally"] = {k: len(v & SO) for k, v in tags.items()}
out["tally"]["H1_reset_gap"] = 0; out["tally"]["H3_torn"] = 0; out["tally"]["H4_misread_spotcheck"] = "0 of 6"
out["tally"]["union_explained"] = len(expl & SO)
res = SO - expl
out["residual"] = {"n": len(res), "labels": dict(collections.Counter(MI[k]["label"] for k in res)),
                   "pills": sorted([list(k) for k in res])}
json.dump(out, open("summary_silfid_20261006.json", "w"), indent=1)
print(json.dumps(out["tally"], indent=1)); print("residual", out["residual"]["n"], out["residual"]["labels"])
