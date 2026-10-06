"""STEER10 analysis (PREREG_STEER10.md): endgame-stall / edge-column rules vs FAIR (= STEER8b fD_bdepD).

  python analyze_steer10.py              # needs steer10/ rows (+ the banked steer8/ and steer9/ FAIR rows)
  python analyze_steer10.py --selftest   # killed-mutant check of the verdict rule (no data read)

Cells (declared reuse; FAIR rows: gb10 = banked steer8 fD_bdepD 39134-40332 + steer9 s9_base on the other 600 (both
identity-gated byte-identical to fD_bdepD); rc10 = banked steer8 fD_bdepD; lulu10b = NEW s10_base rows):
  lulu10b  LULU race, lam 2.84 + sizes 83/7/10 (lulu_fit_202610b), n = 1,200 per arm
  gb10     gate (b) vs owner202610 (owner_fit_202610), n = 1,200 per arm
  rc10     owner race, lam 2.36 (owner_fit_202610 rate, Hartford sizes), M 177, delta 2.65, n = 600 per arm
PRIMARY (per arm, paired, seed bootstrap, Bonferroni over the K arms):
  LULU race WIN averaged over her pace prior M in {80, 100, 120, 140} s (delta 2.65): per seed, the mean of the four
  win indicators (vs_race.evaluate; each M uses the same per-seed pace quantile). Loss rate = 100 - win.
  PASS iff  LULU primary delta lower CI > 0
       AND  NOT gb10 tap-out harm   (tap-out delta lower CI > 0)
       AND  NOT rc10 owner-race harm (race delta upper CI < 0)
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer6r import RC_SEEDS, boot, fmt, win, churn

GB_BANK = list(range(39134, 40333, 2))
GB_NEW = list(range(40334, 40933, 2)) + list(range(33000, 33599, 2))
GB10 = GB_BANK + GB_NEW                                  # 1,200 paired gb10 seeds (= STEER9's block)
LULU10B = GB10                                           # 1,200 (declared reuse)
MS = (80.0, 100.0, 120.0, 140.0)                         # PRIMARY pace prior (s), delta 2.65
DELTA = 2.65
PREREG_ARMS = ("s10_A16", "s10_R60", "s10_R120", "s10_A16R120")   # PRE-REGISTERED (PREREG_STEER10.md sec. 4)
ARMS = ()
K = 1
N_REQ = (1200, 1200, 600)                                # lulu10b, gb10, rc10


def set_arms(arms):
    global ARMS, K, BONF
    ARMS = tuple(arms); K = len(ARMS)
    BONF = (100 * 0.05 / K / 2, 100 - 100 * 0.05 / K / 2)


BONF = (2.5, 97.5)


def load(pattern, label, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def wprior(r, Ms=MS, dl=DELTA):
    return float(np.mean([win(r, M, dl) for M in Ms]))


GARB_S, REL_SIZE = 3.2, 2.27                             # declared secondary: couch garbage-drop time per release


def wprior_g(r, Ms=MS, dl=DELTA):
    """pace-prior win with the AI's finish shifted by +3.2 s per received release (~ tiles_recv / 2.27); approximate"""
    rr = dict(r); rr["t_end"] = r["t_end"] + GARB_S * r.get("tiles_recv", 0) / REL_SIZE
    return float(np.mean([win(rr, M, dl) for M in Ms]))


def stall_bep(r, kind=1):
    return [b for b in r["stuck"]["bep"] if b[0] == kind and b[2] >= 10]


def stall_end16(r):
    """couch-range ENDGAME stall-pills: board-level act-stalls >= 10 that START at <= 16 viruses"""
    return sum(b[2] for b in stall_bep(r) if 0 <= b[3] <= 16)


def stall_end4(r):
    """STEER6e endgame stall-pills: act-stalls >= 10 that start at <= 4 viruses"""
    return sum(b[2] for b in stall_bep(r) if 0 <= b[3] <= 4)


def longest_pills(r):
    return max([b[2] for b in r["stuck"]["bep"] if b[0] == 1] or [0])


def longest_s(r):
    return max([b[7] for b in r["stuck"]["bep"] if b[0] == 1] or [0.0])


def edge_stuck(r):
    """decisions spent by EDGE-column (cols 0/7) viruses inside STRUCTURAL stuck episodes >= 10 (virus episodes)"""
    return sum(e[5] for e in r["stuck"]["vep"] if e[0] == 0 and e[2] in (0, 7))


def paired(D1, D0, seeds, f, lo=2.5, hi=97.5):
    S = [s for s in seeds if s in D1 and s in D0]
    if not S:
        return (np.nan,) * 3, S
    return boot([f(D1[s]) - f(D0[s]) for s in S], lo, hi), S


def verdict(prim, tap, rc, ns, n_req=N_REQ):
    """PRIMARY (PREREG_STEER10): CIs at the Bonferroni level. prim / tap / rc = (mean, lo, hi) in pp.
    PASS iff prim lower > 0 AND tap-out lower <= 0 (no demonstrated harm) AND owner race upper >= 0."""
    if any(n < r for n, r in zip(ns, n_req)):
        return "incomplete"
    return "PASS" if (prim[1] > 0 and not tap[1] > 0 and not rc[2] < 0) else "FAIL"


def report(name, X, Y, out):
    (Lx, Gx, Rx), (Ly, Gy, Ry) = X, Y
    prim, Sl = paired(Lx, Ly, LULU10B, wprior); primB, _ = paired(Lx, Ly, LULU10B, wprior, *BONF)
    tap, Sg = paired(Gx, Gy, GB10, lambda r: r["topout"]); tapB, _ = paired(Gx, Gy, GB10, lambda r: r["topout"], *BONF)
    rc, Sr = paired(Rx, Ry, RC_SEEDS, lambda r: win(r, 177.)); rcB, _ = paired(Rx, Ry, RC_SEEDS, lambda r: win(r, 177.), *BONF)
    ns = (len(Sl), len(Sg), len(Sr))
    m = lambda D, S, f: 100 * np.mean([f(D[s]) for s in S]) if S else np.nan
    out(f"\n=== {name} vs FAIR (fD_bdepD) ===")
    out(f"  PRIMARY lulu10b LULU race win, pace prior M{'/'.join(str(int(x)) for x in MS)} d{DELTA} (n={ns[0]}): "
        f"{m(Ly, Sl, wprior):.2f}% -> {m(Lx, Sl, wprior):.2f}% (loss {100 - m(Ly, Sl, wprior):.2f}% -> {100 - m(Lx, Sl, wprior):.2f}%)"
        f"  d {fmt(prim)}  Bonf {fmt(primB)}")
    for M in MS:
        c = churn([Ly[s] for s in Sl], [Lx[s] for s in Sl], lambda r: not win(r, M, DELTA))
        d, _ = paired(Lx, Ly, LULU10B, lambda r: win(r, M, DELTA))
        out(f"    M{int(M)}: {m(Ly, Sl, lambda r: win(r, M, DELTA)):.2f}% -> {m(Lx, Sl, lambda r: win(r, M, DELTA)):.2f}%  "
            f"d {fmt(d)}  churn fixed {c[0]} / new {c[1]}")
    dg, _ = paired(Lx, Ly, LULU10B, wprior_g)
    out(f"    (secondary) garbage-time-charged pace-prior win (+{GARB_S} s per received release): "
        f"{m(Ly, Sl, wprior_g):.2f}% -> {m(Lx, Sl, wprior_g):.2f}%  d {fmt(dg)}")
    for M, dl in ((100., 2.0), (140., 2.0)):
        d, _ = paired(Lx, Ly, LULU10B, lambda r: win(r, M, dl))
        out(f"    (secondary) M{int(M)} d{dl}: d {fmt(d)}")
    ct = churn([Ly[s] for s in Sl], [Lx[s] for s in Sl], lambda r: r["how"] == "topout")
    out(f"    lulu10b tap-out (how == topout): {m(Ly, Sl, lambda r: r['how'] == 'topout'):.2f}% -> "
        f"{m(Lx, Sl, lambda r: r['how'] == 'topout'):.2f}%  d {fmt(paired(Lx, Ly, LULU10B, lambda r: r['how'] == 'topout')[0])}"
        f"  churn fixed {ct[0]} / new {ct[1]}")
    cg = churn([Gy[s] for s in Sg], [Gx[s] for s in Sg], lambda r: r["topout"])
    out(f"  GUARD gb10 tap-out (n={ns[1]}) {m(Gy, Sg, lambda r: r['topout']):.2f}% -> {m(Gx, Sg, lambda r: r['topout']):.2f}%  "
        f"d {fmt(tap)}  Bonf {fmt(tapB)}  churn fixed {cg[0]} / new {cg[1]}")
    t100, _ = paired(Gx, Gy, GB10, lambda r: int(r["topout"] and r["pills"] <= 100))
    out(f"    gb10 tap<=100: d {fmt(t100)}")
    cr = churn([Ry[s] for s in Sr], [Rx[s] for s in Sr], lambda r: not win(r, 177.))
    out(f"  GUARD rc10 owner race win M177 d2.65 (n={ns[2]}) {m(Ry, Sr, lambda r: win(r, 177.)):.2f}% -> "
        f"{m(Rx, Sr, lambda r: win(r, 177.)):.2f}%  d {fmt(rc)}  Bonf {fmt(rcB)}  churn fixed {cr[0]} / new {cr[1]}")
    for cell, D0, D1, S in (("lulu10b", Ly, Lx, Sl), ("gb10", Gy, Gx, Sg), ("rc10", Ry, Rx, Sr)):
        if not S:
            continue
        parts = []
        for lab, f in (("stall-pills act>=10 from <=16 v", stall_end16), ("from <=4 v", stall_end4),
                       ("longest stall (pills)", longest_pills), ("longest stall (s)", longest_s),
                       ("edge-virus str-stuck decisions", edge_stuck)):
            d = boot([(f(D1[s]) - f(D0[s])) / 100.0 for s in S])
            parts.append(f"{lab} {np.mean([f(D0[s]) for s in S]):.1f} -> {np.mean([f(D1[s]) for s in S]):.1f} "
                         f"d {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]")
        g36 = (100 * np.mean([longest_s(D0[s]) >= 36 for s in S]), 100 * np.mean([longest_s(D1[s]) >= 36 for s in S]))
        out(f"  {cell} per game: " + "; ".join(parts) + f"; games with a stall >= 36 s {g36[0]:.1f}% -> {g36[1]:.1f}%")
    for cell, D1, S in (("lulu10b", Lx, Sl), ("gb10", Gx, Sg), ("rc10", Rx, Sr)):
        if S and "rule" in D1[S[0]]:
            tot = {k: sum(D1[s]["rule"][k] for s in S) for k in D1[S[0]]["rule"]}
            dec = max(tot.get("dec", 0), 1)
            out(f"  ACTIVITY {cell}: " + ", ".join(f"{k} {v} ({100 * v / dec:.1f}%)" for k, v in tot.items() if k != "dec")
                + f" of {tot.get('dec', 0)} decisions")
    v = verdict(primB, tapB, rcB, ns)
    out(f"  VERDICT (Bonferroni {BONF[1]:.3f}%): {v}")
    return v


def fair_rows():
    gb = load("steer8/gb10_fD_bdepD_*.jsonl", "fD_bdepD@owner202610", GB_BANK)
    gb.update(load("steer9/gb10_s9_base_*.jsonl", "s9_base@owner202610", GB_NEW))
    rc = load("steer8/rc10_fD_bdepD_*.jsonl", "fD_bdepD~steer", RC_SEEDS)
    lu = load("steer10/lulu10b_s10_base_*.jsonl", "s10_base~steer", LULU10B)
    return lu, gb, rc


def arm_rows(a):
    return (load(f"steer10/lulu10b_{a}_*.jsonl", f"{a}~steer", LULU10B),
            load(f"steer10/gb10_{a}_*.jsonl", f"{a}@owner202610", GB10),
            load(f"steer10/rc10_{a}_*.jsonl", f"{a}~steer", RC_SEEDS))


def identity(out):
    """s10_base gate rows (steer10/gate/) vs the banked FAIR rows, every non-stamp key."""
    bank = {"gb10": load("steer8/gb10_fD_bdepD_*.jsonl", "fD_bdepD@owner202610", GB_BANK),
            "rc10": load("steer8/rc10_fD_bdepD_*.jsonl", "fD_bdepD~steer", RC_SEEDS),
            "lulu10": load("steer8/lulu10_fD_bdepD_*.jsonl", "fD_bdepD~steer", RC_SEEDS)}
    for cell, lab in (("gb10", "s10_base@owner202610"), ("rc10", "s10_base~steer"), ("lulu10", "s10_base~steer")):
        I = load(f"steer10/gate/{cell}_s10_base*.jsonl", lab, GB10)
        B = bank[cell]
        both = [s for s in I if s in B]
        same = sum(1 for s in both if all(I[s].get(k) == B[s].get(k) for k in B[s] if k not in ("arm", "rig")))
        out(f"IDENTITY s10_base vs banked fD_bdepD {cell}: {same}/{len(both)} rows identical on every non-stamp key")


def main(arms):
    set_arms(arms)
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    identity(out)
    base = fair_rows()
    out(f"rows FAIR: lulu10b {len(base[0])} gb10 {len(base[1])} rc10 {len(base[2])}")
    res = {}
    for a in ARMS:
        X = arm_rows(a)
        out(f"\nrows {a}: lulu10b {len(X[0])} gb10 {len(X[1])} rc10 {len(X[2])}")
        res[a] = report(a, X, base, out)
    out("\nSUMMARY: " + "  ".join(f"{a}={v}" for a, v in res.items()))
    return lines


def selftest():
    rng = np.random.default_rng(5)
    set_arms(("a", "b", "c", "d"))

    def vec(n, p_fix, p_new):                 # -1 = fixed (good), +1 = new (bad) for a FAILURE indicator
        v = np.zeros(n, float); a, b = round(p_fix * n), round(p_new * n); v[:a] = -1; v[a:a + b] = 1
        return rng.permutation(v)
    B = lambda d: boot(d, *BONF)
    cases = [
        ("LULU +5 (win: 70 fixed/10 new), tap null, race null", -vec(1200, .07, .01), np.zeros(1200), np.zeros(600), "PASS"),
        ("LULU +5, tap -1, race +1", -vec(1200, .07, .01), vec(1200, .03, .02), -vec(600, .03, .02), "PASS"),
        ("LULU +5, tap +3 (demonstrated harm)", -vec(1200, .07, .01), vec(1200, .01, .04), np.zeros(600), "FAIL"),
        ("LULU +5, tap +1 at high churn (CI spans 0: no demonstrated harm)", -vec(1200, .07, .01), vec(1200, .05, .06), np.zeros(600), "PASS"),
        ("LULU +5, owner race -4 (demonstrated harm)", -vec(1200, .07, .01), np.zeros(1200), -vec(600, .0, .04), "FAIL"),
        ("LULU +1 (CI spans 0)", -vec(1200, .04, .03), np.zeros(1200), np.zeros(600), "FAIL"),
        ("LULU -3", -vec(1200, .01, .04), np.zeros(1200), np.zeros(600), "FAIL"),
    ]
    ok = True
    for name, dl, dt, dr, want in cases:
        got = verdict(B(dl), B(dt), B(dr), N_REQ)
        ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} {name}: lulu {fmt(B(dl))} tap {fmt(B(dt))} race {fmt(B(dr))} -> {got}")
    got = verdict(B(cases[0][1]), B(cases[0][2]), B(cases[0][3]), (1200, 1200, 599))
    ok &= got == "incomplete"; print(f"  {'ok ' if got == 'incomplete' else 'BAD'} short rc n -> {got}")
    mut = {
        "LULU on the mean": lambda p, t, r: p[0] > 0 and not t[1] > 0 and not r[2] < 0,
        "LULU on the upper CI": lambda p, t, r: p[2] > 0 and not t[1] > 0 and not r[2] < 0,
        "tap guard dropped": lambda p, t, r: p[1] > 0 and not r[2] < 0,
        "tap guard on the upper CI (non-inferiority at 0)": lambda p, t, r: p[1] > 0 and t[2] < 0 and not r[2] < 0,
        "race guard dropped": lambda p, t, r: p[1] > 0 and not t[1] > 0,
    }
    for mname, f in mut.items():
        killed = any(("PASS" if f(B(dl), B(dt), B(dr)) else "FAIL") != want for _, dl, dt, dr, want in cases)
        ok &= killed
        print(f"  mutant '{mname}': {'KILLED' if killed else 'SURVIVED'}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    lines = main(PREREG_ARMS)
    open("steer10/analysis.txt", "w").write("\n".join(lines) + "\n")
