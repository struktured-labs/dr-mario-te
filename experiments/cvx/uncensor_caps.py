"""Uncensor gate-(b) games that hit the 600-pill cap (how == "stall"): replay them with a larger cap and
record whether they eventually clear or tap out.

Why: at L15, fw540's lower tap-out (3.83% vs winner 5.67%) sits beside more capped games (2.33% vs
0.50%); if those end in tap-outs the ranking flips (RESULT_DOSE2.md). Same check for L11.

Control (per arm x level): one NON-capped banked game replayed under the large cap must reproduce its
banked row exactly. That proves the cap only truncates and does not change play. A mismatch aborts that
shard.

Usage: python uncensor_caps.py MAXPILLS SHARD NSHARDS OUT.jsonl
"""
import sys, os, json, glob
CVX = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CVX)
import import_pin; import_pin.pin()
import gate_b as G, vs_race as V, bursty_model as BM

ARMS = ("fw_winner", "fw540", "fw720", "fw900")
SRC = {11: "gateb/{a}_*.jsonl", 15: "gateb_l15/{a}_L15_*.jsonl"}


def banked():
    rows = {}
    for lvl, pat in SRC.items():
        for a in ARMS:
            for f in sorted(glob.glob(os.path.join(CVX, pat.format(a=a)))):
                for l in open(f):
                    r = json.loads(l)
                    if r.get("arm") == a and r.get("model") == "owner" and r.get("level", 11) == lvl:
                        rows[(lvl, a, r["seed"])] = r
    return rows


if __name__ == "__main__":
    maxp, shard, nsh, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    B = banked()
    jobs = []
    for (lvl, a) in sorted({(k[0], k[1]) for k in B}):
        keys = sorted(k for k in B if k[:2] == (lvl, a))
        ctrl = next(k for k in keys if B[k]["how"] != "stall")
        jobs.append(("control", ctrl))
        jobs += [("capped", k) for k in keys if B[k]["how"] == "stall"]
    mine = jobs[shard::nsh]
    model = BM.fit_struktured_20260804()
    with open(out, "w") as fh:
        for kind, (lvl, a, seed) in mine:
            r = G.play(seed, None, model, level=lvl, maxpills=maxp, choose=V._decider(a))
            r.update({"arm": a, "model": "owner", "trate": 0.0})
            if lvl != 11: r["level"] = lvl
            b = B[(lvl, a, seed)]
            if kind == "control":
                ok = json.dumps(r, sort_keys=True) == json.dumps(b, sort_keys=True)
                fh.write(json.dumps({"kind": "control", "level": lvl, "arm": a, "seed": seed, "identical": ok}) + "\n"); fh.flush()
                if not ok:
                    sys.exit(f"CONTROL MISMATCH {lvl} {a} {seed}: cap changes play; abort")
                continue
            r.update({"kind": "capped", "level": lvl, "maxpills": maxp, "banked_pills": b["pills"], "banked_vleft": b["vleft"]})
            fh.write(json.dumps(r) + "\n"); fh.flush()
