"""Cart-rule options on the REAL copro publish timelines (G2 10/03, 116 placements).

Policies (what a COMMITTED driver does when the published answer changes):
  ship        today's c960dd49: adopt every change (column always, orient via DRRELATCH while $0386 >= 8)
  guard       DRLATEGUARD: adopt only if the move can still be finished (lg_gate rule), else freeze
  freeze      never adopt after commit: execute the at-commit running best ("stale answer")
  tallfreeze  coordinator's option: on a tall board (max height >= 12) ignore changes needing a reversal or a rotation
Sources: Mesen (the real cart, lateflip_probe.lua) for ship / guard / freeze (DRLATEGUARD_MUT=always); the validated
churn model (steer_churn.py; 111/116 and 114/116 vs Mesen) for all four.
Metrics: landing == the copro's FINAL answer; HYBRID = landing is none of the copro's published candidates;
python-evaluator regret (Leaf6Decider values, forensics `val`) vs the python brain's own choice, over landings the
python brain scores (reach-allowed); "unscored" = landing outside the python reach mask (e.g. a hybrid).
Usage: policy_eval.py
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/struktured/projects/dr-mario-lateflip-wt/tools/lateflip")
from parse_lateflip import load
import steer_churn as SC
CF = os.path.join(HERE, "..", "couch_forensics")
C = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))}
R = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(HERE, "pubtrace_g2_seed0_tuck.jsonl"))}
LF = "/home/struktured/projects/dr-mario-lateflip-wt/tmp/lateflip/"
MESEN = {"ship": LF + "G2_off/lateflip_G2_off.log", "guard": LF + "G2_on2/lateflip_G2_on2.log",
         "freeze": LF + "G2_freeze/lateflip_G2_freeze.log"}


def metrics(land, subset=None):
    ps = [p for p in sorted(land) if subset is None or p in subset]
    out = dict(n=len(ps), final=0, hybrid=0, python=0, scored=0, regret=0, unscored=0)
    for p in ps:
        a, r, c = land[p], R[p], C[p]
        pubs = {x[3] for x in r["pubs"]} | {r["final"][2]}
        out["final"] += a == r["final"][2]
        out["hybrid"] += a not in pubs
        out["python"] += a == c["sim_action"]
        v = c["val"]
        if str(a) in v:
            out["scored"] += 1; out["regret"] += v[str(c["sim_action"])] - v[str(a)]
        else:
            out["unscored"] += 1
    out["regret_mean"] = round(out["regret"] / max(1, out["scored"]), 1)
    return out


def model_land(policy):
    land, slam = {}, True
    for p in sorted(R):
        r, c = R[p], C[p]
        res = SC.execute(SC.board_color(r["upload"]), [(a, b, cc) for a, b, cc, _ in r["pubs"]], r["done_f"],
                         r["final"][:2], p, r["vc"], slam_arm=slam, policy=policy, tall=max(c["heights"]) >= 12)
        slam = res["done_before_lock"]
        land[p] = res["action"]
    return land


tall = {p for p in C if max(C[p]["heights"]) >= 12}
print(f"{'source':7s} {'policy':10s} | {'n':>3s} {'==final':>7s} {'HYBRID':>6s} {'==python':>8s} {'unscored':>8s} "
      f"{'regret/scored':>13s} | tall n {'==final':>7s} {'HYBRID':>6s} {'unscored':>8s} {'regret':>6s}")
for pol in ("ship", "guard", "freeze", "tallfreeze"):
    for src in ("mesen", "model"):
        if src == "mesen":
            if pol not in MESEN:
                continue
            L = load(MESEN[pol]); land = {p: L[p]["land"]["act"] for p in L if L[p]["land"]}
        else:
            land = model_land(pol)
        m, t = metrics(land), metrics(land, tall)
        print(f"{src:7s} {pol:10s} | {m['n']:3d} {m['final']:7d} {m['hybrid']:6d} {m['python']:8d} {m['unscored']:8d} "
              f"{m['regret_mean']:13.1f} | {t['n']:6d} {t['final']:7d} {t['hybrid']:6d} {t['unscored']:8d} {t['regret_mean']:6.1f}")
sil = {p: C[p]["actual_action"] for p in C if C[p]["actual_action"] is not None}
m, t = metrics(sil), metrics(sil, tall)
print(f"{'silicon':7s} {'(ship)':10s} | {m['n']:3d} {m['final']:7d} {m['hybrid']:6d} {m['python']:8d} {m['unscored']:8d} "
      f"{m['regret_mean']:13.1f} | {t['n']:6d} {t['final']:7d} {t['hybrid']:6d} {t['unscored']:8d} {t['regret_mean']:6.1f}")


# ---- firmware root re-ordering, UPPER BOUND: the main search's own answer is published at the first publish slot
#      (the desk replay measures 66 -> 89% final-at-gate; this assumes 100%). A TUCK-extension commit cannot move: the
#      extension runs after every root, so it keeps its measured publish time.
def reorder_ub(r):
    pubs = r["pubs"]
    tuck = bool(r.get("tuck") and r["tuck"][0] != 255)
    if not pubs:
        return pubs
    t0 = pubs[0][0]
    if not tuck:
        f = r["final"]
        return [(t0, f[0], f[1], f[2])]
    main = [p for p in pubs if p[3] != r["final"][2]]
    mbest = main[-1] if main else pubs[0]
    return [(t0, mbest[1], mbest[2], mbest[3])] + [p for p in pubs if p[3] == r["final"][2]][:1]


print("\nwith firmware root re-ordering (upper bound; tuck commits keep their time):")
for pol in ("ship", "guard", "freeze", "tallfreeze"):
    land, slam = {}, True
    for p in sorted(R):
        r, c = R[p], C[p]
        pubs = reorder_ub(r)
        res = SC.execute(SC.board_color(r["upload"]), [(a, b, cc) for a, b, cc, _ in pubs], r["done_f"],
                         r["final"][:2], p, r["vc"], slam_arm=slam, policy=pol, tall=max(c["heights"]) >= 12)
        slam = res["done_before_lock"]; land[p] = res["action"]
    m, t = metrics(land), metrics(land, tall)
    print(f"{'model':7s} {pol + '+ro':10s} | {m['n']:3d} {m['final']:7d} {m['hybrid']:6d} {m['python']:8d} {m['unscored']:8d} "
          f"{m['regret_mean']:13.1f} | {t['n']:6d} {t['final']:7d} {t['hybrid']:6d} {t['unscored']:8d} {t['regret_mean']:6.1f}")
