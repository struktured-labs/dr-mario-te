"""silfid: the cart-landing vs copro-final rate straight from a PUBLOG capture's log (no co-sim needed).
  landing_log.py PILLS.json [FREEZE_SEQ]
The copro final = silicon's own DONE answer (the log's type-2 event; the replays show it equals Verilator's final), the
landing = the logged lock pose, the at-gate answer = the last live read at <= 12 hooks (the MINTHINK commit gate).
Tall-endgame CELL = <= 20 viruses on max column height 14-16 at GO. Prints rate + Wilson 95% CI + the breakdown."""
import sys, json, math, collections
sys.path.insert(0, "/home/struktured/projects/dr-mario-publog-wt/tools/silfid")
from publog_run import bcd, maxh
G = {0: 3, 1: 1, 2: 0, 3: 2}
P = [p for p in json.load(open(sys.argv[1])) if p["final"]]
freeze = int(sys.argv[2]) if len(sys.argv) > 2 else 1 << 30
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    q = k / n; d = 1 + z * z / n; c = q + z * z / (2 * n); h = z * math.sqrt(q * (1 - q) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)
c = collections.Counter(); gs = collections.Counter(); skip = collections.Counter()
for p in P:
    if p["seq"] >= freeze or not (bcd(p["viruses_bcd"]) <= 20 and maxh(p["board"]) >= 14):
        continue
    ev = p["events"]
    dn = [e for e in ev if e["type"] == "done"]; lk = [e for e in ev if e["type"] == "lock"]
    if not dn:
        skip["no DONE (search torn down: aborted / prestart second volley)"] += 1; continue
    if not lk:
        skip["no lock logged"] += 1; continue
    same = (p["upload4"][0] & 3) == (p["upload4"][1] & 3)
    eq = lambda a, b: a == b or (same and a[0] == b[0] and a[1] % 2 == b[1] % 2)
    fin = (dn[0]["a"], dn[0]["b"]); want = (fin[0], G[fin[1]]); got = (lk[0]["a"], lk[0]["b"] & 3)
    tg = [(e["a"], e["b"]) for e in ev if e["type"] == "tgt" and (lk[0]["hooks"] == 0 or e["hooks"] <= lk[0]["hooks"])]
    before = 0 < lk[0]["hooks"] < dn[0]["hooks"]
    if eq(got, want): k = "lands the copro final"
    elif tg and eq(got, tg[-1]): k = "lands the cart's OWN target != final" + (" (locked before DONE)" if before else "")
    elif not tg: k = "lands != final, no target change logged"
    else: k = "lands neither the final nor its own target"
    c[k] += 1
    g = None
    for e in ev:
        if e["type"] == "live" and e["hooks"] <= 12: g = (e["a"], e["b"])
    gs[(g == fin, k == "lands the copro final")] += 1
n = sum(c.values()); miss = n - c["lands the copro final"]; lo, hi = wilson(miss, n)
print(f"CELL pills judged: {n} (skipped: {dict(skip)})")
print(f"  landing != copro final: {miss}/{n} = {100 * miss / n:.1f}%  (95% CI {100 * lo:.1f}-{100 * hi:.1f}%)")
for k, v in c.most_common():
    print(f"    {k:58s} {v:4d} ({100 * v / n:4.1f}%)")
ng = gs[(True, True)] + gs[(True, False)]; nb = gs[(False, True)] + gs[(False, False)]
print(f"  at-gate answer == final: {ng}/{ng + nb} = {100 * ng / (ng + nb):.1f}%  (95% CI {100 * wilson(ng, ng + nb)[0]:.1f}-"
      f"{100 * wilson(ng, ng + nb)[1]:.1f}%)")
print(f"    gate == final -> landing != final {gs[(True, False)]}/{ng} = {100 * gs[(True, False)] / max(ng, 1):.1f}%")
print(f"    gate != final -> landing != final {gs[(False, False)]}/{nb} = {100 * gs[(False, False)] / max(nb, 1):.1f}%")
