#!/usr/bin/env python3
"""REGIME-GATED d_spawn_h penalty screen (pre-registered in PREREG_REGIME_GATED.md).

Identical to screen_quick.py except the penalty is applied ONLY when garbage actually
landed within the last K placements. Everything else -- seeds, loop, fidelity gate,
endpoint, exchange rate -- is unchanged, so this arm is comparable to the flat screen
line for line.

★ The gate opens on garbage ACTUALLY LANDED (`_inject_drip` returned > 0 halves), not on
the injection schedule. The injector silently skips columns already full to row 0, so on
the tall boards this penalty targets, an injection event is often not a delivery. Gating
on the schedule would mis-state the very regime under test.

Reports DUTY CYCLE per arm: the fraction of decisions with the penalty active. The prior
reactive-mode failure ran 54-79% duty; schedule-predicted duty here is K/8."""
from __future__ import annotations
import sys, os, json, time, random
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import extract_windows as EW
import adversary_harness as AH

SCREEN_RNG = 20260812        # SAME sample as the flat screen -- same 480 seeds
N_EACH = 240
K_LANE = 10
ARMS = ((2, 30), (2, 60), (4, 30), (4, 60))   # (K placements, wq)


def decide_penalized(col, vir, ca, cb, na, nb, wq):   # wq=0 or gate closed -> base chooser
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


def play(seed, wq, kwin=0, max_pills=300):
    """Same loop as screen_quick.play, plus the regime gate.

    `kwin` = penalty active only within this many placements after garbage LANDED.
    kwin=0 means "always on" (the flat screen's behaviour), used for the base arm."""
    L = AH._lazy()
    FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])
    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    res, end_kind = "stall", "stall"
    last_land = None          # pills_placed at the last injection that PLACED >0 halves
    n_dec = n_active = 0
    for i in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        if kwin and wq:
            gate = (last_land is not None and (env.pills_placed - last_land) < kwin)
        else:
            gate = bool(wq)
        n_dec += 1
        n_active += 1 if gate else 0
        a = decide_penalized(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), wq if gate else 0)
        if a is None:
            res = "topout"
            break
        _, _, term, trunc, info = env.step(int(a))
        if not term and env.pills_placed >= AH.GARBAGE_MIN_PILLS \
                and env.pills_placed % AH.GARBAGE_PERIOD == 0:
            placed = AH._inject_drip(env.board, seed, env.pills_placed)
            if placed:                       # DELIVERY, not schedule, opens the gate
                last_land = env.pills_placed
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
                               and vl <= AH.DIES_AHEAD_VIRUS_THRESHOLD),
            "n_dec": n_dec, "n_active": n_active}


def _worker(args):
    seed, wq, kwin = args
    return (wq, kwin), play(seed, wq, kwin)


def main():
    census = EW.load_census()
    rng = random.Random(SCREEN_RNG)
    tops = sorted(s for s, r in census.items() if r["result"] == "topout")
    clears = sorted(s for s, r in census.items() if r["result"] == "clear")
    pick_top = sorted(rng.sample(tops, N_EACH))
    pick_clr = sorted(rng.sample(clears, N_EACH))
    seeds = pick_top + pick_clr
    keys = [(0, 0)] + [(wq, k) for (k, wq) in ARMS]
    jobs = [(s, wq, kw) for (wq, kw) in keys for s in seeds]
    print(f"[screen] {len(seeds)} seeds x {len(keys)} arms = {len(jobs)} games",
          flush=True)
    out = {k: {} for k in keys}
    t0 = time.monotonic()
    done = 0
    with ProcessPoolExecutor(max_workers=8, initializer=AH._lazy) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for fut in as_completed(futs):
            key, row = fut.result()
            out[key][row["seed"]] = row
            done += 1
            if done % 100 == 0:
                dt = time.monotonic() - t0
                print(f"[screen] {done}/{len(jobs)} {dt:.0f}s {done/dt:.2f} g/s",
                      flush=True)

    # fidelity gate: base must reproduce census on ALL 480
    base = out[(0, 0)]
    bad = [s for s in seeds
           if base[s]["result"] != census[s]["result"]
           or base[s]["pills"] != census[s]["pills"]
           or base[s]["viruses_left"] != census[s]["viruses_left"]]
    print(f"[gate] base-vs-census mismatches: {len(bad)}", flush=True)
    result = {"rng": SCREEN_RNG, "k_lane": K_LANE, "arms": [list(a) for a in ARMS],
              "prereg": "PREREG_REGIME_GATED.md",
              "topout_seeds": pick_top, "clear_seeds": pick_clr,
              "base_gate_mismatches": bad}
    if bad:
        json.dump(result, open(os.path.join(HERE, "screen_regime_result.json"), "w"),
                  indent=1)
        sys.exit("[gate] FAILED -- base arm does not reproduce census")

    boot = np.random.default_rng(SCREEN_RNG)
    for (kw, wq) in ARMS:
        key = (wq, kw)
        o = out[key]
        resc = [s for s in pick_top if o[s]["result"] == "clear"]
        brk = [s for s in pick_clr if o[s]["result"] != "clear"]
        da_base = sum(base[s]["dies_ahead"] for s in pick_top)
        da_trt = sum(o[s]["dies_ahead"] for s in pick_top)
        changed = sum(1 for s in seeds
                      if o[s]["result"] != base[s]["result"]
                      or o[s]["pills"] != base[s]["pills"])
        # DUTY CYCLE -- pre-registered sanity check, not an endpoint. The prior
        # reactive-mode failure ran 54-79%; schedule-predicted here is K/8.
        tot_dec = sum(o[s]["n_dec"] for s in seeds)
        tot_act = sum(o[s]["n_active"] for s in seeds)
        duty = tot_act / max(1, tot_dec)
        # population net bad-end change per 40k census seeds (negative = good)
        rv = np.array([o[s]["result"] == "clear" for s in pick_top])
        bv = np.array([o[s]["result"] != "clear" for s in pick_clr])
        nets = []
        for b in range(2000):
            ri = boot.integers(0, N_EACH, N_EACH)
            bi = boot.integers(0, N_EACH, N_EACH)
            nets.append(38182 * bv[bi].mean() - 890 * rv[ri].mean())
        net = 38182 * bv.mean() - 890 * rv.mean()
        tag = f"K{kw}_wq{wq}"
        result[tag] = {
            "K": kw, "wq": wq, "duty_cycle": duty,
            "duty_gate_ok": bool(duty < 0.54),
            "rescues": len(resc), "rescue_seeds": resc,
            "breakages": len(brk), "breakage_seeds": brk,
            "dies_ahead_base": da_base, "dies_ahead_trt": da_trt,
            "n_games_changed_vs_base": changed,
            "net_population_badends_per40k": net,
            "net_ci95": [float(np.percentile(nets, 2.5)),
                         float(np.percentile(nets, 97.5))]}
        print(f"[screen] K={kw} wq={wq}: duty {duty:.1%}"
              f"{'' if duty < 0.54 else '  *** GATE NOT GATING (54-79% band)'}"
              f", rescues {len(resc)}/240, breakages {len(brk)}/240, "
              f"dies-ahead {da_base}->{da_trt}, changed {changed}/480, "
              f"net {net:+.1f} [{result[tag]['net_ci95'][0]:+.1f},"
              f"{result[tag]['net_ci95'][1]:+.1f}]"
              f"  {'BENEFIT' if net < 0 else 'net-positive (worse)'}", flush=True)
    json.dump(result, open(os.path.join(HERE, "screen_regime_result.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
