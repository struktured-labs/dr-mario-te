"""silfid: report on PUBLOG capture #2 (bluemage 2026-10-07, cart d84436ff = DRP1HOLD + DRGPUMP + DRPUBLOG_PDW).
  publog2_report.py PILLS.json COSIM.jsonl SS_DIR  -> publog2_report_20261007.txt + publog2_diverged_20261007.jsonl
- the tall-endgame CELL (<= 20 viruses, max column height 14-16) actually reached vs the ~700 prediction;
- verdicts (EXACT / AMBIGUOUS / DIVERGED / NO_DONE) overall, in the CELL, and by regime;
- EARLY DONE + the post-DONE watch verdict (type-6 events, DONE re-read-0 flags, the watch window each early pill had);
- the pump's realised rate from the save-states' GP_N / GP_C ($6633 / $6635);
- the SAME-INPUT repeat test: identical uploads the cart re-issued (stall watchdog) while the game sat paused;
- the freeze at +49.5 min (decoded from the states);
- every DIVERGED / NO_DONE / EARLY pill banked with its exact upload."""
import sys, os, json, glob, re, collections, datetime, math
TAG = os.environ.get("TAG", "publog2")                     # publog3 = capture #3 (V11 rbf; run with FWDIR=fw_c51d2e21)
GATE_H = 12                                                # the commit gate: WDOG2 >= MINTHINK (12 hooks = 6 f)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/struktured/projects/dr-mario-publog2-wt/tools/silfid")
import publog as PL

pills = {p["seq"]: p for p in json.load(open(sys.argv[1]))}
R = [json.loads(l) for l in open(sys.argv[2]) if l.strip()]
SS = sorted(glob.glob(os.path.join(sys.argv[3], "*.ss")))
out = []
def P(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)

def bcd(b): return (b >> 4) * 10 + (b & 0x0F)
def maxh(hexb):
    b = bytes.fromhex(hexb); h = 0
    for c in range(8):
        for r in range(16):
            if b[r * 8 + c] != 0xFF:
                h = max(h, 16 - r); break
    return h
def hgt(h): return "<=8" if h <= 8 else "9-11" if h <= 11 else "12-13" if h <= 13 else "14-16"
def cell(v, h): return v <= 20 and h >= 14

# ---- the freeze: the first save-state from which the P2 board never changes again
boards, states = [], []
for f in SS:
    ram, prg = PL.load_prg(f)
    t = re.search(r"(\d{8}-\d{6})", os.path.basename(f)).group(1)
    raw = open(f, "rb").read(16)
    states.append(dict(t=datetime.datetime.strptime(t, "%Y%m%d-%H%M%S"), board=bytes(ram[0x500:0x580]), na=ram[0x397],
                       vir=bcd(ram[0x3A4]), atk1=ram[0x318], p2atk=ram[0x398], gs=prg[0x632],
                       gn=prg[0x633] | (prg[0x634] << 8), gc=prg[0x635] | (prg[0x636] << 8),
                       seq=prg[0x605] | (prg[0x606] << 8), inj=prg[0x14B], pc=raw[8] | (raw[9] << 8),
                       esc=prg[0x183] | (prg[0x184] << 8), swd=prg[0x190] | (prg[0x191] << 8)))
k = len(states) - 1
while k > 0 and states[k - 1]["board"] == states[-1]["board"]:
    k -= 1
frozen = states[k:] if len(states) - k >= 3 else []
t0, t1 = states[0]["t"], states[-1]["t"]
live_end = frozen[0]["t"] if frozen else t1
seq_freeze = frozen[0]["seq"] if frozen else 1 << 30
P(f"# {TAG}: {len(SS)} save-states, {(t1 - t0).total_seconds() / 60:.1f} min (fw dir {os.environ.get('FWDIR', 'fw_1488e158 default')})")
if frozen:
    f0 = frozen[0]
    P(f"FREEZE: from {f0['t']:%H:%M:%S} (+{(f0['t'] - t0).total_seconds() / 60:.1f} min) to the end ({len(frozen)} states): P2 board "
      f"frozen, P2 nextAction {f0['na']} at {f0['vir']} viruses, CPU PC in the idle wait loop "
      f"(${collections.Counter('%04X' % s['pc'] for s in frozen).most_common(2)}), frame counter running, the driver alive "
      f"(stall-watchdog re-uploads: seq {f0['seq']} -> {frozen[-1]['seq']}; pump still firing GP_N {f0['gn']} -> {frozen[-1]['gn']}).")
    pre = [s for s in states if s["t"] < f0["t"]]
    P(f"  DRNAVESC injected START at the onset (its inject count {pre[-1]['inj']} -> {f0['inj']}; in the last live state "
      f"its stuck counter was {pre[-1]['esc']} of 1200 hooks and the P2 pose had been static for {pre[-1]['swd']} hooks) -> "
      f"the game PAUSED; NAVESC "
      f"never re-fired (its counter keeps resetting: the P2 driver's held pad changes, max {max(s['esc'] for s in frozen)} "
      f"in the frozen states).")

# ---- the pump's realised rate
live = [s for s in states if s["t"] <= live_end]
dn = live[-1]["gn"] - live[0]["gn"]; dc = live[-1]["gc"] - live[0]["gc"]
mins = (live[-1]["t"] - live[0]["t"]).total_seconds() / 60
P(f"\nPUMP (GP_N $6633 / GP_C $6635, live part {mins:.1f} min): {dn} volleys fired = {dn / mins:.2f}/min "
  f"(design 2.86/play-min), {dc} cells delivered ({dc / max(dn, 1):.2f}/volley; merged stores are capped at 4)")
P(f"  P1's slot at the states: {dict(collections.Counter((s['atk1'], s['gs']) for s in live))} (($0318, pending store))")
P(f"  P2's own attack $0398 (P1 never receives it under DRP1HOLD) reached {max(s['p2atk'] for s in live)} within a round "
  f"(the ROM's max in a real game is 4; it resets at each round start)")

# ---- coverage
fin = [p for s, p in sorted(pills.items()) if p["final"] and s < seq_freeze]
cov = collections.Counter((("<=20" if bcd(p["viruses_bcd"]) <= 20 else ">20"), hgt(maxh(p["board"]))) for p in fin)
ncell = cov[("<=20", "14-16")]
P(f"\nCOVERAGE (live part, {len(fin)} final pills): CELL (<=20 viruses, height 14-16) = {ncell} "
  f"[prediction ~700/h, >= ~360/h; capture #1: 0 of 2250]")
for k2 in sorted(cov):
    P(f"   {k2[0]:>4s} / {k2[1]:>5s}: {cov[k2]}")
P(f"  prestart (garbage-window) searches: {sum(p['kind'] == 1 for p in fin)} (capture #1: 3)")

# ---- verdicts
V = ["EXACT", "AMBIGUOUS", "DIVERGED", "NO_DONE"]
RL = [r for r in R if r["seq"] < seq_freeze]
def tab(name, key):
    g = collections.defaultdict(collections.Counter)
    for r in RL:
        g[key(r)][r["verdict"]] += 1; g[key(r)]["_e"] += r.get("done_dt", 0) < -2
    P(f"\n## by {name}")
    for kk in sorted(g, key=str):
        c = g[kk]; n = sum(c[v] for v in V)
        P(f"  {str(kk):>16s} " + " ".join(f"{v} {c[v]:4d}" for v in V) + f"  n {n:4d}  EARLY-DONE {c['_e']}")
P(f"\nREPLAYED so far: {len(RL)} of {len(fin)} live final pills; overall {dict(collections.Counter(r['verdict'] for r in RL))}")
tab("CELL", lambda r: "CELL" if cell(r["viruses"], r["maxh"]) else "other")
tab("viruses x height", lambda r: f"{'<=20' if r['viruses'] <= 20 else '>20'}/{hgt(r['maxh'])}")
tab("kind", lambda r: "prestart" if r["kind"] == 1 else "normal")
tab("tuck", lambda r: "tuck" if r["tuck"] else "no tuck")
rs = collections.Counter(x["status"] for r in RL for x in r["reads"])
P(f"\nlive reads: {dict(rs)}")

# ---- EARLY DONE + the post-DONE watch
E = [r for r in RL if r.get("done_dt", 0) < -2]
nd = sum("done_dt" in r for r in RL)
pd_all = [(p["seq"], e) for p in fin for e in p["events"] if e["type"] == "pdone"]
rr_all = [(p["seq"], e) for p in fin for e in p["events"] if e.get("reread0")]
P(f"\n## EARLY DONE: {len(E)} of {nd} replayed pills with a DONE ({100.0 * len(E) / max(nd, 1):.1f}%); "
  f"post-DONE watch over ALL {len(fin)} live pills: type-6 events {len(pd_all)}, DONE re-read-0 flags {len(rr_all)}")
for r in sorted(E, key=lambda r: r["seq"]):
    p = pills[r["seq"]]; nx = pills.get(r["seq"] + 1)
    d = [e for e in p["events"] if e["type"] == "done"][0]
    win = ((nx["hookctr"] - p["hookctr"]) & 0xFFFF) - d["hooks"] if nx else None
    P(f"  seq {r['seq']:5d} vir {r['viruses']:2d} h {r['maxh']:2d} | silicon DONE {r['done']['t']:6.2f} f, Verilator "
      f"{r['cosim_done'][0]:6.2f} f, dt {r['done_dt']:7.2f} | watch window {win} hooks, type-6 "
      f"{sum(1 for e in p['events'] if e['type'] == 'pdone')}, re-read-0 {int(bool(d.get('reread0')))} | {r['verdict']}")

# ---- same-input repeats
ups = collections.defaultdict(list)
for s, p in sorted(pills.items()):
    ups[PL.upload_line(p)].append(p)
rep = [(u, L) for u, L in ups.items() if len(L) >= 3]
P(f"\n## SAME-INPUT REPEATS (identical upload re-issued by the cart; the copro searched the same input N times)")
for u, L in rep:
    dd = collections.Counter()
    seqs = collections.Counter()
    for p in L:
        d = [e for e in p["events"] if e["type"] == "done"]
        lv = tuple((e["hooks"], e["a"], e["b"]) for e in p["events"] if e["type"] == "live")
        dd[(d[0]["hooks"] if d else None, (d[0]["a"], d[0]["b"]) if d else None)] += 1
        seqs[lv] += 1
    P(f"  upload {u[:22]}... x{len(L)} (seq {L[0]['seq']}-{L[-1]['seq']}): DONE (hooks, final) {sorted(dd.items(), key=lambda x: -x[1])}")
    for lv, n in seqs.most_common():
        P(f"     live-read sequence x{n}: {list(lv)}")
    if os.environ.get("NO_VSIM") == "1":                   # (shared-box pause: skip the one Verilator run)
        continue
    import ss_cosim as SC                                  # one deterministic Verilator run of the same upload
    vp, vd, vt = SC.cosim_full(u)
    P(f"     Verilator: pubs {[(round(t, 2), c, o) for t, c, o in vp]} DONE {round(vd[0], 2)} f = {vd[0] * 2:.1f} hooks, "
      f"final ({vd[1]},{vd[2]})")
    P(f"     -> silicon == Verilator (DONE hook within 1 and the same live-read sequence) on "
      f"{sum(n for (h, fin_), n in dd.items() if h is not None and abs(h - vd[0] * 2) <= 1.0)} of {len(L)} identical runs")

# ---- landings: where silicon's capsule locked vs the copro final and the cart's own target (lock / tgt events)
GMAP = {0: 3, 1: 1, 2: 0, 3: 2}                            # copro orient4 -> game orientation (the driver's map)
def landings(recs):
    c = collections.Counter()
    for r in recs:
        if "done" not in r:
            continue
        lk = [e for e in r["events"] if e["type"] == "lock"]
        if not lk:
            continue
        u = r["upload"].split(); same = (int(u[0]) & 3) == (int(u[1]) & 3)
        eq = lambda a, b: a == b or (same and a[0] == b[0] and a[1] % 2 == b[1] % 2)
        got = (lk[0]["a"], lk[0]["b"] & 3); fin = (r["cosim_done"][1], GMAP[r["cosim_done"][2]])
        tg = [(e["a"], e["b"]) for e in r["events"] if e["type"] == "tgt" and (lk[0]["hooks"] == 0 or e["hooks"] <= lk[0]["hooks"])]
        dn = [e for e in r["events"] if e["type"] == "done"][0]
        before = 0 < lk[0]["hooks"] < dn["hooks"]
        if eq(got, fin):
            c["lands the copro final"] += 1
        elif tg and eq(got, tg[-1]):
            c["lands the cart's OWN target != final" + (" (locked before DONE)" if before else "")] += 1
        elif not tg:
            c["lands != final, no target change logged"] += 1
        else:
            c["lands neither the final nor its own target (execution)"] += 1
    return c
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)
for name, recs in (("CELL", [r for r in RL if cell(r["viruses"], r["maxh"])]), ("all replayed live pills", RL)):
    c = landings(recs); n = sum(c.values())
    miss = n - c["lands the copro final"]; lo, hi = wilson(miss, n)
    P(f"\n## LANDINGS on silicon ({name}, {n} pills with a lock): landing != copro final {miss} = {100.0 * miss / max(n, 1):.1f}% "
      f"(95% CI {100 * lo:.1f}-{100 * hi:.1f}%)")
    for k2, v in c.most_common():
        P(f"  {k2:62s} {v:4d} ({100.0 * v / max(n, 1):4.1f}%)")
# ---- the anytime-commit split on silicon: the logged answer at the gate (last live read <= 12 hooks) vs the final
gs = collections.Counter()
for r in RL:
    if not cell(r["viruses"], r["maxh"]) or "done" not in r:
        continue
    lk = [e for e in r["events"] if e["type"] == "lock"]
    if not lk:
        continue
    g = None
    for e in r["events"]:
        if e["type"] == "live" and e["hooks"] <= GATE_H:
            g = (e["a"], e["b"])
    fin = (r["cosim_done"][1], r["cosim_done"][2])
    one = landings([r]); ok = one["lands the copro final"] == 1
    gs[(g == fin, ok)] += 1
ng = gs[(True, True)] + gs[(True, False)]; nb = gs[(False, True)] + gs[(False, False)]; nt = ng + nb
P(f"\n## ANYTIME-COMMIT split (CELL, silicon): at-gate answer == final on {ng}/{nt} = {100.0 * ng / max(nt, 1):.1f}% "
  f"(95% CI {100 * wilson(ng, nt)[0]:.1f}-{100 * wilson(ng, nt)[1]:.1f}%)")
P(f"  at-gate == final -> landing != final {gs[(True, False)]}/{ng} = {100.0 * gs[(True, False)] / max(ng, 1):.1f}%")
P(f"  at-gate != final -> landing != final {gs[(False, False)]}/{nb} = {100.0 * gs[(False, False)] / max(nb, 1):.1f}%")

# ---- bank
bank = [r for r in RL if r["verdict"] in ("DIVERGED", "NO_DONE")] + [r for r in E if r["verdict"] not in ("DIVERGED", "NO_DONE")]
with open(os.path.join(HERE, f"{TAG}_diverged_20261007.jsonl"), "w") as f:
    for r in bank:
        f.write(json.dumps(dict(r, repro_class=r["verdict"] if r["verdict"] in ("DIVERGED", "NO_DONE") else "EARLY_DONE")) + "\n")
P(f"\n## DIVERGED / NO_DONE ({sum(r['verdict'] in ('DIVERGED', 'NO_DONE') for r in RL)}) + EARLY ({len(E)}) banked in {TAG}_diverged_20261007.jsonl")
for r in RL:
    if r["verdict"] in ("DIVERGED", "NO_DONE"):
        P(f"  seq {r['seq']} vir {r['viruses']} h {r['maxh']} kind {r['kind']} {r['verdict']}: reads "
          f"{[(x['t'], x['col'], x['o4'], x['status'][:6]) for x in r['reads']]} done {r.get('done')} | cosim {r['cosim_pubs']} "
          f"final {r['cosim_done']} tuck {r['cosim_tuck']}")
open(os.path.join(HERE, f"{TAG}_report_20261007.txt"), "w").write("\n".join(out) + "\n")
