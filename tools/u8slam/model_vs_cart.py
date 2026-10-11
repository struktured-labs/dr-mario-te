#!/usr/bin/env python3
"""u8slam lane: the STEER14 steer model (dr-mario-rl h16 experiments/cvx: steer_model.execute(slam=...), wrapped exactly
as steer14_slamcal.model_pill does) run pill by pill on the replayed cases with each cart's slam constants, against that
cart's own Mesen trace. The model sees what the replay injected: the case board, the publish schedule, the co-sim DONE,
the cart's traced GO frame and the traced SLAM_ARM of the pill. Prestart pills (no GO inside the trace) are excluded, as
in steer14_slamcal.

Answers: does the model that was validated at KOPEN 32 / KEND 255 still predict the cart's DOWN start, lock frame and
landing at KOPEN 8 / KEND 8, and does it predict the paired lock-frame change u8 - f2p on the same pills?

Usage: model_vs_cart.py RUNS FWTAG ARM=KOPEN:KEND[,ARM=KOPEN:KEND...] [--out rows.jsonl]   (first arm = base)"""
import json, math, os, re, statistics, sys

CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as AN                                       # noqa: E402  (this lane's trace parser + strata)

args = sys.argv[1:]
out_path = None
if "--out" in args:
    i = args.index("--out"); out_path = args[i + 1]; del args[i:i + 2]
RUNS, FW = args[0], args[1]
ARMS = [(a.split("=")[0], tuple(int(v) for v in a.split("=")[1].split(":"))) for a in args[2].split(",")]
cwd = os.getcwd()
os.chdir(CVX); sys.path.insert(0, CVX)
import import_pin; import_pin.pin()                         # noqa: E402,E702
import steer14_slamcal as SC                                # noqa: E402
import steer_model as SM                                    # noqa: E402
import steer8_run as S8                                     # noqa: E402


def model_pill(case, d, go, armed, kopen, kend):
    """steer14_slamcal.model_pill with the slam constants as arguments and this lane's GO / SLAM_ARM reading"""
    t = S8.ARMS["fD_bdepD"]["t"]
    st = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True, trace=True)
    st.proph_end_f = t["p_end"]; st.dg_extra = None; st.ledge_commit = bool(t["ledge_c"]); st.proph_first_end = t["p_first"]
    T = d["T"]
    st.v = T[0]["hv"]
    b = case["board"]
    color = [[0 if b[r * 8 + c] == 255 else 1 for c in range(8)] for r in range(16)]
    sched = [(int(math.ceil(go + tt - 1e-9)), (o4 ^ 2) * 8 + col) for tt, col, o4 in case["pubs"]]
    slam = {"done": int(math.ceil(go + case["done_f"] - 1e-9)), "armed": armed, "vc": case["vc"], "kopen": kopen,
            "kend": kend}
    par = None
    for a, bb in zip(T, T[1:]):
        if bb["held"] & 4 and bb["y"] < a["y"]:
            par = bb["f"] % 2; break
    ph = 1 if par is None else (1 - par) % 2
    SM.G0_CHOICES = (2, 2)
    ex = st.execute(color, sched[-1][1], case["spu"] * 10, t_act=go + 6, phase=ph, sched=sched, slam=slam)
    down = next((x[0] for x in ex["trace"] if x[5] & 4), None)
    return {"down": down, "lock": ex["lock_f"], "act": ex["var"] * 8 + ex["col"], "fin": sched[-1][1]}


R = {}
for g in AN.GAMES:
    C2 = AN.cases(g, FW)
    C = SC.parse_cases(f"{AN.T}/a16mt/cases/{g}_{FW}_chain_garb.lua")
    garb_prev = {p + 1 for p in C2 if C2[p]["garb"]}
    for arm, (ko, ke) in ARMS:
        tag = f"{g}_{arm}_{FW}_chain_garb"
        log = os.path.join(RUNS, tag, f"lateflip_{tag}.log")
        if not os.path.exists(log):
            print(f"MISSING {log}"); continue
        P = SC.parse_log(log)                               # slamcal's parser (carries hv)
        Q, _ = AN.parse(log)                                # this lane's parser (carries k: the GO frame)
        for p, d in sorted(P.items()):
            if p not in C or "land" not in d or not d["T"] or p not in Q or "land" not in Q[p]:
                continue
            go = None
            for t in Q[p]["T"]:
                if t["k"] >= 0:
                    go = t["f"] - t["k"] + 1
            if go is None or go < 1:
                continue                                    # prestart pill: the search predates the trace
            sa = next(t["sa"] for t in Q[p]["T"] if t["f"] >= go)
            dn = next((t["f"] for t in Q[p]["T"] if t["held"] & 4), None)
            lastx = max((y["f"] for x, y in zip(Q[p]["T"], Q[p]["T"][1:]) if x["x"] != y["x"]
                         and (dn is None or y["f"] <= dn)), default=None)      # the cart's last lateral move before DOWN
            m = model_pill(C[p], d, go, sa == 1, ko, ke)
            R.setdefault((g, p), {"s": dict(end=C[p]["vc"] < 10, tuck=C2[p]["tuck"][0] != 255, pg=p in garb_prev,
                                            vc=C[p]["vc"])})[arm] = dict(
                cart=dict(down=dn, lock=d["land"]["f"], act=d["land"]["action"], y=d["land"]["y"], lastx=lastx), model=m, go=go,
                sa=sa)
os.chdir(cwd)

STRATA = [("all pills", lambda s: True), (">= 10 viruses", lambda s: not s["end"]), ("< 10 viruses", lambda s: s["end"]),
          ("tuck pills", lambda s: s["tuck"]), ("non-tuck pills", lambda s: not s["tuck"])]
print(f"# STEER14 steer model vs cart, pill by pill, fw={FW} (prestart pills excluded); arms " +
      ", ".join(f"{a} = KOPEN {k[0]} / KEND {k[1]}" for a, k in ARMS))
print("\n## A. the model on each cart (model - cart)")
print(f"{'arm':4s} {'stratum':16s} {'n':>5s} {'DOWN exact':>10s} {'|d|<=1':>7s} {'mean':>6s} | {'LOCK exact':>10s} {'|d|<=1':>7s} "
      f"{'|d|<=3':>7s} {'mean':>6s} | {'landing == cart':>15s} | {'landed final: cart':>18s} {'model':>14s}")
for arm, _ in ARMS:
    for name, sel in STRATA:
        rs = [e[arm] for e in R.values() if arm in e and sel(e["s"])]
        if not rs:
            continue
        dd = [r["model"]["down"] - r["cart"]["down"] for r in rs if r["model"]["down"] is not None and r["cart"]["down"] is not None]
        dl = [r["model"]["lock"] - r["cart"]["lock"] for r in rs if r["model"]["lock"] is not None]
        n = len(rs)
        pc = lambda v, f: 100 * sum(f(x) for x in v) / max(1, len(v))
        la = sum(r["model"]["act"] == r["cart"]["act"] for r in rs)
        fc = sum(r["cart"]["act"] == r["model"]["fin"] for r in rs); fm = sum(r["model"]["act"] == r["model"]["fin"] for r in rs)
        print(f"{arm:4s} {name:16s} {n:5d} {pc(dd, lambda x: x == 0):9.1f}% {pc(dd, lambda x: abs(x) <= 1):6.1f}% "
              f"{statistics.mean(dd):+6.2f} | {pc(dl, lambda x: x == 0):9.1f}% {pc(dl, lambda x: abs(x) <= 1):6.1f}% "
              f"{pc(dl, lambda x: abs(x) <= 3):6.1f}% {statistics.mean(dl):+6.2f} | {la:6d} {100 * la / n:6.2f}% | "
              f"{fc:6d} {100 * fc / n:6.2f}% {fm:6d} {100 * fm / n:6.2f}%")
base = ARMS[0][0]
for arm, _ in ARMS[1:]:
    print(f"\n## B. paired lock-frame change {arm} - {base} on the same pills: cart vs model")
    print(f"{'stratum':16s} {'n':>5s} {'cart mean':>9s} {'model mean':>10s} {'model - cart':>12s} {'per-pill change equal':>21s} "
          f"{'|diff|<=2':>9s} | {'landing changed: cart':>21s} {'model':>6s} {'both':>5s}")
    for name, sel in STRATA:
        pr = [(e[base], e[arm]) for e in R.values() if base in e and arm in e and sel(e["s"])
              and e[base]["model"]["lock"] is not None and e[arm]["model"]["lock"] is not None]
        if not pr:
            continue
        dc = [y["cart"]["lock"] - x["cart"]["lock"] for x, y in pr]
        dm = [y["model"]["lock"] - x["model"]["lock"] for x, y in pr]
        eq = sum(a == b for a, b in zip(dc, dm)); near = sum(abs(a - b) <= 2 for a, b in zip(dc, dm))
        cc = [y["cart"]["act"] != x["cart"]["act"] for x, y in pr]; mc = [y["model"]["act"] != x["model"]["act"] for x, y in pr]
        print(f"{name:16s} {len(pr):5d} {statistics.mean(dc):+9.2f} {statistics.mean(dm):+10.2f} "
              f"{statistics.mean(dm) - statistics.mean(dc):+12.2f} {eq:10d} {100 * eq / len(pr):6.1f}%   {100 * near / len(pr):7.1f}% | "
              f"{sum(cc):21d} {sum(mc):6d} {sum(a and b for a, b in zip(cc, mc)):5d}")
print("\n## C. DOWN start, model - cart, by frames (and, of those pills, how many have the cart starting DOWN on the frame"
      " right after its last lateral move)")
for arm, _ in ARMS:
    h, st = {}, {}
    for e in R.values():
        if arm in e and e[arm]["model"]["down"] is not None and e[arm]["cart"]["down"] is not None:
            c = e[arm]["cart"]; k = max(-3, min(4, e[arm]["model"]["down"] - c["down"]))
            h[k] = h.get(k, 0) + 1; st[k] = st.get(k, 0) + (c["lastx"] is not None and c["down"] - c["lastx"] == 1)
    print(f"  {arm}: " + ", ".join(f"{'<=' if k == -3 else '>=' if k == 4 else ''}{k:+d}: {h[k]} ({st[k]})" for k in sorted(h)))
if out_path:
    with open(out_path, "w") as fh:
        for (g, p), e in sorted(R.items()):
            fh.write(json.dumps(dict(game=g, fw=FW, p=p, **e["s"], **{a: e[a] for a, _ in ARMS if a in e})) + "\n")
