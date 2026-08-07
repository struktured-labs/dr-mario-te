#!/usr/bin/env python3
"""tuck_published_vs_best.py -- THE DISCRIMINATOR: does the firmware publish the
best candidate in its own set, or a worse one?

Below its own best  => SELECTION RULE is the defect (fix scoped to one routine)
At its own best     => selection is fine; the damage is the root-placement overwrite

WHY THIS IS NOW IMPLEMENTABLE. The firmware's tuck ranking was previously opaque
(`tuck_ply2_score.py` is a 6502 emitter, not a callable scorer). But that file
documents exactly how it differs from the base scorer: the EH_PLY1 excav+hang
add-on (D_ADL/D_ADH) is added to BASE candidate values at k_done and is **NOT
INTEGRATED** into the tuck path -- and the wiring
(`tuck_score.emit_eh_terms_reuse_label`) raises NotImplementedError with zero
callers, while `build_copro_d3.py:51` ships `EH_PLY1 = True`.

`RS._root_value` takes `w_excav`/`w_hang` as PARAMETERS, so the firmware's tuck
ranking is modelled exactly by scoring with those set to ZERO, while the true
value of the same placement uses the shipped weights. Nothing is approximated:
the model is the documented difference, not a guess at it.

    firmware_rank(p) = _root_value(..., w_excav=0,     w_hang=0)     - ws*g_stranded
    true_value(p)    = _root_value(..., w_excav=SHIP,  w_hang=SHIP)  - ws*g_stranded
    gate:  firmware_rank(p) >= best_base_val_WITH_EH + theta     (the miscalibration)

SELECTION LOSS = true_value(published) - true_value(best-in-set), which is <= 0
by construction; its MAGNITUDE is what this measures, and it is zero exactly
when the missing EH term does not change the argmax.

⚠ This measures the RANKING consequence of the documented defect. It does not
prove the firmware's 6502 does nothing else differently; it isolates the one
difference its own author wrote down.
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import statistics as st
from collections import Counter

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ROOT = "/home/struktured/projects/dr_mario_rl"
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
for _p in (QA + "/tuck_v3", QA + "/eval47", QA, QA + "/bitexact_gate", QA_TUCK,
           ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                          # noqa: E402
import fast_rtl_x as FX                                     # noqa: E402
import fast_sim_x as FS                                     # noqa: E402
import root_search as RS                                    # noqa: E402
import reach_root as RR                                     # noqa: E402
from tuck_setdiff_value import fw_candidates, orient_of     # noqa: E402

WS = 20
THETA = 150            # fpga/copro/tuck_validation/tuck_root_extension.py:39


def _score(col, vir, p, ca, cb, na, nb, w, fl, c1, v1, w_ex, w_hg, g_stranded):
    r0, c0, r1, cc1 = p["cells"]
    col0, col1 = p["colors"]
    nv, cells = RS._expand_core_at(col, vir, r0, c0, r1, cc1, col0, col1, c1, v1)
    val = RS._root_value(c1, v1, nv, cells, na, nb, 8, w_ex, w_hg, w, fl)
    return float(val) - WS * float(g_stranded(c1, v1))


def probe(seed, w, fl, max_pills=300):
    from terms47 import g_stranded
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB

    env = FaithfulDrMarioEnv(level=11, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill(); env.nxt = env._rand_pill()

    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    rows = []
    for _ in range(max_pills):
        if env.board.virus_count() == 0:
            break
        fb = FB.from_board(env.board)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
        vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)

        # base reference WITH the EH bonus -- what the firmware gates against
        base_val = None
        for o4 in range(4):
            var = int(FX._VAR_OF_O4[o4])
            for cc in range(8):
                ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
                if ok == 0:
                    continue
                v = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                   FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
                v = float(v) - WS * float(g_stranded(c1, v1))
                if base_val is None or v > base_val:
                    base_val = v

        fw = fw_candidates(fb, ca, cb)
        if fw:
            rank = [_score(col, vir, p, ca, cb, na, nb, w, fl, c1, v1,
                           0, 0, g_stranded) for p in fw]            # firmware: NO EH
            true = [_score(col, vir, p, ca, cb, na, nb, w, fl, c1, v1,
                           FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, g_stranded) for p in fw]
            gated = [i for i, r in enumerate(rank) if r >= base_val + THETA]
            if gated:
                pub = max(gated, key=lambda i: rank[i])       # firmware's published pick
                best = max(range(len(fw)), key=lambda i: true[i])   # best in its own set
                rows.append({"seed": seed,
                             "published_true": true[pub], "best_true": true[best],
                             "loss": true[pub] - true[best],
                             "same": pub == best,
                             "pub_or": orient_of(fw[pub]["cells"]),
                             "best_or": orient_of(fw[best]["cells"]),
                             "n_fw": len(fw), "n_gated": len(gated)})

        a = RR.choose_base32(col, vir, ca, cb, na, nb)["action"]
        if a is None:
            break
        _, _, term, trunc, _ = env.step(int(a))
        if term or trunc:
            break
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--seed0", type=int, default=7000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    FX.warmup_ship_eh(topk2=8)
    RR._lazy()
    w, fl = FX.variant("winner")

    rows = []
    for i in range(a.seeds):
        rows.extend(probe(a.seed0 + i, w, fl))
        print(f"  seed {a.seed0 + i}: {len(rows)} gated tuck decisions", flush=True)

    n = len(rows)
    if not n:
        sys.exit("no gated tuck decisions -- nothing to discriminate")
    same = sum(1 for r in rows if r["same"])
    losses = [r["loss"] for r in rows if not r["same"]]
    print(f"\nGATED TUCK DECISIONS: {n}")
    print(f"  published == best-in-set : {same}/{n} ({100*same/n:.1f}%)")
    print(f"  published  < best-in-set : {n-same}/{n} ({100*(n-same)/n:.1f}%)")
    if losses:
        print(f"  when it differs: mean loss {st.mean(losses):+.1f}, "
              f"median {st.median(losses):+.1f}, worst {min(losses):+.1f}")
    print(f"  mean loss over ALL gated decisions: "
          f"{st.mean([r['loss'] for r in rows]):+.1f}")
    print(f"  published orientation {Counter(r['pub_or'] for r in rows)}   "
          f"best {Counter(r['best_or'] for r in rows)}")
    verdict = ("SELECTION RULE CONFIRMED as a defect -- the firmware publishes a "
               "worse candidate than its own set contains"
               if same < n else
               "SELECTION IS CLEAN -- damage lies in the root-placement overwrite")
    print(f"\nVERDICT: {verdict}")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump({"n": n, "same": same, "rows": rows, "verdict": verdict}, f, indent=2)
    with open(os.path.join(os.path.dirname(os.path.abspath(a.out)),
                           "STATUS.tuck_published_vs_best"), "w") as f:
        f.write(f"STATUS: DONE {a.out} n={n} "
                f"published<best {n-same}/{n} -- {verdict}\n")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
