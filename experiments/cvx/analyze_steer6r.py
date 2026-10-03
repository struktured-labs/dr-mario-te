"""STEER6r analysis (PREREG_STEER6r.md): DIST60 vs ANTIBODY (and the 9/26 TAP-only build) under the corrected
2026-10 send fits.

  python analyze_steer6r.py              # identity-free: verdict + secondary + old-vs-new levels
  python analyze_steer6r.py --selftest   # killed-mutant check of the verdict rule (no data read)
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GB_SEEDS = sorted(set(range(39134, 40933, 2)) | set(range(33000, 34199, 2)))      # 1,500 = the STEER6b confirm block
RC_SEEDS = list(range(39134, 40333, 2))                                             # 600
ARMS = {"dist": "s6_dist_target60", "anti": "s5b_hsv512", "tap": "s4_base"}
B = 4000


def boot(d, lo=2.5, hi=97.5, seed=0):
    d = np.asarray(d, float); rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), size=(B, len(d)))].mean(1)
    return 100 * d.mean(), 100 * np.percentile(m, lo), 100 * np.percentile(m, hi)


def fmt(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


def verdict(tap_ci, rc_ci, lulu_ci, ns, n_req):
    """PRIMARY (PREREG_STEER6r sec. 5): GAIN SURVIVES iff gb10 tap-out delta upper CI < 0 AND rc10 race delta upper
    CI >= 0 AND lulu10 race delta upper CI >= 0 (no demonstrated race loss). ns = (n_gb, n_rc, n_lulu), n_req likewise."""
    if any(n < r for n, r in zip(ns, n_req)):
        return "incomplete"
    return "GAIN SURVIVES" if (tap_ci[2] < 0 and rc_ci[2] >= 0 and lulu_ci[2] >= 0) else "DOES NOT SURVIVE"


def selftest():
    rng = np.random.default_rng(2)

    def vec(n, p_fix, p_new):           # tap-out: -1 = fixed; race win: -1 = a game LOST
        v = np.zeros(n, int); a, b = round(p_fix * n), round(p_new * n); v[:a] = -1; v[a:a + b] = 1
        return rng.permutation(v)
    req = (1500, 600, 600)
    cases = [
        ("gain -2.5, races +4/+8", vec(1500, .05, .025), -vec(600, .10, .06), -vec(600, .12, .04), "GAIN SURVIVES"),
        ("gain -2.5, races exactly null (null must pass)", vec(1500, .05, .025), np.zeros(600), np.zeros(600), "GAIN SURVIVES"),
        ("gain -2.5, race -1 at high discordance (CI spans 0: must pass)", vec(1500, .05, .025), vec(600, .16, .15), np.zeros(600), "GAIN SURVIVES"),
        ("gain -2.5, race significantly worse", vec(1500, .05, .025), vec(600, .18, .12), np.zeros(600), "DOES NOT SURVIVE"),
        ("gain -2.5, LULU significantly worse", vec(1500, .05, .025), np.zeros(600), vec(600, .18, .12), "DOES NOT SURVIVE"),
        ("tap-out -0.7 (CI spans 0)", vec(1500, .035, .028), -vec(600, .10, .06), -vec(600, .12, .04), "DOES NOT SURVIVE"),
        ("tap-out +2 (worse)", vec(1500, .02, .04), -vec(600, .10, .06), -vec(600, .12, .04), "DOES NOT SURVIVE"),
    ]
    ok = True
    for name, dt, dr, dl, want in cases:
        got = verdict(boot(dt), boot(dr), boot(dl), req, req)
        ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} {name}: tap {fmt(boot(dt))} race {fmt(boot(dr))} lulu {fmt(boot(dl))} -> {got}")
    got = verdict(boot(cases[0][1]), boot(cases[0][2]), boot(cases[0][3]), (1500, 599, 600), req)
    ok &= got == "incomplete"; print(f"  {'ok ' if got == 'incomplete' else 'BAD'} short race n -> {got}")
    mut = {
        "tap lower CI": lambda t, r, l: t[1] < 0 and r[2] >= 0 and l[2] >= 0,
        "tap mean": lambda t, r, l: t[0] < 0 and r[2] >= 0 and l[2] >= 0,
        "race guard dropped": lambda t, r, l: t[2] < 0 and l[2] >= 0,
        "lulu guard dropped": lambda t, r, l: t[2] < 0 and r[2] >= 0,
        "race guard -2 margin on lower CI": lambda t, r, l: t[2] < 0 and r[1] >= -2 and l[1] >= -2,
        "race guard lower CI >= 0": lambda t, r, l: t[2] < 0 and r[1] >= 0 and l[1] >= 0,
    }
    for mname, f in mut.items():
        killed = any(("GAIN SURVIVES" if f(boot(dt), boot(dr), boot(dl)) else "DOES NOT SURVIVE") != want
                     for _, dt, dr, dl, want in cases)
        ok &= killed
        print(f"  mutant '{mname}': {'KILLED' if killed else 'SURVIVED'}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


def load(pattern, label, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def win(r, M, dl=2.65):
    from vs_race import evaluate
    return int(evaluate(r, M, .15, dl)[0] == "win_race")


def churn(b, a, bad):
    return sum(1 for x, y in zip(b, a) if bad(x) and not bad(y)), sum(1 for x, y in zip(b, a) if not bad(x) and bad(y))


def compare(G, R, L, x, y, lo=2.5, hi=97.5):
    """x vs y (x - y), paired, on each cell's common seeds. Returns the three CIs + text."""
    Sg = [s for s in GB_SEEDS if s in G[x] and s in G[y]]
    Sr = [s for s in RC_SEEDS if s in R[x] and s in R[y]]
    Sl = [s for s in RC_SEEDS if s in L[x] and s in L[y]]
    tt = boot([G[x][s]["topout"] - G[y][s]["topout"] for s in Sg], lo, hi) if Sg else (np.nan,) * 3
    t1 = boot([int(G[x][s]["topout"] and G[x][s]["pills"] <= 100) - int(G[y][s]["topout"] and G[y][s]["pills"] <= 100) for s in Sg], lo, hi) if Sg else (np.nan,) * 3
    tr = boot([win(R[x][s], 177.) - win(R[y][s], 177.) for s in Sr], lo, hi) if Sr else (np.nan,) * 3
    tl = boot([win(L[x][s], 140.) - win(L[y][s], 140.) for s in Sl], lo, hi) if Sl else (np.nan,) * 3
    cg = churn([G[y][s] for s in Sg], [G[x][s] for s in Sg], lambda r: r["topout"])
    cr = churn([R[y][s] for s in Sr], [R[x][s] for s in Sr], lambda r: not win(r, 177.))
    cl = churn([L[y][s] for s in Sl], [L[x][s] for s in Sl], lambda r: not win(r, 140.))
    lv = lambda D, S, f: 100 * np.mean([f(D[s]) for s in S]) if S else np.nan
    txt = (f"  gb10 tap-out (n={len(Sg)}) {lv(G[y], Sg, lambda r: r['topout']):.2f}% -> {lv(G[x], Sg, lambda r: r['topout']):.2f}%  "
           f"d {fmt(tt)}  churn fixed {cg[0]} / new {cg[1]}   tap<=100 d {fmt(t1)}\n"
           f"  rc10 race win M177 (n={len(Sr)}) {lv(R[y], Sr, lambda r: win(r, 177.)):.2f}% -> {lv(R[x], Sr, lambda r: win(r, 177.)):.2f}%  "
           f"d {fmt(tr)}  churn fixed {cr[0]} / new {cr[1]}   race-row tap-out d "
           f"{fmt(boot([(R[x][s]['how'] == 'topout') - (R[y][s]['how'] == 'topout') for s in Sr], lo, hi)) if Sr else 'n/a'}\n"
           f"  lulu10 race win M140 (n={len(Sl)}) {lv(L[y], Sl, lambda r: win(r, 140.)):.2f}% -> {lv(L[x], Sl, lambda r: win(r, 140.)):.2f}%  "
           f"d {fmt(tl)}  churn fixed {cl[0]} / new {cl[1]}")
    return tt, tr, tl, (len(Sg), len(Sr), len(Sl)), txt


def main():
    G = {k: load(f"steer6r/gb10_{k}_*.jsonl", f"{a}@owner202610", GB_SEEDS) for k, a in ARMS.items()}
    R = {k: load(f"steer6r/rc10_{k}_*.jsonl", f"{a}~steer", RC_SEEDS) for k, a in ARMS.items()}
    L = {k: load(f"steer6r/lulu10_{k}_*.jsonl", f"{a}~steer", RC_SEEDS) for k, a in ARMS.items()}
    for k in ARMS:
        print(f"rows {k}: gb10 {len(G[k])}  rc10 {len(R[k])}  lulu10 {len(L[k])}  "
              f"garbage cells/game gb10 {np.mean([r['garbage'] for r in G[k].values()]) if G[k] else float('nan'):.1f}")
    print("\nPRIMARY (PREREG_STEER6r sec. 5): DIST60 vs ANTIBODY")
    tt, tr, tl, ns, txt = compare(G, R, L, "dist", "anti")
    print(txt)
    print(f"  -> {verdict(tt, tr, tl, ns, (1500, 600, 600))}")
    print(f"     race gain survives (lower CI > 0): rc10 {'yes' if tr[1] > 0 else 'no'}, lulu10 {'yes' if tl[1] > 0 else 'no'}")
    for x, y in (("dist", "tap"), ("anti", "tap")):
        print(f"\nSECONDARY {x.upper()} vs TAP-only (95%; Bonferroni 97.5% below)")
        print(compare(G, R, L, x, y)[4])
        b = compare(G, R, L, x, y, 1.25, 98.75)
        print(f"  Bonferroni 97.5%: tap-out {fmt(b[0])}  race {fmt(b[1])}  lulu {fmt(b[2])}")

    # ---- old vs new levels on identical seeds (OWNER-0804 / lam 6 banked)
    print("\nOLD vs NEW (identical seeds)")
    GO = {"anti": load("steer5d/*/gb_s5b_hsv512_*.jsonl", "fw540_steer_s5b_hsv512", GB_SEEDS),
          "dist": load("steer6/holdout/*/gb_s6_dist_target60_*.jsonl", "s6_dist_target60@owner0804", GB_SEEDS)}
    RO = {"anti": load("steer5d/*/rc_s5b_hsv512_*.jsonl", "s5b_hsv512~steer", RC_SEEDS),
          "dist": load("steer6/holdout/*/rc_s6_dist_target60_*.jsonl", "s6_dist_target60~steer", RC_SEEDS)}
    S = [s for s in GB_SEEDS if all(s in GO[k] and s in G[k] for k in ("anti", "dist"))]
    if S:
        for k in ("anti", "dist"):
            print(f"  {ARMS[k]:18s} gate-b tap-out OWNER-0804 {100 * np.mean([GO[k][s]['topout'] for s in S]):.2f}%  ->  "
                  f"owner202610 {100 * np.mean([G[k][s]['topout'] for s in S]):.2f}%   (n={len(S)}; garbage cells/game "
                  f"{np.mean([GO[k][s]['garbage'] for s in S]):.1f} -> {np.mean([G[k][s]['garbage'] for s in S]):.1f})")
        old = [GO["dist"][s]["topout"] - GO["anti"][s]["topout"] for s in S]
        new = [G["dist"][s]["topout"] - G["anti"][s]["topout"] for s in S]
        print(f"  DIST60 - ANTIBODY tap-out: old {fmt(boot(old))}  new {fmt(boot(new))}  new - old (DiD) "
              f"{fmt(boot([n - o for n, o in zip(new, old)]))}")
    Sr = [s for s in RC_SEEDS if all(s in RO[k] and s in R[k] for k in ("anti", "dist"))]
    if Sr:
        old = [win(RO["dist"][s], 177.) - win(RO["anti"][s], 177.) for s in Sr]
        new = [win(R["dist"][s], 177.) - win(R["anti"][s], 177.) for s in Sr]
        print(f"  race M177: ANTIBODY win lam 6 {100 * np.mean([win(RO['anti'][s], 177.) for s in Sr]):.2f}% -> lam 2.36 "
              f"{100 * np.mean([win(R['anti'][s], 177.) for s in Sr]):.2f}%;  DIST60 - ANTIBODY old {fmt(boot(old))}  new {fmt(boot(new))}")
        print(f"  race-row tap-out ANTIBODY lam 6 {100 * np.mean([RO['anti'][s]['how'] == 'topout' for s in Sr]):.2f}% -> lam 2.36 "
              f"{100 * np.mean([R['anti'][s]['how'] == 'topout' for s in Sr]):.2f}%")
    print("  LULU old (lam 4.7, SCREEN block 37934-39132, a different seed block): ANTIBODY 68.5% -> DIST60 81.0% (+12.50 "
          "[+9.67, +15.50]), race-row tap-out 26.7% -> 16.7% (steer6/opp, RESULT_STEER6.md)")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    main()
