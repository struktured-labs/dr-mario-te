"""silfid: report on the DRPUBLOG bluemage capture (2026-10-07).
  publog_report.py COSIM.jsonl [SINGLE.json] [CHAIN.jsonl]  -> publog_report_20261007.txt + publog_diverged_20261007.jsonl
Verdict counts overall and by regime (viruses left, max column height, prestart, tuck), every DIVERGED / NO_DONE pill
banked as a repro case, DONE-time agreement (the EARLY-DONE class: silicon's DONE > 2 f before Verilator's on the same
upload), the chained-co-sim check of the early pills, and the tie-back to the 77 unexplained 10/05 couch misses."""
import json, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import load

R = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
single = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else None
chain = [json.loads(l) for l in open(sys.argv[3]) if l.strip()] if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else []
out = []
def P(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)

EARLY = -2.0                       # silicon DONE read more than 2 f before Verilator's DONE (reads are 0.5 f apart)
def early(r): return "done_dt" in r and r["done_dt"] < EARLY
def late(r): return "done_dt" in r and r["done_dt"] > 2.0
def vir(r): return "<=20" if r["viruses"] <= 20 else ">20"
def hgt(r): return "<=8" if r["maxh"] <= 8 else "9-11" if r["maxh"] <= 11 else "12-13" if r["maxh"] <= 13 else "14-16"
def cdb(r): d = r["cosim_done"][0]; return "<30" if d < 30 else "30-39" if d < 40 else "40-49" if d < 50 else "50+"

V = ["EXACT", "AMBIGUOUS", "DIVERGED", "NO_DONE"]
def tab(name, key, extra=True):
    groups = collections.defaultdict(collections.Counter)
    for r in R:
        groups[key(r)][r["verdict"]] += 1
        groups[key(r)]["_early"] += early(r)
    P(f"\n## by {name}")
    P(f"{'group':>14s} " + " ".join(f"{v:>9s}" for v in V) + "    n   EARLY-DONE")
    for g in sorted(groups, key=str):
        c = groups[g]; n = sum(c[v] for v in V)
        P(f"{str(g):>14s} " + " ".join(f"{c[v]:9d}" for v in V) + f" {n:5d}   {c['_early']:4d} ({100.0 * c['_early'] / n:4.1f}%)")

P(f"# DRPUBLOG bluemage capture: {len(R)} final pills replayed on Verilator (vsim_pub2, fw 1488e158)")
c = collections.Counter(r["verdict"] for r in R)
P("overall:", {v: c[v] for v in V})
tab("viruses left", vir)
tab("max column height", hgt)
tab("viruses x height", lambda r: f"{vir(r)}/{hgt(r)}")
tab("search kind", lambda r: "prestart" if r["kind"] == 1 else "normal")
tab("tuck (co-sim or silicon DONE)", lambda r: "tuck" if r["tuck"] else "no tuck")
tab("co-sim publications", lambda r: "1" if len(r["cosim_pubs"]) <= 1 else "2-3" if len(r["cosim_pubs"]) <= 3 else "4+")
tab("co-sim DONE time (f)", cdb)

rs = collections.Counter(x["status"] for r in R for x in r["reads"])
P("\nlive reads:", dict(rs), " total", sum(rs.values()))
dts = collections.Counter(round(r["done_dt"]) for r in R if "done_dt" in r)
P("DONE read time - co-sim DONE (frames, rounded):", sorted(dts.items()))
later = [r for r in R if any(x["status"] == "MATCH" for x in r["reads"][1:])]
P("pills where silicon showed a LATER running best (2nd+ read MATCH):", len(later))

# ---- EARLY DONE ---------------------------------------------------------------------------------------------------
E = [r for r in R if early(r)]
nd = sum("done_dt" in r for r in R)
P(f"\n## EARLY DONE: {len(E)} of {nd} pills with a DONE ({100.0 * len(E) / max(nd, 1):.1f}%); late (> +2 f): "
  f"{sum(late(r) for r in R)}")
P("  every early pill: seq vir h | silicon DONE f, Verilator DONE f, dt | co-sim pubs after silicon's DONE | lock frame vs DONE")
exp_div = 0
for r in sorted(E, key=lambda r: r["seq"]):
    t = r["done"]["t"]
    after = [p for p in r["cosim_pubs"] if p[0] > t]
    exp_div += bool(after)
    lk = [e for e in r["events"] if e["type"] == "lock"]
    P(f"  {r['seq']:5d} {r['viruses']:3d} {r['maxh']:3d} | {t:6.2f} {r['cosim_done'][0]:6.2f} {r['done_dt']:7.2f} | "
      f"{after} | lock f {lk[0]['frames'] if lk else None} {r['verdict']}")
P(f"  early pills whose co-sim published an improvement AFTER silicon's DONE (=> silicon keeps the older answer): {exp_div}")
if E:
    sd = sorted(r["done"]["t"] for r in E)
    P(f"  silicon DONE time of the early pills: min {sd[0]} median {sd[len(sd) // 2]} max {sd[-1]}")

if chain:
    P("\n## chained co-sim (one copro process, silicon's GO spacing, 3 lead pills) of the early pills")
    CH = {(x["target"], x["p"]): x for x in chain}
    RR = {r["seq"]: r for r in R}
    agree = 0
    for (t, p), x in sorted(CH.items()):
        if t != p:
            continue
        r = RR.get(t)
        if r is None:
            continue
        same = abs(x["done_f"] - r["cosim_done"][0]) <= 1.0
        agree += same
        P(f"  target {t}: chained DONE {x['done_f']:6.2f}  fresh {r['cosim_done'][0]:6.2f}  silicon {r['done']['t'] if r.get('done') else None}"
          f"  chained final {x['final'][:2]}  pubs {[(round(a, 2), b, c) for a, b, c, *_ in x['pubs']]}")
    P(f"  chained DONE == fresh DONE (+-1 f) on {agree} targets")

div = [r for r in R if r["verdict"] in ("DIVERGED", "NO_DONE")]
with open(os.path.join(HERE, "publog_diverged_20261007.jsonl"), "w") as f:
    for r in div + [r for r in E if r not in div]:
        f.write(json.dumps(dict(r, repro_class=r["verdict"] if r in div else "EARLY_DONE")) + "\n")
P(f"\n## DIVERGED / NO_DONE pills ({len(div)}) + EARLY-DONE pills ({len(E)}), banked in publog_diverged_20261007.jsonl")
for r in div:
    P(f"seq {r['seq']} kind {r['kind']} vir {r['viruses']} h {r['maxh']} tuck {r['tuck']} {r['verdict']}: "
      f"reads {[(x['t'], x['col'], x['o4'], x['status'][:6]) for x in r['reads']]} missed {r['missed']} "
      f"done {r.get('done')} | cosim {r['cosim_pubs']} final {r['cosim_done']} tuck {r['cosim_tuck']}  [{r['src']}]")

if single is not None:
    sc = collections.Counter(x["status"] for x in single)
    P("\n## single-sample cross-check (ss_cosim.py on every state):", dict(sc))

# ---- tie-back: the 77 residual couch misses -------------------------------------------------------------------------
summ = json.load(open(os.path.join(HERE, "summary_silfid_20261006.json")))
res = [tuple(x) for x in summ["residual"]["pills"]]
MI = load.misses()
PT = {g: load.pubtrace(g) for g in load.GAMES}
tuck_res = 0
for g, p in res:
    pt = PT[g].get(p)
    if pt and pt.get("tuck") and pt["tuck"][0] != 255:
        tuck_res += 1
P("\n## the 77 residual couch misses, by the same regimes")
P("viruses <=20:", sum(MI[k]["virus_count"] <= 20 for k in res), " >20:", sum(MI[k]["virus_count"] > 20 for k in res))
mh = collections.Counter(hgt(dict(maxh=MI[k]["maxh"])) for k in res)
P("max height:", dict(mh))
cov = collections.Counter(f"{vir(dict(viruses=MI[k]['virus_count']))}/{hgt(dict(maxh=MI[k]['maxh']))}" for k in res)
capn = collections.Counter(f"{vir(r)}/{hgt(r)}" for r in R)
P("residual cell -> residual misses / capture pills replayed in that cell:")
for k in sorted(cov):
    P(f"   {k:>12s}: {cov[k]:3d} / {capn.get(k, 0)}")
P("after a garbage window:", sum(bool(MI[k]["after_garbage_window"]) for k in res), " tuck final (seed-0 co-sim):", tuck_res)

# Expected couch EARLIER-PUB misses if silicon's early DONE happened on the couch at the capture's rate:
# a couch pill whose copro final is published at t_f becomes an earlier-answer landing when silicon's DONE < t_f.
# P(DONE < t_f) is taken from the capture, conditional on the Verilator DONE bucket (co-sim DONE +-5 f).
withd = [r for r in R if "done_dt" in r]
def p_before(D, tf):
    pool = [r for r in withd if abs(r["cosim_done"][0] - D) <= 5.0] or withd
    return sum(r["done"]["t"] < tf for r in pool) / len(pool)
expect = 0.0; n_late_final = 0
for g in load.GAMES:
    for p, pt in PT[g].items():
        pubs = pt.get("pubs") or []
        if len(pubs) < 2:
            continue
        tf = pubs[-1][0]
        n_late_final += tf >= 2.0
        expect += p_before(pt["done_f"], tf)
obs = [(g, p) for g, p in res if MI[(g, p)]["label"] == "EARLIER-PUB"]
obs_tf = sorted(round(PT[g][p]["pubs"][-1][0], 1) for g, p in obs if PT[g].get(p))
P(f"\nEARLY-DONE tie-back: over all {sum(len(v) for v in PT.values())} couch pills, the capture's DONE-time distribution "
  f"predicts {expect:.1f} couch landings on an EARLIER answer (pills with >=2 pubs whose final arrives after silicon's DONE)."
  f"\n  observed residual EARLIER-PUB: {len(obs)}; their copro-final publish times (f): {obs_tf}"
  f"\n  of which final published >= the earliest early DONE seen ({min((r['done']['t'] for r in E), default=None)} f): "
  f"{sum(t >= min((r['done']['t'] for r in E), default=1e9) for t in obs_tf)}")
open(os.path.join(HERE, "publog_report_20261007.txt"), "w").write("\n".join(out) + "\n")
