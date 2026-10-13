"""TAPOUT analysis (PREREG_TAPOUT sec. 3-4).
  python analyze_tapout.py screen   -> tapout/screen_select.txt (+ the selected arms, one per line, tapout/selected.txt)
  python analyze_tapout.py main     -> tapout/analysis.txt
"""
import sys, json, glob
import numpy as np
sys.path.insert(0, "."); import import_pin; import_pin.pin()
from vs_race import evaluate
M, SIG, DEL = 167.5, 0.15, 2.65


def rows(pattern, arm):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r["arm"] == arm + "~steer":
                out[r["seed"]] = r
    return out


def oc(r):
    o = evaluate(r, M, SIG, DEL)[0]
    return dict(loss=int(o != "win_race"), kill=int(o == "loss_kill"), slow=int(o in ("loss_race", "loss_cap")),
                top=int(r["how"] == "topout"))


def boot(d, B=10000, alpha=0.05, seed=1):
    d = np.asarray(d, float); n = len(d); rng = np.random.default_rng(seed)
    m = d[rng.integers(0, n, (B, n))].mean(1)
    return 100 * d.mean(), 100 * np.quantile(m, alpha / 2), 100 * np.quantile(m, 1 - alpha / 2)


def screen():
    base = rows("tapout/screen/T_a16_u8_*.jsonl", "T_a16_u8")
    out = [f"SCREEN (600 seeds 47000.., A16 + u8), n base {len(base)}"]
    bt = sum(oc(r)["top"] for r in base.values())
    res = []
    for a in ("D1", "D2", "D3", "D4", "D5"):
        R = rows(f"tapout/screen/T_{a}_u8_*.jsonl", f"T_{a}_u8")
        S = sorted(set(R) & set(base))
        L = sum(oc(R[s])["loss"] for s in S); K = sum(oc(R[s])["kill"] for s in S); T = sum(oc(R[s])["top"] for s in S)
        bl = sum(oc(base[s])["loss"] for s in S); bk = sum(oc(base[s])["kill"] for s in S); btt = sum(oc(base[s])["top"] for s in S)
        mm = sum(R[s]["knob"].get("meta_pen_mismatch", 0) for s in S); dec = sum(R[s]["knob"]["dec"] for s in S)
        ch = sum(R[s]["rule"]["changed"] for s in S)
        out.append(f"  {a}: n {len(S)} loss {L} (base {bl}) kill {K} (base {bk}) topout {T} (base {btt}) changed {ch}/{dec} "
                   f"meta_pen_mismatch {mm}")
        res.append((L, K, a, T < btt))
    q = [x for x in sorted(res) if x[3]][:3]
    sel = [x[2] for x in q] or ["D2"]
    out.append(f"SELECTED (rule: best total loss among arms with fewer tap-outs than base; up to 3): {sel}")
    open("tapout/screen_select.txt", "w").write("\n".join(out) + "\n"); open("tapout/selected.txt", "w").write("\n".join(sel) + "\n")
    print("\n".join(out))


def main():
    sel = open("tapout/selected.txt").read().split(); K = len(sel)
    base = rows("steer14/main/lulu14_S14_d16_u8_*.jsonl", "S14_d16_u8")
    out = [f"MAIN (5,100 seeds 44300.., paired vs banked S14_d16_u8; Bonferroni K={K})"]
    for a in sel:
        R = rows(f"tapout/main/T_{a}_u8_*.jsonl", f"T_{a}_u8")
        S = sorted(set(R) & set(base)); n = len(S)
        out.append(f"  {a} {json.dumps(__import__('tapout_run').DANGER[a][1])}: n {n}")
        for key in ("kill", "loss", "slow", "top"):
            d = [oc(R[s])[key] - oc(base[s])[key] for s in S]
            a_ = 100 * np.mean([oc(R[s])[key] for s in S]); b_ = 100 * np.mean([oc(base[s])[key] for s in S])
            m, lo, hi = boot(d); _, blo, bhi = boot(d, alpha=0.05 / K)
            out.append(f"    {key:5s} arm {a_:5.2f}% base {b_:5.2f}%  diff {m:+.2f} [{lo:+.2f}, {hi:+.2f}] Bonf [{blo:+.2f}, {bhi:+.2f}]")
        mm = sum(R[s]["knob"].get("meta_pen_mismatch", 0) for s in S); dec = sum(R[s]["knob"]["dec"] for s in S)
        out.append(f"    activity: changed {sum(R[s]['rule']['changed'] for s in S)}/{dec}, meta_pen_mismatch {mm} ({100*mm/max(dec,1):.2f}%),"
                   f" pills/game {np.mean([R[s]['pills'] for s in S]):.1f} (base {np.mean([base[s]['pills'] for s in S]):.1f})")
    for a in sel:
        R = rows(f"tapout/main/T_{a}_k32_*.jsonl", f"T_{a}_k32")
        if not R:
            continue
        B = rows("steer14/main/lulu14_S14_d4_k32_*.jsonl", "S14_d4_k32"); S = sorted(set(R) & set(B))
        out.append(f"  Q2 (descriptive) {a} at k32 vs S14_d4_k32: n {len(S)}")
        for key in ("kill", "loss"):
            d = [oc(R[s])[key] - oc(B[s])[key] for s in S]; m, lo, hi = boot(d)
            out.append(f"    {key:5s} diff {m:+.2f} [{lo:+.2f}, {hi:+.2f}]")
    open("tapout/analysis.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))


if __name__ == "__main__":
    {"screen": screen, "main": main}[sys.argv[1]]()
