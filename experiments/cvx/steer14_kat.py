"""STEER14 analyzer KNOWN-ANSWER TEST (R96: a checker ships with a control that must fail). No farm row is read.

Builds a synthetic bank in dr-mario-h16-wt/tmp/steer14/kat/ from REAL gate rows used as templates (a dr. lulu race WIN
and LOSS at M 167.5 from the slam-gate rows, an owner race WIN and LOSS at M 239.5, a gate-b row with / without a
tap-out), assigned to every arm of parts R, M and D (and to synthetic STEER13 rows for part R's survival ratio) by a
seeded 0/1 design matrix. The expected value of every pre-registered number is computed HERE from the design matrix
(numpy) and compared with analyze_steer14's RESULTS / return values:
  part R: the corrected V11 - 1488 delta + churn, STEER13's delta + churn, the survival ratio;
  part M: (i) / (ii) / (iii) primary deltas + churn, both guards for each, (iv) interaction mean + histogram, the q 2 %
          sensitivity delta + churn, the reference (the gate cut alone); part D: every configuration - k32 delta.
Controls: (a) one file missing -> parts M/D WITHHELD (part_M returns None); (b) D16 G* <-> D4 G* swapped -> the
comparison must FAIL (the test can fail). Exit 0 = PASS.
"""
import os, sys, json, glob, copy, shutil
import numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
import analyze_steer14 as A
import steer14_jobs as J
from vs_race import evaluate

KAT = "/home/struktured/projects/dr-mario-h16-wt/tmp/steer14/kat"
GS = "u16"
LO, NL, NG, NS, ND = 1000, 200, 100, 100, 100
LO13, NL13, NG13 = 3000, 120, 60


def rows(pat):
    return [json.loads(l) for f in sorted(glob.glob(pat)) for l in open(f)]


def templates():
    lulu = rows("steer14/gate/det1_lulu_S14_d4_k32.jsonl") + rows("steer14/gate/pc_lulu_S14_d16_k32.jsonl") + \
        rows("steer14/gate/cons_lulu_C13_14886.jsonl")
    wl = [r for r in lulu if evaluate(r, A.M_LULU, A.SIGMA, A.DELTA)[0] == "win_race"]
    ll = [r for r in lulu if evaluate(r, A.M_LULU, A.SIGMA, A.DELTA)[0] != "win_race"]
    race = lulu + rows("steer14/gate/id_rc_S14_id_v116.jsonl")
    wo = [r for r in race if evaluate(r, A.M_OWNER, A.SIGMA, A.DELTA)[0] == "win_race"]
    lo_ = [r for r in race if evaluate(r, A.M_OWNER, A.SIGMA, A.DELTA)[0] != "win_race"]
    g0 = [r for r in rows("steer14/gate/id_gb_S14_id_v116.jsonl") if r["topout"] == 0][0]
    g1 = copy.deepcopy(g0); g1["topout"] = 1; g1["how"] = "topout"; g1["won"] = 0
    assert wl and ll and wo and lo_, (len(wl), len(ll), len(wo), len(lo_))
    return {"lulu": (ll[0], wl[0]), "rc": (lo_[0], wo[0]), "gb": (g0, g1)}


def design(seed):
    rng = np.random.default_rng(seed)
    flip = lambda x, p_up, p_dn: np.where(x == 1, (rng.random(len(x)) >= p_dn).astype(int), (rng.random(len(x)) < p_up).astype(int))
    a, b, c, d = J.main_arms(); q4, q16 = J.sens_arms()
    D = {}
    D[a] = (rng.random(NL) < 0.6).astype(int)
    D[b] = flip(D[a], 0.15, 0.08)
    D[c] = flip(D[a], 0.25, 0.05)
    D[d] = flip(D[c], 0.20, 0.10)
    D[q4] = (rng.random(NS) < 0.5).astype(int)
    D[q16] = flip(D[q4], 0.3, 0.1)
    for k, arm in enumerate(J.dose_arms()):
        D[arm] = flip(D[a][:ND], 0.1 + 0.05 * k, 0.1)
    G = {x: (rng.random(NG) < 0.1).astype(int) for x in (a, b, c, d)}
    R = {x: (rng.random(NG) < 0.85).astype(int) for x in (a, b, c, d)}
    Rd = {"C13_14886": (rng.random(NL13) < 0.6).astype(int)}
    Rd["C13_v116"] = flip(Rd["C13_14886"], 0.2, 0.1)
    S13 = {"B_14886_qb": (rng.random(NL13) < 0.6).astype(int)}
    S13["B_v116_qb"] = flip(S13["B_14886_qb"], 0.4, 0.05)
    Rg = {x: ((rng.random(NG13) < 0.1).astype(int), (rng.random(NG13) < 0.85).astype(int)) for x in Rd}
    return D, G, R, Rd, S13, Rg


def write_bank(Dz, T, root, drop=None):
    D, G, R, Rd, S13, Rg = Dz
    shutil.rmtree(root, ignore_errors=True); os.makedirs(root + "/main"); os.makedirs(root + "/s13")
    seeds = lambda n, lo: [lo + 2 * i for i in range(n)]

    def dump(path, lab, tpl, vec, ss):
        with open(path, "w") as fh:
            for s, v in zip(ss, vec):
                r = copy.deepcopy(tpl[int(v)]); r["seed"] = s; r["arm"] = lab
                fh.write(json.dumps(r) + "\n")
    for a, vec in D.items():
        dump(f"{root}/main/lulu14_{a}_{LO}.jsonl", f"{a}~steer", T["lulu"], vec, seeds(len(vec), LO))
    for a in G:
        dump(f"{root}/main/gb14_{a}_{LO}.jsonl", f"{a}@owner202610", T["gb"], G[a], seeds(NG, LO))
        dump(f"{root}/main/rc14_{a}_{LO}.jsonl", f"{a}~steer", T["rc"], R[a], seeds(NG, LO))
    for a, vec in Rd.items():
        dump(f"{root}/main/lulu14_{a}_{LO13}.jsonl", f"{a}~steer", T["lulu"], vec, seeds(NL13, LO13))
        dump(f"{root}/main/gb14_{a}_{LO13}.jsonl", f"{a}@owner202610", T["gb"], Rg[a][0], seeds(NG13, LO13))
        dump(f"{root}/main/rc14_{a}_{LO13}.jsonl", f"{a}~steer", T["rc"], Rg[a][1], seeds(NG13, LO13))
    for a, vec in S13.items():
        dump(f"{root}/s13/lulu13_{a}_{LO13}.jsonl", f"{a}~steer", T["lulu"], vec, seeds(NL13, LO13))
    if drop:
        os.remove(f"{root}/main/{drop}")


def setup(root):
    A.MAIN_DIR = root + "/main"; A.S13_DIR = root + "/s13"; A.OUT = root + "/analysis.txt"; A.OUT_R = root + "/analysis_R.txt"
    A.RESULTS.clear()
    J.GS = GS; J.LO, J.N_LULU, J.N_GUARD, J.N_SENS, J.N_DOSE = LO, NL, NG, NS, ND
    J.LO13, J.N13_LULU, J.N13_GUARD = LO13, NL13, NG13


def expected(Dz):
    D, G, R, Rd, S13, Rg = Dz
    a, b, c, d = J.main_arms(); q4, q16 = J.sens_arms()
    E = {}
    ch = lambda y, x: (int(np.sum((y == 0) & (x == 1))), int(np.sum((y == 1) & (x == 0))))   # good = 1
    chb = lambda y, x: (int(np.sum((y == 1) & (x == 0))), int(np.sum((y == 0) & (x == 1))))  # bad = 1
    for key, X, Y in (("i", b, a), ("ii", d, c), ("iii", d, a)):
        E[f"({key}) PRIMARY LULU race"] = (100 * np.mean(D[X] - D[Y]), ch(D[Y], D[X]))
        E[f"({key}) GUARD gate-b tap-out"] = (100 * np.mean(G[X] - G[Y]), chb(G[Y], G[X]))
        E[f"({key}) GUARD owner race M{A.M_OWNER}"] = (100 * np.mean(R[X] - R[Y]), ch(R[Y], R[X]))
    iv = (D[d] - D[c]) - (D[b] - D[a])
    E["(iv)"] = (100 * np.mean(iv), {x: int(np.sum(iv == x)) for x in (-2, -1, 0, 1, 2)})
    E[f"(iii) q 2 %: {q16} - {q4}"] = (100 * np.mean(D[q16] - D[q4]), ch(D[q4], D[q16]))
    E[f"(ref) the gate cut alone: {c} - {a}"] = (100 * np.mean(D[c] - D[a]), ch(D[a], D[c]))
    for arm in J.dose_arms():
        g = arm.split("_", 2)[2]
        E[f"(D) {g} - k32"] = (100 * np.mean(D[arm] - D[a][:ND]), ch(D[a][:ND], D[arm]))
    E[f"(D) {GS} - k32"] = (100 * np.mean(D[c][:ND] - D[a][:ND]), ch(D[a][:ND], D[c][:ND]))
    E["(R) LULU race"] = (100 * np.mean(Rd["C13_v116"] - Rd["C13_14886"]), ch(Rd["C13_14886"], Rd["C13_v116"]))
    E["(R) gate-b tap-out"] = (100 * np.mean(Rg["C13_v116"][0] - Rg["C13_14886"][0]), chb(Rg["C13_14886"][0], Rg["C13_v116"][0]))
    E["(R) owner race"] = (100 * np.mean(Rg["C13_v116"][1] - Rg["C13_14886"][1]), ch(Rg["C13_14886"][1], Rg["C13_v116"][1]))
    E["(R13) LULU race, STEER13 model"] = (100 * np.mean(S13["B_v116_qb"] - S13["B_14886_qb"]), ch(S13["B_14886_qb"], S13["B_v116_qb"]))
    ratio = np.mean(Rd["C13_v116"] - Rd["C13_14886"]) / np.mean(S13["B_v116_qb"] - S13["B_14886_qb"])
    return E, ratio


def compare(E):
    bad = []
    for lab, (dv, extra) in E.items():
        got = A.RESULTS.get(lab)
        if got is None:
            bad.append((lab, "missing")); continue
        if abs(got["d"][0] - dv) > 1e-9:
            bad.append((lab, "d", got["d"][0], dv))
        if lab == "(iv)":
            if got["hist"] != extra:
                bad.append((lab, "hist", got["hist"], extra))
        elif tuple(got["churn"]) != tuple(extra):
            bad.append((lab, "churn", got["churn"], extra))
    return bad


def main():
    T = templates()
    ok = True
    setup(KAT + "/good")
    Dz = design(14)
    E, ratio = expected(Dz)
    write_bank(Dz, T, KAT + "/good")
    rr = A.part_R(lambda s="": None)
    res = A.part_M(lambda s="": None)
    bad = compare(E)
    rat_ok = rr is not None and abs(rr["ratio"] - ratio) < 1e-9
    ok &= res is not None and not bad and rat_ok
    print(f"KAT good bank: {len(E)} known answers, {len(bad)} mismatches {bad[:3]}; survival ratio analyzer "
          f"{rr['ratio'] if rr else float('nan'):.6f} vs known {ratio:.6f} -> {'ok' if (not bad and rat_ok) else 'FAIL'}")
    for lab in ("(iii) PRIMARY LULU race", "(iv)", "(R) LULU race"):
        if lab in A.RESULTS:
            print(f"    {lab}: analyzer {A.RESULTS[lab]['d'][0]:+.4f} vs known {E[lab][0]:+.4f}")
    setup(KAT + "/short")
    write_bank(Dz, T, KAT + "/short", drop=f"lulu14_{J.sens_arms()[1]}_{LO}.jsonl")
    res2 = A.part_M(lambda s="": None)
    ok &= res2 is None
    print(f"KAT control (a) one file missing -> {'WITHHELD (ok)' if res2 is None else 'NOT WITHHELD (FAIL)'}")
    setup(KAT + "/swap")
    D2 = dict(Dz[0]); a, b, c, d = J.main_arms()
    D2[c], D2[d] = Dz[0][d], Dz[0][c]
    write_bank((D2,) + Dz[1:], T, KAT + "/swap")
    A.part_R(lambda s="": None); A.part_M(lambda s="": None)
    bad3 = compare(E)
    ok &= len(bad3) > 0
    print(f"KAT control (b) D16 G* <-> D4 G* swapped -> {len(bad3)} mismatches ({'detected, ok' if bad3 else 'NOT DETECTED, FAIL'})")
    print("STEER14 KAT", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
