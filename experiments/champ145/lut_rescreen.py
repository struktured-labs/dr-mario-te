"""lut_rescreen.py — stage-2 LUT re-screen at L20 (discard-pile directive 3/3).

RE-SCREEN ONLY: the LUT's L11 conviction stands (rollout NO_GO; label-blind
null matched it). The question here is narrower — at L20-honest-bursty, what
is the LUT re-ranker's flip DOSE and where do its flips sit (strata,
fail-games vs clear-games)? No outcome claim is made or implied by this
screen; anything promising gets its own registered mini-endpoint.

Design: replay champion-const games (same machinery as screen_home_states)
over the SAME consumed regime-map seed population; per ply, score all
candidates with the SHIPPED LUT (arm_lut.LutDelta, RECOMMENDED_lut64.json,
exact integer path) and log whether the adjusted argmax differs from the
champion's. THE CHAMPION'S MOVE IS ALWAYS PLAYED — a screen, not an arm.

Runs POST-endpoint at 6 workers (approved core split). Per-seed atomic,
resumable.
"""
import argparse
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.abspath(os.path.join(HERE, "..", "eval47", "stage2", "oracle"))
ROLLOUT = os.path.abspath(os.path.join(HERE, "..", "eval47", "stage2",
                                       "rollout"))
sys.path.insert(0, ORACLE)
sys.path.insert(0, ROLLOUT)

import numpy as np  # noqa: E402

SEED_LO, SEED_HI, SEED_STRIDE = 30000, 32998, 2
REGISTERED_N = (SEED_HI - SEED_LO) // SEED_STRIDE + 1


def play_and_screen(seed, C, bmodel, level, max_pills, lut, out_dir):
    import fast_rtl_x as FX
    import root_search as RS
    from fb import FB
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded
    import pressure_rig as PR
    import oracle_arm as OA
    from arm_lut import _heights

    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    env = OA.make_env(seed, level, max_pills=max_pills)
    res = "stall"
    rows = []
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)

    for ply in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        vals = np.full(32, np.nan)
        posts = {}
        for o4 in range(4):
            var = int(FX._VAR_OF_O4[o4])
            for cc in range(8):
                ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
                if ok == 0:
                    continue
                val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                     FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
                if wt:
                    val -= wt * g_tower(c1, v1, PR.H0)
                if ws:
                    val -= ws * g_stranded(c1, v1)
                slot = var * 8 + cc
                vals[slot] = val
                posts[slot] = (c1.copy(), v1.copy())

        a = OA._champ_action(vals, OA.CHAMP_ORDER)
        if a is None:
            break
        # LUT-adjusted argmax (prune: below best-span cannot win)
        best = np.nanmax(vals)
        adj = vals.copy()
        for slot, (pc, pv) in posts.items():
            if vals[slot] < best - lut.span:
                adj[slot] = -np.inf
                continue
            base = np.empty(FX.NBASE, dtype=np.int64)
            FX._base_scan(pc, pv, fl, base)
            adj[slot] = vals[slot] - lut.delta_from_feats(
                lut.feats_of(base, _heights(pc)))
        a_lut = int(OA.CHAMP_ORDER[np.nanargmax(adj[OA.CHAMP_ORDER])])
        fires, d_spawn_h, viruses = OA.gate_fires(env)
        rows.append({"seed": seed, "ply": ply, "vir": int(viruses),
                     "dsh": int(d_spawn_h), "gate": int(fires),
                     "maxh": int(OA.heights(env.board.color).max()),
                     "flip": int(a_lut != a)})
        r, v = OA._advance(env, a, C, seed, bmodel)   # champion's move ALWAYS
        if r is not None:
            res = r
            break

    game = {"seed": seed, "res": res, "won": int(res == "clear"),
            "n_plies": len(rows), "flips": sum(r["flip"] for r in rows)}
    tmp = os.path.join(out_dir, f".lut_{seed}.tmp")
    dst = os.path.join(out_dir, f"lut_{seed}.jsonl.gz")
    with gzip.open(tmp, "wt") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
        fh.write(json.dumps({"game": game}) + "\n")
    os.replace(tmp, dst)
    return game


def worker(args):
    seed, level, max_pills, out_dir = args
    import oracle_arm as OA
    from arm_lut import load_recommended
    C, bmodel = OA.init_rig(model="lulu", level=level)
    C = dict(C)
    C["level"] = level
    lut = load_recommended()
    return play_and_screen(seed, C, bmodel, level, max_pills, lut, out_dir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=20)
    ap.add_argument("--max-pills", type=int, default=400)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(HERE, "out", "lut_screen"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    seeds = list(range(SEED_LO, SEED_HI + 1, SEED_STRIDE))
    assert len(seeds) == REGISTERED_N, (len(seeds), REGISTERED_N)
    if args.limit:
        seeds = seeds[:args.limit]
    todo = [s for s in seeds
            if not os.path.exists(os.path.join(args.out,
                                               f"lut_{s}.jsonl.gz"))]
    print(f"[lut-screen] requested={len(seeds)} todo={len(todo)}", flush=True)
    if not todo:
        print("LUT_SCREEN_BANK_OK")
        return
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(worker, (s, args.level, args.max_pills, args.out)): s
                for s in todo}
        for fut in as_completed(futs):
            g = fut.result()
            done += 1
            if done % 50 == 0 or done == len(todo):
                dt = time.time() - t0
                print(f"[lut-screen] {done}/{len(todo)} ({dt:.0f}s) "
                      f"last seed={g['seed']} {g['res']} flips={g['flips']}",
                      flush=True)
    print("LUT_SCREEN_BANK_OK", flush=True)


if __name__ == "__main__":
    main()
