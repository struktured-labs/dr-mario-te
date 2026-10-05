"""DONE-gated pills: Mesen pressed DOWN only once the copro's DONE was served (down1 >= done). On those, the silicon -
Mesen arrival gap (minus the +1 f alignment seen on every other pill) measures silicon's DONE time vs the co-sim's
GO + done_f. Regress it on done_f: proportional = a copro CLOCK ratio, flat = a fixed latency."""
import json, os, sys
sys.path.insert(0, ".")
import timing as T
import numpy as np


def run(label, Q, log, pub):
    P = {t["p"]: t for t in map(json.loads, open(pub))}
    rows = T.compare(Q, log, pub)
    pts = []
    for r in rows:
        m = r["mes"]
        if not r["same"] or m["down1"] is None or m["done"] is None:
            continue
        if m["down1"] + 1 >= m["done"] and m["down1"] - m["done"] <= 2 and m["arrive"] > m["down1"]:
            pts.append((r["p"], P[r["p"]]["done_f"], r["d_arrive"] - 1, r["state"], r["garb"]))
    if not pts:
        print(label, "no DONE-gated pills"); return []
    x = np.array([p[1] for p in pts]); y = np.array([p[2] for p in pts])
    A = np.vstack([x, np.ones_like(x)]).T
    k, c = np.linalg.lstsq(A, y, rcond=None)[0]
    print(f"{label}: DONE-gated same-landing pills n={len(pts)}; silicon DONE - co-sim DONE (f): median {np.median(y):+.1f} "
          f"mean {y.mean():+.2f} sd {y.std():.2f}; fit y = {k:+.3f}*done_f {c:+.2f} (done_f {x.min():.0f}-{x.max():.0f})")
    print("    " + " ".join(f"p{p}:{d:.0f}f->{g:+d}{'S' if s == 'STALE' else ''}{'G' if gb else ''}" for p, d, g, s, gb in pts))
    return pts


CF = "../couch_forensics"; LF = "/home/struktured/projects/dr-mario-lateflip-wt/tmp/lateflip"
FV = "/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay"
allp = []
Q = [json.loads(l) for l in open(f"{CF}/cases_m4g2_fair_20261004.jsonl")]
allp += run("M4G2 FAIR2 V11", Q, "/home/struktured/projects/dr_mario_rl/tmp/fair_20261004/mesen/lateflip_M4G2_fair2_stale0.log",
            f"{CF}/pubtrace_m4g2_fair_20261004.jsonl")
Q = T.attach_traj([json.loads(l) for l in open(f"{CF}/cases_g2_dist60_20261003.jsonl")], [f"{CF}/rawh_dist60_20261003_G2.jsonl"])
allp += run("10/03 G2 1488", Q, f"{LF}/G2_off/lateflip_G2_off.log", f"{FV}/timelines/pubtrace_G2_fw1488e158.jsonl")
for g in ("G3", "G4"):
    Q = [json.loads(l) for l in open(f"{CF}/cases_dist60_20261003.jsonl")]
    Q = T.attach_traj([q for q in Q if q["game"] == g], [f"{CF}/rawh_dist60_20261003_{x}.jsonl" for x in ("G3", "G4a", "G4b")])
    allp += run(f"10/03 {g} 1488", Q, f"{LF}/{g}_off/lateflip_{g}_off.log", f"{FV}/timelines/pubtrace_{g}_fw1488e158.jsonl")

# ---- 10/04 games, chained + silicon garbage base runs (execfid)
import prevtarget as PT
RUNS = "/home/struktured/projects/dr_mario_rl/tmp/execfid/runs"
for g, b in (("m1g2", "D"), ("m3g1", "D"), ("m3g2", "D"), ("m3g3", "D"), ("m5g2", "D"), ("m1g1", "D"),
             ("m2g1", "A"), ("m2g2", "A"), ("m2g3", "A"), ("m4g1", "A"), ("m4g2", "A")):
    cp, tp = PT.paths(g)
    tag = "M4G2_A_chain_garb" if g == "m4g2" else f"{g}_{b}_chain_garb"
    lg = f"{RUNS}/{tag}/lateflip_{tag}.log"
    if not (os.path.exists(lg) and os.path.exists(tp)):
        continue
    allp += run(f"10/04 {g} ({'FAIR' if b == 'D' else 'FAIR2'})", [json.loads(l) for l in open(cp)], lg, tp)
pts = [p for p in allp if not p[4]]
y = np.array([p[2] for p in pts]); x = np.array([p[1] for p in pts])
k, c = np.linalg.lstsq(np.vstack([x, np.ones_like(x)]).T, y, rcond=None)[0]
print(f"ALL (excluding garbage-window prestart pills): n={len(pts)} silicon DONE - co-sim DONE median {np.median(y):+.1f} f, "
      f"IQR {np.percentile(y, 25):+.0f}..{np.percentile(y, 75):+.0f}, fit {k:+.3f}*done_f {c:+.2f}")
