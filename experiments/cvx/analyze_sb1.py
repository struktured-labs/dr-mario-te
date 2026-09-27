"""STALL BREAKER screen (PREREG_STALLBREAK1.md): each sb_* arm vs fw540, paired seeds.
PRIMARY: gate (b) owner-model tap-out paired diff (advance iff < 0 with CI excluding 0).
SECONDARY: VS-race win vs a 177-s human, lam 6, delta 2.65 (must not drop > 2 pp).
Usage: python analyze_sb1.py [--base fw540]
"""
import sys, os, json, glob, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs_race import evaluate

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="fw540")
a = ap.parse_args()
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ARMS = ("sb_chain0", "sb_spawn", "sb_virus", "sb_all", "sb_all_early")


def gb(arm):
    d = {}
    for f in glob.glob(f"gateb/{arm}_*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            # glob sb_all_* also matches sb_all_early_*: key on the row's own arm label
            if r.get("arm") == arm and r.get("model") == "owner" and r.get("level", 11) == 11: d[r["seed"]] = r
    return d


def vr(arm, dirs):
    d = {}
    for dr in dirs:
        for f in glob.glob(f"{dr}/{arm}_l6.0_*.jsonl"):
            for l in open(f):
                r = json.loads(l)
                if r.get("arm") == arm and r.get("level", 11) == 11: d[r["seed"]] = r
    return d


def boot(xs, n=4000, seed=1):
    rng = random.Random(seed); k = len(xs)
    o = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return o[int(.025 * n)], o[int(.975 * n)]


def win(r): return evaluate(r, 177.0, 0.15, 2.65)[0] == "win_race"


bg, bv = gb(a.base), vr(a.base, ("vsrace2", "vsrace3"))
print(f"base {a.base}: gate-b n={len(bg)} tap-out {100*sum(r['topout'] for r in bg.values())/max(1,len(bg)):.2f}% "
      f"stall {100*sum(r['stall'] for r in bg.values())/max(1,len(bg)):.2f}% | VS n={len(bv)} win {100*sum(map(win, bv.values()))/max(1,len(bv)):.1f}%\n")
print(f"{'arm':13s} {'n_gb':>5} {'tap%':>6} {'d tap-out vs base [95% CI]':>28} {'stall%':>6} {'d win':>7} | {'n_vr':>4} {'VS win%':>7} {'d VS [95% CI]':>22}  verdict")
for arm in ARMS:
    g, v = gb(arm), vr(arm, ("vsrace4",))
    if not g: print(f"{arm:13s} (no rows yet)"); continue
    s = sorted(set(g) & set(bg))
    dt = [g[x]["topout"] - bg[x]["topout"] for x in s]; lo, hi = boot(dt)
    dw = [g[x]["won"] - bg[x]["won"] for x in s]
    tap = 100 * sum(g[x]["topout"] for x in s) / len(s); stl = 100 * sum(g[x]["stall"] for x in s) / len(s)
    line = f"{arm:13s} {len(s):5d} {tap:5.2f}% {100*sum(dt)/len(s):+6.2f}pp [{100*lo:+5.2f},{100*hi:+5.2f}] {stl:5.2f}% {100*sum(dw)/len(s):+6.2f}pp"
    vs_ok = None
    sv = sorted(set(v) & set(bv))
    if sv:
        dv = [float(win(v[x])) - float(win(bv[x])) for x in sv]; vlo, vhi = boot(dv)
        vs_ok = 100 * sum(dv) / len(sv) >= -2.0
        line += f" | {len(sv):4d} {100*sum(win(v[x]) for x in sv)/len(sv):6.1f}% {100*sum(dv)/len(sv):+5.1f}pp [{100*vlo:+5.1f},{100*vhi:+5.1f}]"
    else:
        line += " |    - (VS pending)"
    primary = hi < 0
    complete = len(s) >= 600 and len(sv) >= 300
    verdict = ("ADVANCE" if primary and vs_ok else "FAIL-primary" if not primary else "FAIL-VS" if vs_ok is False else "pending-VS")
    print(line + f"  {verdict}{'' if complete else ' (partial)'}")
