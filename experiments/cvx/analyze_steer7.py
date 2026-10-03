"""STEER7 analysis (PREREG_STEER7.md): answer latency in the faster direction, s6_dist_target60 under the STEER6d
measured endgame latency distribution, shifted by S frames on every decision (+1, 0, -1, -2, -4) or zero-latency (ceil).

  python analyze_steer7.py              # identity + activity + primary verdict + worth-per-frame curve
  python analyze_steer7.py --selftest   # killed-mutant check of the verdict rule on synthetic tables (no data read)
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SEEDS_A = list(range(37934, 39133, 2))       # STEER6 screen block (600; banked STEER6d rows = identity reference)
SEEDS_B = list(range(39134, 40333, 2))       # STEER6b holdout block, first 600 (primary extension: S = 0, -1 only)
ARM = "s6_dist_target60"
SHIFTS = ("sp1", "s0", "sm1", "sm2", "sm4", "ceil")
SHIFT_F = {"sp1": 1, "s0": 0, "sm1": -1, "sm2": -2, "sm4": -4, "ceil": None}
SECONDARY = ("sp1", "sm2", "sm4", "ceil")
ROOT = os.environ.get("STEER7_ROOT", "steer7")       # override only for the analyzer dry-run on synthetic rows
B = 4000
NEWKEYS = ("shift", "lat_dec", "lat_ans_sum", "lat_nom_sum", "lat_clamp", "lat_overcredit_f", "lat_mask_calls",
           "lat_mask_tlat_sum", "lat_tempo_sum", "rig")


def boot(d, lo=2.5, hi=97.5, seed=0):
    d = np.asarray(d, float); rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), size=(B, len(d)))].mean(1)
    return 100 * d.mean(), 100 * np.percentile(m, lo), 100 * np.percentile(m, hi)


def fmt(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


def verdict(tap_ci, race_ci, n_gb, n_rc, n_req):
    """PRIMARY BAR (PREREG_STEER7 sec. 4): S = -1 vs S = 0, paired.
    PASS iff gate-(b) whole-game tap-out delta upper 95% CI < 0 (a cut whose CI excludes 0) AND no demonstrated race
    loss: race (lam 6, M 177, delta 2.65) win delta upper 95% CI >= 0. tap_ci / race_ci = (mean, lo, hi) in pp.
    (A -2 pp non-inferiority margin on the lower CI was REJECTED by the pass-condition audit: at the whole-game-shift
    race discordance measured in STEER6c, a NULL race outcome would fail it ~75% of the time at n = 1200.)
    Incomplete data -> 'incomplete'."""
    if n_gb < n_req or n_rc < n_req:
        return "incomplete"
    return "PASS" if (tap_ci[2] < 0 and race_ci[2] >= 0) else "FAIL"


def selftest():
    """Killed-mutant check: synthetic paired delta vectors on both sides of every threshold."""
    rng = np.random.default_rng(1)

    def vec(n, p_fix, p_new):                     # paired deltas: EXACTLY round(p_fix*n) -1s and round(p_new*n) +1s
        # (tap-out: -1 = fixed; race win: -1 = a game LOST)
        v = np.zeros(n, int); nf, nn = round(p_fix * n), round(p_new * n)
        v[:nf] = -1; v[nf:nf + nn] = 1
        return rng.permutation(v)
    n = 1200
    cases = [
        ("symmetric -2.7pp tap-out, race +2", vec(n, .08, .053), -vec(n, .06, .04), "PASS"),
        ("tap-out -3, race exactly null (null outcome must PASS the race guard)", vec(n, .08, .05), np.zeros(n), "PASS"),
        ("tap-out -3, race -1 at STEER6c race discordance 31% (CI spans 0: null-like, must PASS)",
         vec(n, .08, .05), vec(n, .16, .15), "PASS"),
        ("tap-out -3, race -4 significant (race loss)", vec(n, .08, .05), vec(n, .18, .14), "FAIL"),
        ("tap-out -1 (CI spans 0)", vec(n, .065, .055), -vec(n, .05, .03), "FAIL"),
        ("tap-out null", np.zeros(n), np.zeros(n), "FAIL"),
        ("tap-out +3 (faster is WORSE)", vec(n, .05, .08), -vec(n, .06, .04), "FAIL"),
    ]
    ok = True
    for name, dt, dr, want in cases:
        got = verdict(boot(dt), boot(dr), n, n, n)
        ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} {name}: tap {fmt(boot(dt))} race {fmt(boot(dr))} -> {got} (want {want})")
    got = verdict(boot(cases[0][1]), boot(cases[0][2]), n - 1, n, n)
    ok &= got == "incomplete"; print(f"  {'ok ' if got == 'incomplete' else 'BAD'} short n -> {got}")
    # mutants of the rule itself must be KILLED by the cases above
    mutants = {
        "tap uses LOWER ci": lambda t, r, a, b, c: "incomplete" if a < c or b < c else ("PASS" if t[1] < 0 and r[2] >= 0 else "FAIL"),
        "tap uses mean": lambda t, r, a, b, c: "incomplete" if a < c or b < c else ("PASS" if t[0] < 0 and r[2] >= 0 else "FAIL"),
        "race guard dropped": lambda t, r, a, b, c: "incomplete" if a < c or b < c else ("PASS" if t[2] < 0 else "FAIL"),
        "race guard = lower CI >= -2 (rejected margin)": lambda t, r, a, b, c: "incomplete" if a < c or b < c else ("PASS" if t[2] < 0 and r[1] >= -2 else "FAIL"),
        "race guard uses mean >= 0": lambda t, r, a, b, c: "incomplete" if a < c or b < c else ("PASS" if t[2] < 0 and r[0] >= 0 else "FAIL"),
        "race guard uses lower CI >= 0": lambda t, r, a, b, c: "incomplete" if a < c or b < c else ("PASS" if t[2] < 0 and r[1] >= 0 else "FAIL"),
    }
    for mname, mf in mutants.items():
        killed = any(mf(boot(dt), boot(dr), n, n, n) != want for _, dt, dr, want in cases)
        ok &= killed
        print(f"  mutant '{mname}': {'KILLED' if killed else 'SURVIVED'}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


def load(pattern, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def win(r, M, dl=2.65):
    from vs_race import evaluate
    return int(evaluate(r, M, .15, dl)[0] == "win_race")


def churn(base, arm, bad):
    """fixed = base bad & arm good; new = base good & arm bad."""
    return sum(1 for b, a in zip(base, arm) if bad(b) and not bad(a)), sum(1 for b, a in zip(base, arm) if not bad(b) and bad(a))


def identity():
    print("IDENTITY: S = 0 (block A) vs banked STEER6d 'full' rows (steer6/d6), every key of the banked row")
    allok = True
    for cell, pat in (("gb", "gb_full_*"), ("rc6", "rc6_full_*"), ("rc47", "rc47_full_*")):
        N = load(f"{ROOT}/A/{cell}_s0_*.jsonl", SEEDS_A); O = load(f"steer6/d6/{pat}.jsonl", SEEDS_A)
        same = sum(1 for s in N if {k: v for k, v in N[s].items() if k not in NEWKEYS} == O.get(s))
        print(f"  {cell}: {same} / {len(N)} identical (banked {len(O)})")
        allok &= same == len(N) == len(O) == 600
    print("  ->", "EXACT" if allok else "NOT EXACT / incomplete")
    return allok


def activity(rows, label):
    dec = sum(r["lat_dec"] for r in rows)
    if not dec:
        return f"{label}: no rows"
    return (f"{label}: decisions {dec}, answer frame mean {sum(r['lat_ans_sum'] for r in rows) / dec:6.2f} "
            f"(nominal sample {sum(r['lat_nom_sum'] for r in rows) / dec:5.2f}), clamp binds {100 * sum(r['lat_clamp'] for r in rows) / dec:5.2f}% "
            f"of decisions, tempo over-credit {sum(r['lat_overcredit_f'] for r in rows) / dec:.3f} f/dec, "
            f"mask T_LAT mean {sum(r['lat_mask_tlat_sum'] for r in rows) / max(1, sum(r['lat_mask_calls'] for r in rows)):5.2f}, "
            f"tempo shift mean {sum(r['lat_tempo_sum'] for r in rows) / dec:+.2f} f")


def main():
    from vs_race import evaluate  # noqa: F401  (fail early if the race evaluator is missing)
    identity()
    G = {s: load(f"{ROOT}/A/gb_{s}_*.jsonl", SEEDS_A) for s in SHIFTS}
    R = {s: load(f"{ROOT}/A/rc6_{s}_*.jsonl", SEEDS_A) for s in SHIFTS}
    L = {s: load(f"{ROOT}/A/rc47_{s}_*.jsonl", SEEDS_A) for s in SHIFTS}
    GB = {s: load(f"{ROOT}/B/gb_{s}_*.jsonl", SEEDS_B) for s in ("s0", "sm1")}
    RB = {s: load(f"{ROOT}/B/rc6_{s}_*.jsonl", SEEDS_B) for s in ("s0", "sm1")}

    print("\nACTIVITY (rule 26) per arm, block A gate (b) / race lam 6 / LULU race:")
    for s in SHIFTS:
        for cell, D in (("gb", G), ("rc6", R), ("rc47", L)):
            print("  " + activity(list(D[s].values()), f"{s:4s} {cell:4s}"))
    for s in ("s0", "sm1"):
        print("  " + activity(list(GB[s].values()), f"{s:4s} gb  B") + "\n  " + activity(list(RB[s].values()), f"{s:4s} rc6 B"))

    # ---------------- PRIMARY: S = -1 vs S = 0, blocks A + B (n = 1200), gate (b) tap-out + race lam 6
    gb0 = {**G["s0"], **GB["s0"]}; gb1 = {**G["sm1"], **GB["sm1"]}
    rc0 = {**R["s0"], **RB["s0"]}; rc1 = {**R["sm1"], **RB["sm1"]}
    S = [s for s in SEEDS_A + SEEDS_B if s in gb0 and s in gb1]; SR = [s for s in SEEDS_A + SEEDS_B if s in rc0 and s in rc1]
    print(f"\nPRIMARY (PREREG_STEER7 sec. 4): S = -1 f vs S = 0, paired, gate b n={len(S)}, race n={len(SR)}")
    if S and SR:
        tt = boot([gb1[s]["topout"] - gb0[s]["topout"] for s in S])
        tr = boot([win(rc1[s], 177.) - win(rc0[s], 177.) for s in SR])
        t1 = boot([int(gb1[s]["topout"] and gb1[s]["pills"] <= 100) - int(gb0[s]["topout"] and gb0[s]["pills"] <= 100) for s in S])
        f, nw = churn([gb0[s] for s in S], [gb1[s] for s in S], lambda r: r["topout"])
        rf, rn = churn([rc0[s] for s in SR], [rc1[s] for s in SR], lambda r: not win(r, 177.))
        v = verdict(tt, tr, len(S), len(SR), 1200)
        print(f"  gate b tap-out {100 * np.mean([gb0[s]['topout'] for s in S]):.2f}% -> {100 * np.mean([gb1[s]['topout'] for s in S]):.2f}%  "
              f"d {fmt(tt)}  churn fixed {f} / new {nw}")
        print(f"  race win (lam 6, M 177, delta 2.65) {100 * np.mean([win(rc0[s], 177.) for s in SR]):.2f}% -> "
              f"{100 * np.mean([win(rc1[s], 177.) for s in SR]):.2f}%  d {fmt(tr)}  churn fixed {rf} / new {rn}")
        print(f"  tap<=100 d {fmt(t1)} (reported, no bar)")
        for blk, seeds in (("A", SEEDS_A), ("B", SEEDS_B)):
            s_ = [s for s in seeds if s in gb0 and s in gb1]
            if s_:
                print(f"    block {blk} (n={len(s_)}): tap-out d {fmt(boot([gb1[s]['topout'] - gb0[s]['topout'] for s in s_]))}")
        print(f"  -> PRIMARY VERDICT: {v}")

    # ---------------- CURVE (block A, n = 600 per arm), vs S = 0
    print("\nWORTH-PER-FRAME CURVE (block A, n=600 paired vs S = 0 = dist_target60 @ STEER6d latency):")
    hdr = ("arm", "dframes", "gb tap-out d [95%]", "fix/new", "tap<=100 d", "race M177 d [95%]", "fix/new",
           "LULU M140 d [95%]", "fix/new", "race-row tap-out d", "LULU-row tap-out d")
    print("  " + " | ".join(hdr))
    curve = {}
    base_ans = {c: sum(r["lat_ans_sum"] for r in D["s0"].values()) / max(1, sum(r["lat_dec"] for r in D["s0"].values()))
                for c, D in (("gb", G), ("rc6", R), ("rc47", L))}
    for s in SHIFTS:
        Sg = [x for x in SEEDS_A if x in G[s] and x in G["s0"]]; Sr = [x for x in SEEDS_A if x in R[s] and x in R["s0"]]
        Sl = [x for x in SEEDS_A if x in L[s] and x in L["s0"]]
        if not (Sg and Sr and Sl):
            print(f"  {s}: incomplete gb {len(Sg)} rc6 {len(Sr)} rc47 {len(Sl)}"); continue
        dec = sum(G[s][x]["lat_dec"] for x in Sg)
        dfr = sum(G[s][x]["lat_ans_sum"] for x in Sg) / dec - base_ans["gb"]
        tt = boot([G[s][x]["topout"] - G["s0"][x]["topout"] for x in Sg])
        t1 = boot([int(G[s][x]["topout"] and G[s][x]["pills"] <= 100) - int(G["s0"][x]["topout"] and G["s0"][x]["pills"] <= 100) for x in Sg])
        tr = boot([win(R[s][x], 177.) - win(R["s0"][x], 177.) for x in Sr])
        tl = boot([win(L[s][x], 140.) - win(L["s0"][x], 140.) for x in Sl])
        rt = boot([(R[s][x]["how"] == "topout") - (R["s0"][x]["how"] == "topout") for x in Sr])
        lt = boot([(L[s][x]["how"] == "topout") - (L["s0"][x]["how"] == "topout") for x in Sl])
        cg = churn([G["s0"][x] for x in Sg], [G[s][x] for x in Sg], lambda r: r["topout"])
        cr = churn([R["s0"][x] for x in Sr], [R[s][x] for x in Sr], lambda r: not win(r, 177.))
        cl = churn([L["s0"][x] for x in Sl], [L[s][x] for x in Sl], lambda r: not win(r, 140.))
        curve[s] = dict(dframes=dfr, tap=tt, race=tr, lulu=tl, cg=cg, cr=cr, cl=cl)
        print(f"  {s:4s} | {dfr:+6.2f} | {fmt(tt)} | {cg[0]}/{cg[1]} | {fmt(t1)} | {fmt(tr)} | {cr[0]}/{cr[1]} | {fmt(tl)} | "
              f"{cl[0]}/{cl[1]} | {fmt(rt)} | {fmt(lt)}")
        if s in SECONDARY:
            b_t = boot([G[s][x]["topout"] - G["s0"][x]["topout"] for x in Sg], 0.625, 99.375)
            b_r = boot([win(R[s][x], 177.) - win(R["s0"][x], 177.) for x in Sr], 0.625, 99.375)
            print(f"         Bonferroni 98.75% (4 secondary arms): tap-out {fmt(b_t)}  race {fmt(b_r)}")
        base_t = 100 * np.mean([G["s0"][x]["topout"] for x in Sg])
        print(f"         gate b tap-out {base_t:.2f}% -> {100 * np.mean([G[s][x]['topout'] for x in Sg]):.2f}%   "
              f"race {100 * np.mean([win(R['s0'][x], 177.) for x in Sr]):.2f}% -> {100 * np.mean([win(R[s][x], 177.) for x in Sr]):.2f}%   "
              f"LULU {100 * np.mean([win(L['s0'][x], 140.) for x in Sl]):.2f}% -> {100 * np.mean([win(L[s][x], 140.) for x in Sl]):.2f}%")

    # ---------------- SYMMETRY (descriptive): d(+1) + d(-1), paired per seed on block A; symmetric <=> CI spans 0
    Ss = [x for x in SEEDS_A if all(x in G[s] for s in ("sp1", "s0", "sm1"))]
    Srs = [x for x in SEEDS_A if all(x in R[s] for s in ("sp1", "s0", "sm1"))]
    if Ss and Srs:
        sym_t = boot([G["sp1"][x]["topout"] + G["sm1"][x]["topout"] - 2 * G["s0"][x]["topout"] for x in Ss])
        sym_r = boot([win(R["sp1"][x], 177.) + win(R["sm1"][x], 177.) - 2 * win(R["s0"][x], 177.) for x in Srs])
        print(f"\nSYMMETRY d(+1) + d(-1) (block A, paired; 0 = symmetric): tap-out {fmt(sym_t)}  race {fmt(sym_r)}")

    # ---------------- SLOPE (descriptive): pp per frame, joint seed bootstrap over the integer-shift arms
    arms_int = [s for s in ("sp1", "s0", "sm1", "sm2", "sm4") if s in curve or s == "s0"]
    Sj = [x for x in SEEDS_A if all(x in G[s] and x in R[s] and x in L[s] for s in arms_int)]
    if len(arms_int) == 5 and Sj:
        xs = np.array([SHIFT_F[s] for s in arms_int], float)
        Tg = np.array([[G[s][x]["topout"] for s in arms_int] for x in Sj], float)
        Tr = np.array([[win(R[s][x], 177.) for s in arms_int] for x in Sj], float)
        Tl = np.array([[win(L[s][x], 140.) for s in arms_int] for x in Sj], float)
        rng = np.random.default_rng(0)
        idx = rng.integers(0, len(Sj), size=(B, len(Sj)))

        def slope(M, cols):
            xx = xs[cols]; xc = xx - xx.mean()
            ym = M[:, cols].mean(0); pt = 100 * (xc @ (ym - ym.mean())) / (xc @ xc)
            bm = M[idx][:, :, cols].mean(1)
            bs = 100 * ((bm - bm.mean(1, keepdims=True)) @ xc) / (xc @ xc)
            return pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)
        allc = [0, 1, 2, 3, 4]; fast = [1, 2, 3, 4]
        print(f"\nSLOPE (descriptive, OLS over arm means, joint seed bootstrap, n={len(Sj)}): pp per +1 frame of latency")
        for name, M in (("gate b tap-out", Tg), ("race win M177", Tr), ("LULU race win M140", Tl)):
            a, f_ = slope(M, allc), slope(M, fast)
            print(f"  {name:20s} all (+1..-4): {a[0]:+.2f} [{a[1]:+.2f}, {a[2]:+.2f}]    faster side (0..-4): {f_[0]:+.2f} [{f_[1]:+.2f}, {f_[2]:+.2f}]")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    main()
