"""For each banked <=4-virus decision: can the target's D be reduced / the target finished within TWO pills
(cur then nxt, straight drops, garbage ignored)? And which single-pill colour pairs could reduce D at the root
(the 'colour wait' test). Usage: python twoply_dist60_20261003.py CASES.jsonl GAME P_LO P_HI"""
import json, sys
import analyze_g2 as A
from endgame_dist60_20261003 import after, pose_of, d_of

R = [json.loads(l) for l in open(sys.argv[1])]
g, lo, hi = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
PAIRS = ((1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3))
GL = "RYB"
for q in R:
    if q["game"] != g or not (lo <= q["p"] <= hi) or q.get("D_before") is None:
        continue
    S = q["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
    tr, tc, _ = q["target"]; tgt = tr * 8 + tc; D0 = q["D_before"]
    cur, nxt = tuple(q["cur"]), tuple(q["nxt"])
    red1 = []
    for pr in PAIRS:
        ok = False
        for a in range(32):
            bb, _ = after(b, pose_of(a, pr, b))
            if bb is not None and (not bb.is_virus[tr, tc] or d_of(bb, tgt) < D0):
                ok = True; break
        if ok:
            red1.append(GL[pr[0] - 1] + GL[pr[1] - 1])
    two_red = two_fin = False
    for a in range(32):
        b1, _ = after(b, pose_of(a, cur, b))
        if b1 is None:
            continue
        if not b1.is_virus[tr, tc]:
            two_red = two_fin = True; break
        for a2 in range(32):
            b2, _ = after(b1, pose_of(a2, nxt, b1))
            if b2 is None:
                continue
            if not b2.is_virus[tr, tc]:
                two_red = two_fin = True; break
            if d_of(b2, tgt) < D0:
                two_red = True
        if two_fin:
            break
    print(f"{g} p{q['p']} cur {GL[cur[0]-1]}{GL[cur[1]-1]} nxt {GL[nxt[0]-1]}{GL[nxt[1]-1]} D{D0} "
          f"root-D-reducing pairs: {red1 or '-'}  2-pill(cur,nxt): reduce={two_red} finish={two_fin}")
