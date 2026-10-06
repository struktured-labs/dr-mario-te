import json, os, collections, subprocess, sys
import score
S = "/home/struktured/projects/dr_mario_rl/tmp/silfid/mesen/runs"
seeds = [int(x) for x in sys.argv[1:]] or [1, 25, 11, 9, 3, 17, 19, 27]
G = ["m1g1", "m1g2", "m1g4", "m2g2", "m2g3"]
union = collections.defaultdict(set)
print("seed  " + "  ".join(f"{g:>16s}" for g in G))
base = {g: score.score(g, f"ctl_{g}_D") for g in G}
print("s0    " + "  ".join(f"{base[g]['eq_sil']:3d}/{base[g]['n']:3d} so{base[g]['so_reproduced']:2d}/{base[g]['so_n']:2d}" for g in G))
for s in seeds:
    row = []
    for g in G:
        t = f"seed{s}_{g}"
        if not os.path.exists(os.path.join(S, t, f"lateflip_{t}.log")) or not open(os.path.join(S, t, f"lateflip_{t}.log")).read().count("SUMMARY"):
            row.append(" " * 16); continue
        r = score.score(g, t); union[g] |= set(r["so_pills"])
        row.append(f"{r['eq_sil']:3d}/{r['n']:3d} so{r['so_reproduced']:2d}/{r['so_n']:2d}")
    print(f"s{s:<4d} " + "  ".join(row))
print("union over seeds:", {g: len(v) for g, v in union.items()}, sum(len(v) for v in union.values()))
