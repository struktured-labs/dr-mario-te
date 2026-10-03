"""Coordinator's discriminating test on the REAL copro publish timelines (Verilator co-sim of the shipped RTL + fw,
pubtrace_g2_seed0_tuck.jsonl): is the running best at the driver's commit gate (GO + 6 f, MIN_THINK = 12 hooks) the
final answer? Does the silicon late flip go TOWARD the final (or a later intermediate)? Do wrong-direction first
moves match an intermediate best? Split by category and by whether the final came from the firmware's TUCK extension
(final published with a tuck descriptor; the extension runs after the main search and is not reach-masked).

Usage: gate_vs_final.py
"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); CF = os.path.join(HERE, "..", "couch_forensics")
GATE = 6.0
C = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))}
R = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(HERE, "pubtrace_g2_seed0_tuck.jsonl"))}
raw = {json.loads(l)["k"]: json.loads(l) for l in open(os.path.join(CF, "rawh_dist60_20261003_G2.jsonl"))}


def best_at(r, t):
    b = None
    for tp, c, o, a in r["pubs"]:
        if tp <= t:
            b = a
    return b


def first_lateral(k):
    tr = raw.get(k, {}).get("traj") or []
    if not tr:
        return None
    c0 = tr[0][3]
    for t, o, row, col, cols in tr:
        if col != c0:
            return "R" if col > c0 else "L"
    return None


def side(a):
    col = a % 8
    return "R" if col > 3 else ("L" if col < 3 else "-")


rows = collections.defaultdict(list)
for p, r in sorted(R.items()):
    c = C[p]
    gate, fin = best_at(r, GATE), r["final"][2]
    tuck = bool(r.get("tuck") and r["tuck"][0] != 255)
    later = [a for tp, cc, o, a in r["pubs"] if tp > GATE]
    sil = c["actual_action"]
    rows[c["category"]].append(dict(p=p, gate=gate, fin=fin, tuck=tuck, later=later, sil=sil, sim=c["sim_action"],
                                    fl=first_lateral(c["k"]), tall=max(c["heights"]) >= 12))
print(f"{'category':14s} {'n':>3s} {'gate==final':>11s} {'final=tuck':>10s} {'sil==final':>10s} {'sil==gate':>9s} "
      f"{'sil in later pubs':>17s} {'sil==python':>11s}")
for cat in ("MATCH", "LATE-FLIP", "OTHER", "SHORT-LANDING", "TUCK"):
    L = rows[cat]
    if not L:
        continue
    print(f"{cat:14s} {len(L):3d} {sum(x['gate'] == x['fin'] for x in L):11d} {sum(x['tuck'] for x in L):10d} "
          f"{sum(x['sil'] == x['fin'] for x in L):10d} {sum(x['sil'] == x['gate'] for x in L):9d} "
          f"{sum(x['sil'] in x['later'] for x in L):17d} {sum(x['sil'] == x['sim'] for x in L):11d}")
print("\nLATE-FLIP and OTHER detail (gate = running best at GO+6 f; later = publishes after the gate):")
for cat in ("LATE-FLIP", "OTHER"):
    for x in rows[cat]:
        fl = x["fl"]
        print(f"  {cat:9s} p{x['p']:3d} python a{x['sim']:2d} gate a{x['gate']} final a{x['fin']:2d}{' TUCK' if x['tuck'] else '     '} "
              f"later {x['later']} silicon a{x['sil']} first-lateral {fl} (gate side {side(x['gate']) if x['gate'] is not None else '?'}, "
              f"final side {side(x['fin'])}, python side {side(x['sim'])})")
# first-move test for OTHER: opposite to python's side -> does it match the gate best's side?
opp = [x for x in rows["OTHER"] if x["fl"] and side(x["sim"]) in "LR" and x["fl"] != side(x["sim"])]
print(f"\nOTHER with first lateral opposite to the python target: {len(opp)}; of those the first move matches the "
      f"at-gate RTL best's side: {sum(1 for x in opp if x['gate'] is not None and side(x['gate']) == x['fl'])}, "
      f"the RTL final's side: {sum(1 for x in opp if side(x['fin']) == x['fl'])}")
