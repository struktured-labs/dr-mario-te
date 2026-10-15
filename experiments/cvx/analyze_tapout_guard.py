"""TAPOUT addendum A: owner-race + gate-b guards for D4 / D1 vs A16 + u8 (and at today's gate k32, descriptive)."""
import json, glob, sys
import numpy as np
sys.path.insert(0, "."); import import_pin; import_pin.pin()
from vs_race import evaluate
from analyze_tapout import boot
M_OWNER, SIG, DEL = 239.5, 0.15, 2.65
SEEDS = [44300 + 2 * i for i in range(5100)]


def rows(pats, label):
    out = {}
    for p in pats:
        for f in glob.glob(p):
            for l in open(f):
                r = json.loads(l)
                if r["arm"] == label:
                    out[r["seed"]] = r
    return out


def rc_oc(r):
    o = evaluate(r, M_OWNER, SIG, DEL)[0]
    return dict(kill=int(o == "loss_kill"), loss=int(o != "win_race"), slow=int(o in ("loss_race", "loss_cap")))


def gb_oc(r):
    return dict(loss=int(not r["won"]), tapout=int(r["topout"]), stall=int(r["stall"]))


def block(out, title, A, B, fn, keys, K):
    S = sorted(set(A) & set(B)); out.append(f"  {title}: n {len(S)}")
    res = {}
    for k in keys:
        d = [fn(A[s])[k] - fn(B[s])[k] for s in S]
        a_ = 100 * np.mean([fn(A[s])[k] for s in S]); b_ = 100 * np.mean([fn(B[s])[k] for s in S])
        m, lo, hi = boot(d); _, blo, bhi = boot(d, alpha=0.05 / K)
        res[k] = (m, blo, bhi)
        out.append(f"    {k:6s} arm {a_:5.2f}% base {b_:5.2f}%  diff {m:+.2f} [{lo:+.2f}, {hi:+.2f}] Bonf(K={K}) [{blo:+.2f}, {bhi:+.2f}]")
    return res


out = ["GUARDS (PREREG_TAPOUT addendum A)"]
rcB = rows(["steer14/main/rc14_S14_d16_u8_*.jsonl"], "S14_d16_u8~steer") | rows(["tapout/guard/rc_T_a16_u8_*.jsonl"], "T_a16_u8~steer")
gbB = rows(["steer14/main/gb14_S14_d16_u8_*.jsonl"], "S14_d16_u8@owner202610") | rows(["tapout/guard/gb_T_a16_u8_*.jsonl"], "T_a16_u8@owner202610")
harm = {}
for a in ("D4", "D1"):
    out.append(f"== {a} vs A16 + u8")
    r1 = block(out, "owner race (M 239.5)", rows([f"tapout/guard/rc_T_{a}_u8_*.jsonl"], f"T_{a}_u8~steer"), rcB, rc_oc, ("kill", "loss", "slow"), 2)
    r2 = block(out, "gate b vs owner202610", rows([f"tapout/guard/gb_T_{a}_u8_*.jsonl"], f"T_{a}_u8@owner202610"), gbB, gb_oc, ("loss", "tapout", "stall"), 2)
    harm[a] = r1["loss"][1] > 0 or r2["tapout"][1] > 0
    out.append(f"    HARM (owner-race loss Bonf lower > 0 or gate-b tap-out Bonf lower > 0): {'YES' if harm[a] else 'no'}")
rcK = rows(["steer14/main/rc14_S14_d4_k32_*.jsonl"], "S14_d4_k32~steer"); gbK = rows(["steer14/main/gb14_S14_d4_k32_*.jsonl"], "S14_d4_k32@owner202610")
for a in ("D4", "D1"):
    out.append(f"== {a} at today's gate k32 vs S14_d4_k32 (descriptive)")
    block(out, "owner race", rows([f"tapout/guard/rc_T_{a}_k32_*.jsonl"], f"T_{a}_k32~steer"), rcK, rc_oc, ("kill", "loss", "slow"), 1)
    block(out, "gate b", rows([f"tapout/guard/gb_T_{a}_k32_*.jsonl"], f"T_{a}_k32@owner202610"), gbK, gb_oc, ("loss", "tapout", "stall"), 1)
open("tapout/guard_analysis.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
