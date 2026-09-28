"""STEER6 latency cost of each RTL route: leaves per root search on REAL boards x extra cycles / copro clock.

The firmware search is the golden mirror bit-for-bit (reach G3 240/240; chain co-sim 69/69 address-match), so the
number of LeafEval evaluations it issues per decision = the number of leaf evaluations in
`cascade_leaf6_x._choose_d3_chain_s_leaf6`. This script counts them with the SAME enumeration:
  ply 1   every ALLOWED legal root candidate (32 = 4 orientations x 8 columns, reach mask applied)
  ply 2   every legal placement of the next pill on each non-winning root child
  ply 3   for the top-8 ply-2 children: 4 third-pill classes x every legal placement
(top-8 is approximated by the first 8 legal ply-2 children; only their column heights matter for the count), split
into clearing leaves (full NODE path) and non-clearing leaves (CMD 6/7 delta path).

  python steer6_latency.py [N_SEEDS]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np

CLK = {"MiSTer": 85.909e6, "Pocket": 54.669e6}
FPS = 60.0988


def count_leaves(board, cur, nxt, allowed):
    from fast_sim_x import _expand_core, _virus_count
    from fast_rtl_x import _VAR_OF_O4, _THIRD_X, _THIRD_Y
    from cascade_link_x import board_flat
    col, vir = board_flat(board)
    c1 = np.empty(128, np.int8); v1 = np.empty(128, np.int8)
    c2 = np.empty(128, np.int8); v2 = np.empty(128, np.int8)
    c3 = np.empty(128, np.int8); v3 = np.empty(128, np.int8)
    n = {"leaf": 0, "clear": 0, "base": 0}
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            if not allowed[var * 8 + cl]:
                continue
            ok, nv, cells = _expand_core(col, vir, var, cl, cur[0], cur[1], c1, v1)
            if not ok:
                continue
            n["leaf"] += 1; n["clear"] += int(cells > 0)
            if _virus_count(v1) == 0:
                continue
            n["base"] += 1
            kids = []
            for o42 in range(4):
                var2 = _VAR_OF_O4[o42]
                for cl2 in range(8):
                    ok2, nv2, cells2 = _expand_core(c1, v1, var2, cl2, nxt[0], nxt[1], c2, v2)
                    if not ok2:
                        continue
                    n["leaf"] += 1; n["clear"] += int(cells2 > 0)
                    if len(kids) < 8 and _virus_count(v2) != 0:
                        kids.append((c2.copy(), v2.copy()))
            for kc, kv in kids:
                n["base"] += 1
                for t in range(4):
                    for o43 in range(4):
                        var3 = _VAR_OF_O4[o43]
                        for cl3 in range(8):
                            ok3, nv3, cells3 = _expand_core(kc, kv, var3, cl3, _THIRD_X[t], _THIRD_Y[t], c3, v3)
                            if ok3:
                                n["leaf"] += 1; n["clear"] += int(cells3 > 0)
    return n


def collect(n_seeds=6, lo=36734):
    """Decision boards from ANTIBODY gate-(b) games (selection-free block 36734..)."""
    import stuck_probe as SP, steer_run as SR, opp_run as OR
    out = []
    for i in range(n_seeds):
        steer, choose = SR.make("s5b_hsv512"); opp = OR.make_opponent("owner0804")
        def ch(env, col, vir, ctx, choose=choose):
            out.append((env.board.clone(), (int(env.cur.a), int(env.cur.b)), (int(env.nxt.a), int(env.nxt.b)),
                        env.pills_placed, int(env.board.virus_count())))
            return choose(env, col, vir, ctx)
        SP.play_gb(lo + 2 * i, ch, steer, opp)
    return out


if __name__ == "__main__":
    import reach_fw_tap as RFT, steer_model as SM
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    boards = collect(n_seeds)
    rows = []
    for b, cur, nxt, k, nv in boards:
        allowed = np.asarray(RFT.reach_mask_fw(b.color.tolist(), SM.table_threshold(k), tap=2), dtype=np.int8)
        c = count_leaves(b, cur, nxt, allowed)
        c.update(k=k, nv=nv, nvir_leafmax=nv)
        rows.append(c)
    os.makedirs("steer6", exist_ok=True)
    with open("steer6/latency_leaves.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    L = np.array([r["leaf"] for r in rows]); C = np.array([r["clear"] for r in rows]); NV = np.array([r["nv"] for r in rows])
    E = NV <= 4
    def q(x):
        return f"median {np.median(x):,.0f}  p90 {np.percentile(x, 90):,.0f}  p95 {np.percentile(x, 95):,.0f}  max {x.max():,.0f}"
    print(f"decisions {len(rows)} from {n_seeds} ANTIBODY games")
    print(f"  leaves/search ALL:        {q(L)}   clearing share {C.sum()/L.sum():.3f}")
    print(f"  leaves/search vcount<=4:  {q(L[E])}  (n={E.sum()})")
    print(f"  implied avg clocks/leaf at the 69-board median 48.3M: {48.3e6/np.median(L):,.0f}")
    for name, cyc in (("dist_target seq (8 cyc/leaf)", lambda nv: 8), ("dist_end seq (20 cyc x nv<=4)", lambda nv: 20 * min(nv, 4)),
                      ("dist_stall seq (20 cyc x nv)", lambda nv: 20 * nv)):
        for plat, hz in CLK.items():
            sel = E if "stall" not in name else np.ones(len(rows), bool)
            d = np.array([r["leaf"] * cyc(r["nv"]) / hz * FPS for r, s in zip(rows, sel) if s])
            print(f"  {name:32s} {plat:6s}: +{np.median(d):.2f} f median, p95 +{np.percentile(d, 95):.2f} f, max +{d.max():.2f} f (on active decisions)")
