"""STEER12 addendum A (S10): STALL CALIBRATION, sim vs couch (declared, descriptive; PREREG_STEER12.md).

  python steer12_stallcal.py couch DAY:GAME   per-decision act-stall flags of one couch AI game -> steer12/stallcal/
  python steer12_stallcal.py report           couch vs sim (FAIR pilot rows + execution arms) -> steer12/stallcal.txt

Stall = stuck_probe's board-level "act" stall, identical on both sides: a maximal run of >= 10 consecutive AI decisions
on which no remaining virus can be cleared by any legal placement of the ACTUAL current pill (stuck_probe.cleared_by).
v0 = viruses at its first decision; duration = time from the first stalled decision to the decision that ends it (a run
open at the game end: to the game end). Per game: stall-pills and longest run (s) with v0 <= 16 / 12 / 8; any stall
>= 30 s. Sim rows are TRUNCATED at the human's finish T_L (vs_race.evaluate at her measured M): a straddling run is cut
pro rata, runs starting after T_L dropped (a couch game ends when the human wins).
"""
import json, os, sys, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CF = os.path.join(HERE, "..", "couch_forensics")
OUT = os.path.join(HERE, "steer12", "stallcal")
KEEP = 10
VS = (16, 12, 8)
M_LULU, M_OWNER = 167.5, 239.5


def couch_game(spec):
    import import_pin; import_pin.pin()
    import stuck_probe as SP
    sys.path.insert(0, CF)
    day, g = spec.split(":")
    if day == "20261005":
        S = {r["game"]: r for r in json.load(open(os.path.join(CF, "summary_lulu_20261005.json")))["results"]}[g]
        Q = sorted([json.loads(l) for l in open(os.path.join(CF, f"cases_ai_{g}_lulu_20261005.jsonl"))], key=lambda q: q["p"])
        dec = [(q["t_spawn"], q["S"], q["cur"], q["virus_count"]) for q in Q]
        t0, t_end = S["t0_first_spawn"], S["t_end"]
    else:
        import fair_20261004 as FA
        FA.SCAN = os.path.expanduser("~/projects/dr_mario_rl/tmp/fair_20261004/scan")
        S = {x["game"]: x for x in json.load(open(os.path.join(CF, "summary_fair_20261004.json")))["games"]}[g]
        R = FA.load_raw(g, "p2", S["t_round"], S["t_end"])
        bank = sorted([json.loads(l) for l in open(os.path.join(CF, "cases_fair_20261004_ai_pills.jsonl"))
                       if json.loads(l)["game"] == g], key=lambda q: q["k"])
        assert len(bank) == len(R) and all(abs(b["t_spawn"] - r["t_spawn"]) < 1e-6 for b, r in zip(bank, R)), g
        dec = [(r["t_spawn"], r["S"], r["cur"], r["virus_count"]) for r in R]
        t0, t_end = S["t0_first_spawn"], S["t_end"]
    import analyze_g2 as A
    rows = []
    for t, Sx, cur, vc in dec:
        b = A.board_from_strings(Sx["color"], Sx["virus"], Sx["link"])
        nv = int(b.virus_count())
        ok = bool(SP.cleared_by(b, int(cur[0]), int(cur[1]))) if nv > 0 else True
        rows.append({"t": round(t - t0, 3), "nv": nv, "act": int(ok)})
    os.makedirs(OUT, exist_ok=True)
    json.dump({"day": day, "game": g, "t_end": round(t_end - t0, 3), "dec": rows},
              open(os.path.join(OUT, f"couch_{day}_{g}.json"), "w"))
    print(f"{spec}: {len(rows)} decisions, {sum(1 - r['act'] for r in rows)} without a clearing move")


def couch_runs(G):
    """stall runs [v0, len, t0, dur] from a per-decision act list"""
    runs, i, D = [], 0, G["dec"]
    while i < len(D):
        if D[i]["act"] == 0 and D[i]["nv"] > 0:
            j = i
            while j < len(D) and D[j]["act"] == 0:
                j += 1
            L = j - i
            if L >= KEEP:
                t_stop = D[j]["t"] if j < len(D) else G["t_end"]
                runs.append([D[i]["nv"], L, D[i]["t"], round(t_stop - D[i]["t"], 2)])
            i = j
        else:
            i += 1
    return runs


def sim_runs(r, T=None):
    """bep act runs [v0, len, t0, dur]; truncated at T (pro rata) if given"""
    out = []
    for b in r["stuck"]["bep"]:
        if b[0] != 1 or b[2] < KEEP:
            continue
        v0, L, t0, dur = b[3], b[2], b[6], b[7]
        if T is not None:
            if t0 >= T:
                continue
            if t0 + dur > T and dur > 0:
                L = L * (T - t0) / dur; dur = T - t0
                if L < KEEP:
                    continue
        out.append([v0, L, t0, dur])
    return out


def metrics(runs):
    m = {}
    for v in VS:
        sel = [x for x in runs if 0 <= x[0] <= v]
        m[f"pills{v}"] = float(sum(x[1] for x in sel))
        m[f"long{v}"] = float(max([x[3] for x in sel] or [0.0]))
    m["ge30"] = float(any(x[3] >= 30 for x in runs))
    return m


def summarize(ms, lab, out, boot=True):
    keys = [f"pills{v}" for v in VS] + [f"long{v}" for v in VS] + ["ge30"]
    rng = np.random.default_rng(1)
    parts = []
    for k in keys:
        a = np.array([m[k] for m in ms])
        if boot and len(a) > 1:
            bs = [a[rng.integers(0, len(a), len(a))].mean() for _ in range(2000)]
            ci = f" [{np.percentile(bs, 2.5):.1f}, {np.percentile(bs, 97.5):.1f}]"
        else:
            ci = ""
        val = 100 * a.mean() if k == "ge30" else a.mean()
        if k == "ge30" and ci:
            ci = f" [{100 * np.percentile(bs, 2.5):.0f}, {100 * np.percentile(bs, 97.5):.0f}]"
        parts.append(f"{k} {val:.1f}{'%' if k == 'ge30' else ''}{ci}")
    out(f"  {lab} (n={len(ms)}): " + "; ".join(parts))


def report(fair_only=False):
    from vs_race import evaluate
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    C = {}
    for f in sorted(glob.glob(os.path.join(OUT, "couch_*.json"))):
        G = json.load(open(f)); C[(G["day"], G["game"])] = G
    out(f"STALL CALIBRATION (PREREG_STEER12 addendum A): couch games {len(C)}; act stall >= {KEEP} pills; "
        f"pills / longest s at v0 <= 16 / 12 / 8; ge30 = share of games with any stall >= 30 s")
    out("\nCOUCH per game (v0, pills, start s, duration s):")
    cm = {"20261005": [], "20261004": []}
    for (d, g), G in sorted(C.items()):
        R = couch_runs(G); cm[d].append(metrics(R))
        out(f"  {d[4:]} {g}: {len(G['dec'])} decisions, t_end {G['t_end']:.0f} s, runs {[(x[0], x[1], round(x[2]), x[3]) for x in R]}")
    out("\nCOUCH summary (game bootstrap):")
    summarize(cm["20261005"], "10/05 vs dr. lulu", out)
    summarize(cm["20261004"], "10/04 vs owner", out)
    summarize(cm["20261005"] + cm["20261004"], "both days", out)

    import analyze_steer10 as A10
    LU = A10.LULU10B; SIX = list(range(39134, 40333, 2))

    def load(pat, lab, seeds):
        d = {}
        for f in glob.glob(pat):
            for l in open(f):
                r = json.loads(l)
                if r.get("arm") == lab:
                    d[r["seed"]] = r
        return [d[s] for s in seeds if s in d]
    sims = [("FAIR LULU race (pilot)", load("steer11/pilot/lulu10b_c11_s10_base_*.jsonl", "s10_base~steer", LU), M_LULU),
            ("FAIR owner race (pilot)", load("steer11/pilot/rc10_c11_s10_base_*.jsonl", "s10_base~steer", SIX), M_OWNER)]
    for a in (() if fair_only else ("ex_perfect", "ex_q02", "ex_q03", "ex_q05")):
        sims.append((f"{a} LULU race", load(f"steer12/main/lulu12_{a}_*.jsonl", f"{a}~steer", LU), M_LULU))
    out("\nSIM (couch11), truncated at the human's finish T_L | untruncated:")
    for lab, rows, M in sims:
        if not rows:
            out(f"  {lab}: no rows"); continue
        tr = [metrics(sim_runs(r, evaluate(r, M, .15, 2.65)[1])) for r in rows]
        un = [metrics(sim_runs(r)) for r in rows]
        summarize(tr, f"{lab} @M{M} TRUNCATED", out)
        summarize(un, f"{lab} untruncated", out, boot=False)
    # garbage attribution
    out("\nGARBAGE (cells received per minute):")
    P = [json.loads(l) for l in open("steer11/clockcal_pills.jsonl")]
    for d in ("20261005", "20261004"):
        gs = sorted({p["game"] for p in P if p["day"] == d})
        rates = []
        for g in gs:
            Pg = [p for p in P if p["day"] == d and p["game"] == g]
            rates.append(60 * sum(p.get("gsize", 0) for p in Pg if p.get("vol")) / Pg[0]["dur_s"])
        out(f"  couch {d[4:]}: median {np.median(rates):.1f}, per game {[round(x, 1) for x in rates]}")
    for lab, rows, M in sims[:2]:
        rr = np.array([60 * r["tiles_recv"] / max(r["t_end"], 1) for r in rows])
        out(f"  sim {lab}: median {np.median(rr):.1f}")
        q = np.percentile(rr, [33.3, 66.7])
        for name, sel in (("bottom tercile", rr <= q[0]), ("top tercile", rr >= q[1])):
            sub = [metrics(sim_runs(r, evaluate(r, M, .15, 2.65)[1])) for r, s in zip(rows, sel) if s]
            summarize(sub, f"    {name} of received garbage", out, boot=False)
    open(os.path.join(HERE, "steer12", "stallcal_fair.txt" if fair_only else "stallcal.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    os.chdir(HERE)
    if sys.argv[1] == "couch":
        couch_game(sys.argv[2])
    elif sys.argv[1] == "report":
        report()
    elif sys.argv[1] == "faironly":                    # couch + FAIR pilot rows only (no STEER12 main row is read)
        report(fair_only=True)
    elif sys.argv[1] == "couchcheck":                  # couch side only (no sim / main rows read) + banked cross-check
        for f in sorted(glob.glob(os.path.join(OUT, "couch_2026100*.json"))):
            G = json.load(open(f)); R = couch_runs(G)
            bank = os.path.join(CF, f"stall_{G['game']}_lulu_20261005.json")
            b = sum(x["pills"] for x in json.load(open(bank))["stalls"]) if G["day"] == "20261005" and os.path.exists(bank) else None
            print(f"{G['day'][4:]} {G['game']}: act-stall pills {sum(x[1] for x in R):4d} (banked couch stall json: {b}) "
                  f"runs {[(x[0], x[1], round(x[2]), x[3]) for x in R]}")
