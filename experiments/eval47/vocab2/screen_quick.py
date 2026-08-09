#!/usr/bin/env python3
"""Quick screen of the d_spawn_h survival penalty (pre-registered in
PREREG_PHASE2.md ADDENDUM). val -= WQ*max(0, spawn_h_post-10) inside the
census-fidelity-gated replayer loop. Base arm (WQ=0) must reproduce census."""
from __future__ import annotations
import sys, os, json, time, random
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import extract_windows as EW
import adversary_harness as AH

SCREEN_RNG = 20260812
N_EACH = 240
K_LANE = 10
DOSES = (60, 120)


def decide_penalized(col, vir, ca, cb, na, nb, wq):
    import reach_root as RR
    L = RR._lazy()
    FX, FS, RS, g_stranded = L["FX"], L["FS"], L["RS"], L["g_stranded"]
    w, fl = L["w"], L["fl"]
    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    best_val, best_a = None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, RR.TOPK2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= EW.WS * g_stranded(c1, v1)
            if wq:
                sph = 0
                for c in (3, 4):
                    for r in range(16):
                        if c1[r * 8 + c] != 0:
                            h = 16 - r
                            if h > sph:
                                sph = h
                            break
                if sph > K_LANE:
                    val -= wq * (sph - K_LANE)
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
    return best_a


def play(seed, wq, max_pills=300):
    """Same loop as extract_windows.instrumented_play but with the penalized
    chooser; wq=0 must be trace-identical to the census (fidelity gate)."""
    L = AH._lazy()
    FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])
    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    res, end_kind = "stall", "stall"
    for i in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a = decide_penalized(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), wq)
        if a is None:
            res = "topout"
            break
        _, _, term, trunc, info = env.step(int(a))
        if not term and env.pills_placed >= AH.GARBAGE_MIN_PILLS \
                and env.pills_placed % AH.GARBAGE_PERIOD == 0:
            AH._inject_drip(env.board, seed, env.pills_placed)
            if env.board.virus_count() == 0:
                term, info = True, {"won": True}
            elif env.board.spawn_blocked():
                term, info = True, {"won": False}
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            res = "stall"
            break
    vl = int(env.board.virus_count())
    return {"seed": seed, "result": res, "pills": env.pills_placed,
            "viruses_left": vl,
            "dies_ahead": bool(res == "topout"
                               and vl <= AH.DIES_AHEAD_VIRUS_THRESHOLD)}


def _worker(args):
    seed, wq = args
    return wq, play(seed, wq)


def main():
    census = EW.load_census()
    rng = random.Random(SCREEN_RNG)
    tops = sorted(s for s, r in census.items() if r["result"] == "topout")
    clears = sorted(s for s, r in census.items() if r["result"] == "clear")
    pick_top = sorted(rng.sample(tops, N_EACH))
    pick_clr = sorted(rng.sample(clears, N_EACH))
    seeds = pick_top + pick_clr
    jobs = [(s, wq) for wq in (0,) + DOSES for s in seeds]
    print(f"[screen] {len(seeds)} seeds x {1+len(DOSES)} arms = {len(jobs)} games",
          flush=True)
    out = {wq: {} for wq in (0,) + DOSES}
    t0 = time.monotonic()
    done = 0
    with ProcessPoolExecutor(max_workers=8, initializer=AH._lazy) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for fut in as_completed(futs):
            wq, row = fut.result()
            out[wq][row["seed"]] = row
            done += 1
            if done % 100 == 0:
                dt = time.monotonic() - t0
                print(f"[screen] {done}/{len(jobs)} {dt:.0f}s {done/dt:.2f} g/s",
                      flush=True)

    # fidelity gate: base must reproduce census on ALL 480
    bad = [s for s in seeds
           if out[0][s]["result"] != census[s]["result"]
           or out[0][s]["pills"] != census[s]["pills"]
           or out[0][s]["viruses_left"] != census[s]["viruses_left"]]
    print(f"[gate] base-vs-census mismatches: {len(bad)}", flush=True)
    result = {"rng": SCREEN_RNG, "k_lane": K_LANE, "doses": DOSES,
              "topout_seeds": pick_top, "clear_seeds": pick_clr,
              "base_gate_mismatches": bad}
    if bad:
        json.dump(result, open(os.path.join(HERE, "screen_result.json"), "w"),
                  indent=1)
        sys.exit("[gate] FAILED -- base arm does not reproduce census")

    boot = np.random.default_rng(SCREEN_RNG)
    for wq in DOSES:
        resc = [s for s in pick_top if out[wq][s]["result"] == "clear"]
        brk = [s for s in pick_clr if out[wq][s]["result"] != "clear"]
        da_base = sum(out[0][s]["dies_ahead"] for s in pick_top)
        da_trt = sum(out[wq][s]["dies_ahead"] for s in pick_top)
        changed = sum(1 for s in seeds
                      if out[wq][s]["result"] != out[0][s]["result"]
                      or out[wq][s]["pills"] != out[0][s]["pills"])
        # population net bad-end change per 40k census seeds (negative = good)
        rv = np.array([out[wq][s]["result"] == "clear" for s in pick_top])
        bv = np.array([out[wq][s]["result"] != "clear" for s in pick_clr])
        nets = []
        for b in range(2000):
            ri = boot.integers(0, N_EACH, N_EACH)
            bi = boot.integers(0, N_EACH, N_EACH)
            nets.append(38182 * bv[bi].mean() - 890 * rv[ri].mean())
        net = 38182 * bv.mean() - 890 * rv.mean()
        result[f"wq{wq}"] = {
            "rescues": len(resc), "rescue_seeds": resc,
            "breakages": len(brk), "breakage_seeds": brk,
            "dies_ahead_base": da_base, "dies_ahead_trt": da_trt,
            "n_games_changed_vs_base": changed,
            "net_population_badends_per40k": net,
            "net_ci95": [float(np.percentile(nets, 2.5)),
                         float(np.percentile(nets, 97.5))]}
        print(f"[screen] wq={wq}: rescues {len(resc)}/240, breakages "
              f"{len(brk)}/240, dies-ahead {da_base}->{da_trt}, "
              f"changed {changed}/480, net {net:+.1f} "
              f"[{result[f'wq{wq}']['net_ci95'][0]:+.1f},"
              f"{result[f'wq{wq}']['net_ci95'][1]:+.1f}]", flush=True)
    json.dump(result, open(os.path.join(HERE, "screen_result.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
