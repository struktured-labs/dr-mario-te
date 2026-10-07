"""STEER14 KOPEN-cut calibration reader (EXECUTION METRICS ONLY; no race outcome, time or pill count is read or printed).
Written and committed to this file BEFORE the calibration rows exist. Rows: steer14/cal/ (steer14_jobs.py cal).

RULE (pre-declared): candidates KOPEN K in {24, 16, 8, 4} (DIST4, V11, MIN_THINK 6 f). K is ELIGIBLE iff
    landed-on-final(K) >= landed-on-final(32) - 1.0 pp   AND   refusals(K) <= refusals(32) + 0.5 pp   (per pill)
KC = the eligible K with the most negative mean paired tempo change vs KOPEN 32 (f/pill, seed-paired); if no eligible K
gains at least 0.10 f/pill, KC = 16 (the default named in the coordinator's request). Ties -> the larger K.
MODEL CHECK (reported, not a gate on KC): the model's MIN_THINK 2 f - 6 f tempo change must be within +-0.25 f/pill of 0
(the cart's measured lock change is +0.00 f on 622 same-landing pills, steer14/slamcal/rule.txt).
Writes steer14/cal/kopen_cut.txt.
"""
import os, json, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
import steer14_jobs as J


def load(arm):
    d = {}
    for f in glob.glob(os.path.join(HERE, f"steer14/cal/lulu14c_{arm}_*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r["arm"] == arm + "~steer":
                d[r["seed"]] = r["knob"]
    return d


def main():
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    seeds = [lo + 2 * i for lo in J.CAL for i in range(J.JOB)]
    K = {a: load(a) for a in J.CAL_ARMS}
    short = {a: len(v) for a, v in K.items() if len(v) < len(seeds)}
    if short:
        out(f"INCOMPLETE {short}: nothing computed"); print("\n".join(lines)); return
    rate = lambda a, key: 100 * sum(K[a][s][key] for s in seeds) / sum(K[a][s]["dec"] for s in seeds)
    tp = lambda a: np.array([K[a][s]["tempo_f"] / max(K[a][s]["dec"], 1) for s in seeds])
    out(f"STEER14 KOPEN CALIBRATION (execution only; {len(seeds)} seeds 39134-39932, LULU race, DIST4, V11, MIN_THINK 6 f "
        f"unless stated; tempo = lock-frame change vs today's cart (fw 1488, KOPEN 32) per pill)")
    base_tp = tp("S14_d4_k32")
    rng = np.random.default_rng(14)
    res = {}
    for a in J.CAL_ARMS:
        d = tp(a) - base_tp
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        res[a] = dict(tempo=float(tp(a).mean()), dtempo=float(d.mean()), ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
                      final=rate(a, "landed_final"), refuse=rate(a, "refuse"), nonfinal=rate(a, "nonfinal_commit"),
                      disarmed=rate(a, "disarmed"), down_done=rate(a, "down_done"), down_stab=rate(a, "down_stab"),
                      no_down=rate(a, "no_down"))
        r = res[a]
        out(f"  {a:16s} tempo {r['tempo']:+.2f} f/pill (vs KOPEN 32: {r['dtempo']:+.2f} [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]); "
            f"landed on the final {r['final']:.2f} %; refused {r['refuse']:.2f} %; non-final commits {r['nonfinal']:.1f} %; "
            f"disarmed {r['disarmed']:.1f} %; DOWN via DONE {r['down_done']:.1f} % / stability {r['down_stab']:.1f} % / none "
            f"{r['no_down']:.1f} %")
    b = res["S14_d4_k32"]
    elig = [k for k in (24, 16, 8, 4) if res[f"S14_d4_k{k}"]["final"] >= b["final"] - 1.0
            and res[f"S14_d4_k{k}"]["refuse"] <= b["refuse"] + 0.5]
    gain = [k for k in elig if res[f"S14_d4_k{k}"]["dtempo"] <= -0.10]
    if gain:
        kc = sorted(gain, key=lambda k: (res[f"S14_d4_k{k}"]["dtempo"], -k))[0]
        why = f"eligible {elig}; most negative tempo change among those gaining >= 0.10 f/pill"
    else:
        kc = 16
        why = f"eligible {elig}; none gains >= 0.10 f/pill -> the default 16"
    mt = res["CAL_d4_k32_mt2"]["dtempo"]
    out(f"  MODEL CHECK MIN_THINK 2 f - 6 f: {mt:+.2f} f/pill -> {'consistent with the cart (+0.00)' if abs(mt) <= 0.25 else 'NOT within +-0.25 of the cart'}")
    out(f"KOPEN CUT KC = {kc} ({why})")
    open(os.path.join(HERE, "steer14/cal/kopen_cut.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
