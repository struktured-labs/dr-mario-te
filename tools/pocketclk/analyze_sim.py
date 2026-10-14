#!/usr/bin/env python3
"""pocketclk lane: paired LULU race contrast, Pocket-clock arm (steer14_pocket.py rows) vs the banked MiSTer-clock rows of
the same arm and seeds (dr-mario-h16-wt experiments/cvx/steer14/main), using analyze_steer14's win/loss rule and bootstrap.
Also checks the K = 1 identity control row-for-row. Usage: analyze_sim.py"""
import glob, json, os, sys
CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
O = "/home/struktured/projects/dr_mario_rl/tmp/pocketclk/steer14"
os.chdir(CVX); sys.path.insert(0, CVX)
import analyze_steer14 as A
from analyze_steer6r import boot, fmt, churn
def rows(pat):
    d = {}
    for f in glob.glob(pat):
        for l in open(f):
            r = json.loads(l); d[r["seed"]] = r
    return d
M = A.M_LULU; win = lambda r: A.win(r, M)
# identity control
ctl, bank = rows(f"{O}/ctl_K1_S14_d4_k32_44300.jsonl"), rows(f"{CVX}/steer14/main/lulu14_S14_d4_k32_44300.jsonl")
keys = ("how", "t_end", "pills", "vleft", "tiles_sent", "tiles_recv", "sent")
same = sum(all(ctl[s][k] == bank[s][k] for k in keys) for s in ctl if s in bank)
print(f"identity control (K = 1, S14_d4_k32 seeds 44300..44398): {same}/{len(ctl)} rows identical to the banked MiSTer rows")
for arm in ("S14_d4_k32", "S14_d16_k32", "S14_d4_u8"):
    P = rows(f"{O}/pk_{arm}_*.jsonl"); B = rows(f"{CVX}/steer14/main/lulu14_{arm}_*.jsonl")
    S = sorted(s for s in P if s in B)
    if not S: continue
    lp = [1 - win(P[s]) for s in S]; lb = [1 - win(B[s]) for s in S]
    d = boot([a - b for a, b in zip(lp, lb)]); c = churn([B[s] for s in S], [P[s] for s in S], lambda r: not win(r))
    typ = lambda D: {t: sum(A.ltype(D[s], M) == t for s in S) for t in ("slow", "kill")}
    kp = [P[s]["knob"] for s in S]; kb = [B[s]["knob"] for s in S]
    gl = lambda K: sum(k["golock_f"] for k in K) / max(1, sum(k.get("pills_n", 0) or 0 for k in K) or 1)
    print(f"{arm}: n {len(S)}  LULU loss MiSTer {100*sum(lb)/len(S):.2f}% -> Pocket {100*sum(lp)/len(S):.2f}%  "
          f"d {fmt(d)} pp  (loss types MiSTer {typ(B)} / Pocket {typ(P)}; losses new {c[1]} / fixed {c[0]})")
    # vs today's MiSTer couch (S14_d4_k32 banked) for the retune arm
    if arm != "S14_d4_k32":
        B0 = rows(f"{CVX}/steer14/main/lulu14_S14_d4_k32_*.jsonl"); S0 = [s for s in S if s in B0]
        d0 = boot([(1 - win(P[s])) - (1 - win(B0[s])) for s in S0])
        print(f"   ... Pocket {arm} vs MiSTer S14_d4_k32 (today's couch config): d {fmt(d0)} pp (n {len(S0)})")
    tp = sum(k["golock_f"] for k in kp) / sum(P[s]["pills"] for s in S); tb = sum(k["golock_f"] for k in kb) / sum(B[s]["pills"] for s in S)
    ep = sum(k["end_golock_f"] for k in kp) / max(1, sum(k["end_pills"] for k in kp)); eb = sum(k["end_golock_f"] for k in kb) / max(1, sum(k["end_pills"] for k in kb))
    fp = sum(k["end_landed_final"] for k in kp) / max(1, sum(k["end_pills"] for k in kp)); fb = sum(k["end_landed_final"] for k in kb) / max(1, sum(k["end_pills"] for k in kb))
    print(f"   GO->lock per pill MiSTer {tb:.1f} f -> Pocket {tp:.1f} f; endgame {eb:.1f} -> {ep:.1f} f; endgame landed-on-final {100*fb:.1f}% -> {100*fp:.1f}%")
