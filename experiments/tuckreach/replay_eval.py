#!/usr/bin/env python3
"""Score Mesen replays of co-sim publish timelines (run_lateflip.sh on the REAL couch cart) the way the late-flip
lane's policy_eval.py does:
  ==final   landing == the copro's DONE final (the firmware's own answer)
  HYBRID    landing is none of the copro's published candidates (pubs + final)
  ==python  landing == the python brain's choice (G2 sim_action, G3/G4 dist_action)
  regret    python-evaluator regret (Leaf6Decider per-action values, couch forensics `val`, G2 only) of the landing vs
            the python brain's choice, over landings the python evaluator scores (reach-allowed); unscored = outside
  tall      the subset with max column height >= 12
  reg-xT    the same regret without the landings ON a tuck answer (the evaluator scores an action's straight drop,
            so a tuck landing is mis-scored)
  frozen    cases where the cart's DRLATEGUARD lock ($61D7, the probe's `lg=` second field) engaged = a refused late
            answer (carts without LATEGUARD must read 0 here: control)
  lateRT    target changes the driver adopted after its first commit (parse_lateflip late_retargets), summed
Usage: replay_eval.py LABEL:GAME:PUBTRACE.jsonl:MESEN.log [...]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "replay"))
from parse_lateflip import load  # noqa: E402

CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
VAL = {json.loads(l)["p"]: json.loads(l).get("val") for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))}


def metrics(R, land, game, subset=None):
    ps = [p for p in sorted(land) if p in R and (subset is None or p in subset)]
    o = dict(n=len(ps), final=0, hybrid=0, python=0, silicon=0, scored=0, regret=0, unscored=0, xs=0, xr=0)
    for p in ps:
        a, r = land[p], R[p]
        pubs = {x[3] for x in r["pubs"]} | {r["final"][2]}
        o["final"] += a == r["final"][2]
        o["hybrid"] += a not in pubs
        o["python"] += a == r["sim_action"]
        o["silicon"] += a == r.get("actual_action")
        v = VAL.get(p) if game == "G2" else None
        if v is not None and r["sim_action"] is not None:
            if str(a) in v:
                o["scored"] += 1; o["regret"] += v[str(r["sim_action"])] - v[str(a)]
                tuckland = bool(r.get("tuck")) and r["tuck"][0] != 255 and a == r["final"][2]
                if not tuckland:          # the python evaluator scores the STRAIGHT drop of an action, not a tuck
                    o["xs"] += 1; o["xr"] += v[str(r["sim_action"])] - v[str(a)]
            else:
                o["unscored"] += 1
    o["regret_mean"] = round(o["regret"] / o["scored"], 1) if o["scored"] else None
    o["xregret_mean"] = round(o["xr"] / o["xs"], 1) if o["xs"] else None
    return o


def main():
    print(f"{'label':22s} {'game':4s} | {'n':>3s} {'==final':>7s} {'HYBRID':>6s} {'==python':>8s} {'==silicon':>9s} "
          f"{'unscored':>8s} {'regret/scored':>13s} {'reg-xT':>6s} {'frozen':>6s} {'lateRT':>6s} | tall n ==final HYBRID regret")
    for spec in sys.argv[1:]:
        label, game, pt, log = spec.split(":")
        R = {json.loads(l)["p"]: json.loads(l) for l in open(pt)}
        L = load(log)
        land = {p: L[p]["land"]["act"] for p in L if L[p]["land"]}
        tall = {p for p, r in R.items() if r.get("heights") and max(r["heights"]) >= 12}
        m, t = metrics(R, land, game), metrics(R, land, game, tall)
        rm = "-" if m["regret_mean"] is None else f"{m['regret_mean']:.1f}"
        rt = "-" if t["regret_mean"] is None else f"{t['regret_mean']:.1f}"
        rx = "-" if m["xregret_mean"] is None else f"{m['xregret_mean']:.1f}"
        fz = sum(1 for p in L if p in R and L[p]["land"] and L[p]["frozen"])
        lr = sum(L[p]["late_retargets"] for p in L if p in R and L[p]["land"])
        print(f"{label:22s} {game:4s} | {m['n']:3d} {m['final']:7d} {m['hybrid']:6d} {m['python']:8d} {m['silicon']:9d} "
              f"{m['unscored']:8d} {rm:>13s} {rx:>6s} {fz:6d} {lr:6d} | {t['n']:6d} {t['final']:7d} {t['hybrid']:6d} {rt:>6s}   (cases {len(R)})")


if __name__ == "__main__":
    main()
