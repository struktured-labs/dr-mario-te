"""silfid: predict PUBLOG capture #3's tall-endgame landing != copro-final rate on V11 (fw c51d2e21) from capture #2.
  predict_v11.py CAP2_COSIM_1488.jsonl CAP2_COSIM_V11_CELL.jsonl  -> predict_v11_20261007.txt
Anytime-commit decomposition (the steersim lane's model): the cart commits to the copro's RUNNING answer at the gate
(WDOG2 >= MINTHINK = 12 hooks = 6 f after GO) and only partly follows later changes, so a pill whose at-gate answer is
not the final is where landings != final concentrate.
  1. On capture #2's CELL pills (silicon, fw 1488e158): at-gate answer = the last live read at <= 12 hooks (silicon's
     own log); split the landing outcome (lock pose vs copro final) by at-gate == final.
  2. The same CELL uploads co-simulated on V11 (Verilator, same RTL 3b164c7, fw c51d2e21): the at-gate answer = the
     publication valid at 6.0 f; at-gate == final rate on V11 (and on 1488 from the same co-sim, as a control).
  3. Predicted V11 rate = P_V11(gate != final) * P(land != final | gate != final) + P_V11(gate == final) * P(land !=
     final | gate == final), with the conditionals from silicon (1). Interval: binomial 90% on each conditional."""
import sys, json, math, collections, os
HERE = os.path.dirname(os.path.abspath(__file__))
G = {0: 3, 1: 1, 2: 0, 3: 2}
GATE_H = 12
R1 = {json.loads(l)["seq"]: json.loads(l) for l in open(sys.argv[1]) if l.strip()}
RV = {json.loads(l)["seq"]: json.loads(l) for l in open(sys.argv[2]) if l.strip()}
out = []
def P(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)
def cell(r): return r["viruses"] <= 20 and r["maxh"] >= 14 and r["seq"] < 1597
def wilson(k, n, z=1.645):
    if n == 0: return (0, 1)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)
def at(pubs, t):
    v = None
    for tt, c, o in pubs:
        if tt <= t: v = (c, o)
    return v
tab = collections.Counter(); ctl = collections.Counter(); sil_gate = {}
for s, r in R1.items():
    if not cell(r) or "done" not in r:
        continue
    lk = [e for e in r["events"] if e["type"] == "lock"]
    if not lk:
        continue
    live = [(e["hooks"], e["a"], e["b"]) for e in r["events"] if e["type"] == "live"]
    g = None
    for h, c, o in live:
        if h <= GATE_H: g = (c, o)
    fin = (r["cosim_done"][1], r["cosim_done"][2])
    u = r["upload"].split(); same = (int(u[0]) & 3) == (int(u[1]) & 3)
    got = (lk[0]["a"], lk[0]["b"] & 3); want = (fin[0], G[fin[1]])
    land_ok = got == want or (same and got[0] == want[0] and got[1] % 2 == want[1] % 2)
    gate_ok = g == fin
    sil_gate[s] = gate_ok
    tab[(gate_ok, land_ok)] += 1
    # control: the co-sim's own 1488 at-gate (should equal silicon's)
    cg = at([(t, c, o) for t, c, o in r["cosim_pubs"]], GATE_H / 2.0)
    ctl[cg == g] += 1
n = sum(tab.values())
ng = tab[(True, True)] + tab[(True, False)]; nb = tab[(False, True)] + tab[(False, False)]
pg = tab[(True, False)] / max(ng, 1); pb = tab[(False, False)] / max(nb, 1)
P(f"# capture #2 CELL, silicon fw 1488e158: {n} pills with a lock")
P(f"  at-gate == final: {ng} ({100 * ng / n:.1f}%) -> landing != final {tab[(True, False)]} ({100 * pg:.1f}%, 90% "
  f"[{100 * wilson(tab[(True, False)], ng)[0]:.1f}, {100 * wilson(tab[(True, False)], ng)[1]:.1f}])")
P(f"  at-gate != final: {nb} ({100 * nb / n:.1f}%) -> landing != final {tab[(False, False)]} ({100 * pb:.1f}%, 90% "
  f"[{100 * wilson(tab[(False, False)], nb)[0]:.1f}, {100 * wilson(tab[(False, False)], nb)[1]:.1f}])")
P(f"  overall landing != final: {tab[(True, False)] + tab[(False, False)]} / {n} = "
  f"{100 * (tab[(True, False)] + tab[(False, False)]) / n:.1f}%")
P(f"  control: the 1488 co-sim's at-gate answer == silicon's logged at-gate answer on {ctl[True]} / {sum(ctl.values())}")
# V11 co-sim of the same uploads
vg = collections.Counter(); vdone = []; vfin_same = 0; nv = 0
for s, r in RV.items():
    if s not in R1 or not cell(R1[s]):
        continue
    pubs = [(t, c, o) for t, c, o in r["cosim_pubs"]]
    fin = (r["cosim_done"][1], r["cosim_done"][2])
    g = at(pubs, GATE_H / 2.0)
    vg[g == fin] += 1; nv += 1
    vdone.append(r["cosim_done"][0])
    vfin_same += fin == (R1[s]["cosim_done"][1], R1[s]["cosim_done"][2])
if nv:
    qv = vg[False] / nv
    P(f"\n# the same {nv} CELL uploads on V11 (fw c51d2e21, Verilator)")
    paired = [sil_gate[s] for s in RV if s in sil_gate]
    P(f"  at-gate (6.0 f) == final: {vg[True]} ({100 * (1 - qv):.1f}%)   [1488 silicon on the SAME pills: "
      f"{100 * sum(paired) / max(len(paired), 1):.1f}% (n {len(paired)}); on all {n}: {100 * ng / n:.1f}%]")
    P(f"  V11 final == 1488 final on {vfin_same} / {nv}; V11 DONE median {sorted(vdone)[len(vdone) // 2]:.1f} f")
    if nv < n:
        # partial V11 run: the replayed pills are a seq-ordered subset; scale the FULL 1488 non-final rate by the PAIRED
        # V11 / 1488 non-final ratio on the subset (the subset can be easier or harder than the whole CELL)
        nf88 = 1 - sum(paired) / max(len(paired), 1)
        ratio = qv / nf88 if nf88 > 0 else 1.0
        qv_full = min(1.0, (nb / n) * ratio)
        P(f"  PARTIAL ({nv}/{n}): paired non-final ratio V11/1488 = {100 * qv:.1f}% / {100 * nf88:.1f}% = {ratio:.2f} -> "
          f"V11 non-final on the whole CELL ~ {100 * qv_full:.1f}% (1488: {100 * nb / n:.1f}%)")
        qv = qv_full
    pred = qv * pb + (1 - qv) * pg
    lo = qv * wilson(tab[(False, False)], nb)[0] + (1 - qv) * wilson(tab[(True, False)], ng)[0]
    hi = qv * wilson(tab[(False, False)], nb)[1] + (1 - qv) * wilson(tab[(True, False)], ng)[1]
    P(f"\n# PREDICTION for capture #3 (V11), tall-endgame CELL landing != copro final: {100 * pred:.1f}% "
      f"(90% band {100 * lo:.1f}-{100 * hi:.1f}%)   vs capture #2 on 1488: "
      f"{100 * (tab[(True, False)] + tab[(False, False)]) / n:.1f}%")
    P("  caveats: the conditionals are FAIR's (capture #2); capture #3 runs FAIR2PLUS (DRABORTSTALE + DRLGPRESTART +")
    P("  DRDISTROW=2), which changes the gate's follow-through (DISTROW widens the lateral budget, LGPRESTART lets prestart")
    P("  answers bypass LATEGUARD), so the gate != final arm is an UPPER-side estimate; the gate == final arm is execution")
    P("  only and should carry over.")
open(os.path.join(HERE, "predict_v11_20261007.txt"), "w").write("\n".join(out) + "\n")
