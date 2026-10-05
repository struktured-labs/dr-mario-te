"""Q3 census: after a garbage window (the previous AI pill received garbage), does the AI execute the PREVIOUS pill's
target? Signature on silicon: action(k) == action(k-1) (same column + orientation, new colours), an early lateral
(<= f5) and an early fast drop (<= f8) -- an answer already DONE at the spawn -- and != the copro final for pill k
(co-sim on the real board). Control: the same equality rate on pills that did NOT follow garbage.
Usage: prevtarget.py GAME [GAME ...]   (cases/timelines from execfid/, m4g2 from couch_forensics/)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timing as T
HERE = os.path.dirname(os.path.abspath(__file__)); CF = os.path.join(HERE, "..", "couch_forensics")


def paths(g):
    c = os.path.join(HERE, "cases", f"cases_{g}_fair_20261004.jsonl")
    t = os.path.join(HERE, "timelines", f"pubtrace_{g}_fair_20261004.jsonl")
    if g == "m4g2":
        c = os.path.join(CF, "cases_m4g2_fair_20261004.jsonl"); t = os.path.join(CF, "pubtrace_m4g2_fair_20261004.jsonl")
    return c, t


def census(g, verbose=True):
    cp, tp = paths(g)
    Q = [json.loads(l) for l in open(cp)]
    P = {t["p"]: t for t in map(json.loads, open(tp))} if os.path.exists(tp) else {}
    qi = {q["p"]: q for q in Q}
    rows = []
    for q in Q:
        prev = qi.get(q["p"] - 1)
        if prev is None or prev.get("actual_action") is None or q.get("actual_action") is None:
            continue
        s = T.sil_events(q)
        garb = (prev.get("garbage_recv") or 0) > 0
        same_prev = q["actual_action"] == prev["actual_action"]
        fin = P[q["p"]]["final"][2] if q["p"] in P else None
        early = s is not None and s["lat1"] is not None and s["lat1"] <= 5 and s["drop1"] is not None and s["drop1"] <= 8
        rows.append(dict(game=g, p=q["p"], garb=garb, same_prev=same_prev, early=early, sil=q["actual_action"],
                         prev=prev["actual_action"], brain=q.get("sim_action"), final=fin,
                         lat1=s and s["lat1"], drop1=s and s["drop1"], interval=round((q["t_spawn"] - prev["t_spawn"]) * 60)))
    G = [r for r in rows if r["garb"]]; N = [r for r in rows if not r["garb"]]
    bug = [r for r in G if r["same_prev"] and (r["final"] is None or r["sil"] != r["final"]) and r["sil"] != r["brain"]]
    if verbose:
        print(f"{g}: pills after garbage {len(G)}: sil==prev {sum(r['same_prev'] for r in G)} (early-signature "
              f"{sum(r['same_prev'] and r['early'] for r in G)}); sil==prev AND != brain/final {len(bug)} | control (no garbage) "
              f"{len(N)}: sil==prev {sum(r['same_prev'] for r in N)}, early-signature {sum(r['early'] for r in N)}")
        for r in G:
            print(f"    p{r['p']:3d} interval {r['interval']:3d} f  sil a{r['sil']} prev a{r['prev']} brain a{r['brain']} final a{r['final']} "
                  f"lat1 {r['lat1']} drop1 {r['drop1']} {'PREV-TARGET' if r in bug else ('sil==prev (== brain/final)' if r['same_prev'] else '')}")
    return rows, bug


if __name__ == "__main__":
    allb = []; allg = 0
    for g in sys.argv[1:]:
        rows, bug = census(g)
        allb += bug; allg += sum(r["garb"] for r in rows)
    print(f"TOTAL pills after garbage {allg}, previous-target executions {len(allb)}")
