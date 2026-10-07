"""silfid: PUBLOG capture #2 coverage prediction from pump_sim.py rows.
  pump_an.py ROWS_GLOB...   -> pump_an_20261007.txt (+ .json)
CELL = a P2 decision at <= 20 viruses on a board of max column height 14-16 (where 50 of the 77 residual couch misses
sit). Per arm: games, pills, how, CELL pills per game-hour (sim time on the couch11 clock + ROUND_OH s per round).
Calibration anchors (the sim must reproduce what silicon showed before its predictions count):
  A  capture #1 (CvC, native P1, no garbage): sim lam 0 L11, each game cut at a capture round length (in pills: P1 won
     every round). Capture: 2250 pills, <=20 viruses 419, of which height 12-13: 21, height 14-16: 0.
  B  the 10/05 couch (dr. lulu, 9 games): sim lam 2.84 L11, each game cut at a couch game's duration (s).
Option (b) (a stronger P1 = a copro bot): FAIR's own send rate as the volley rate, each game cut at an independent FAIR
lam-0 game's clear time (the faster bot ends the round)."""
import sys, os, json, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CAP = "/home/struktured/projects/dr_mario_rl/tmp/silfid/publog_out/pills.json"
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
ROUND_OH = 8.0          # s between rounds on capture #1: 59.8 min wall - 2251 pills x 1.43 s, over 45 rounds

rows = []
for g in sys.argv[1:]:
    for f in sorted(glob.glob(g)):
        rows += [json.loads(l) for l in open(f) if l.strip()]
out = []
def P(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)

def cell(v, h): return v <= 20 and h >= 14

def bcd(b): return (b >> 4) * 10 + (b & 0x0F)

# ---- capture #1 round lengths (pills) and the couch game durations (s) + couch cell counts
cap = json.load(open(CAP))
def maxh(board_hex):
    b = bytes.fromhex(board_hex); h = 0
    for c in range(8):
        for r in range(16):
            if b[r * 8 + c] != 0xFF:
                h = max(h, 16 - r); break
    return h
lens, cur = [], []
for p in cap:
    v = bcd(p["viruses_bcd"])
    if cur and v > cur[-1] + 2:
        lens.append(len(cur)); cur = []
    cur.append(v)
lens.append(len(cur))
couch = []
for f in sorted(glob.glob(os.path.join(CF, "cases_ai_m?g?_lulu_20261005.jsonl"))):
    Q = sorted((json.loads(l) for l in open(f)), key=lambda q: q["t_spawn"])
    couch.append(dict(dur=Q[-1]["t_spawn"] - Q[0]["t_spawn"], n=len(Q), le20=sum(q["virus_count"] <= 20 for q in Q),
                      cell=sum(cell(q["virus_count"], q["maxh"]) for q in Q)))
cn = sum(c["n"] for c in couch); cc = sum(c["cell"] for c in couch); cl = sum(c["le20"] for c in couch)
cdur = sum(c["dur"] for c in couch)
P(f"# capture #2 coverage prediction (FAIR sim, couch11 clock, lulu202610b sizes); {len(rows)} sim games")
P(f"capture #1: {len(cap)} pills in {len(lens)} rounds (P1 won all), round length median {sorted(lens)[len(lens) // 2]} pills")
P(f"couch 10/05: {len(couch)} games, {cn} pills in {cdur / 60:.1f} min; <=20 viruses {cl} ({100 * cl / cn:.1f}%), "
  f"CELL {cc} ({100 * cc / cn:.1f}% of pills, {cc / cdur * 3600:.0f}/h of play)")

arms = collections.defaultdict(list)
for r in rows:
    arms[(r["level"], r["lam"], r.get("q", 0.0))].append(r)

def tally(trs):
    n = sum(len(t) for t in trs)
    le = sum(1 for t in trs for (_, v, h) in t if v <= 20)
    c1213 = sum(1 for t in trs for (_, v, h) in t if v <= 20 and 12 <= h <= 13)
    c = sum(1 for t in trs for (_, v, h) in t if cell(v, h))
    return n, le, c1213, c

P("\n## anchors (per execution-miss dose q: q 0 = sim FAIR's near-perfect execution)")
qs = sorted({k[2] for k in arms})
for q in qs:
    a0 = arms.get((11, 0.0, q), [])
    if a0:
        trs = [r["trace"][:lens[i % len(lens)]] for i, r in enumerate(a0)]
        n, le, c1213, c = tally(trs)
        P(f"A q={q:g} capture #1 vs sim lam 0 cut at capture round lengths: sim {n} pills, <=20 {le} ({100 * le / n:.1f}%), "
          f"<=20/h12-13 {c1213} ({100 * c1213 / n:.2f}%), CELL {c} ({100 * c / n:.2f}%)   |   capture 2250, 419 (18.6%), "
          f"21 (0.93%), 0 (0%)")
    a1 = arms.get((11, 2.84, q), [])
    if a1:
        trs = [[x for x in r["trace"] if x[0] <= couch[i % len(couch)]["dur"]] for i, r in enumerate(a1)]
        n, le, c1213, c = tally(trs)
        P(f"B q={q:g} couch vs sim lam 2.84 cut at couch game durations: sim {n} pills, <=20 {le} ({100 * le / n:.1f}%), "
          f"CELL {c} ({100 * c / n:.1f}%)   |   couch {cn}, {cl} ({100 * cl / cn:.1f}%), {cc} ({100 * cc / cn:.1f}%)")

P("\n## arms (P1 held: each game runs to P2's own end)")
P(f"{'arm':>20s} {'games':>5s} {'pills':>6s} {'clear':>5s} {'top':>4s} {'cap':>4s} {'min/game':>8s} {'<=20%':>6s} {'CELL%':>6s} "
  f"{'CELL/h':>7s} {'CELL/game':>9s}")
res = {}
for (lv, lam, q), rs in sorted(arms.items()):
    n, le, c1213, c = tally([r["trace"] for r in rs])
    how = collections.Counter(r["how"] for r in rs)
    secs = sum(r["t_end"] for r in rs) + ROUND_OH * len(rs)
    name = f"L{lv} lam{lam:g} q{q:g}"
    res[name] = dict(level=lv, lam=lam, q=q, games=len(rs), pills=n, le20=le, cell=c, how=dict(how),
                     cell_per_h=c / secs * 3600 if secs else 0, min_per_game=secs / 60 / len(rs))
    P(f"{name:>20s} {len(rs):5d} {n:6d} {how['clear']:5d} {how['topout']:4d} {how['cap'] + how['nomove']:4d} "
      f"{secs / 60 / len(rs):8.2f} {100 * le / n:6.1f} {100 * c / n:6.1f} {c / secs * 3600:7.0f} {c / len(rs):9.1f}")

for q in qs:
    a0 = arms.get((11, 0.0, q), [])
    if not a0:
        continue
    sends = sum(len(r["sent"]) for r in a0); tsec = sum(r["t_end"] for r in a0)
    lam_b = sends / tsec * 60
    clears = sorted(r["t_end"] for r in a0 if r["how"] == "clear")
    P(f"\n(b) q={q:g} a copro-bot P1: FAIR's own send rate at lam 0 = {lam_b:.2f} volleys/min; a FAIR game clears in median "
      f"{clears[len(clears) // 2] if clears else float('nan'):.0f} s.")
    near = min((k for k in arms if k[0] == 11 and k[2] == q), key=lambda k: abs(k[1] - lam_b), default=None)
    if near is not None and clears:
        rs = arms[near]
        trs = [[x for x in r["trace"] if x[0] <= clears[i % len(clears)]] for i, r in enumerate(rs)]
        n, le, c1213, c = tally(trs)
        secs = sum(min(r["t_end"], clears[i % len(clears)]) for i, r in enumerate(rs)) + ROUND_OH * len(rs)
        P(f"    nearest simulated rate lam {near[1]:g}, cut at FAIR clear times: CELL {c} of {n} pills "
          f"({100 * c / max(n, 1):.1f}%) = {c / secs * 3600:.0f}/h")
        res[f"b_copro_p1_q{q:g}"] = dict(lam_b=lam_b, near=near[1], cell=c, pills=n, cell_per_h=c / secs * 3600)
open(os.path.join(HERE, "pump_an_20261007.txt"), "w").write("\n".join(out) + "\n")
json.dump(res, open(os.path.join(HERE, "pump_an_20261007.json"), "w"), indent=1)
