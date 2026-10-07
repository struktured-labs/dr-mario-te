"""STEER13 analysis (PREREG_STEER13.md). Withholds every contrast until all pre-registered rows exist (R97).

  python analyze_steer13.py             -> steer13/analysis.txt
  python analyze_steer13.py --selftest  -> killed-mutant check of both decision rules (no data read)

PART A (silicon-like execution = random-root misses at q 4 %; sensitivity q 2 %): A16 / R60 vs FAIR at the SAME dose.
  PRIMARY  LULU race win at her measured M 167.5 (delta 2.65, sigma 0.15), n = 2,000 paired; Bonferroni over K = 2 arms.
  GUARDS   owner race M 239.5 and gate-b tap-out (n = 600): harm iff the Bonferroni CI (2 arms x 2 guards = 4) excludes 0
           on the bad side.  RECOMMEND (couch test) iff primary Bonferroni lower > 0 AND no guard harm.
  ALSO     loss split slow / kill, churn, gate-b tap<=100, stall metrics (act-stall = no legal placement of the ACTUAL
           pill clears any virus, >= 10 decisions; truncated at her finish T_L and untruncated), q 2 % deltas.
PART B (anytime commit + DRLATEGUARD, residual miss dose q_B): B_14886 (today: fw 1488, MIN_THINK 6 f), B_v116 / v114 /
  v112 (V11, MIN_THINK 6 / 4 / 2 f), B_orc6 / B_orc4 (oracle: the final answer at the gate, 6 / 4 f).
  PRIMARY contrasts (LULU race at M 167.5, Bonferroni K = 3): v114 - v116 (DRMINTHINK = 8 with V11), v112 - v116,
           v116 - 14886 (V11 vs today at 6 f).  WORTH A COUCH TEST (DRMINTHINK = 8 + V11) iff v114 - v116 Bonferroni
           lower > 0 AND no harm (gate-b tap-out up / owner race down, Bonferroni over the 2 guards x 3 contrasts).
  ALSO     survival of the -2 f gain = (v114 - v116) / (orc4 - orc6) (seed bootstrap); orc6 - 14886 (what today's
           non-final commits cost); absolute loss rates vs dr. lulu / the owner per arm; activity (non-final commits,
           late publishes, adoptions, refusals, landed on the final, tempo f per pill).
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer6r import boot, fmt, churn
from vs_race import evaluate
import steer12_stallcal as SC
import steer13_jobs as J

M_LULU, M_OWNER, DELTA, SIGMA = 167.5, 239.5, 2.65, 0.15
A_ARMS = ("A_fair_q04", "A_a16_q04", "A_r60_q04")
A_SENS = ("A_fair_q02", "A_a16_q02", "A_r60_q02")
B_REF = None                                                    # set from steer13_jobs.B_MAIN
Pc = lambda K: (100 * 0.05 / K / 2, 100 - 100 * 0.05 / K / 2)


def load(pattern, label, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def win(r, M, dl=DELTA):
    return int(evaluate(r, M, SIGMA, dl)[0] == "win_race")


def ltype(r, M):
    o = evaluate(r, M, SIGMA, DELTA)[0]
    return {"win_race": "win", "loss_race": "slow", "loss_cap": "slow", "loss_kill": "kill"}[o]


def cls(ci):
    return "HELPS" if ci[1] > 0 else ("HURTS" if ci[2] < 0 else "n.s.")


def rule_A(prim_bonf, tap_bonf, rc_bonf):
    """RECOMMEND iff primary Bonferroni lower > 0 and neither guard shows demonstrated harm"""
    return "RECOMMEND" if (prim_bonf[1] > 0 and not tap_bonf[1] > 0 and not rc_bonf[2] < 0) else "NOT RECOMMENDED"


def rule_B(prim_bonf, tap_bonf, rc_bonf):
    return "WORTH A COUCH TEST" if (prim_bonf[1] > 0 and not tap_bonf[1] > 0 and not rc_bonf[2] < 0) else "NOT WORTH IT"


def m(D, S, f):
    return 100 * np.mean([f(D[s]) for s in S])


def levels(lab, L, R, G, SL, SG, out):
    sl = 100 * np.mean([ltype(L[s], M_LULU) == "slow" for s in SL]); kl = 100 * np.mean([ltype(L[s], M_LULU) == "kill" for s in SL])
    w = boot([win(L[s], M_LULU) for s in SL])
    cs = [L[s] for s in SL if L[s]["how"] == "clear"]
    k = {kk: sum(L[s]["knob"][kk] for s in SL) for kk in L[SL[0]]["knob"]}
    dec = max(k["dec"], 1)
    act = (f"miss {100 * k['miss'] / dec:.2f}%, landed on the final {100 * k['landed_final'] / dec:.1f}%"
           + (f", non-final commits {100 * k['nonfinal_commit'] / dec:.1f}%, late {k['late'] / dec:.3f}/pill, adopted "
              f"{k['adopt'] / dec:.3f}, refused {k['refuse'] / dec:.3f}, tempo {k['tempo_f'] / dec:+.2f} f/pill"
              if "nonfinal_commit" in k and lab.startswith("B") else ""))
    out(f"  {lab:12s} LULU loss {100 - w[0]:5.2f}% [{100 - w[2]:.2f}, {100 - w[1]:.2f}] (slow {sl:.2f} / kill {kl:.2f}) | owner loss "
        f"{100 - m(R, SG, lambda r: win(r, M_OWNER)):.2f}% | gate-b tap-out {m(G, SG, lambda r: r['topout']):.2f}% | t_clear "
        f"{np.median([r['t_end'] for r in cs]):.1f} s, s/pill {np.median([r['t_end'] / r['pills'] for r in cs]):.2f} | {act}")


def contrast(lab, X, Y, S, f, K, out, bad_up=False):
    d = boot([f(X[s]) - f(Y[s]) for s in S]); db = boot([f(X[s]) - f(Y[s]) for s in S], *Pc(K))
    c = churn([Y[s] for s in S], [X[s] for s in S], (lambda r: f(r)) if bad_up else (lambda r: not f(r)))
    out(f"    {lab}: {m(Y, S, f):.2f}% -> {m(X, S, f):.2f}%  d {fmt(d)}  Bonferroni(K={K}) {fmt(db)}  churn fixed {c[0]} / new {c[1]}")
    return d, db


def stall_rows(D, S, M):
    tr = [SC.metrics(SC.sim_runs(D[s], evaluate(D[s], M, SIGMA, DELTA)[1])) for s in S]
    un = [SC.metrics(SC.sim_runs(D[s])) for s in S]
    return tr, un


def main():
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    assert J.B_MAIN is not None
    B_ARMS = J.B_MAIN
    SL = [J.LO + 2 * i for i in range(J.N_LULU)]; SG = [J.LO + 2 * i for i in range(J.N_GUARD)]
    SS = [J.LO + 2 * i for i in range(J.N_SENS)]
    L = {a: load(f"steer13/main/lulu13_{a}_*.jsonl", f"{a}~steer", SL) for a in A_ARMS + A_SENS + B_ARMS}
    GA = A_ARMS + tuple(a for a in B_ARMS if not a.startswith("B_orc"))      # oracle arms: LULU only
    R = {a: load(f"steer13/main/rc13_{a}_*.jsonl", f"{a}~steer", SG) for a in GA}
    G = {a: load(f"steer13/main/gb13_{a}_*.jsonl", f"{a}@owner202610", SG) for a in GA}
    need = {a: (J.N_SENS if a in A_SENS else J.N_LULU) for a in L}
    short = [a for a in L if len(L[a]) < need[a]] + [a for a in R if len(R[a]) < J.N_GUARD or len(G[a]) < J.N_GUARD]
    out("STEER13 rows: " + ", ".join(f"{a} {len(L[a])}/{len(R.get(a, {}))}/{len(G.get(a, {}))}" for a in L))
    if short:
        out(f"INCOMPLETE ({short}): every contrast is WITHHELD (R97).")
        open("steer13/analysis.txt", "w").write("\n".join(lines) + "\n")
        return
    # ------------------------------------------------------------------------------------------- PART A
    out(f"\n=== PART A: stall fixes under silicon-like execution (random-root misses q 4 %) ===")
    out("ABSOLUTE (LULU M 167.5 n=2,000; owner M 239.5 and gate b n=600):")
    for a in A_ARMS:
        levels(a, L[a], R[a], G[a], SL, SG, out)
    F = "A_fair_q04"
    for a in ("A_a16_q04", "A_r60_q04"):
        out(f"\n  [{a} vs {F}]")
        p, pb = contrast("PRIMARY LULU race M167.5", L[a], L[F], SL, lambda r: win(r, M_LULU), 2, out)
        t, tb = contrast("GUARD gate-b tap-out", G[a], G[F], SG, lambda r: r["topout"], 4, out, bad_up=True)
        c, cb = contrast("GUARD owner race M239.5", R[a], R[F], SG, lambda r: win(r, M_OWNER), 4, out)
        contrast("gate-b tap<=100", G[a], G[F], SG, lambda r: int(r["topout"] and r["pills"] <= 100), 1, out, bad_up=True)
        contrast("LULU-race tap-out (how==topout)", L[a], L[F], SL, lambda r: r["how"] == "topout", 1, out, bad_up=True)
        for k in ("slow", "kill"):
            a0 = [ltype(L[F][s], M_LULU) == k for s in SL]; a1 = [ltype(L[a][s], M_LULU) == k for s in SL]
            out(f"    loss type {k}: {sum(a0)} -> {sum(a1)} (fixed {sum(x and not y for x, y in zip(a0, a1))} / new "
                f"{sum(y and not x for x, y in zip(a0, a1))})")
        sa = [s for s in SS]
        contrast(f"SENSITIVITY q 2 % LULU (n={len(sa)})", L[a.replace("q04", "q02")], L["A_fair_q02"], sa, lambda r: win(r, M_LULU), 2, out)
        out(f"    VERDICT {a}: primary {cls(pb)}; {rule_A(pb, tb, cb)}")
    out("\n  STALLS (act-stall: no legal placement of the actual pill clears any virus, >= 10 decisions), LULU per game, "
        "truncated at her finish | untruncated:")
    for a in A_ARMS:
        tr, un = stall_rows(L[a], SL, M_LULU)
        f_ = lambda ms, k: np.mean([x[k] for x in ms])
        out(f"    {a:12s} pills<=16 {f_(tr, 'pills16'):.1f} | {f_(un, 'pills16'):.1f}; pills<=12 {f_(tr, 'pills12'):.1f}; "
            f"pills<=8 {f_(tr, 'pills8'):.1f}; longest<=16 {f_(tr, 'long16'):.1f} s | {f_(un, 'long16'):.1f} s; "
            f"stall>=30 s {100 * f_(tr, 'ge30'):.1f}% | {100 * f_(un, 'ge30'):.1f}%")
    for a in ("A_a16_q04", "A_r60_q04"):
        trF, _ = stall_rows(L[F], SL, M_LULU); trA, _ = stall_rows(L[a], SL, M_LULU)
        d = boot([(x["pills16"] - y["pills16"]) / 100 for x, y in zip(trA, trF)])
        d2 = boot([(x["ge30"] - y["ge30"]) for x, y in zip(trA, trF)])
        out(f"    {a} - FAIR: stall-pills<=16 (truncated) {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]; games with a stall >= 30 s "
            f"{fmt(d2)} pp")
    # ------------------------------------------------------------------------------------------- PART B
    out(f"\n=== PART B: anytime commit + DRLATEGUARD (residual misses q_B), MIN_THINK pricing ===")
    out("ABSOLUTE:")
    for a in B_ARMS:
        if a.startswith("B_orc"):
            w = boot([win(L[a][s], M_LULU) for s in SL])
            out(f"  {a:12s} LULU loss {100 - w[0]:5.2f}% [{100 - w[2]:.2f}, {100 - w[1]:.2f}] (oracle reference, LULU only)")
            continue
        levels(a, L[a], R[a], G[a], SL, SG, out)
    nm = {x.split("_")[1]: x for x in B_ARMS}
    for lab, x, y in (("v114 - v116 (DRMINTHINK=8 with V11)", "v114", "v116"), ("v112 - v116 (MIN_THINK 2 f with V11)", "v112", "v116"),
                      ("v116 - 14886 (V11 vs today, MIN_THINK 6 f)", "v116", "14886")):
        X, Y = nm[x], nm[y]
        out(f"\n  [{lab}]")
        p, pb = contrast("PRIMARY LULU race M167.5", L[X], L[Y], SL, lambda r: win(r, M_LULU), 3, out)
        t, tb = contrast("GUARD gate-b tap-out", G[X], G[Y], SG, lambda r: r["topout"], 6, out, bad_up=True)
        c, cb = contrast("GUARD owner race M239.5", R[X], R[Y], SG, lambda r: win(r, M_OWNER), 6, out)
        out(f"    primary {cls(pb)}" + (f"; VERDICT: {rule_B(pb, tb, cb)}" if x in ("v114", "v112") else ""))
    out("\n  REFERENCES (LULU race M167.5, 95%):")
    contrast("orc4 - orc6 (the -2 f lever with the final always at the gate)", L[nm["orc4"]], L[nm["orc6"]], SL, lambda r: win(r, M_LULU), 1, out)
    contrast("orc6 - 14886 (what today's non-final commits cost vs an instant final)", L[nm["orc6"]], L[nm["14886"]], SL, lambda r: win(r, M_LULU), 1, out)
    # survival of the -2 f gain
    W = {k: np.array([win(L[v][s], M_LULU) for s in SL], float) for k, v in nm.items()}
    num = W["v114"] - W["v116"]; den = W["orc4"] - W["orc6"]
    rng = np.random.default_rng(13); bs = []
    for _ in range(4000):
        i = rng.integers(0, len(SL), len(SL))
        dd = den[i].mean()
        bs.append(num[i].mean() / dd if dd != 0 else np.nan)
    bs = np.array(bs)
    out(f"  SURVIVAL of the -2 f gain under non-final commits = (v114 - v116) / (orc4 - orc6) = "
        f"{100 * num.mean():+.2f} / {100 * den.mean():+.2f} = {num.mean() / den.mean():.2f} "
        f"[{np.nanpercentile(bs, 2.5):.2f}, {np.nanpercentile(bs, 97.5):.2f}]")
    open("steer13/analysis.txt", "w").write("\n".join(lines) + "\n")


def selftest():
    ok = True
    cases = [((+2, +0.5, +3.5), (0, -1, +1), (0, -1, +1), "RECOMMEND"), ((+2, +0.5, +3.5), (+2, +0.5, +3), (0, -1, 1), "NOT RECOMMENDED"),
             ((+2, +0.5, +3.5), (0, -1, 1), (-2, -3, -0.5), "NOT RECOMMENDED"), ((+1, -0.5, +2.5), (0, -1, 1), (0, -1, 1), "NOT RECOMMENDED"),
             ((+2, +0.5, +3.5), (+0.5, -0.2, +1.5), (-0.5, -1.5, +0.3), "RECOMMEND")]
    for p, t, c, want in cases:
        got = rule_A(p, t, c); ok &= got == want
        gotb = rule_B(p, t, c); ok &= (gotb == "WORTH A COUCH TEST") == (want == "RECOMMEND")
        print(f"  {'ok ' if got == want else 'BAD'} prim {p} tap {t} race {c} -> {got} / {gotb}")
    muts = {"primary on the mean": lambda p, t, c: p[0] > 0 and not t[1] > 0 and not c[2] < 0,
            "tap guard dropped": lambda p, t, c: p[1] > 0 and not c[2] < 0,
            "race guard dropped": lambda p, t, c: p[1] > 0 and not t[1] > 0,
            "race guard sign flipped": lambda p, t, c: p[1] > 0 and not t[1] > 0 and not c[1] > 0}
    for name, f in muts.items():
        killed = any((("RECOMMEND" if f(p, t, c) else "NOT RECOMMENDED") != want) for p, t, c, want in cases)
        ok &= killed
        print(f"  mutant '{name}': {'KILLED' if killed else 'SURVIVED'}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    main()
