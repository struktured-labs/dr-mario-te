"""STEER12 analysis (PREREG_STEER12.md): tempo levers for FAIR on the couch11 race clock, at OPPONENT-MEASURED pace.

  python analyze_steer12.py             -> steer12/analysis.txt (WITHHOLDS every arm contrast until all rows exist: R97)
  python analyze_steer12.py --selftest  -> classifier / interpolation / slope positive controls (no data read)

PRIMARY: LULU race win at dr. lulu's MEASURED pace M_LULU (steer12/pace.json: 167.5 s; delta 2.65, sigma 0.15),
lam 2.84, lulu_fit_202610b sizes, couch11 clock. Per arm: the ABSOLUTE win / loss rate (seed bootstrap 95% CI, loss
split slow / kill) and the paired delta vs FAIR (95% and Bonferroni over the K = 8 arms, churn fixed / new).
A lever is ESTABLISHED (helps / hurts) only if its Bonferroni CI excludes 0.
SECONDARY: owner race at M_OWNER (239.5 s); gate-b tap-out and tap<=100; LULU stress bracket M 100 / M 120; delta-paired
sensitivity (delta 1.5 with its own measured M 248.0; delta 4.0 with M 113.4); sigma 0.229 (her measured spread);
time / pills / s per pill; activity (realised tempo shift, clamps, misses); the latency SLOPE (pp per frame of
realised answer shift, OLS over FAIR / m2 / m4 / m6); the EXECUTION curve (overhead pills vs ex_perfect, loss at
0 / +9 / +18 pills by linear interpolation); the MIN_THINK bracket (lat_m2's delta as the upper bound; minus
dp x the per-miss cost from the q arms, dp in [0.01, 0.07] = RESULT_SETTLE sec. 8's final-at-gate drop).
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer6r import boot, fmt, churn
import analyze_steer10 as A10
from vs_race import evaluate

M_LULU, M_OWNER, DELTA, SIGMA = 167.5, 239.5, 2.65, 0.15          # PRE-REGISTERED (steer12/pace.json, rounded 0.1 s)
SIGMA_MEAS = 0.229
DPAIRS = ((1.5, 248.0), (4.0, 113.4))
STRESS = (100.0, 120.0)
ARMS = ("lat_m2", "lat_m4", "lat_m6", "lat_ceil", "ex_perfect", "ex_q02", "ex_q03", "ex_q05")
K = len(ARMS)
BONF = (100 * 0.05 / K / 2, 100 - 100 * 0.05 / K / 2)
LULU = A10.LULU10B                                                  # 1,200
SIX = list(range(39134, 40333, 2))                                  # 600 (owner race + gate b)
LAT_D = {"FAIR": 0, "lat_m2": -2, "lat_m4": -4, "lat_m6": -6}
Q = {"ex_perfect": None, "FAIR": 0.0, "ex_q02": 0.02, "ex_q03": 0.03, "ex_q05": 0.05}


def load(pattern, label, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def win(r, M, dl=DELTA, sg=SIGMA):
    return int(evaluate(r, M, sg, dl)[0] == "win_race")


def ltype(r, M):
    o = evaluate(r, M, SIGMA, DELTA)[0]
    return {"win_race": "win", "loss_race": "slow", "loss_cap": "slow", "loss_kill": "kill"}[o]


def classify(bonf):
    """ESTABLISHED direction of a win-rate delta from its Bonferroni CI (mean, lo, hi)"""
    return "HELPS" if bonf[1] > 0 else ("HURTS" if bonf[2] < 0 else "n.s.")


def interp(x, xs, ys):
    """linear interpolation (extrapolation flagged by the caller) on sorted xs"""
    o = np.argsort(xs); xs, ys = np.asarray(xs)[o], np.asarray(ys)[o]
    return float(np.interp(x, xs, ys))


def slope(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    return float(np.polyfit(xs, ys, 1)[0])


def rows():
    L = {"FAIR": load("steer11/pilot/lulu10b_c11_s10_base_*.jsonl", "s10_base~steer", LULU)}
    R = {"FAIR": load("steer11/pilot/rc10_c11_s10_base_*.jsonl", "s10_base~steer", SIX)}
    G = {"FAIR": load("steer8/gb10_fD_bdepD_*.jsonl", "fD_bdepD@owner202610", SIX)}
    for a in ARMS:
        L[a] = load(f"steer12/main/lulu12_{a}_*.jsonl", f"{a}~steer", LULU)
        R[a] = load(f"steer12/main/rc12_{a}_*.jsonl", f"{a}~steer", SIX)
        G[a] = load(f"steer12/main/gb12_{a}_*.jsonl", f"{a}@owner202610", SIX)
    return L, R, G


def main():
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    pace = json.load(open("steer12/pace.json"))
    assert round(pace["lulu"]["M"], 1) == M_LULU and round(pace["owner"]["M"], 1) == M_OWNER, "pace.json drifted"
    L, R, G = rows()
    out(f"STEER12 rows: " + ", ".join(f"{a} {len(L[a])}/{len(R[a])}/{len(G[a])}" for a in ("FAIR",) + ARMS)
        + " (lulu/rc/gb; need 1200/600/600)")
    if any(len(L[a]) < 1200 or len(R[a]) < 600 or len(G[a]) < 600 for a in ("FAIR",) + ARMS):
        out("INCOMPLETE: every arm contrast is WITHHELD until all rows exist (R97).")
        open("steer12/analysis.txt", "w").write("\n".join(lines) + "\n")
        return
    m = lambda D, S, f: 100 * np.mean([f(D[s]) for s in S])
    out(f"\nPRIMARY: LULU race at her MEASURED pace M {M_LULU} s (delta {DELTA}, sigma {SIGMA}); FAIR = steer11 pilot rows")
    out(f"{'arm':11s} {'win %':>22s} {'loss slow/kill':>15s} {'d vs FAIR [95%]':>24s} {'Bonferroni':>18s} verdict  churn  "
        f"| t_clear med  pills  s/pill  tempo f/pill  activity")
    res = {}
    for a in ("FAIR",) + ARMS:
        D = L[a]; S = LULU
        w = boot([win(D[s], M_LULU) for s in S])
        sl = 100 * np.mean([ltype(D[s], M_LULU) == "slow" for s in S]); kl = 100 * np.mean([ltype(D[s], M_LULU) == "kill" for s in S])
        cs = [D[s] for s in S if D[s]["how"] == "clear"]
        tf = np.mean([D[s]["knob"]["tempo_f"] / max(D[s]["knob"]["dec"], 1) for s in S]) if "knob" in D[S[0]] else 0.0
        act = ""
        if "knob" in D[S[0]]:
            kk = {k: sum(D[s]["knob"][k] for s in S) for k in D[S[0]]["knob"]}
            dec = max(kk["dec"], 1)
            act = f"clamp {100 * kk['clamp'] / dec:.1f}% armed {100 * kk['armed'] / dec:.1f}% miss {100 * kk['miss'] / dec:.1f}% fallback {kk['perfect_fallback']}"
        base = f"{a:11s} {w[0]:6.2f} [{w[1]:.2f}, {w[2]:.2f}]  {sl:6.2f}/{kl:5.2f}"
        tail = (f"| {np.median([r['t_end'] for r in cs]):6.1f} s  {np.median([r['pills'] for r in cs]):5.0f}  "
                f"{np.median([r['t_end'] / r['pills'] for r in cs]):.2f}  {tf:+6.2f}  {act}")
        if a == "FAIR":
            out(f"{base} {'(control)':>24s} {'':>18s}           {tail}")
        else:
            d = boot([win(D[s], M_LULU) - win(L['FAIR'][s], M_LULU) for s in S])
            db = boot([win(D[s], M_LULU) - win(L['FAIR'][s], M_LULU) for s in S], *BONF)
            c = churn([L["FAIR"][s] for s in S], [D[s] for s in S], lambda r: not win(r, M_LULU))
            res[a] = dict(d=d, db=db, w=w, tf=tf)
            out(f"{base} {fmt(d):>24s} {('[' + format(db[1], '+.2f') + ', ' + format(db[2], '+.2f') + ']'):>18s} "
                f"{classify(db):6s} {c[0]}/{c[1]}  {tail}")
        res.setdefault(a, {}).update(w=w, tf=tf, slow=sl, kill=kl)
    out(f"\nSECONDARY (paired delta vs FAIR [95%], absolute FAIR level first)")
    cells = [(f"owner race M{M_OWNER}", R, SIX, lambda r: win(r, M_OWNER))]
    cells += [(f"LULU stress M{int(Ms)}", L, LULU, (lambda Ms: lambda r: win(r, Ms))(Ms)) for Ms in STRESS]
    cells += [(f"LULU delta {dl} M {Md}", L, LULU, (lambda dl, Md: lambda r: win(r, Md, dl))(dl, Md)) for dl, Md in DPAIRS]
    cells += [(f"LULU sigma {SIGMA_MEAS}", L, LULU, lambda r: win(r, M_LULU, DELTA, SIGMA_MEAS))]
    cells += [("gate-b tap-out", G, SIX, lambda r: r["topout"]), ("gate-b tap<=100", G, SIX, lambda r: int(r["topout"] and r["pills"] <= 100))]
    for name, DD, S, f in cells:
        parts = [f"FAIR {m(DD['FAIR'], S, f):.2f}%"]
        for a in ARMS:
            d = boot([f(DD[a][s]) - f(DD["FAIR"][s]) for s in S])
            parts.append(f"{a} {m(DD[a], S, f):.2f} ({d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}])")
        out(f"  {name}: " + "; ".join(parts))
    # ---- latency slope (pp of LULU win per frame of realised answer shift; seed bootstrap)
    arms = ["FAIR", "lat_m2", "lat_m4", "lat_m6"]
    xs = [res[a]["tf"] for a in arms]
    rng = np.random.default_rng(7); S = np.array(LULU); sl = []
    W = {a: np.array([win(L[a][s], M_LULU) for s in S]) for a in arms + ["lat_ceil"]}
    for _ in range(2000):
        i = rng.integers(0, len(S), len(S))
        sl.append(slope(xs, [100 * W[a][i].mean() for a in arms]))
    s0 = slope(xs, [100 * W[a].mean() for a in arms])
    out(f"\nLATENCY CURVE (primary cell): realised tempo shift per pill FAIR / m2 / m4 / m6 / ceil = "
        + " / ".join(f"{res[a]['tf']:+.2f}" for a in arms + ["lat_ceil"]) + " f;  slope "
        f"{s0:+.3f} pp per +1 f [{np.percentile(sl, 2.5):+.3f}, {np.percentile(sl, 97.5):+.3f}]")
    # ---- execution curve: overhead pills vs ex_perfect (paired, seeds where both cleared)
    out("\nEXECUTION CURVE (primary cell): overhead = mean (pills - ex_perfect pills) over seeds where both cleared")
    ov, lr = [], []
    for a in ("ex_perfect", "FAIR", "ex_q02", "ex_q03", "ex_q05"):
        both = [s for s in LULU if L[a][s]["how"] == "clear" and L["ex_perfect"][s]["how"] == "clear"]
        o = float(np.mean([L[a][s]["pills"] - L["ex_perfect"][s]["pills"] for s in both])) if a != "ex_perfect" else 0.0
        loss = 100 - res[a]["w"][0]
        ov.append(o); lr.append(loss)
        out(f"  {a:10s} overhead {o:+6.2f} pills (n both clear {len(both)}), loss {loss:.2f}% (slow {res[a]['slow']:.2f} / kill {res[a]['kill']:.2f})")
    for k in (0, 9, 18):
        flag = " (EXTRAPOLATED)" if k > max(ov) else ""
        out(f"  loss at +{k} pills overhead: {interp(k, ov, lr):.2f}%{flag}")
    qs = [0.0, 0.02, 0.03, 0.05]; ls = [100 - res[a]["w"][0] for a in ("FAIR", "ex_q02", "ex_q03", "ex_q05")]
    cost = slope(qs, ls) / 100.0                    # pp of loss per +1 pp of injected miss rate
    out(f"  per-miss cost (OLS over FAIR / q02 / q03 / q05): {cost:+.3f} pp loss per +1 pp miss rate")
    g2 = res["lat_m2"]["d"][0]
    out(f"\nMIN_THINK -2 f BRACKET: latency channel (= lat_m2) {g2:+.2f} pp win; minus non-final commits at the earlier gate "
        f"(dp 1-7 pp of decisions, priced as random misses: an upper bound on their cost) -> net "
        f"[{g2 - 7 * cost:+.2f}, {g2 - 1 * cost:+.2f}] pp")
    open("steer12/analysis.txt", "w").write("\n".join(lines) + "\n")


def selftest():
    ok = True
    for ci, want in (((+2, +0.5, +3.5), "HELPS"), ((-2, -3.5, -0.5), "HURTS"), ((+1, -0.5, +2.5), "n.s."), ((0, 0, 0), "n.s.")):
        got = classify(ci); ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} classify {ci} -> {got}")
    v = interp(9, [0, 6, 12, 20], [30, 33, 37, 45]); ok &= abs(v - 35.0) < 1e-9; print(f"  interp 9 on 0/6/12/20 -> {v} (want 35.0)")
    v = interp(9, [12, 0, 20, 6], [37, 30, 45, 33]); ok &= abs(v - 35.0) < 1e-9; print(f"  unsorted interp -> {v} (want 35.0)")
    s = slope([0, -2, -4, -6], [40, 42, 44, 46]); ok &= abs(s + 1.0) < 1e-9; print(f"  slope -> {s} (want -1.0 pp per +1 f)")
    # mutant: a classifier on the 95% mean must be killed by case 3
    mut = lambda ci: "HELPS" if ci[0] > 0 else ("HURTS" if ci[0] < 0 else "n.s.")
    killed = mut((+1, -0.5, +2.5)) != "n.s."; ok &= killed; print(f"  mutant 'classify on the mean': {'KILLED' if killed else 'SURVIVED'}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    main()
