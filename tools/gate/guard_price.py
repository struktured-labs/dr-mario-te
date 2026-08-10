#!/usr/bin/env python3
"""In-process paired price of DRTUCKGUARD. Bypasses the worker pool, whose result rows came back
without the veto counters (0/0) even though the guard is demonstrably active in-process --
938 vetoes / 47 offers / 153 reach-model calls on seed 2. Reporting a null from that path would
have been the vacuous-pass trap, so this takes the pool out of the picture entirely.

Stride-2 seeds: the NES LFSR gives 2k and 2k+1 the same capsule stream.
"""
import os, sys, json, statistics as st
sys.path.insert(0, "/home/struktured/projects/dr-mario-v8-wt/experiments")

def arm(tag, tuck, execonly, guard, seeds, gmin=3):
    os.environ["DRTUCK_EXEC"] = "1" if execonly else "0"
    os.environ["DRTUCK_GUARD"] = "1" if guard else "0"
    os.environ["DRTUCK_GUARD_MIN"] = str(gmin)
    os.environ["DRTUCK_GATE"] = "0"; os.environ["DRTUCK_V2"] = "0"
    for m in [m for m in list(sys.modules) if m.startswith("tuck_ab")]:
        sys.modules.pop(m, None)
    import tuck_ab as TA
    TA._init(11, tuck, 1, 12)
    assert TA._C.get("execonly") == execonly and TA._C.get("guard") == guard, "flags not applied"
    rows = [TA.play(s) for s in seeds]
    print(f"[{tag}] n={len(rows)} clear={sum(r['won'] for r in rows)/len(rows):.1%} "
          f"medpills={st.median([r['pills'] for r in rows]):.1f} "
          f"fires/g={st.mean([r['fired'] for r in rows]):.2f} "
          f"VETOED/g={st.mean([r['vetoed'] for r in rows]):.0f} "
          f"OFFERED/g={st.mean([r['offered'] for r in rows]):.0f}", flush=True)
    return rows

def paired(a, b, label):
    d = [b[i]["pills"] - a[i]["pills"] for i in range(len(a)) if a[i]["won"] and b[i]["won"]]
    if not d:
        print(f"  {label}: no both-clear pairs"); return
    import random
    boots = sorted(st.mean(random.choices(d, k=len(d))) for _ in range(2000))
    print(f"  {label}: paired n={len(d)} mean={st.mean(d):+.2f} pills "
          f"[95% CI {boots[50]:+.2f}, {boots[1949]:+.2f}] median={st.median(d):+.1f}")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    seeds = [2 * (i + 1) for i in range(n)]
    A = arm("A_notuck", 0, False, False, seeds)
    B = arm("B_tuck_exec", 1, True, False, seeds)
    D1 = arm("D_guard_min1", 1, True, True, seeds, 1)
    D2 = arm("D_guard_min2", 1, True, True, seeds, 2)
    D = arm("D_guard_min3", 1, True, True, seeds, 3)
    print("\n=== paired vs A (both-clear only) ===")
    paired(A, B, "B tuck        ")
    paired(A, D1, "D min1 vs A   ")
    paired(A, D2, "D min2 vs A   ")
    paired(A, D, "D min3 vs A   ")
    paired(B, D1, "min1 cost vs B")
    paired(B, D2, "min2 cost vs B")
    paired(B, D, "min3 cost vs B")
    json.dump({"A": A, "B": B, "D": D},
              open("/home/struktured/projects/dr-mario-v8-wt/tmp/guard_price.json", "w"))
