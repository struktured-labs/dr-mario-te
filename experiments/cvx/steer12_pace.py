"""STEER12 desk: OPPONENT-MEASURED pace for the vs_race human model, from couch data only (no sim win rate is read).

vs_race.evaluate's human: T_L = T_L0 + delta * D(T_L), T_L0 ~ lognormal(median M, sigma) per seed, delta = 2.65 s per AI
tile landed on her (tape fit, VS-RACE endpoint). To measure M we need T_L0 per couch game:
  tau(t)  = t - delta * D(t)     her EFFECTIVE (damage-free) time; D(t) = AI garbage cells landed on her board by t
  f(t)    = (48 - v(t)) / 48      fraction of her viruses cleared (v from her own hidden-spawn track, per pill)
  a game she CLEARED at T gives T_L0 = tau(T) directly; a game that ended first (the AI cleared, or she topped out at
  v_end > 0) is CENSORED and is extrapolated with a POOLED progress shape f = (tau / T0)^a, `a` shared by all games of
  that player, T0 per game, fitted by least squares on every pill point of every game (cleared games included).
  M     = the median of the per-game T0 (lognormal median), sigma_meas = SD of log T0 (reported; NOT used by the primary,
          which keeps the standing sigma 0.15 -- extrapolation noise inflates the per-game spread)
  RULES declared before running: games with fewer than 12 viruses cleared (< 25%) are EXCLUDED (an opening alone does
  not identify T0); delta fixed at 2.65 (sensitivity at 1.5 and 4.0 printed); bootstrap over games for M's CI.
PLAYERS / DATA (both seats tracked, the 10/04-10/05 fixed-tracker pipeline):
  dr. lulu  10/05, 9 games vs FAIR: cases_lulu_20261005_lulu_pills.jsonl + volleys kind 'lulu_recv'; ends from
            summary_lulu_20261005.json (final HUD counts). The 9/27 two games have NO human-seat track: not used
            (reported as a gap).
  owner     10/04, 10 games vs FAIR/FAIR2: cases_fair_20261004_owner_pills.jsonl + volleys kind 'owner_recv'; ends from
            the summary log line (he never cleared in these 10 games).
  python steer12_pace.py -> steer12/pace.txt + steer12/pace.json
"""
import json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.join(HERE, "..", "couch_forensics")
OUT = os.path.join(HERE, "steer12")
NV = 48
MIN_CLEARED = 12
DELTA = 2.65


def lulu_games():
    S = json.load(open(os.path.join(CF, "summary_lulu_20261005.json")))
    res = {r["game"]: r for r in S["results"]}
    P = [json.loads(l) for l in open(os.path.join(CF, "cases_lulu_20261005_lulu_pills.jsonl"))]
    V = [json.loads(l) for l in open(os.path.join(CF, "cases_lulu_20261005_volleys.jsonl"))]
    out = []
    for g in S["games"]:
        n = g["game"]; r = res[n]
        t0 = r["t0_first_spawn"]; t_end = r["t_end"]
        pts = sorted([(p["t_spawn"] - t0, p["virus_count"]) for p in P if p["game"] == n])
        recv = sorted([(v["t"] - t0, v["size"] or 0) for v in V if v["game"] == n and v["kind"] == "lulu_recv"])
        v_end = r["hud_final_lulu_ai"][0]
        out.append(dict(player="lulu", game=n, T=t_end - t0, v_end=v_end, cleared=v_end == 0, pts=pts, recv=recv,
                        how=f"{g['winner']} {g['how']}"))
    return out


def owner_games():
    S = json.load(open(os.path.join(CF, "summary_fair_20261004.json")))
    P = [json.loads(l) for l in open(os.path.join(CF, "cases_fair_20261004_owner_pills.jsonl"))]
    V = [json.loads(l) for l in open(os.path.join(CF, "cases_fair_20261004_volleys.jsonl"))]
    out = []
    for g in S["games"]:
        n = g["game"]; t0 = g["t0_first_spawn"]; t_end = g["t_end"]
        pts = sorted([(p["t_spawn"] - t0, p["virus_count"]) for p in P if p["game"] == n])
        recv = sorted([(v["t"] - t0, v["size"] or 0) for v in V if v["game"] == n and v["kind"] == "owner_recv"])
        # final owner viruses from the log line ("owner tapped out 25 / 5", "AI full clear, owner at 17", ...)
        log = g["log"]
        m = re.search(r"owner (?:at|tapped out|topped out|out) (\d+)", log) or re.search(r"owner (\d+)", log)
        v_end = int(m.group(1)) if m else None
        out.append(dict(player="owner", game=n, T=t_end - t0, v_end=v_end, cleared=v_end == 0, pts=pts, recv=recv,
                        how=log, build=g["build"]))
    return out


def tau_series(G, delta):
    """(tau, f) per pill point, plus the end point (tau_end, f_end)"""
    def D(t):
        return sum(s for tr, s in G["recv"] if tr <= t)
    xs = [(t - delta * D(t), (NV - v) / NV) for t, v in G["pts"] if v is not None]
    xs.append((G["T"] - delta * D(G["T"]), (NV - G["v_end"]) / NV))
    return xs, D(G["T"])


def fit_shape(games, delta):
    """pooled exponent a + per-game T0: least squares on f over all points, f = min(1, (tau/T0)^a)"""
    data = []
    for G in games:
        xs, _ = tau_series(G, delta)
        data.append([(t, f) for t, f in xs if t > 1.0])

    def T0_for(a, pts, cleared, tau_end):
        if cleared:
            return tau_end
        # 1-D least squares in log T0 (grid then refine)
        best = None
        for lt in np.linspace(np.log(30), np.log(3000), 400):
            T0 = np.exp(lt)
            e = sum((min(1.0, (t / T0) ** a) - f) ** 2 for t, f in pts)
            if best is None or e < best[0]:
                best = (e, T0)
        return best[1]

    best = None
    for a in np.linspace(0.5, 2.0, 61):
        sse = 0.0; T0s = []
        for G, pts in zip(games, data):
            xs, _ = tau_series(G, delta)
            T0 = T0_for(a, pts, G["cleared"], xs[-1][0])
            T0s.append(T0)
            sse += sum((min(1.0, (t / T0) ** a) - f) ** 2 for t, f in pts)
        if best is None or sse < best[0]:
            best = (sse, a, T0s)
    return best[1], best[2], best[0]


def analyse(player, games, out, delta=DELTA, verbose=True):
    keep = [G for G in games if G["v_end"] is not None and NV - G["v_end"] >= MIN_CLEARED]
    drop = [G for G in games if G not in keep]
    a, T0s, sse = fit_shape(keep, delta)
    lin = []
    for G in keep:
        xs, Dt = tau_series(G, delta)
        tau_end, f_end = xs[-1]
        lin.append(tau_end / f_end)
    lt = np.log(T0s)
    M = float(np.exp(np.median(lt)))
    rng = np.random.default_rng(12)
    bs = [float(np.exp(np.median(rng.choice(lt, len(lt))))) for _ in range(4000)]
    res = dict(player=player, delta=delta, n_games=len(keep), excluded=[(G["game"], G["v_end"], round(G["T"], 1)) for G in drop],
               a=float(a), M=M, M_ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
               M_linear=float(np.exp(np.median(np.log(lin)))), sigma_meas=float(np.std(lt, ddof=1)),
               T0=[(G["game"], round(T, 1)) for G, T in zip(keep, T0s)])
    if verbose:
        out(f"\n== {player} (delta {delta}) ==")
        for G, T, L in zip(keep, T0s, lin):
            xs, Dt = tau_series(G, delta)
            out(f"  {G['game']}: {G['how']:40s} T {G['T']:6.1f} s, viruses left {G['v_end']:2d}, AI cells landed on "
                f"{player} {Dt:3d} (-{delta * Dt:5.1f} s) -> tau_end {xs[-1][0]:6.1f} s, f_end {xs[-1][1]:.2f} | "
                f"T0 {'(cleared) ' if G['cleared'] else ''}{T:6.1f} s (linear extrapolation {L:6.1f})")
        out(f"  excluded (< {MIN_CLEARED} viruses cleared): {res['excluded']}")
        out(f"  pooled shape exponent a = {a:.3f} (f = (tau/T0)^a; a > 1 = slower start, a < 1 = slower finish)")
        out(f"  MEASURED PACE M = {M:.1f} s [game bootstrap 95% {res['M_ci'][0]:.1f}, {res['M_ci'][1]:.1f}] (linear "
            f"extrapolation instead: {res['M_linear']:.1f}); per-game sigma of log T0 = {res['sigma_meas']:.3f}")
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    out(__doc__.split("\n")[0])
    L = lulu_games(); O = owner_games()
    rl = analyse("lulu", L, out)
    ro = analyse("owner", O, out)
    out("\nSENSITIVITY to delta (M only):")
    for d in (1.5, 4.0):
        a = analyse("lulu", L, out, d, verbose=False); b = analyse("owner", O, out, d, verbose=False)
        out(f"  delta {d}: lulu M {a['M']:.1f} s, owner M {b['M']:.1f} s")
    json.dump({"lulu": rl, "owner": ro}, open(os.path.join(OUT, "pace.json"), "w"), indent=1)
    open(os.path.join(OUT, "pace.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
