"""STEER11 analysis: the s10_A16 confirmation on the couch-calibrated race clock (couch11).

  python analyze_steer11.py pilot      step 1: FAIR (and A16) on the couch11 clock vs the legacy clock, STEER10 blocks
                                       -> steer11/pilot.txt (absolute FAIR levels; the sizing inputs for the prereg)
  python analyze_steer11.py confirm    PREREG_STEER11.md decision -> steer11/confirm.txt (REFUSES to print any arm
                                       contrast until every pre-registered row exists: R97)
  python analyze_steer11.py --selftest killed-mutant check of the verdict rule (no data read)

PRIMARY (PREREG_STEER11 sec. 6): LULU race win (lam 2.84, lulu_fit_202610b sizes, couch11 clock) averaged over the
pace prior M in {80, 100, 120, 140} s (delta 2.65, sigma 0.15): per seed the mean of the four vs_race.evaluate win
indicators; paired A16 - FAIR, seed bootstrap (4,000). Single arm: plain two-sided 95%; PASS needs lower > 0.
GUARDS (no demonstrated harm; Bonferroni over the 3-guard family, two-sided 1 - 0.05/3):
  G1 gate-b tap-out (owner202610), harm iff Bonferroni lower > 0
  G2 gate-b tap-out within 100 pills, harm iff Bonferroni lower > 0
  G3 owner race win (lam 2.36 Hartford sizes, couch11, M 177, delta 2.65), harm iff Bonferroni upper < 0
PASS iff primary lower95 > 0 AND no guard shows harm.
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer6r import boot, fmt, win, churn
import analyze_steer10 as A10

MS = (80.0, 100.0, 120.0, 140.0)
DELTA = 2.65
KG = 3
GBONF = (100 * 0.05 / KG / 2, 100 - 100 * 0.05 / KG / 2)          # 0.833 / 99.167
P95 = (2.5, 97.5)


def load(pattern, label, seeds=None):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return out if seeds is None else {s: out[s] for s in seeds if s in out}


def wprior(r):
    return float(np.mean([win(r, M, DELTA) for M in MS]))


def losstype(r, M):
    """'win' | 'slow' (alive, finished after her or capped) | 'kill' (topped out / no move before her)"""
    from vs_race import evaluate
    o = evaluate(r, M, .15, DELTA)[0]
    return {"win_race": "win", "loss_race": "slow", "loss_cap": "slow", "loss_kill": "kill"}[o]


def paired(D1, D0, seeds, f, lo=2.5, hi=97.5):
    S = [s for s in seeds if s in D1 and s in D0]
    return (boot([f(D1[s]) - f(D0[s]) for s in S], lo, hi) if S else (np.nan,) * 3), S


def verdict(prim95, g1, g2, g3, ns, n_req):
    """prim95 = primary (mean, lo, hi) at 95%; g1/g2 = tap-out / tap<=100 deltas (bad = up), g3 = owner race delta
    (bad = down), all at the Bonferroni guard level. ns / n_req = (lulu, gb, rc) seeds."""
    if any(n < r for n, r in zip(ns, n_req)):
        return "incomplete"
    harm = g1[1] > 0 or g2[1] > 0 or g3[2] < 0
    return "PASS" if (prim95[1] > 0 and not harm) else "FAIL"


def m(D, S, f):
    return 100 * np.mean([f(D[s]) for s in S]) if S else np.nan


def stall_block(D0, D1, S, out, lab):
    parts = []
    for name, f in (("stall-pills act>=10 from <=16 v", A10.stall_end16), ("from <=4 v", A10.stall_end4),
                    ("longest stall (pills)", A10.longest_pills), ("longest stall (s)", A10.longest_s),
                    ("edge-virus str-stuck decisions", A10.edge_stuck)):
        d = boot([(f(D1[s]) - f(D0[s])) / 100.0 for s in S])
        parts.append(f"{name} {np.mean([f(D0[s]) for s in S]):.1f} -> {np.mean([f(D1[s]) for s in S]):.1f} "
                     f"d {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]")
    g36 = (100 * np.mean([A10.longest_s(D0[s]) >= 36 for s in S]), 100 * np.mean([A10.longest_s(D1[s]) >= 36 for s in S]))
    out(f"  {lab} stalls per game: " + "; ".join(parts) + f"; games with a stall >= 36 s {g36[0]:.1f}% -> {g36[1]:.1f}%")


def race_levels(D, S, out, lab, Ms=MS):
    """absolute levels of one arm in one race cell"""
    cs = [D[s] for s in S if D[s]["how"] == "clear"]
    t = [r["t_end"] for r in cs]
    parts = [f"M{int(M)} win {m(D, S, lambda r, M=M: win(r, M, DELTA)):.2f}%" for M in Ms]
    lt = {k: 100 * np.mean([losstype(D[s], M) == k for s in S for M in Ms]) for k in ("slow", "kill")}
    out(f"  {lab} (n={len(S)}): pace-prior win {m(D, S, wprior):.2f}% (loss {100 - m(D, S, wprior):.2f}%: slow "
        f"{lt['slow']:.2f} / kill {lt['kill']:.2f}); " + ", ".join(parts))
    out(f"      clears {len(cs)}/{len(S)}, time to clear p25/50/75 {np.percentile(t, 25):.1f}/{np.median(t):.1f}/"
        f"{np.percentile(t, 75):.1f} s, pills {np.median([r['pills'] for r in cs]):.0f}, s/pill "
        f"{np.median([r['t_end'] / r['pills'] for r in cs]):.2f}, tiles recv {np.median([r['tiles_recv'] for r in cs]):.1f}, "
        f"tap-out (how==topout) {m(D, S, lambda r: r['how'] == 'topout'):.2f}%"
        + (f", garbage time {np.median([r['garb_s'] for r in cs]):.1f} s/clear game" if cs and "garb_s" in cs[0] else ""))


def contrast(name, X, Y, S, out, rcell=False):
    """paired arm contrast in one race cell (X - Y)"""
    if rcell:
        d, _ = paired(X, Y, S, lambda r: win(r, 177.)); c = churn([Y[s] for s in S], [X[s] for s in S], lambda r: not win(r, 177.))
        out(f"  {name} owner race M177: {m(Y, S, lambda r: win(r, 177.)):.2f}% -> {m(X, S, lambda r: win(r, 177.)):.2f}%  "
            f"d {fmt(d)}  churn fixed {c[0]} / new {c[1]}")
        return d
    d, _ = paired(X, Y, S, wprior)
    out(f"  {name} LULU pace-prior win: {m(Y, S, wprior):.2f}% -> {m(X, S, wprior):.2f}%  d {fmt(d)}")
    for M in MS:
        dm, _ = paired(X, Y, S, lambda r, M=M: win(r, M, DELTA))
        c = churn([Y[s] for s in S], [X[s] for s in S], lambda r, M=M: not win(r, M, DELTA))
        out(f"    M{int(M)}: {m(Y, S, lambda r, M=M: win(r, M, DELTA)):.2f}% -> {m(X, S, lambda r, M=M: win(r, M, DELTA)):.2f}% "
            f"d {fmt(dm)} churn fixed {c[0]} / new {c[1]}")
    return d


def pilot():
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    LU = A10.LULU10B; RC = A10.RC_SEEDS
    L = {a: load(f"steer11/pilot/lulu10b_c11_{a}_*.jsonl", f"{a}~steer", LU) for a in ("s10_base", "s10_A16")}
    R = {a: load(f"steer11/pilot/rc10_c11_{a}_*.jsonl", f"{a}~steer", RC) for a in ("s10_base", "s10_A16")}
    Lo = {"s10_base": load("steer10/lulu10b_s10_base_*.jsonl", "s10_base~steer", LU),
          "s10_A16": load("steer10/lulu10b_s10_A16_*.jsonl", "s10_A16~steer", LU)}
    Ro = {"s10_base": load("steer8/rc10_fD_bdepD_*.jsonl", "fD_bdepD~steer", RC),
          "s10_A16": load("steer10/rc10_s10_A16_*.jsonl", "s10_A16~steer", RC)}
    out("STEER11 step 1 -- FAIR on the couch11 race clock (STEER10 blocks, declared reuse; legacy rows = banked STEER10/8)")
    clk = next(iter(L["s10_base"].values()))["rig"]["clock"] if L["s10_base"] else None
    out(f"clock: {clk}")
    for a in ("s10_base", "s10_A16"):
        S = [s for s in LU if s in L[a] and s in Lo[a]]
        out(f"\n[{a}] LULU race (lam 2.84, lulu_fit_202610b sizes, delta {DELTA})")
        race_levels(Lo[a], S, out, "legacy clock ")
        race_levels(L[a], S, out, "couch11 clock")
        Sr = [s for s in RC if s in R[a] and s in Ro[a]]
        out(f"[{a}] owner race (lam 2.36, Hartford sizes, M177)")
        for lab, D in (("legacy clock ", Ro[a]), ("couch11 clock", R[a])):
            if Sr:
                out(f"  {lab} (n={len(Sr)}): win {m(D, Sr, lambda r: win(r, 177.)):.2f}%, tap-out "
                    f"{m(D, Sr, lambda r: r['how'] == 'topout'):.2f}%, time to clear median "
                    f"{np.median([D[s]['t_end'] for s in Sr if D[s]['how'] == 'clear']):.1f} s")
    S = [s for s in LU if all(s in D for D in (L["s10_base"], L["s10_A16"], Lo["s10_base"], Lo["s10_A16"]))]
    if S:
        out(f"\nA16 - FAIR on the SAME seeds (n={len(S)}; the STEER10 hypothesis block: NOT confirmatory)")
        d_old = contrast("legacy clock ", Lo["s10_A16"], Lo["s10_base"], S, out)
        d_new = contrast("couch11 clock", L["s10_A16"], L["s10_base"], S, out)
        dd = np.array([wprior(L["s10_A16"][s]) - wprior(L["s10_base"][s]) for s in S])
        do = np.array([wprior(Lo["s10_A16"][s]) - wprior(Lo["s10_base"][s]) for s in S])
        out(f"  per-seed SD of the pace-prior win difference: legacy {100 * do.std(ddof=1):.2f} pp, couch11 "
            f"{100 * dd.std(ddof=1):.2f} pp; share of seeds with any difference: legacy {np.mean(do != 0):.3f}, "
            f"couch11 {np.mean(dd != 0):.3f}")
        out(f"  clock ratio (couch11 / legacy point estimate) {d_new[0] / d_old[0]:.2f}" if d_old[0] else "")
        stall_block(L["s10_base"], L["s10_A16"], S, out, "couch11 LULU")
        ct = churn([L["s10_base"][s] for s in S], [L["s10_A16"][s] for s in S], lambda r: r["how"] == "topout")
        dt, _ = paired(L["s10_A16"], L["s10_base"], S, lambda r: r["how"] == "topout")
        out(f"  couch11 LULU race tap-out: {m(L['s10_base'], S, lambda r: r['how'] == 'topout'):.2f}% -> "
            f"{m(L['s10_A16'], S, lambda r: r['how'] == 'topout'):.2f}% d {fmt(dt)} churn fixed {ct[0]} / new {ct[1]}")
        out("  loss type (couch11; FAIR -> A16, games summed over the four M):")
        for M in MS:
            k0 = {k: sum(losstype(L["s10_base"][s], M) == k for s in S) for k in ("slow", "kill")}
            k1 = {k: sum(losstype(L["s10_A16"][s], M) == k for s in S) for k in ("slow", "kill")}
            out(f"    M{int(M)}: slow {k0['slow']} -> {k1['slow']}, kill {k0['kill']} -> {k1['kill']}")
    Sr = [s for s in RC if all(s in D for D in (R["s10_base"], R["s10_A16"]))]
    if Sr:
        contrast("couch11 clock", R["s10_A16"], R["s10_base"], Sr, out, rcell=True)
    open("steer11/pilot.txt", "w").write("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------------------------- confirm
def confirm_seeds():
    import steer11_jobs as J
    c = J.CONFIRM
    return [c["lo"] + 2 * i for i in range(c["n"])], c["n"]


def confirm():
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    seeds, n = confirm_seeds()
    D = {}
    for a in ("s10_base", "s10_A16"):
        D[a] = (load(f"steer11/confirm/lulu11_{a}_*.jsonl", f"{a}~steer", seeds),
                load(f"steer11/confirm/gb11_{a}_*.jsonl", f"{a}@owner202610", seeds),
                load(f"steer11/confirm/rc11_{a}_*.jsonl", f"{a}~steer", seeds))
    (L0, G0, R0), (L1, G1, R1) = D["s10_base"], D["s10_A16"]
    Sl = [s for s in seeds if s in L0 and s in L1]; Sg = [s for s in seeds if s in G0 and s in G1]
    Sr = [s for s in seeds if s in R0 and s in R1]
    ns = (len(Sl), len(Sg), len(Sr))
    out(f"STEER11 confirm (PREREG_STEER11.md): rows FAIR {len(L0)}/{len(G0)}/{len(R0)}, A16 {len(L1)}/{len(G1)}/{len(R1)} "
        f"(lulu/gb/rc) of {n}; paired {ns}")
    if any(x < n for x in ns):
        out("INCOMPLETE: the arm contrast is WITHHELD until every pre-registered row exists (R97).")
        open("steer11/confirm.txt", "w").write("\n".join(lines) + "\n")
        return "incomplete"
    clocks = {r["rig"]["clock"]["name"] if isinstance(r["rig"]["clock"], dict) else r["rig"]["clock"]
              for DD in (L0, L1, R0, R1) for r in DD.values()}
    out(f"race-cell clocks stamped: {sorted(clocks)}")
    assert clocks == {"couch11"}, clocks
    prim, _ = paired(L1, L0, seeds, wprior, *P95)
    tap, _ = paired(G1, G0, seeds, lambda r: r["topout"], *GBONF)
    t100, _ = paired(G1, G0, seeds, lambda r: int(r["topout"] and r["pills"] <= 100), *GBONF)
    rc, _ = paired(R1, R0, seeds, lambda r: win(r, 177.), *GBONF)
    out("\nLEVELS (absolute, couch11 clock):")
    race_levels(L0, Sl, out, "FAIR LULU race")
    race_levels(L1, Sl, out, "A16  LULU race")
    out(f"\nPRIMARY LULU race pace-prior win, A16 - FAIR (n={ns[0]}): d {fmt(prim)} (95%)")
    contrast("primary", L1, L0, Sl, out)
    dgc, _ = paired(L1, L0, seeds, A10.wprior_g)
    out(f"  (secondary) legacy-style post-hoc garbage charge on top of couch11 (+3.2 s/release; double-counts, shown "
        f"only for comparability with STEER10): d {fmt(dgc)}")
    ct = churn([L0[s] for s in Sl], [L1[s] for s in Sl], lambda r: r["how"] == "topout")
    out(f"  LULU race tap-out (how == topout): {m(L0, Sl, lambda r: r['how'] == 'topout'):.2f}% -> "
        f"{m(L1, Sl, lambda r: r['how'] == 'topout'):.2f}% d {fmt(paired(L1, L0, seeds, lambda r: r['how'] == 'topout')[0])} "
        f"churn fixed {ct[0]} / new {ct[1]}")
    out("  LOSS TYPE (games; FAIR -> A16 with fixed / new):")
    for M in MS:
        row = []
        for k in ("slow", "kill"):
            a0 = [losstype(L0[s], M) == k for s in Sl]; a1 = [losstype(L1[s], M) == k for s in Sl]
            fx = sum(1 for x, y in zip(a0, a1) if x and not y); nw = sum(1 for x, y in zip(a0, a1) if y and not x)
            row.append(f"{k} {sum(a0)} -> {sum(a1)} ({fx}/{nw})")
        out(f"    M{int(M)}: " + ", ".join(row))
    stall_block(L0, L1, Sl, out, "LULU")
    stall_block(G0, G1, Sg, out, "gate-b")
    cg = churn([G0[s] for s in Sg], [G1[s] for s in Sg], lambda r: r["topout"])
    out(f"\nGUARD G1 gate-b tap-out (n={ns[1]}): {m(G0, Sg, lambda r: r['topout']):.2f}% -> {m(G1, Sg, lambda r: r['topout']):.2f}%"
        f"  d {fmt(tap)} (Bonferroni {GBONF[1]:.2f}%)  95% {fmt(paired(G1, G0, seeds, lambda r: r['topout'])[0])}"
        f"  churn fixed {cg[0]} / new {cg[1]}")
    out(f"GUARD G2 gate-b tap<=100: {m(G0, Sg, lambda r: int(r['topout'] and r['pills'] <= 100)):.2f}% -> "
        f"{m(G1, Sg, lambda r: int(r['topout'] and r['pills'] <= 100)):.2f}%  d {fmt(t100)} (Bonferroni)")
    cr = churn([R0[s] for s in Sr], [R1[s] for s in Sr], lambda r: not win(r, 177.))
    out(f"GUARD G3 owner race M177 (n={ns[2]}): {m(R0, Sr, lambda r: win(r, 177.)):.2f}% -> {m(R1, Sr, lambda r: win(r, 177.)):.2f}%"
        f"  d {fmt(rc)} (Bonferroni)  churn fixed {cr[0]} / new {cr[1]}")
    for cell, DD, S in (("lulu", L1, Sl), ("gb", G1, Sg), ("rc", R1, Sr)):
        tot = {k: sum(DD[s]["rule"][k] for s in S) for k in DD[S[0]]["rule"]}
        dec = max(tot.get("dec", 0), 1)
        out(f"  ACTIVITY A16 {cell}: " + ", ".join(f"{k} {v} ({100 * v / dec:.1f}%)" for k, v in tot.items() if k != "dec")
            + f" of {tot.get('dec', 0)} decisions")
    v = verdict(prim, tap, t100, rc, ns, (n, n, n))
    out(f"\nVERDICT (PREREG_STEER11): {v}   [primary lower95 {prim[1]:+.2f} > 0: {prim[1] > 0}; harm G1 {tap[1] > 0}, "
        f"G2 {t100[1] > 0}, G3 {rc[2] < 0}]")
    open("steer11/confirm.txt", "w").write("\n".join(lines) + "\n")
    return v


def selftest():
    rng = np.random.default_rng(11)

    def vec(n, p_fix, p_new):                 # -1 = fixed (good), +1 = new (bad) for a FAILURE indicator
        v = np.zeros(n, float); a, b = round(p_fix * n), round(p_new * n); v[:a] = -1; v[a:a + b] = 1
        return rng.permutation(v)
    N = 3000
    P = lambda d: boot(d, *P95)
    B = lambda d: boot(d, *GBONF)
    z = np.zeros(N)
    cases = [
        ("primary +2 (win), guards null", -vec(N, .05, .03), z, z, z, "PASS"),
        ("primary +2, tap +0.4 at high churn (no demonstrated harm)", -vec(N, .05, .03), vec(N, .03, .034), z, z, "PASS"),
        ("primary +2, tap +2 (harm)", -vec(N, .05, .03), vec(N, .01, .03), z, z, "FAIL"),
        ("primary +2, tap<=100 +0.6 (harm: 0 fixed / 18 new)", -vec(N, .05, .03), z, vec(N, .0, .006), z, "FAIL"),
        ("primary +2, tap<=100 +0.2 at churn (no harm)", -vec(N, .05, .03), z, vec(N, .004, .006), z, "PASS"),
        ("primary +2, owner race -2 (harm)", -vec(N, .05, .03), z, z, -vec(N, .0, .02), "FAIL"),
        ("primary +0.6 (CI spans 0)", -vec(N, .04, .034), z, z, z, "FAIL"),
        ("primary -1", -vec(N, .03, .04), z, z, z, "FAIL"),
        ("primary +2, owner race +2 (good side)", -vec(N, .05, .03), z, z, vec(N, .03, .01) * -1, "PASS"),
    ]
    ok = True
    for name, dl, dt, d1, dr, want in cases:
        got = verdict(P(dl), B(dt), B(d1), B(dr), (N, N, N), (N, N, N))
        ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} {name}: prim {fmt(P(dl))} tap {fmt(B(dt))} t100 {fmt(B(d1))} "
              f"race {fmt(B(dr))} -> {got}")
    got = verdict(P(cases[0][1]), B(z), B(z), B(z), (N, N, N - 1), (N, N, N))
    ok &= got == "incomplete"; print(f"  {'ok ' if got == 'incomplete' else 'BAD'} short rc n -> {got}")
    mut = {
        "primary on the mean": lambda p, t, a, r: p[0] > 0 and not (t[1] > 0 or a[1] > 0 or r[2] < 0),
        "primary on the upper CI": lambda p, t, a, r: p[2] > 0 and not (t[1] > 0 or a[1] > 0 or r[2] < 0),
        "tap guard dropped": lambda p, t, a, r: p[1] > 0 and not (a[1] > 0 or r[2] < 0),
        "tap<=100 guard dropped": lambda p, t, a, r: p[1] > 0 and not (t[1] > 0 or r[2] < 0),
        "race guard dropped": lambda p, t, a, r: p[1] > 0 and not (t[1] > 0 or a[1] > 0),
        "race guard sign flipped": lambda p, t, a, r: p[1] > 0 and not (t[1] > 0 or a[1] > 0 or r[1] > 0),
        "guards as non-inferiority at 0 (upper < 0 required)": lambda p, t, a, r: p[1] > 0 and t[2] < 0 and a[2] < 0 and r[1] > 0,
    }
    for mname, f in mut.items():
        killed = any(("PASS" if f(P(dl), B(dt), B(d1), B(dr)) else "FAIL") != want for _, dl, dt, d1, dr, want in cases)
        ok &= killed
        print(f"  mutant '{mname}': {'KILLED' if killed else 'SURVIVED'}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    {"pilot": pilot, "confirm": confirm}[sys.argv[1]]()
