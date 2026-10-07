"""STEER13 part B, step 1: validate + calibrate the anytime publish model (anytime13.py) on the measured co-sim timelines.

Corpus: the 10/03 couch boards G2/G3/G4 (335 decisions; cases_g2_dist60_20261003 / cases_dist60_20261003: board, cur,
nxt, p) with their Verilator co-sim publish timelines:
  fw 1488e158 (FAIR's firmware)          dr-mario-lateflip-wt experiments/lateflip/pubtrace_G*_fw1488e158.jsonl
  V1 a1ef31c8 (= V11 without preemption)  dr-mario-fwtuckreach-wt tmp/cosim/runs/pubtrace_G*_ship.jsonl
Checks (R96: every claim against the measured instrument):
  ID    anytime13._choose_fw_meta final + every root value == Leaf6FwDecider.choose / .vals (verbatim copy)
  SEQ   the model's publish ACTION SEQUENCE == the co-sim's (exact list), per fw, on boards without a tuck commit
  TIME  fit T0, a, b, c, d, e on 1488 publish times (least squares, all publishes of SEQ-exact non-tuck boards); report
        residuals; predict V1's publish times OUT OF SAMPLE (pass-B cost from the same coefficients)
  GATE  P(mailbox == final at GO + g), g = 2 / 4 / 6 / 8 f: model vs co-sim, both fws
  python steer13_anytime_cal.py -> steer13/anytime_cal.txt + steer13/anytime_coef.json + steer13/anytime_cal_rows.jsonl
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
import anytime13 as AT  # noqa: E402

CF = os.path.join(HERE, "..", "couch_forensics")
LF = "/home/struktured/projects/dr-mario-lateflip-wt/experiments/lateflip"
TR = "/home/struktured/projects/dr-mario-fwtuckreach-wt/tmp/cosim/runs"
OUT = os.path.join(HERE, "steer13")
GATES = (2, 4, 6, 8)


def load():
    sys.path.insert(0, CF)
    sys.path.insert(0, os.path.join(HERE, "..", "braingap"))
    Q = {}
    for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl")):
        q = json.loads(l); Q[("G2", q["p"])] = q
    for l in open(os.path.join(CF, "cases_dist60_20261003.jsonl")):
        q = json.loads(l)
        if q.get("game") in ("G3", "G4"):
            Q[(q["game"], q["p"])] = q
    T = {"1488": {}, "v11": {}}
    for g in ("G2", "G3", "G4"):
        for l in open(os.path.join(LF, f"pubtrace_{g}_fw1488e158.jsonl")):
            t = json.loads(l); T["1488"][(g, t["p"])] = t
        for l in open(os.path.join(TR, f"pubtrace_{g}_ship.jsonl")):
            t = json.loads(l); T["v11"][(g, t["p"])] = t
    return Q, T


def feats(roots, upto, fw):
    """[1, n1, roots done, sum m2, sum n3, sum kk2] for the time at which TODAY-index `upto` completes (1488) or the
    pass-C position `upto` completes (v11: pass B over all roots first)"""
    n1 = len(roots)
    f = np.array([1.0, n1, 0, 0, 0, 0])
    if fw == "1488":
        for r in roots[:upto + 1]:
            f[2] += 1; f[3] += r[3]; f[4] += r[5]; f[5] += r[4]
        return f
    for r in roots:
        f[2] += 1; f[3] += r[3]
    order = sorted(range(n1), key=lambda j: (-roots[j][2], j))
    for j in order[:upto + 1]:
        r = roots[j]
        f[2] += 1; f[3] += r[3]; f[4] += r[5]; f[5] += r[4]
    return f


def pub_positions(roots, fw):
    """positions (1488: today index; v11: pass-C position) at which the model publishes, with the action"""
    out = []
    if fw == "1488":
        best = None
        for j, r in enumerate(roots):
            if best is None or r[1] > best:
                best = r[1]; out.append((j, r[0]))
        return out
    order = sorted(range(len(roots)), key=lambda j: (-roots[j][2], j))
    best = None; bj = None
    for pos, j in enumerate(order):
        r = roots[j]
        if best is None or r[1] > best or (r[1] == best and j < bj):
            best = r[1]; bj = j; out.append((pos, r[0]))
    return out


def main():
    sys.path.insert(0, CF)
    import analyze_g2 as A
    import rules_steer10 as R10
    from drmario.faithful_game import Pill
    dec = R10.base_decider()
    meta = AT.Meta()
    Q, T = load()
    os.makedirs(OUT, exist_ok=True)
    lines = []

    def pr(s=""):
        print(s, flush=True); lines.append(s)
    rows = []
    nid = nbad = 0
    for key in sorted(T["1488"]):
        q = Q[key]
        b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
        cur, nxt = Pill(*q["cur"]), Pill(*q["nxt"])
        a_ref = dec.choose(b.clone(), cur, nxt, q["p"]); vref = dec.vals.copy()
        a_m, roots = meta.run(dec, b.clone(), cur, nxt, q["p"])
        nid += 1
        ok_id = a_m == a_ref and all(int(meta.vals[a]) == int(vref[a]) for a in range(32))
        nbad += int(not ok_id)
        row = {"game": key[0], "p": key[1], "vc": int(b.virus_count()), "final": a_m, "roots": roots, "id_ok": ok_id}
        for fw in ("1488", "v11"):
            t = T[fw].get(key)
            if t is None:
                continue
            seq_obs = [x[3] for x in t["pubs"]]
            pos = pub_positions(roots, fw)
            seq_mod = [x[1] for x in pos]
            tuck = t.get("tuck") not in (None, [255, 255])
            row[fw] = {"obs": [[x[0], x[3]] for x in t["pubs"]], "done_f": t.get("done_f"), "final_obs": t["final"][2],
                       "tuck": tuck, "seq_eq": seq_obs == seq_mod, "pos": pos,
                       "feats": [feats(roots, p_, fw).tolist() for p_, _ in pos]}
        rows.append(row)
    with open(os.path.join(OUT, "anytime_cal_rows.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    pr(f"ID  _choose_fw_meta == Leaf6FwDecider (final + all 32 root values): {nid - nbad}/{nid}")
    for fw in ("1488", "v11"):
        R = [r for r in rows if fw in r]
        nt = [r for r in R if not r[fw]["tuck"]]
        fe = sum(r[fw]["final_obs"] == r["final"] for r in nt)
        se = sum(r[fw]["seq_eq"] for r in nt)
        pr(f"SEQ {fw}: boards {len(R)}, tuck commits {len(R) - len(nt)}; non-tuck: co-sim final == model final {fe}/{len(nt)}; "
           f"publish SEQUENCE exactly equal {se}/{len(nt)}")
    # ---- fit timing on 1488
    X, y = [], []
    for r in rows:
        d = r.get("1488")
        if d is None or d["tuck"] or not d["seq_eq"]:
            continue
        for f, (t, a) in zip(d["feats"], d["obs"]):
            X.append(f); y.append(t)
    X = np.array(X); y = np.array(y)
    # leaf-cost models (all leaves = engine commands): L = n1 + roots + sum m2 + sum n3 + sum kk2 (STEER7: flat clocks
    # per leaf). M1: t = k * L; M2: t = T0 + k * L + b * roots (per-root overhead). Coefficients >= 0 required.
    L = X[:, 1] + X[:, 2] + X[:, 3] + X[:, 4] + X[:, 5]
    k1 = float((L @ y) / (L @ L))
    X2 = np.column_stack([np.ones(len(y)), L, X[:, 2]])
    b2, *_ = np.linalg.lstsq(X2, y, rcond=None)
    fits = {"M1": dict(T0=0.0, k=k1, b=0.0), "M2": dict(T0=float(b2[0]), k=float(b2[1]), b=float(b2[2]))}
    for name, f in fits.items():
        pred = f["T0"] + f["k"] * L + f["b"] * X[:, 2]
        r_ = y - pred
        pr(f"TIME {name} on 1488 publishes (n={len(y)}): T0 {f['T0']:+.3f} f, {f['k'] * 85.909e6 / 60.0988:.0f} clocks/leaf, "
           f"per-root {f['b']:+.3f} f; residual sd {r_.std():.2f} f, |res| p50/p90 {np.percentile(np.abs(r_), 50):.2f}/"
           f"{np.percentile(np.abs(r_), 90):.2f}")
    CH = "M1" if fits["M2"]["T0"] < 0 or fits["M2"]["b"] < 0 else "M2"
    f = fits[CH]
    coef = dict(T0=f["T0"], a=f["k"], b=f["k"] + f["b"], c=f["k"], d=f["k"], e=f["k"], model=CH)
    pr(f"CHOSEN {CH} (M2 unless it fits a negative intercept / per-root cost) -> anytime13 coef {coef}")
    beta = np.array([coef[x] for x in ("T0", "a", "b", "c", "d", "e")])
    json.dump(coef, open(os.path.join(OUT, "anytime_coef.json"), "w"), indent=1)
    # ---- predict + gate rates
    for fw in ("1488", "v11"):
        Xo, yo = [], []
        for r in rows:
            d = r.get(fw)
            if d is None or d["tuck"] or not d["seq_eq"]:
                continue
            for f, (t, a) in zip(d["feats"], d["obs"]):
                Xo.append(f); yo.append(t)
        Xo = np.array(Xo); yo = np.array(yo); ro = yo - Xo @ beta
        pr(f"\n[{fw}] publish-time prediction ({'IN-sample' if fw == '1488' else 'OUT-of-sample'}, n={len(yo)}): "
           f"bias {ro.mean():+.2f} f, sd {ro.std():.2f} f")
        for scope, sel in (("all non-tuck boards", lambda r: True), ("endgame vc<=16", lambda r: (r["vc"] or 48) <= 16)):
            Rn = [r for r in rows if fw in r and not r[fw]["tuck"] and sel(r)]
            parts = []
            for g in GATES:
                obs = np.mean([AT.mailbox([(t, a) for t, a in r[fw]["obs"]], g) == r[fw]["final_obs"] for r in Rn])
                mod = np.mean([AT.mailbox(AT.publishes(r["roots"], fw, coef), g) == r["final"] for r in Rn])
                parts.append(f"g{g}: co-sim {100 * obs:.1f}% model {100 * mod:.1f}%")
            pr(f"   GATE P(final at GO+g) {scope} (n={len(Rn)}): " + "; ".join(parts))
        Rn = [r for r in rows if fw in r and not r[fw]["tuck"]]
        tf_obs = [next(t for t, a in r[fw]["obs"] if a == r[fw]["final_obs"]) for r in Rn
                  if any(a == r[fw]["final_obs"] for t, a in r[fw]["obs"])]
        tf_mod = [next(t for t, a in AT.publishes(r["roots"], fw, coef) if a == r["final"]) for r in Rn]
        pr(f"   time the final is first published (f after GO) p25/50/75/90: co-sim "
           + "/".join(f"{x:.1f}" for x in np.percentile(tf_obs, [25, 50, 75, 90]))
           + "; model " + "/".join(f"{x:.1f}" for x in np.percentile(tf_mod, [25, 50, 75, 90])))
    open(os.path.join(OUT, "anytime_cal.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
