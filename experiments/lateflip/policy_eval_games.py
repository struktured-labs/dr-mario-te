"""Ship vs DRLATEGUARD vs the other cart options on G3 / G4 (10/03), Mesen (real cart) + the churn model.
Metrics: landing == copro FINAL; HYBRID (none of the copro's published candidates); == python brain (dist_action);
== silicon; tall (max height >= 12) subset hybrids. No python per-action values exist for these games (no regret).
Usage: policy_eval_games.py G3|G4"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/struktured/projects/dr-mario-lateflip-wt/tools/lateflip")
from parse_lateflip import load
import steer_churn as SC
g = sys.argv[1]
R = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(HERE, f"pubtrace_{g}_seed0.jsonl"))}
LF = "/home/struktured/projects/dr-mario-lateflip-wt/tmp/lateflip/"
tall = {p for p, r in R.items() if r["heights"] and max(r["heights"]) >= 12}


def met(land):
    ps = sorted(land)
    pubs = lambda r: {x[3] for x in r["pubs"]} | {r["final"][2]}
    return dict(n=len(ps), final=sum(land[p] == R[p]["final"][2] for p in ps),
                hybrid=sum(land[p] not in pubs(R[p]) for p in ps),
                python=sum(land[p] == R[p]["sim_action"] for p in ps),
                silicon=sum(land[p] == R[p]["actual_action"] for p in ps),
                tall_hybrid=sum(land[p] not in pubs(R[p]) for p in ps if p in tall), tall_n=len([p for p in ps if p in tall]))


def model(pol):
    land, slam = {}, True
    for p in sorted(R):
        r = R[p]
        res = SC.execute(SC.board_color(r["upload"]), [(a, b, c) for a, b, c, _ in r["pubs"]], r["done_f"],
                         r["final"][:2], p, r["vc"], slam_arm=slam, policy=pol,
                         tall=bool(r["heights"]) and max(r["heights"]) >= 12)
        slam = res["done_before_lock"]; land[p] = res["action"]
    return land


print(f"{g}: {len(R)} placements, {len(tall)} tall")
for src, pol, log in (("mesen", "ship", f"{g}_off"), ("mesen", "guard", f"{g}_on"), ("model", "ship", None),
                      ("model", "guard", None), ("model", "freeze", None), ("model", "tallfreeze", None)):
    if log:
        L = load(LF + f"{log}/lateflip_{log}.log"); land = {p: L[p]["land"]["act"] for p in L if L[p]["land"]}
    else:
        land = model(pol)
    m = met(land)
    print(f"  {src:5s} {pol:10s} n={m['n']:3d} ==final {m['final']:3d} HYBRID {m['hybrid']:2d} ==python {m['python']:3d} "
          f"==silicon {m['silicon']:3d} | tall {m['tall_n']:3d} hybrid {m['tall_hybrid']:2d}")
