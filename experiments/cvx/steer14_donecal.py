"""STEER14 DONE-time model (the slam gate opens at DONE; DONE is the ONLY gate at vcount < 10, and it decides SLAM_ARM).

The STEER13 anytime model times PUBLISHES (validated: sd 0.95 f); its implied search end is ~10 f EARLY on the co-sim
(steer13 calibration rows: DONE p50 44.5 f, leaf-count time 34.5 f) and nearly constant, while the co-sim DONE spreads
32-57 f. Model (fitted on the fw-1488 co-sim boards, non-tuck, IN-sample; checked OUT-of-sample on V11):
    done_f = BETA x leaves(fw) + eps,    leaves(1488) = n1 + sum(1 + m2 + n3 + kk2), leaves(V11) = that + sum(1 + m2)
    eps    = a draw from the 1488 in-sample residuals of the same vcount band (0-9 / 10-16 / 17-30 / 31+), keyed by
             (seed, pill) -> common to every arm and to the reference (CRN)
Writes steer14/done_model.json and steer14/done_model.txt.
"""
import os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BANDS = ((0, 9), (10, 16), (17, 30), (31, 99))


def leaves(roots, fw):
    n1 = len(roots)
    deep = sum(1 + r[3] + r[5] + r[4] for r in roots)
    return n1 + deep + (sum(1 + r[3] for r in roots) if fw == "v11" else 0)


def band(vc):
    return next(i for i, (lo, hi) in enumerate(BANDS) if lo <= vc <= hi)


def main():
    os.chdir(HERE)
    rows = [json.loads(l) for l in open("steer13/anytime_cal_rows.jsonl")]
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    D = {}
    for fw in ("1488", "v11"):
        D[fw] = [(leaves(r["roots"], fw), r[fw]["done_f"], r["vc"]) for r in rows
                 if r.get(fw) and r[fw].get("done_f") is not None and not r[fw].get("tuck")]
    L, Y, V = (np.array(x, float) for x in zip(*D["1488"]))
    beta = float(L @ Y / (L @ L))
    res = Y - beta * L
    pools = {str(i): [round(float(e), 3) for e, v in zip(res, V) if BANDS[i][0] <= v <= BANDS[i][1]] for i in range(len(BANDS))}
    out(f"DONE model: BETA {beta:.7f} f/leaf (the publish fit: 0.0011507); 1488 IN-sample n {len(Y)}: bias {res.mean():+.2f}, "
        f"sd {res.std():.2f}; residual pools by vcount band: " + ", ".join(f"{BANDS[int(k)]} n {len(v)}" for k, v in pools.items()))
    Lv, Yv, Vv = (np.array(x, float) for x in zip(*D["v11"]))
    rng = np.random.default_rng(14)
    sim = np.array([beta * l + pools[str(band(int(v)))][rng.integers(len(pools[str(band(int(v)))]))] for l, v in zip(Lv, Vv)])
    e = beta * Lv - Yv
    out(f"V11 OUT-of-sample n {len(Yv)}: mean bias (BETA x leaves - co-sim) {e.mean():+.2f} f; DONE quantiles p10/50/90 co-sim "
        f"{np.percentile(Yv, [10, 50, 90]).round(1).tolist()} vs model+eps {np.percentile(sim, [10, 50, 90]).round(1).tolist()}")
    for i, (lo, hi) in enumerate(BANDS):
        s = (Vv >= lo) & (Vv <= hi)
        out(f"   vc {lo}-{hi}: n {s.sum()}, co-sim p50 {np.median(Yv[s]):.1f}, model+eps p50 {np.median(sim[s]):.1f}")
    json.dump({"beta": beta, "bands": BANDS, "pools": pools, "source": "steer13/anytime_cal_rows.jsonl (1488, non-tuck)"},
              open("steer14/done_model.json", "w"), indent=1)
    open("steer14/done_model.txt", "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
