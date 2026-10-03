"""Per-game endgame comparison table (root viruses <= 4 -> end), 10/03 ANTIBODY_DIST vs prior ANTIBODY / TAP couch.
Usage: python compare_dist60_20261003.py CASES.jsonl [...]"""
import json, sys
from summary_dist60_20261003 import per_virus

R = []
for p in sys.argv[1:]:
    R += [json.loads(l) for l in open(p)]
games = []
for q in R:
    if q["game"] not in games:
        games.append(q["game"])
print("| game | 4->0 s / pills | last virus s / pills | last 2 s / pills | no D-reducing move (sealed / colour) | "
      "finish avail, not taken | pill-only clears | cascades | volleys sent (cells) | garbage recv volleys (cells) | outcome |")
for g in games:
    rows = per_virus(R, g, 4)
    L = [q for q in R if q["game"] == g and q.get("D_before") is not None]
    secs = sum(r.get("secs", 0) for r in rows); pills = sum(r["pills"] for r in rows)
    last = rows[-1]; l2 = rows[-2]
    sealed = sum(1 for q in L if q["n_d_reducing"] == 0 and q["D_before"] == 16)
    colour = sum(1 for q in L if q["n_d_reducing"] == 0 and q["D_before"] < 16)
    fin_nt = sum(1 for q in L if q["n_finishing"] > 0 and not q["actual_clears_target"])
    fin_av = sum(1 for q in L if q["n_finishing"] > 0)
    po = sum(r.get("pill_only_clears", 0) for r in rows); ca = sum(r.get("cascades", 0) for r in rows)
    sv = sum(r.get("sent_volleys", 0) for r in rows); sc = sum(r.get("sent_cells", 0) for r in rows)
    rv = sum(r.get("recv_volleys", 0) for r in rows); rc = sum(r.get("recv_cells", 0) for r in rows)
    end_nv = min(q["virus_count"] for q in R if q["game"] == g)
    print(f"| {g} | {secs:.1f} / {pills} | {last.get('secs', 0):.1f} / {last['pills']} | "
          f"{last.get('secs', 0) + l2.get('secs', 0):.1f} / {last['pills'] + l2['pills']} | {sealed + colour} ({sealed} / {colour}) | "
          f"{fin_nt} of {fin_av} | {po} | {ca} | {sv} ({sc}) | {rv} ({rc}) | min vc {end_nv} |")
