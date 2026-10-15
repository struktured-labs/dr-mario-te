"""TAPOUT stage 0 (PREREG_TAPOUT sec. 2 Q0 / sec. 4 classification): characterise tap-outs from tapout/trace_*.jsonl."""
import json, glob, collections, statistics as st, sys
sys.path.insert(0, "."); import import_pin; import_pin.pin()
from vs_race import evaluate
W = 8


def load(tag, kind):
    T, R = {}, {}
    for f in glob.glob(f"tapout/trace_chunk_{tag}_{kind}_*.jsonl"):
        for l in open(f):
            d = json.loads(l); T[d["seed"]] = d
    for f in glob.glob(f"tapout/tr_rows_chunk_{tag}_{kind}_*.jsonl"):
        for l in open(f):
            d = json.loads(l); R[d["seed"]] = d
    return T, R


def hs(h):
    return max(h[2:6])


def classify(tr, garb):
    n = len(tr); win = range(max(0, n - W), n)
    gt = sum(s for k, s in garb if k >= n - W)
    first14 = next((i for i, p in enumerate(tr) if hs(p["h"]) >= 14), None)
    stab = sum(tr[i]["stab"] for i in win); m = len(win)
    if gt >= 4:
        return "GARBAGE"
    if first14 is not None and first14 <= n - 3:
        return "THROAT"
    if stab * 2 >= m:
        return "CUT-SHORT"
    return "OTHER"


def q(xs):
    xs = sorted(xs)
    return [round(xs[int(p * (len(xs) - 1))], 1) for p in (0.1, 0.5, 0.9)] if xs else None


out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))
for tag, lab in (("a16u8", "A16 + u8"), ("f2p", "FAIR2PLUS-equiv (d4 k32)")):
    T, R = load(tag, "top"); C, CR = load(tag, "ctl")
    kills = {s for s, r in R.items() if evaluate(r, 167.5, 0.15, 2.65)[0] == "loss_kill"}
    P(f"\n== {lab}: tap-out replays {len(T)} (kill before her finish {len(kills)}), control clears {len(C)}")
    for name, S in (("ALL tap-outs", set(T)), ("KILLS", kills & set(T))):
        tt = [T[s] for s in S]
        P(f"-- {name} n={len(tt)}")
        P("  pills at death p10/50/90", q([len(t["trace"]) for t in tt]), " time s", q([t["t_end"] for t in tt]),
          " viruses left", q([t["trace"][-1]["vc"] for t in tt]))
        P("  viruses-left bands at death:", dict(sorted(collections.Counter(
            "<=4" if t["trace"][-1]["vc"] <= 4 else "5-9" if t["trace"][-1]["vc"] <= 9 else "10-19" if t["trace"][-1]["vc"] <= 19 else "20+" for t in tt).items())))
        P("  garbage tiles in last 8 pills", q([sum(s for k, sz in [(k, s) for k, s in t["garb"]] if k >= len(t["trace"]) - W for s in [sz]) for t in tt]),
          " whole game", q([sum(s for _, s in t["garb"]) for t in tt]))
        P("  throat Hs (cols2-5) 8 pills before / at last decision", q([hs(t["trace"][max(0, len(t["trace"]) - 8)]["h"]) for t in tt]),
          q([hs(t["trace"][-1]["h"]) for t in tt]))
        P("  max col height at last decision", q([max(t["trace"][-1]["h"]) for t in tt]),
          " cols>=12 at last", q([sum(x >= 12 for x in t["trace"][-1]["h"]) for t in tt]))
        P("  pills since throat first >=12 / >=14", q([len(t["trace"]) - next((i for i, p in enumerate(t["trace"]) if hs(p["h"]) >= 12), len(t["trace"])) for t in tt]),
          q([len(t["trace"]) - next((i for i, p in enumerate(t["trace"]) if hs(p["h"]) >= 14), len(t["trace"])) for t in tt]))
        last = [p for t in tt for p in t["trace"][-W:]]
        P(f"  last-8 pills: stab-lock (before DONE) {100*st.mean(p['stab'] for p in last):.1f}%  disarmed {100*st.mean(p['disarmed'] for p in last):.1f}%"
          f"  landed!=final {100*(1-st.mean(p['final'] for p in last)):.1f}%  same-colour pills {100*st.mean(p['pill'][0]==p['pill'][1] for p in last):.1f}%")
        P("  class:", dict(collections.Counter(classify(t["trace"], t["garb"]) for t in tt).most_common()))
    cc = list(C.values())
    allp = [p for t in cc for p in t["trace"]]
    P(f"-- CONTROL clears n={len(cc)}: stab-lock {100*st.mean(p['stab'] for p in allp):.1f}% disarmed {100*st.mean(p['disarmed'] for p in allp):.1f}% landed!=final {100*(1-st.mean(p['final'] for p in allp)):.1f}%")
    P("  max throat Hs reached per game", q([max(hs(p["h"]) for p in t["trace"]) for t in cc]),
      " games reaching Hs>=12 / >=14:", f"{100*st.mean(max(hs(p['h']) for p in t['trace'])>=12 for t in cc):.0f}% / {100*st.mean(max(hs(p['h']) for p in t['trace'])>=14 for t in cc):.0f}%",
      " garbage tiles/game", q([sum(s for _, s in t["garb"]) for t in cc]))
    # identity vs banked
    import glob as g
    arm = "S14_d16_u8" if tag == "a16u8" else "S14_d4_k32"
    B = {}
    for f in g.glob(f"steer14/main/lulu14_{arm}_*.jsonl"):
        for l in open(f):
            d = json.loads(l)
            if d["arm"] == arm + "~steer": B[d["seed"]] = d
    allR = {**R, **CR}
    P("  identity vs banked rows (t_end, how, pills):", sum(B[s]["t_end"] == r["t_end"] and B[s]["how"] == r["how"] and B[s]["pills"] == r["pills"] for s, r in allR.items()), "/", len(allR))
print("\n".join(out))
open("tapout/characterisation.txt", "w").write("\n".join(out) + "\n")
