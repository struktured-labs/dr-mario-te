"""STEER11 confirmation sizing rule (PREREG_STEER11.md sec. 5). COMMITTED BEFORE the pilot was analysed (stage A).

Inputs (pilot = steer11/pilot rows: s10_base + s10_A16 on the couch11 clock, STEER10 LULU block, 1,200 seeds):
  d_new   A16 - FAIR LULU pace-prior win delta (pp) on couch11
  d_old   the same seeds on the legacy clock (the banked STEER10 rows) = +1.35 pp by construction
  sd_new  per-seed SD (pp) of the pace-prior win difference on couch11
RULE:
  r       = clamp(d_new / d_old, 0.5, 1.0)       the clock correction may only SHRINK the design effect; the floor
                                                 keeps a pilot dip on 1,200 seeds (SE ~0.7 pp) from sizing to infinity
  delta   = 1.35 x r                             "the STEER10 effect shrunk for the clock correction"
  n85     = ((z_.975 + z_.85) x sd_new / delta)^2      85% power (the middle of 80-90%), two-sided 5%
  n       = clamp(ceil50(n85), 2400, N_MAX)       2,400 = STEER10's own 80% figure; N_MAX = 4,000 (the declared reuse
                                                 block 41100-49098 and ~25k games of compute)
  If n85 > N_MAX the run is n = N_MAX and its power at delta is printed and declared UNDERPOWERED BY DESIGN up front.
Also printed (not used by the rule): power at 0.7 x delta (a winner's-curse shrink; A16 was the best of 4 STEER10 arms).
"""
import json, math, os, sys, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
D_OLD_STEER10 = 1.35
N_MIN, N_MAX = 2400, 4000
Z975, Z85 = 1.959964, 1.036433


def power(delta, sd, n):
    se = sd / math.sqrt(n)
    z = delta / se - Z975
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def rule(d_new, d_old, sd_new):
    r = min(1.0, max(0.5, d_new / d_old))
    delta = D_OLD_STEER10 * r
    n85 = ((Z975 + Z85) * sd_new / delta) ** 2
    n = int(min(N_MAX, max(N_MIN, 50 * math.ceil(n85 / 50))))
    return dict(r=r, delta=delta, n85=n85, n=n, power=power(delta, sd_new, n), power_curse=power(0.7 * delta, sd_new, n),
                underpowered=bool(n85 > N_MAX))


def selftest():
    ok = True
    for d_new, sd, want in ((1.35, 23.9, 2850), (2.0, 23.9, 2850), (0.9, 23.9, 4000), (0.1, 23.9, 4000), (1.35, 15.0, 2400)):
        got = rule(d_new, 1.35, sd)
        ok &= got["n"] == want
        print(f"  {'ok ' if got['n'] == want else 'BAD'} d_new {d_new} sd {sd}: r {got['r']:.2f} delta {got['delta']:.2f} "
              f"n85 {got['n85']:.0f} -> n {got['n']} (power {got['power']:.2f}, underpowered {got['underpowered']})")
    print("SIZING SELFTEST", "PASS" if ok else "FAIL")
    return ok


def main():
    import analyze_steer11 as A
    import analyze_steer10 as A10
    LU = A10.LULU10B
    L = {a: A.load(f"steer11/pilot/lulu10b_c11_{a}_*.jsonl", f"{a}~steer", LU) for a in ("s10_base", "s10_A16")}
    Lo = {a: A.load(f"steer10/lulu10b_{a}_*.jsonl", f"{a}~steer", LU) for a in ("s10_base", "s10_A16")}
    S = [s for s in LU if all(s in D for D in (L["s10_base"], L["s10_A16"], Lo["s10_base"], Lo["s10_A16"]))]
    assert len(S) == 1200, f"pilot incomplete: {len(S)} paired seeds"
    dn = np.array([A.wprior(L["s10_A16"][s]) - A.wprior(L["s10_base"][s]) for s in S]) * 100
    do = np.array([A.wprior(Lo["s10_A16"][s]) - A.wprior(Lo["s10_base"][s]) for s in S]) * 100
    res = rule(dn.mean(), do.mean(), dn.std(ddof=1))
    out = (f"pilot n={len(S)}: d_old {do.mean():+.3f} pp (sd {do.std(ddof=1):.2f}), d_new {dn.mean():+.3f} pp "
           f"(sd {dn.std(ddof=1):.2f}) -> r {res['r']:.3f}, design delta {res['delta']:.3f} pp, n85 {res['n85']:.0f} -> "
           f"n = {res['n']} seeds per instrument per arm; power at delta {res['power']:.3f}, at 0.7 x delta "
           f"{res['power_curse']:.3f}; underpowered by design: {res['underpowered']}")
    print(out)
    open(os.path.join(HERE, "steer11", "sizing.txt"), "w").write(out + "\n" + json.dumps(res) + "\n")
    return res


if __name__ == "__main__":
    os.chdir(HERE)
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    main()
