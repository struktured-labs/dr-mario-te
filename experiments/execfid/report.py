"""execfid lane (2026-10-04) roll-up over every 10/04 couch game with Mesen runs (and the 10/03 G2 tall endgame):
  Q1 timing    silicon vs Mesen per pill: the forensics' OLD metric (last tracked frame - Mesen lock) vs ARRIVAL at the
               final pose, by predicted cart state (FIRST / STALE / armed / +GARB), base cart, chained + silicon garbage
  Q2 clamp     DISTGATE clamp-slams (clampslam.py) on the base runs, PROPH-armed or not, and what DRDISTROW does to them
  Q3 prev-tgt  previous-target executions after a garbage window: silicon census (prevtarget.py) + Mesen base vs DRLGPRESTART
  replay       before/after: landing == silicon / == copro final / hybrid (straight drop on no published candidate)
Banks: cases_timing_20261004.jsonl, cases_prevtarget_20261004.jsonl, cases_clampslam_20261004.jsonl, replay_20261004.json
Usage: report.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import timing as T
import clampslam as CS
import prevtarget as PT
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/tmp/execfid/tools")
import parse_lateflip as PL

RUNS = "/home/struktured/projects/dr_mario_rl/tmp/execfid/runs"
CF = os.path.join(HERE, "..", "couch_forensics")
GAMES = [("m1g1", "FAIR"), ("m1g2", "FAIR"), ("m3g1", "FAIR"), ("m3g2", "FAIR"), ("m3g3", "FAIR"), ("m5g2", "FAIR"),
         ("m2g1", "FAIR2"), ("m2g2", "FAIR2"), ("m2g3", "FAIR2"), ("m4g1", "FAIR2"), ("m4g2", "FAIR2")]


def log(tag):
    p = os.path.join(RUNS, tag, f"lateflip_{tag}.log")
    if not os.path.exists(p):
        return None
    if not any(l.startswith("SUMMARY") for l in open(p, errors="replace")):
        return None
    return p


def tags(g, build):
    b = "D" if build == "FAIR" else "A"
    if g == "m4g2":
        return dict(nochain="M4G2_A_nochain", chain="M4G2_A_chain", base="M4G2_A_chain_garb", lgp="M4G2_A_lgp_chain_garb",
                    row="M4G2_A_row_chain_garb", lgp_row="M4G2_A_lgp_row_chain_garb", row2="M4G2_A_row2_chain_garb",
                    lgp_row2="M4G2_A_lgp_row2_chain_garb")
    return dict(nochain=f"{g}_{b}_nochain", chain=f"{g}_{b}_chain", base=f"{g}_{b}_chain_garb",
                lgp=f"{g}_{b}_lgp_chain_garb", row=f"{g}_{b}_row_chain_garb", lgp_row=f"{g}_{b}_lgp_row_chain_garb",
                row2=f"{g}_{b}_row2_chain_garb", lgp_row2=f"{g}_{b}_lgp_row2_chain_garb")


def landings(path, pub):
    C = PL.load(path)
    P = {t["p"]: t for t in map(json.loads, open(pub))}
    out = {}
    for p, c in C.items():
        if c["land"]:
            ld = c["land"]
            hyb = p in P and ld["act"] != P[p]["final"][2] and ld["act"] not in [x[3] for x in P[p]["pubs"]]
            out[p] = dict(act=ld["act"], sil=ld["sil"], fin=ld["fin"], hyb=hyb)
    return out


def main():
    timing_rows, prev_rows, clamp_rows, replay = [], [], [], {}
    print("== Q1 timing (base cart, chained + silicon garbage)")
    for g, build in GAMES:
        cp, tp = PT.paths(g)
        t = tags(g, build)
        base = log(t["base"])
        if not base or not os.path.exists(tp):
            print(f"  {g} {build}: runs not ready"); continue
        Q = [json.loads(l) for l in open(cp)]
        rows = T.compare(Q, base, tp)
        S = [r for r in rows if r["same"]]
        a = [r["d_arrive"] for r in S]; ll = [r["d_last_lock"] for r in S]
        by = {}
        for r in S:
            k = r["state"] + ("+GARB" if r["garb"] else "")
            by.setdefault(k, []).append(r["d_arrive"])
        print(f"  {g} {build:5s} same-landing {len(S):3d}/{len(rows):3d} | OLD last-lock median {T.med(ll)[0]:5} "
              f"(p10 {T.pct(ll, .1)}, p90 {T.pct(ll, .9)}) | ARRIVAL median {T.med(a)[0]:+} |d|<=2 {sum(abs(x) <= 2 for x in a)} "
              f"({100 * sum(abs(x) <= 2 for x in a) / max(1, len(a)):.0f}%) | " +
              "  ".join(f"{k} {sum(abs(x) <= 2 for x in v)}/{len(v)}" for k, v in sorted(by.items())) +
              f" | STALE-predicted pills {sum(r['state'] == 'STALE' for r in rows)}/{len(rows)}")
        for r in rows:
            timing_rows.append(dict(game=g, build=build, p=r["p"], same=r["same"], trk_ok=r["trk_ok"], state=r["state"],
                                    garb=r["garb"], d_arrive=r["d_arrive"], d_last_lock=r["d_last_lock"], d_drop1=r["d_drop1"],
                                    sil_arrive=r["sil"]["arrive"], sil_last=r["sil"]["last"], mes_arrive=r["mes"]["arrive"],
                                    mes_lock=r["mes"]["lock"], log=t["base"]))
    print("\n== Q1 on 10/03 ANTIBODY_DIST (silicon c960dd49 + fw 1488e158): late-flip lane's UNCHAINED Mesen replays (c960dd49)")
    LF = "/home/struktured/projects/dr-mario-lateflip-wt/tmp/lateflip"; FV = "/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay"
    for g in ("G2", "G3", "G4"):
        if g == "G2":
            Q = T.attach_traj([json.loads(l) for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))],
                              [os.path.join(CF, "rawh_dist60_20261003_G2.jsonl")])
        else:
            Q = T.attach_traj([q for q in map(json.loads, open(os.path.join(CF, "cases_dist60_20261003.jsonl"))) if q["game"] == g],
                              [os.path.join(CF, f"rawh_dist60_20261003_{x}.jsonl") for x in ("G3", "G4a", "G4b")])
        rows = T.compare(Q, f"{LF}/{g}_off/lateflip_{g}_off.log", f"{FV}/timelines/pubtrace_{g}_fw1488e158.jsonl")
        S = [r for r in rows if r["same"]]; a = [r["d_arrive"] for r in S]; ll = [r["d_last_lock"] for r in S]
        print(f"  10/03 {g} same-landing {len(S):3d}/{len(rows):3d} | OLD last-lock median {T.med(ll)[0]:5} (p10 {T.pct(ll, .1)}, "
              f"p90 {T.pct(ll, .9)}) | ARRIVAL median {T.med(a)[0]:+} |d|<=2 {sum(abs(x) <= 2 for x in a)} "
              f"({100 * sum(abs(x) <= 2 for x in a) / max(1, len(a)):.0f}%) | STALE-predicted {sum(r['state'] == 'STALE' for r in rows)}, "
              f"GARB early (< -2 f) {sum(1 for r in S if r['garb'] and r['d_arrive'] < -2)}/{sum(1 for r in S if r['garb'])}")
        for r in rows:
            timing_rows.append(dict(game=f"1003{g}", build="ANTIBODY_DIST", p=r["p"], same=r["same"], trk_ok=r["trk_ok"],
                                    state=r["state"], garb=r["garb"], d_arrive=r["d_arrive"], d_last_lock=r["d_last_lock"],
                                    d_drop1=r["d_drop1"], log=f"{g}_off (lateflip-wt, unchained)"))
    print("\n== Q2 DISTGATE clamps (committed capsule parked at the clamped column; slam = DOWN before the lock) on the base runs")
    for g, build in GAMES:
        t = tags(g, build)
        base, row, lgprow = log(t["base"]), log(t["row2"]), log(t["lgp_row2"])
        if not base:
            continue
        R = CS.scan(base)
        Lrow = {r["p"]: r for r in CS.scan(row)} if row else {}
        Llr = {r["p"]: r for r in CS.scan(lgprow)} if lgprow else {}
        armed = sum(r["armed"] for r in R)
        cs = [r for r in R if r["ev"]]
        print(f"  {g} {build:5s} pills {len(R):3d} PROPH-armed {armed:2d} clamps {len(cs)} (slam {sum(r["ev"]["how"] == "slam" for r in cs)}; PROPH-armed "
              f"{sum(r['armed'] for r in cs)}, reachable in the current row {sum(r['ev']['reachable'] for r in cs)}, landing != "
              f"final {sum(r['land']['act'] != r['land']['fin'] for r in cs)}, Mesen landing == silicon {sum(str(r['land']['act']) == r['land']['sil'] for r in cs)})")
        for r in cs:
            e = r["ev"]
            rr = Lrow.get(r["p"]); lr = Llr.get(r["p"])
            print(f"     p{r['p']:3d} {'PROPH' if r['armed'] else 'plain'} {e['how']} clamp f{e['f']} x={e['x']} answer col {e['tgt']} "
                  f"frames-left {e['frames_left']} {'REACHABLE' if e['reachable'] else 'unreachable'} | base a{r['land']['act']} "
                  f"final a{r['land']['fin']} silicon a{r['land']['sil']} | DISTROW=2 a{rr['land']['act'] if rr else '?'} "
                  f"LGP+DISTROW=2 a{lr['land']['act'] if lr else '?'}")
            clamp_rows.append(dict(game=g, build=build, p=r["p"], proph_armed=r["armed"], **e, base=r["land"]["act"],
                                   final=r["land"]["fin"], silicon=r["land"]["sil"],
                                   distrow2=rr["land"]["act"] if rr else None, lgp_distrow2=lr["land"]["act"] if lr else None))
    print("\n== Q3 previous-target executions after a garbage window: silicon census + Mesen base vs DRLGPRESTART")
    for g, build in GAMES:
        rows, bug = PT.census(g, verbose=False)
        t = tags(g, build)
        base, lgp = log(t["base"]), log(t["lgp"])
        cp, tp = PT.paths(g)
        Lb = landings(base, tp) if base else {}
        Ll = landings(lgp, tp) if lgp else {}
        G = [r for r in rows if r["garb"]]
        rep = sum(1 for r in bug if r["p"] in Lb and Lb[r["p"]]["act"] == r["sil"])
        fixed = sum(1 for r in bug if r["p"] in Ll and r["final"] is not None and Ll[r["p"]]["act"] == r["final"])
        print(f"  {g} {build:5s} after-garbage pills {len(G):2d}: silicon previous-target {len(bug):2d} | Mesen base reproduces "
              f"{rep if base else '-'} | DRLGPRESTART lands the copro final {fixed if lgp else '-'}")
        for r in G:
            prev_rows.append(dict(r, build=build, prev_target=r in bug, mesen_base=Lb.get(r["p"], {}).get("act"),
                                  mesen_lgp=Ll.get(r["p"], {}).get("act")))
    print("\n== replay before/after (chained + silicon garbage): ==silicon / ==copro-final / hybrid")
    tot = {}
    for g, build in GAMES:
        t = tags(g, build); cp, tp = PT.paths(g)
        if not os.path.exists(tp):
            continue
        line = []
        for arm in ("chain", "base", "lgp", "row", "lgp_row", "row2", "lgp_row2"):
            p = log(t[arm])
            if not p:
                line.append(f"{arm} -"); continue
            L = landings(p, tp)
            n = len(L); sil = sum(str(v["act"]) == v["sil"] for v in L.values()); fin = sum(v["act"] == v["fin"] for v in L.values())
            hyb = sum(v["hyb"] for v in L.values())
            replay.setdefault(g, {})[arm] = dict(n=n, eq_silicon=sil, eq_final=fin, hybrid=hyb, log=t[arm])
            k = (build, arm); a = tot.setdefault(k, [0, 0, 0, 0]); a[0] += n; a[1] += sil; a[2] += fin; a[3] += hyb
            line.append(f"{arm} {sil}/{fin}/{hyb}")
        print(f"  {g} {build:5s} n={len(landings(log(t['base']), tp)) if log(t['base']) else '?':>3} | " + " | ".join(line))
    for (build, arm), a in sorted(tot.items()):
        print(f"  TOTAL {build:5s} {arm:8s} n={a[0]:4d} ==silicon {a[1]:4d} ==final {a[2]:4d} hybrid {a[3]:3d}")
    for name, rows in (("cases_timing_20261004.jsonl", timing_rows), ("cases_prevtarget_20261004.jsonl", prev_rows),
                       ("cases_clampslam_20261004.jsonl", clamp_rows)):
        with open(os.path.join(HERE, name), "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    json.dump({"replay": replay, "totals": {f"{b}/{a}": v for (b, a), v in tot.items()}},
              open(os.path.join(HERE, "replay_20261004.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
