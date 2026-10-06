"""STEER11 identity gate: the patched race loops (vs_race.pill_frames / garbage_drop_timed, CLOCK None) + steer11_run must
reproduce the banked FAIR / A16 rows byte-identically on every non-stamp key.
  lulu10b s10_base / s10_A16 -> steer10/lulu10b_<arm>_*.jsonl ; rc10 s10_base -> steer8/rc10_fD_bdepD_*.jsonl ;
  gb10 s10_base -> steer8/gb10_fD_bdepD_*.jsonl
POSITIVE CONTROL (must FAIL): the same comparison of the lulu10b s10_base gate rows against the banked s10_A16 rows
(a different arm on the same seeds) -- a checker that cannot see a difference there is dead (R96).
Exit 0 iff every cell is identical AND the control differs."""
import json, glob, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
STAMP = ("arm", "rig")


def load(pat, lab):
    d = {}
    for f in glob.glob(pat):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == lab:
                d[r["seed"]] = r
    return d


def cmp(G, B):
    both = [s for s in G if s in B]
    same, diffs = 0, []
    for s in both:
        bad = [k for k in B[s] if k not in STAMP and G[s].get(k) != B[s].get(k)]
        same += not bad
        if bad:
            diffs.append((s, bad))
    return same, len(both), diffs


ok = True
cells = (("lulu10b s10_base", "steer11/gate/lulu10b_s10_base_legacy.jsonl", "s10_base~steer", "steer10/lulu10b_s10_base_*.jsonl", "s10_base~steer"),
         ("lulu10b s10_A16", "steer11/gate/lulu10b_s10_A16_legacy.jsonl", "s10_A16~steer", "steer10/lulu10b_s10_A16_*.jsonl", "s10_A16~steer"),
         ("rc10 s10_base", "steer11/gate/rc10_s10_base_legacy.jsonl", "s10_base~steer", "steer8/rc10_fD_bdepD_*.jsonl", "fD_bdepD~steer"),
         ("gb10 s10_base", "steer11/gate/gb10_s10_base.jsonl", "s10_base@owner202610", "steer8/gb10_fD_bdepD_*.jsonl", "fD_bdepD@owner202610"))
for name, gp, gl, bp, bl in cells:
    G, B = load(gp, gl), load(bp, bl)
    same, n, diffs = cmp(G, B)
    ok &= n > 0 and same == n
    print(f"IDENTITY {name}: {same}/{n} rows identical on every non-stamp key" + (f"  DIFFS {diffs[:3]}" if diffs else ""))
    if G:
        r = G[min(G)]
        print(f"   e.g. seed {r['seed']}: how {r['how']} t_end {r.get('t_end', r.get('elapsed_s'))} pills {r['pills']} "
              f"clock-keys {[k for k in ('clock', 'nrel', 'garb_s') if k in r]}")
G = load("steer11/gate/lulu10b_s10_base_legacy.jsonl", "s10_base~steer")
B = {s: dict(r, arm="s10_base~steer") for s, r in load("steer10/lulu10b_s10_A16_*.jsonl", "s10_A16~steer").items()}
same, n, diffs = cmp(G, B)
ctl = n > 0 and same < n
ok &= ctl
print(f"POSITIVE CONTROL (gate s10_base vs banked s10_A16, must differ): {same}/{n} identical -> "
      f"{'DIFFERS (checker alive)' if ctl else 'NO DIFFERENCE: CHECKER DEAD'}")
print("IDENTITY GATE", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
