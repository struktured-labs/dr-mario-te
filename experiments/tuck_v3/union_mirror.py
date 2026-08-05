#!/usr/bin/env python3
"""#17 enumerator-alignment step 1 (the dissection's named next experiment):
UNION-enumerator A/B under the leaf_r47 mirror ruler.

The dissection (n=40 trajectories) proved the python proof's enumerator
(RS.tuck_root_candidates) and the firmware's (tuck_scan_v3) choose from
substantially different candidate sets (62.3% of real fires out-of-proof-set,
71% of those horizontal), with GOOD fire quality on both sides and the two
channels cancelling. This measures the CEILING: mirror decider with
tuck_cands = UNION of both enumerators, θ=150, vs a base-only off arm —
the same protocol that scored the RS-only set at −12.94 [−20.43,−5.48].

If union >> RS-only: the firmware's horizontal reach is additive value and
the proof's enumerator was the limiter — align the PROOF up.
If union ≈ RS-only: overlap dominates; the miss channel is the whole story —
align the FIRMWARE's acceptance (why it declines proof-visible tucks).

Usage: union_mirror.py --seeds 120 --workers 8 --out results/union_theta150
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/bitexact_gate", QA_TUCK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_C = {}
import os as _os0
THETA = float(_os0.environ.get("UM_THETA", "150"))


def _init(level, arm):
    """arm: 'off' | 'rs' | 'union'"""
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    _C.update(level=level, arm=arm, w=w)


def _norm(cells, colors):
    r0, c0, r1, c1 = cells
    a, b = colors
    return tuple(sorted([(r0, c0, int(a)), (r1, c1, int(b))]))


def union_cands(fb, ca, cb):
    """RS.tuck_root_candidates ∪ tuck_scan_v3 (converted), deduped physically."""
    import root_search as RS
    from tuck_scan_v3_ref import ref_tuck_scan_v3, candidate_cells, H, V, RH, RV
    from common import arrays_to_nes
    import numpy as np

    rs = RS.tuck_root_candidates(fb, ca, cb, 12, True)
    seen = {_norm(p["cells"], p["colors"]) for p in rs}
    col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
    vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
    board = arrays_to_nes(col, vir)
    fw_cands, _dropped = ref_tuck_scan_v3(board)
    FLIP = {H: 0, V: 1, RH: 1, RV: 0}
    out = list(rs)
    for c in fw_cands:
        r0, c0, r1, c1 = candidate_cells(c["target"], c["rest"], c["orient"])
        flip = FLIP[c["orient"]]
        col0, col1 = (ca, cb) if flip == 0 else (cb, ca)
        key = _norm((r0, c0, r1, c1), (col0, col1))
        if key in seen:
            continue
        seen.add(key)
        out.append({"cells": (r0, c0, r1, c1), "colors": (col0, col1),
                    "src": "fw"})
    return out, len(rs), len(out)


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource
    from fb import FB
    import mirrored_leaf as ML

    level, arm, w = _C["level"], _C["arm"], _C["w"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    fired = fired_fw_only = 0
    res = "stall"
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        ca, cb = int(env.cur.a), int(env.cur.b)
        if arm == "off":
            tc = []
        elif arm == "rs":
            import root_search as RS
            tc = RS.tuck_root_candidates(fb, ca, cb, 12, True)
        elif arm == "te":
            import tuck_enum as _TE
            tc = [{"cells": tuple(p["cells"]), "colors": tuple(p["colors"]), "src": "te"}
                  for p in _TE.enumerate(fb, ca, cb, mode="free")
                  if p["is_tuck"] and p["reachable"]]
        elif arm == "v4":
            import numpy as np
            from scan_v4 import scan_v4 as _sv4
            from common import arrays_to_nes
            col_ = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
            vir_ = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
            tc = [{"cells": d["cells"], "colors": d["colors"], "src": "v4"}
                  for d in _sv4(arrays_to_nes(col_, vir_), ca, cb)]
        else:
            tc, n_rs, n_u = union_cands(fb, ca, cb)
        best = ML.choose_root_with_tucks_mirrored(fb, env.cur, env.nxt, w, topk2=8,
                                                  tuck_cands=tc, theta=THETA)
        if best["kind"] == "tuck":
            p = best["placement"]
            r0, c0, r1, c1 = p["cells"]
            col0, col1 = p["colors"]
            b = env.board
            b.color[r0, c0] = col0
            b.color[r1, c1] = col1
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT; b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN; b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            fired += 1
            if p.get("src") == "fw":
                fired_fw_only += 1
            if b.virus_count() == 0:
                res = "clear"; break
            if b.spawn_blocked():
                res = "topout"; break
            if env.pills_placed >= 300:
                break
            continue
        _, _, term, trunc, info = env.step(int(best["action"]))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break
    return {"seed": seed, "won": int(res == "clear"), "pills": env.pills_placed,
            "fired": fired, "fired_fw_only": fired_fw_only}


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def run_arm(level, seeds, workers, arm):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, arm)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 5) == 0 or (i + 1) == seeds:
                print(f"  arm={arm} {i + 1}/{seeds}", flush=True)
    return {r["seed"]: r for r in rows}


def compare(off, on, tag):
    ss = sorted(set(off) & set(on))
    both = [s for s in ss if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    c0 = sum(off[s]["won"] for s in ss) / len(ss)
    c1 = sum(on[s]["won"] for s in ss) / len(ss)
    fires = st.mean([on[s]["fired"] for s in ss])
    fwonly = st.mean([on[s].get("fired_fw_only", 0) for s in ss])
    verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
    print(f"{tag}: pills {st.mean(d) if d else float('nan'):+.2f} [{lo:+.2f},{hi:+.2f}] "
          f"{verdict}  clear {c0:.1%}->{c1:.1%}  fires/g {fires:.2f} "
          f"(fw-only {fwonly:.2f})", flush=True)
    return {"tag": tag, "delta": st.mean(d) if d else None, "ci": [lo, hi],
            "verdict": verdict, "clear0": c0, "clear1": c1,
            "fires": fires, "fires_fw_only": fwonly}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()
    print(f"=== UNION-ENUMERATOR MIRROR A/B, L{a.level}, n={a.seeds}, theta={THETA} ===",
          flush=True)
    import os as _os
    arms = _os.environ.get("UM_ARMS", "rs,union").split(",")
    off = run_arm(a.level, a.seeds, a.workers, "off")
    results = {}
    for armname in arms:
        results[armname] = run_arm(a.level, a.seeds, a.workers, armname)
    for armname in arms:
        compare(off, results[armname], f"{armname:>6s} vs off")
    r1 = r2 = r3 = None
    if a.out and r1 is not None:
        with open(f"{a.out}.json", "w") as fh:
            json.dump({"rs": r1, "union": r2, "union_vs_rs": r3,
                       "rows": {"off": [off[s] for s in sorted(off)],
                                "rs": [rs[s] for s in sorted(rs)],
                                "union": [un[s] for s in sorted(un)]}}, fh)
        print(f"wrote {a.out}.json")
    print("DONE")


if __name__ == "__main__":
    main()
