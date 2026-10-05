"""STEER9 analysis (PREREG_STEER9.md): "don't seal a live column" rules vs FAIR (= STEER8b fD_bdepD, banked rows).

  python analyze_steer9.py              # needs steer9/ rows + the banked steer8/ fD_bdepD rows
  python analyze_steer9.py --selftest   # killed-mutant check of the verdict rule (no data read)
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer6r import RC_SEEDS, boot, fmt, win, churn

GB_BANK = list(range(39134, 40333, 2))                  # 600 = STEER8b's gb10 block: FAIR rows banked (fD_bdepD)
GB_NEW = list(range(40334, 40933, 2)) + list(range(33000, 33599, 2))   # 600 more (declared reuse): FAIR = s9_base rows
GB9 = GB_BANK + GB_NEW                                  # 1,200 paired gb10 seeds
ARMS = ("s9_V150", "s9_VVETO", "s9_CVETO")              # PRE-REGISTERED (PREREG_STEER9.md); order = report order
K = len(ARMS)
BONF = (100 * 0.05 / K / 2, 100 - 100 * 0.05 / K / 2)
N_REQ = (1200, 600, 600)


def load(pattern, label, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def cells(pattern, label):
    return (load(pattern.format(c="gb10"), f"{label}@owner202610", GB9),
            load(pattern.format(c="rc10"), f"{label}~steer", RC_SEEDS),
            load(pattern.format(c="lulu10"), f"{label}~steer", RC_SEEDS))


def stall_all(r):
    """pills in board-level act-stalls >= 10 (STEER6 stall_pills)"""
    return sum(b[2] for b in r["stuck"]["bep"] if b[0] == 1 and b[2] >= 10)


def stall_end(r):
    """ENDGAME stall-pills: board-level act-stalls >= 10 that START at <= 4 viruses (STEER6e)"""
    return sum(b[2] for b in r["stuck"]["bep"] if b[0] == 1 and b[2] >= 10 and 0 <= b[3] <= 4)


def stall_str(r):
    """SEALED stall-pills: board-level STRUCTURAL stalls >= 10 (no pill colour pair clears any virus)"""
    return sum(b[2] for b in r["stuck"]["bep"] if b[0] == 0 and b[2] >= 10)


def verdict(tap, rc, lulu, ns, n_req=N_REQ):
    """PRIMARY (PREREG_STEER9 sec. 6), all three CIs at the Bonferroni level:
    PASS iff gb10 tap-out delta upper CI < 0 AND rc10 race delta lower CI > -1 AND lulu10 race delta lower CI > -1."""
    if any(n < r for n, r in zip(ns, n_req)):
        return "incomplete"
    return "PASS" if (tap[2] < 0 and rc[1] > -1 and lulu[1] > -1) else "FAIL"


def secondary(tap, rc, lulu):
    """DECLARED SECONDARY (not the bar): STEER6r's no-demonstrated-loss form, race upper CI >= 0."""
    return "would pass" if (tap[2] < 0 and rc[2] >= 0 and lulu[2] >= 0) else "would fail"


def diff(X, Y, lo=2.5, hi=97.5):
    (Gx, Rx, Lx), (Gy, Ry, Ly) = X, Y
    Sg = [s for s in GB9 if s in Gx and s in Gy]; Sr = [s for s in RC_SEEDS if s in Rx and s in Ry]
    Sl = [s for s in RC_SEEDS if s in Lx and s in Ly]
    nan = (np.nan,) * 3
    tt = boot([Gx[s]["topout"] - Gy[s]["topout"] for s in Sg], lo, hi) if Sg else nan
    tr = boot([win(Rx[s], 177.) - win(Ry[s], 177.) for s in Sr], lo, hi) if Sr else nan
    tl = boot([win(Lx[s], 140.) - win(Ly[s], 140.) for s in Sl], lo, hi) if Sl else nan
    return tt, tr, tl, (len(Sg), len(Sr), len(Sl)), (Sg, Sr, Sl)


def report(name, X, Y):
    (Gx, Rx, Lx), (Gy, Ry, Ly) = X, Y
    tt, tr, tl, ns, (Sg, Sr, Sl) = diff(X, Y)
    bt, br, bl, _, _ = diff(X, Y, *BONF)
    m = lambda D, S, f: 100 * np.mean([f(D[s]) for s in S]) if S else np.nan
    cg = churn([Gy[s] for s in Sg], [Gx[s] for s in Sg], lambda r: r["topout"])
    cr = churn([Ry[s] for s in Sr], [Rx[s] for s in Sr], lambda r: not win(r, 177.))
    cl = churn([Ly[s] for s in Sl], [Lx[s] for s in Sl], lambda r: not win(r, 140.))
    print(f"\n=== {name} vs FAIR (fD_bdepD) ===")
    print(f"  gb10 tap-out (n={ns[0]}) {m(Gy, Sg, lambda r: r['topout']):.2f}% -> {m(Gx, Sg, lambda r: r['topout']):.2f}%  "
          f"d {fmt(tt)}  Bonf {fmt(bt)}  churn fixed {cg[0]} / new {cg[1]}")
    print(f"  rc10 race win M177 (n={ns[1]}) {m(Ry, Sr, lambda r: win(r, 177.)):.2f}% -> {m(Rx, Sr, lambda r: win(r, 177.)):.2f}%  "
          f"d {fmt(tr)}  Bonf {fmt(br)}  churn fixed {cr[0]} / new {cr[1]}")
    print(f"  lulu10 race win M140 (n={ns[2]}) {m(Ly, Sl, lambda r: win(r, 140.)):.2f}% -> {m(Lx, Sl, lambda r: win(r, 140.)):.2f}%  "
          f"d {fmt(tl)}  Bonf {fmt(bl)}  churn fixed {cl[0]} / new {cl[1]}")
    for cell, D0, D1, S in (("gb10", Gy, Gx, Sg), ("rc10", Ry, Rx, Sr), ("lulu10", Ly, Lx, Sl)):
        if not S:
            continue
        parts = []
        for lab, f in (("endgame stall-pills (act>=10 from <=4 v)", stall_end), ("all act-stall pills", stall_all),
                       ("SEALED (str) stall pills", stall_str)):
            d = boot([(f(D1[s]) - f(D0[s])) / 100.0 for s in S])
            parts.append(f"{lab} {np.mean([f(D0[s]) for s in S]):.1f} -> {np.mean([f(D1[s]) for s in S]):.1f} d {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]")
        print(f"  {cell} per game: " + "; ".join(parts))
    for cell, D1, S in (("gb10", Gx, Sg), ("rc10", Rx, Sr), ("lulu10", Lx, Sl)):
        if S and "seal" in D1[S[0]]:
            dec = sum(D1[s]["seal"]["dec"] for s in S); fi = sum(D1[s]["seal"]["fired"] for s in S)
            ch = sum(D1[s]["seal"]["changed"] for s in S)
            print(f"  ACTIVITY {cell}: decisions {dec}, rule fired {fi} ({100 * fi / max(dec, 1):.1f}%), "
                  f"changed the root {ch} ({100 * ch / max(dec, 1):.2f}% of decisions, {ch / len(S):.1f}/game)")
    v = verdict(bt, br, bl, ns)
    print(f"  VERDICT (primary, Bonferroni {BONF[1]:.2f}%): {v}   [declared secondary, STEER6r form: {secondary(bt, br, bl)}]")
    return v


def main():
    base = cells("steer8/{c}_fD_bdepD_*.jsonl", "fD_bdepD")
    print(f"rows FAIR fD_bdepD (banked STEER8b): gb10 {len(base[0])} rc10 {len(base[1])} lulu10 {len(base[2])}")
    ident = cells("steer9/{c}_s9_base_*.jsonl", "s9_base")
    for cell, I, B in zip(("gb10", "rc10", "lulu10"), ident, base):
        both = [s for s in I if s in B]
        same = sum(1 for s in both if all(I[s].get(k) == B[s].get(k) for k in B[s] if k not in ("arm", "rig")))
        print(f"IDENTITY s9_base vs banked fD_bdepD {cell}: {same}/{len(both)} overlapping rows identical on every non-stamp key")
    newb = {s: r for s, r in ident[0].items() if s in GB_NEW}
    print(f"FAIR gb10 on the 600 new seeds = s9_base rows: {len(newb)}")
    base = ({**base[0], **newb}, base[1], base[2])
    out = {}
    for a in ARMS:
        X = cells(f"steer9/{{c}}_{a}_*.jsonl", a)
        print(f"\nrows {a}: gb10 {len(X[0])} rc10 {len(X[1])} lulu10 {len(X[2])}")
        out[a] = report(a, X, base)
    print("\nSUMMARY: " + "  ".join(f"{a}={v}" for a, v in out.items()))


def selftest():
    rng = np.random.default_rng(3)

    def vec(n, p_fix, p_new):
        v = np.zeros(n, int); a, b = round(p_fix * n), round(p_new * n); v[:a] = -1; v[a:a + b] = 1
        return rng.permutation(v)
    B = lambda d: boot(d, *BONF)
    cases = [
        ("tap -3 (30/12), races +3/+3 low churn", vec(600, .05, .02), -vec(600, .04, .01), -vec(600, .04, .01), "PASS"),
        ("tap -3, races exactly null (null race must pass)", vec(600, .05, .02), np.zeros(600), np.zeros(600), "PASS"),
        ("tap -3, race null at high churn (lower CI < -1: the bar fails it)", vec(600, .05, .02), vec(600, .06, .06), np.zeros(600), "FAIL"),
        ("tap -3, LULU -2 low churn", vec(600, .05, .02), np.zeros(600), vec(600, .03, .01), "FAIL"),
        ("tap -0.5 (CI spans 0)", vec(600, .02, .015), -vec(600, .04, .01), -vec(600, .04, .01), "FAIL"),
        ("tap +2 (worse)", vec(600, .01, .03), -vec(600, .04, .01), -vec(600, .04, .01), "FAIL"),
    ]
    ok = True
    for name, dt, dr, dl, want in cases:
        got = verdict(B(dt), B(dr), B(dl), N_REQ)
        ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} {name}: tap {fmt(B(dt))} race {fmt(B(dr))} lulu {fmt(B(dl))} -> {got}")
    got = verdict(B(cases[0][1]), B(cases[0][2]), B(cases[0][3]), (600, 599, 600))
    ok &= got == "incomplete"; print(f"  {'ok ' if got == 'incomplete' else 'BAD'} short race n -> {got}")
    mut = {
        "tap lower CI": lambda t, r, l: t[1] < 0 and r[1] > -1 and l[1] > -1,
        "tap mean": lambda t, r, l: t[0] < 0 and r[1] > -1 and l[1] > -1,
        "race guard dropped": lambda t, r, l: t[2] < 0 and l[1] > -1,
        "lulu guard dropped": lambda t, r, l: t[2] < 0 and r[1] > -1,
        "race guard on upper CI (STEER6r form)": lambda t, r, l: t[2] < 0 and r[2] >= 0 and l[2] >= 0,
        "race margin 0 instead of -1": lambda t, r, l: t[2] < 0 and r[1] > 0 and l[1] > 0,
    }
    for mname, f in mut.items():
        killed = any(("PASS" if f(B(dt), B(dr), B(dl)) else "FAIL") != want for _, dt, dr, dl, want in cases)
        ok &= killed
        print(f"  mutant '{mname}': {'KILLED' if killed else 'SURVIVED'}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    main()
