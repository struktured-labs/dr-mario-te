"""STEER14 STAGE-1 SCREEN of the slam-gate cut (EXECUTION METRICS ONLY; no race outcome, race time or pill count is read
or printed). Written and committed BEFORE the stage-1 rows exist (steer14/cal/, steer14_jobs.py cal).
Supersedes the KOPEN-only rule of e859887a: its calibration run was stopped at 113 rows, unread, when the coordinator
added the endgame (KEND / VCEND) cut; those rows were set aside (tmp/steer14/cal_run1_superseded/) and are not used.

CANDIDATES (DIST4, V11, MIN_THINK 6 f; steer14_run.GATES = (KOPEN, KEND, VCEND)): today k32 = (32, 255, 10); KOPEN cuts
k24 / k16 / k8 / k4; ENDGAME cuts e32 = (32, 32, 10), e16 = (32, 16, 10), v4 = (32, 255, 4); uniform u16 = (16, 16, 10),
u8 = (8, 8, 10). 400 seeds 39134-39932, LULU race; every number is seed-paired against k32.
RULE (pre-declared): a candidate is ELIGIBLE iff
    landed-on-final, all pills        >= k32's - 1.0 pp
    landed-on-final, endgame pills    >= k32's - 1.0 pp   (vcount < 10 at the pill: an endgame misplacement is costly)
    refusals per pill                 <= k32's + 0.5 pp
G* = the eligible candidate with the most negative mean tempo change PER GAME vs k32 (frames: the sum over the game's
pills of the lock-frame change vs today's cart); ties -> the earlier in the list above. If no eligible candidate gains at
least 30 f per game (0.5 s), G* = u16 (the default, declared).
G* is the 2x2's second factor (PREREG_STEER14 sec. 3); every other candidate goes to the dose-response (part D).
MODEL CHECK (reported, not a gate): the model's MIN_THINK 2 f - 6 f tempo change must be within +-0.25 f/pill of 0 (the
cart's measured lock change is +0.00 f on 622 same-landing pills, steer14/slamcal/rule.txt).
Writes steer14/cal/gate_cut.txt.
"""
import os, sys, json, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import steer14_jobs as J

CANDS = ("k24", "k16", "k8", "k4", "e32", "e16", "v4", "u16", "u8")
DEFAULT = "u16"


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
    S = lambda a, key: sum(K[a][s][key] for s in seeds)
    rate = lambda a, key, den="dec": 100 * S(a, key) / max(S(a, den), 1)
    per_game = lambda a: np.array([K[a][s]["tempo_f"] for s in seeds], float)
    out(f"STEER14 STAGE-1 SCREEN (execution only; {len(seeds)} seeds 39134-39932, LULU race, DIST4, V11, MIN_THINK 6 f unless "
        f"stated; tempo = lock-frame change vs today's cart (fw 1488, k32), summed per game)")
    base = per_game("S14_d4_k32")
    rng = np.random.default_rng(14)
    res = {}
    for a in J.CAL_ARMS:
        d = per_game(a) - base
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        res[a] = dict(dg=float(d.mean()), ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
                      dpill=float(S(a, "tempo_f") / S(a, "dec") - S("S14_d4_k32", "tempo_f") / S("S14_d4_k32", "dec")),
                      final=rate(a, "landed_final"), final_end=rate(a, "end_landed_final", "end_pills"),
                      refuse=rate(a, "refuse"), disarmed=rate(a, "disarmed"), ref_disarmed=rate(a, "ref_disarmed"),
                      dd=rate(a, "down_done"), ds=rate(a, "down_stab"), dn=rate(a, "no_down"),
                      end_gl=S(a, "end_golock_f") / max(S(a, "end_pills"), 1), end_ref=S(a, "end_ref_golock_f") / max(S(a, "end_pills"), 1),
                      gl=S(a, "golock_f") / S(a, "dec"), end_share=100 * S(a, "end_pills") / S(a, "dec"))
        r = res[a]
        out(f"  {a:16s} tempo vs k32 {r['dg']:+7.1f} f/game [{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}] ({r['dpill']:+.2f} f/pill); "
            f"landed on the final {r['final']:.2f} % (endgame {r['final_end']:.2f} %); refused {r['refuse']:.2f} %; disarmed "
            f"{r['disarmed']:.1f} % (today's ref {r['ref_disarmed']:.1f} %); DOWN via DONE {r['dd']:.1f} / stability {r['ds']:.1f} / "
            f"none {r['dn']:.1f} %; GO->lock {r['gl']:.1f} f, endgame pills ({r['end_share']:.1f} %) {r['end_gl']:.1f} f "
            f"(today's cart on the same pills {r['end_ref']:.1f} f)")
    b = res["S14_d4_k32"]
    elig = [g for g in CANDS if res[f"S14_d4_{g}"]["final"] >= b["final"] - 1.0
            and res[f"S14_d4_{g}"]["final_end"] >= b["final_end"] - 1.0 and res[f"S14_d4_{g}"]["refuse"] <= b["refuse"] + 0.5]
    gain = [g for g in elig if res[f"S14_d4_{g}"]["dg"] <= -30.0]
    if gain:
        gs = sorted(gain, key=lambda g: (res[f"S14_d4_{g}"]["dg"], CANDS.index(g)))[0]
        why = f"eligible {elig}; the most negative tempo per game among those gaining >= 30 f/game"
    else:
        gs = DEFAULT
        why = f"eligible {elig}; none gains >= 30 f/game -> the declared default {DEFAULT}"
    mt = res["CAL_d4_k32_mt2"]["dpill"]
    out(f"  MODEL CHECK MIN_THINK 2 f - 6 f: {mt:+.2f} f/pill -> "
        f"{'consistent with the cart (+0.00)' if abs(mt) <= 0.25 else 'NOT within +-0.25 of the cart'}")
    out(f"GATE CUT G* = {gs} ({why})")
    open(os.path.join(HERE, "steer14/cal/gate_cut.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
