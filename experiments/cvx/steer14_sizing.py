"""STEER14 sizing (PREREG_STEER14.md sec. 4) from STEER13's OBSERVED per-seed variance (no STEER14 row is read).

Contrast (iii) = (A16, KOPEN cut) - (DIST4, KOPEN 32) = [A16 - DIST4 at the cut] + [the cut - KOPEN 32 with DIST4].
Neither piece has been measured under the slam-gate model. Proxies, both measured by STEER13 on the SAME 1,600 seeds
(41100-44298), so their covariance is observed too:
  piece 1 proxy  A16 - FAIR at q 4 % (part A: STEER13's only A16 measurement on these seeds)
  piece 2 proxy  V11 MT 2 - V11 MT 6 (part B, B_v112_qb - B_v116_qb): the nearest measured TEMPO lever on the anytime
                 model, standing in for the KOPEN cut
sigma(iii) = sd(piece 1 + piece 2) per seed. Rule 47: n = ((z_{1 - a/2K} + z_power) * sigma / effect)^2, K = 4.
Also printed: the alternative proxies (q 0 pilot A16 from STEER11; two-change v112 - 14886) and the MDEs of every other
pre-registered cell at the chosen n.  Writes steer14/sizing.txt.
"""
import os, sys, json, glob, math
import numpy as np
from scipy.stats import norm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs_race import evaluate
import steer14_jobs as J

M_LULU, M_OWNER, SIG, DL = 167.5, 239.5, 0.15, 2.65
EFFECT, POWER, K, JOB = 0.03, 0.80, 4, 50


def load(pat, lab, f):
    d = {}
    for p in glob.glob(pat):
        for l in open(p):
            r = json.loads(l)
            if r["arm"] == lab:
                d[r["seed"]] = f(r)
    return d


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    wl = lambda r: int(evaluate(r, M_LULU, SIG, DL)[0] == "win_race")
    wo = lambda r: int(evaluate(r, M_OWNER, SIG, DL)[0] == "win_race")
    L = {a: load(f"steer13/main/lulu13_{a}_*.jsonl", f"{a}~steer", wl)
         for a in ("A_fair_q04", "A_a16_q04", "B_v116_qb", "B_v112_qb", "B_14886_qb", "A_fair_q02", "A_a16_q02")}
    S = sorted(L["B_v116_qb"]); assert len(S) == 1600, len(S)
    v = lambda a, ss=S: np.array([L[a][s] for s in ss], float)
    p1 = v("A_a16_q04") - v("A_fair_q04"); p2 = v("B_v112_qb") - v("B_v116_qb")
    sd = lambda x: float(np.std(x, ddof=1))
    s3 = sd(p1 + p2)
    za, zb = norm.ppf(1 - 0.05 / (2 * K)), norm.ppf(POWER)
    n80 = ((za + zb) * s3 / EFFECT) ** 2
    n_pick = int(math.ceil(n80 / JOB) * JOB)
    out("STEER14 SIZING from STEER13's observed per-seed variance (LULU race win at M 167.5; seeds 41100-44298, n = 1,600)")
    out(f"  piece 1 (A16 - FAIR, part A q 4 %):  mean {100 * p1.mean():+.2f} pp, sd {sd(p1):.4f}, discordance {np.mean(p1 != 0):.3f}")
    out(f"  piece 2 proxy (V11 MT 2 - MT 6):     mean {100 * p2.mean():+.2f} pp, sd {sd(p2):.4f}, discordance {np.mean(p2 != 0):.3f}")
    out(f"  cov(piece 1, piece 2) {np.cov(p1, p2)[0, 1]:+.5f} (corr {np.corrcoef(p1, p2)[0, 1]:+.3f})")
    out(f"  => sigma(iii) = sd(piece 1 + piece 2) = {s3:.4f}")
    out(f"  Rule 47: z(1 - 0.05 / {2 * K}) = {za:.4f} (Bonferroni K = {K}, two-sided), z({POWER}) = {zb:.4f}")
    out(f"  n for power {POWER} at +{100 * EFFECT:.0f} pp = (({za:.3f} + {zb:.3f}) x {s3:.4f} / {EFFECT})^2 = {n80:.0f}"
        f"  -> rounded UP to the {JOB}-game job: N_LULU = {n_pick}")
    assert n_pick == J.N_LULU, f"steer14_jobs.N_LULU {J.N_LULU} != sized {n_pick}"
    # alternative proxies, for the record
    pil = {}
    for arm in ("s10_base", "s10_A16"):
        pil[arm] = load(f"steer11/pilot/lulu10b_c11_{arm}_*.jsonl", f"{arm}~steer", wl)
    sp = sorted(set(pil["s10_base"]) & set(pil["s10_A16"]))
    q0 = np.array([pil["s10_A16"][s] - pil["s10_base"][s] for s in sp], float)
    two = v("B_v112_qb") - v("B_14886_qb")
    out("  alternative proxies (NOT used for N):")
    out(f"    A16 - base at q 0 (STEER11 pilot, n {len(sp)}): sd {sd(q0):.4f} -> with piece 2 independent: "
        f"sigma(iii) ~ {math.sqrt(sd(q0) ** 2 + sd(p2) ** 2):.4f}")
    out(f"    two-change v112 - 14886 (STEER13): sd {sd(two):.4f}")
    # power / MDE of every pre-registered cell at the chosen n
    mde = lambda sig, n, z: 100 * (z + zb) * sig / math.sqrt(n)
    pw = lambda sig, n, z, eff: float(norm.cdf(eff * math.sqrt(n) / sig - z))
    out(f"\n  AT N_LULU = {J.N_LULU} (Bonferroni K = {K}):")
    out(f"    (iii) combined: power at +3 pp {pw(s3, J.N_LULU, za, EFFECT):.3f}; 80 % MDE {mde(s3, J.N_LULU, za):.2f} pp")
    for lab, sig in (("(i)/(ii) A16 alone, q 4 % proxy", sd(p1)), ("(i)/(ii) A16 alone, q 0 proxy", sd(q0))):
        out(f"    {lab} (sd {sig:.3f}): power at +3 pp {pw(sig, J.N_LULU, za, EFFECT):.3f}; 80 % MDE {mde(sig, J.N_LULU, za):.2f} pp")
    for lab, sig in (("(iv) interaction, 2 x var(A16) q 4 % proxy", math.sqrt(2) * sd(p1)),
                     ("(iv) interaction, 2 x var(A16) q 0 proxy", math.sqrt(2) * sd(q0))):
        out(f"    {lab} (sd {sig:.3f}): 80 % MDE {mde(sig, J.N_LULU, za):.2f} pp")
    # guards (n = N_GUARD) from STEER13's v112 - v116 guard rows; Bonferroni over 2 guards x 3 contrasts = 6
    zg = norm.ppf(1 - 0.05 / (2 * 6))
    SG = sorted(load("steer13/main/gb13_B_v116_qb_*.jsonl", "B_v116_qb@owner202610", lambda r: 0))
    for cell, pat, lab, f in (("gate-b tap-out", "gb13", "@owner202610", lambda r: r["topout"]),
                              ("owner race loss", "rc13", "~steer", lambda r: 1 - wo(r))):
        a = load(f"steer13/main/{pat}_B_v112_qb_*.jsonl", "B_v112_qb" + lab, f)
        b = load(f"steer13/main/{pat}_B_v116_qb_*.jsonl", "B_v116_qb" + lab, f)
        d = np.array([a[s] - b[s] for s in SG], float)
        out(f"    guard {cell} (STEER13 n {len(SG)}, v116 level {100 * np.mean([b[s] for s in SG]):.2f} %, paired sd "
            f"{sd(d):.4f}): at N_GUARD = {J.N_GUARD}, Bonferroni-6 80 % MDE {mde(sd(d), J.N_GUARD, zg):.2f} pp")
    # sensitivity q 2 % (contrast (iii) only, 95 % unadjusted): sigma proxy = sigma(iii) inflated by the part-A q 2 / q 4
    # discordance ratio of A16 - FAIR (n 800)
    S8 = sorted(L["A_fair_q02"])
    c2 = v("A_a16_q02", S8) - v("A_fair_q02", S8)
    out(f"    sensitivity q 2 % (iii) at N_SENS = {J.N_SENS}: sigma proxy {s3:.3f} -> 95 % (unadjusted) 80 % MDE "
        f"{mde(s3, J.N_SENS, norm.ppf(0.975)):.2f} pp  (part-A A16 - FAIR at q 2 %: sd {sd(c2):.3f}, n {len(S8)})")
    g_r = 2 * (J.N13_LULU + 2 * J.N13_GUARD)
    g_m = 4 * J.N_LULU + 2 * J.N_SENS + 4 * 2 * J.N_GUARD
    g_d = (len(J.GATE_NAMES) - 2) * J.N_DOSE
    out(f"\n  GAMES: part R 2 x ({J.N13_LULU} + 2 x {J.N13_GUARD}) = {g_r:,}; part M 4 x {J.N_LULU} LULU + 2 x {J.N_SENS} "
        f"sensitivity + 4 x 2 x {J.N_GUARD} guards = {g_m:,}; part D {len(J.GATE_NAMES) - 2} x {J.N_DOSE} = {g_d:,}; total {g_r + g_m + g_d:,} "
        f"({(g_r + g_m + g_d) // JOB} jobs of {JOB})")
    os.makedirs("steer14", exist_ok=True)
    open("steer14/sizing.txt", "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
