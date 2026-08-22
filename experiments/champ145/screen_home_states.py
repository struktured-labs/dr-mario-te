"""screen_home_states.py — H14 candidate screening: bank champion decision
states in the HOME REGIME (L20 + honest bursty v1.1) and measure candidate
dose/flip statistics BEFORE any endpoint A/B.

Purpose (champion-145 lane, 2026-08-21): the regime map (regime-141) certified
L20+honest-bursty as the home regime (failure 22.8% [17.7,28.5], c5, n=250,
real RTL).  Every H14 candidate needs an argmax-flip-rate screen in THIS
regime before an A/B is fundable (dr-mario-spawn-lane-gate-probe: <2% flip =
untestable).  This runner replays the champion (const arm — proven
outcome-identical to pressure_rig.play by oracle_arm.selftest) at level 20
under the same honest bursty v1.1 model the lab certified H12 with, and banks
EVERY decision state with the full 32-candidate value vector and each
candidate's resulting spawn-lane height.  Banked rows make every future
candidate screen free (vocab-wall lesson: dump rows, don't discard them).

SEED POLICY: uses the regime map's ALREADY-CONSUMED block (even 30000-32998)
on purpose — screening must not burn fresh endpoint seeds, and this population
is the one the map's 22.8% describes.  NO seed outside [30000, 32998] is
accepted (startup assert).

Per-seed atomic: each seed writes states_<seed>.jsonl.gz + a final game row;
re-running skips banked seeds.  One work item = one seed.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.abspath(os.path.join(HERE, "..", "eval47", "stage2", "oracle"))
sys.path.insert(0, ORACLE)

import numpy as np  # noqa: E402

SEED_LO, SEED_HI, SEED_STRIDE = 30000, 32998, 2
REGISTERED_N = (SEED_HI - SEED_LO) // SEED_STRIDE + 1   # 1500


def seed_list():
    seeds = list(range(SEED_LO, SEED_HI + 1, SEED_STRIDE))
    # startup assert per the 2026-08-21 lesson: list length == registered n
    assert len(seeds) == REGISTERED_N, (len(seeds), REGISTERED_N)
    assert all(SEED_LO <= s <= SEED_HI for s in seeds)
    return seeds


def board_key(c1, v1, ncell):
    h = hashlib.sha1()
    h.update(bytes(c1[:ncell]))
    h.update(bytes(v1[:ncell]))
    return h.hexdigest()[:12]


def play_and_bank(seed, C, bmodel, level, max_pills, out_dir):
    """Champion const game at `level`; bank one row per decision ply."""
    import copy  # noqa: F401  (parity with oracle_arm imports)
    import fast_rtl_x as FX
    import root_search as RS
    from fb import FB
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded
    import pressure_rig as PR
    import oracle_arm as OA

    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    env = OA.make_env(seed, level, max_pills=max_pills)
    res, v_at_topout = "stall", None
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

        # LAYOUT GATE (killed-mutant discipline, every ply): the flat plane
        # must reshape to the same (16,8) top-first layout heights() reads,
        # or every child_dsh below is garbage.  Cross-check against the env.
        flat_occ = np.asarray(col[:NCELL]).reshape(16, 8) != 0
        got = np.where(flat_occ.any(axis=0),
                       16 - np.argmax(flat_occ, axis=0), 0)
        want = OA.heights(env.board.color)
        assert (got == want).all(), (seed, ply, got.tolist(), want.tolist())

        vals = np.full(32, np.nan)
        child_dsh = np.full(32, -1, dtype=np.int64)
        child_keys = {}
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
                # spawn-lane height of the RESULTING board (cols 3,4).
                # c1 is the flat colour plane, row-major 16x8, row 0 = top.
                bc = np.asarray(c1[:NCELL]).reshape(16, 8)
                occ = bc != 0
                hs = []
                for ccol in (3, 4):
                    colocc = occ[:, ccol]
                    hs.append(int(16 - np.argmax(colocc)) if colocc.any()
                              else 0)
                child_dsh[slot] = max(hs)
                child_keys[slot] = board_key(c1, v1, NCELL)

        a = OA._champ_action(vals, OA.CHAMP_ORDER)
        if a is None:
            break
        fires, d_spawn_h, viruses = OA.gate_fires(env)
        finite = np.isfinite(vals)
        legal = [int(s) for s in OA.CHAMP_ORDER if finite[int(s)]]
        svals = sorted((float(vals[s]) for s in legal), reverse=True)
        best = svals[0]
        margins = [round(best - svals[i], 3) if i < len(svals) else None
                   for i in (1, 2, 3)]
        # exact top-value tie, and the board-dedup'd version (rule-7 trap:
        # double capsules make ~7.5x spurious ties without dedup)
        tied = [s for s in legal if float(vals[s]) == best]
        tie_boards = len({child_keys[s] for s in tied})
        rows.append({
            "seed": seed, "ply": ply, "vir": int(viruses),
            "dsh": int(d_spawn_h), "gate": int(fires),
            "maxh": int(OA.heights(env.board.color).max()),
            "m2": margins[0], "m3": margins[1], "m4": margins[2],
            "tie_raw": len(tied), "tie_dedup": tie_boards,
            "a": int(a),
            "vals": [None if not finite[s] else round(float(vals[s]), 3)
                     for s in range(32)],
            "cdsh": [int(x) for x in child_dsh],
        })
        r, v = OA._advance(env, a, C, seed, bmodel)
        if r is not None:
            res, v_at_topout = r, v
            break

    game = {"seed": seed, "res": res, "won": int(res == "clear"),
            "topout": int(res == "topout"), "stall": int(res == "stall"),
            "pills": env.pills_placed, "level": level,
            "viruses_left": (int(v_at_topout) if v_at_topout is not None
                             else -1),
            "n_plies": len(rows)}

    tmp = os.path.join(out_dir, f".states_{seed}.tmp")
    dst = os.path.join(out_dir, f"states_{seed}.jsonl.gz")
    with gzip.open(tmp, "wt") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
        fh.write(json.dumps({"game": game}) + "\n")
    os.replace(tmp, dst)
    return game


def worker(args):
    seed, level, max_pills, out_dir = args
    import oracle_arm as OA
    C, bmodel = OA.init_rig(model="lulu", level=level)
    C = dict(C)
    C["level"] = level
    return play_and_bank(seed, C, bmodel, level, max_pills, out_dir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=20)
    ap.add_argument("--max-pills", type=int, default=400)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0,
                    help="first N seeds only (smoke test)")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "states"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    seeds = seed_list()
    if args.limit:
        seeds = seeds[:args.limit]
    todo = [s for s in seeds
            if not os.path.exists(os.path.join(args.out,
                                               f"states_{s}.jsonl.gz"))]
    print(f"[screen] registered={REGISTERED_N} requested={len(seeds)} "
          f"todo={len(todo)} banked={len(seeds) - len(todo)}", flush=True)
    if not todo:
        print("[screen] nothing to do")
        return

    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(worker, (s, args.level, args.max_pills, args.out)): s
                for s in todo}
        for fut in as_completed(futs):
            g = fut.result()   # a worker exception must kill the run loudly
            done += 1
            if done % 25 == 0 or done == len(todo):
                dt = time.time() - t0
                print(f"[screen] {done}/{len(todo)} "
                      f"({dt:.0f}s, {dt/done:.1f}s/game) "
                      f"last: seed={g['seed']} res={g['res']} "
                      f"pills={g['pills']}", flush=True)
    print("SCREEN_BANK_OK", flush=True)


if __name__ == "__main__":
    main()
