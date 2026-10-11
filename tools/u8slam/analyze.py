#!/usr/bin/env python3
"""u8slam lane: paired per-pill analysis of chained + garbage Mesen replays (execfid_probe.lua traces) of slam-gate carts.

Arms are carts on the SAME case files (a16mt lane: 12 games, 1,197 pills, V11 and V11 + A16 timelines). Per pill and
arm, from the per-frame trace:
  lock   LAND f (frames since the spawn)                   land   action = var * 8 + x of the last falling frame
  go     the frame of this pill's GO hook (f - k + 1 at the last frame the shim is searching); None or < 1 = the
         search was started before the spawn (DRPRESTART in the garbage window)
  down   first frame DOWN is held ($F8 & 4)
  why    what opened DOWN at that frame: done (ARMED2 = 0) | open / end / cross (the stability rule, K_OPEN / K_END /
         K_CROSS branch) | other (not aligned + orient-locked: the stuck drop) | none (never held)
  sa     SLAM_ARM while this pill's search runs (at the GO frame; the first traced frame if the search predates it)
  class  final (landing == the copro's final) | pub (a non-final published answer) | hybrid (neither); frozen =
         DRLATEGUARD refused a late answer on this pill
  cycle  frames from this case's spawn to the next case's spawn (lock + clears + settle; the whole pill cycle)
Strata are pre-treatment: virus count of the case board (< 10 = the K_END branch), tuck = the copro's final carries a
tuck descriptor, post-garbage = the previous case delivered a garbage volley (this pill's search is the DRPRESTART one).
Paired contrast arm - base: lock frame (all pills landed in both arms, and same-landing pills), DOWN start, with a
t interval over pills and a cluster bootstrap over the 12 games.

Usage: analyze.py RUNS FWTAG BASE,ARM[,ARM...] [--pills OUT.jsonl] [--list N] [--ctl BANKED_RUNS]"""
import json, math, os, random, re, statistics, sys

T = "/home/struktured/projects/dr_mario_rl/tmp"
X = "/home/struktured/projects/dr-mario-h16-wt/experiments/execfid"
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
GAMES = "m2g1 m2g2 m2g3 m4g1 m4g2 G2 m1g1 m1g2 m3g1 m3g2 m3g3 m5g2".split()
KV = re.compile(r"(\w+)=([^ |]+)")
LOWY, VCEND = 8, 10
INTENT = 0x80 | 0x40 | 0x02 | 0x01                        # A B LEFT RIGHT: the tapped buttons (DOWN is a hold)


def timeline(g, fw):
    if fw == "a16":
        return [f"{T}/a16mt/timelines/pubtrace_{g}_a16.jsonl"]
    if g in ("m2g1", "m2g2", "m2g3", "m4g1"):
        return [f"{X}/timelines/pubtrace_{g}_fair_20261004.jsonl"]
    if g == "m4g2":
        return [f"{CF}/pubtrace_m4g2_fair_20261004.jsonl"]
    if g == "G2":                                          # the banked V1 a1ef31c8 timeline (V11 == V1 on G2), or the
        return [f"{T}/fair_v1_replay/timelines/pubtrace_G2_fwa1ef31c8_fwlane.jsonl",   # a16mt lane's own V11 co-sim
                f"{T}/a16mt/timelines/pubtrace_G2_v11.jsonl"]
    return [f"{T}/a16mt/timelines/pubtrace_{g}_v11.jsonl"]


def cases(g, fw):
    """the case file the replay ran: p -> (vc, fin action, final (col, o), done_f, garb volley on this case)"""
    out = {}
    for ln in open(f"{T}/a16mt/cases/{g}_{fw}_chain_garb.lua"):
        m = re.match(r"\s*\{p=(\d+),", ln)
        if not m:
            continue
        q = re.search(r"vc=(\d+), actual=(-?\d+), sim=(-?\d+), fin=(\d+), sched=\{pubs=\{(.*?)\}, done_f=([\d.]+), "
                      r"final=\{(\d+),(\d+)\}, tuck=\{(\d+),(\d+)\}", ln)
        out[int(m.group(1))] = dict(vc=int(q.group(1)), fin=int(q.group(4)), done_f=float(q.group(6)),
                                    final=(int(q.group(7)), int(q.group(8))), tuck=(int(q.group(9)), int(q.group(10))),
                                    npub=len(re.findall(r"\{[\d.]+,\d+,\d+\}", q.group(5))), garb="garb={" in ln)
    return out


def load_timeline(g, fw, C):
    """the publish timeline whose finals equal the case file's on every pill (asserted): p -> record"""
    for path in timeline(g, fw):
        P = {t["p"]: t for t in map(json.loads, open(path))}
        if set(P) == set(C) and all(P[p]["final"][2] == C[p]["fin"] and tuple(P[p]["final"][:2]) == C[p]["final"]
                                    and tuple(P[p]["tuck"]) == C[p]["tuck"] for p in C):
            return P, path
    raise SystemExit(f"no timeline matches the case file of {g} {fw}")


def parse(log):
    P, summ = {}, None
    for l in open(log, errors="replace"):
        tag = l.split(" ", 1)[0]
        if tag == "SUMMARY":
            summ = l.strip(); continue
        if tag not in ("T", "INJECT", "LAND", "GARB"):
            continue
        m = re.match(r"\w+ p(\d+) ", l)
        if not m:
            continue
        d = P.setdefault(int(m.group(1)), {"T": []})
        kv = dict(KV.findall(l))
        if tag == "T":
            if "land" in d:
                continue
            d["T"].append(dict(f=int(kv["f"]), y=int(kv["y"]), x=int(kv["x"]), rot=int(kv["rot"]), rd2=int(kv["rd2"]),
                               arm=int(kv["arm"]), pend=int(kv["pend"]), eff=int(kv["eff"]), lock=int(kv["lg"].split(",")[1]),
                               pad=int(kv["pad"], 16), held=int(kv["held"], 16), k=int(kv["k"]), sa=int(kv["sa"]),
                               st=int(kv["st"]), tgt=kv["tgt"]))
        elif tag == "INJECT":
            d["vc"] = int(kv["vc"]); d["inj"] = int(re.search(r" at f=(\d+)", l).group(1))
        elif tag == "LAND":
            d["land"] = dict(f=int(kv["f"]), x=int(kv["x"]), y=int(kv["y"]), act=int(kv["action"]))
        elif tag == "GARB":
            d["garb"] = True
    return P, summ


def pill_row(d, c, tl):
    Tr = d["T"]
    go = None
    for t in Tr:
        if t["k"] >= 0:
            go = t["f"] - t["k"] + 1
    down = next((t for t in Tr if t["held"] & 4), None)
    why = "none"
    if down is not None:
        why = ("other" if not (down["rd2"] == 1 and down["x"] == down["eff"]) else "done" if down["arm"] == 0 else
               "cross" if down["y"] < LOWY else "end" if c["vc"] < VCEND else "open")
    sa_t = next((t for t in Tr if go is not None and t["f"] >= max(go, 1)), Tr[0])
    act = d["land"]["act"]
    pubs = [x[3] for x in tl["pubs"]]
    cls = "final" if act == c["fin"] else "pub" if act in pubs else "hybrid"
    commit = next((t["f"] for t in Tr if t["rd2"] == 1 and t["pend"] == 0), None)
    done = next((t["f"] for t in Tr if go is not None and t["f"] >= max(go, 1) and t["arm"] == 0), None)
    # press cadence on the real cart: tapped-button presses (any of A/B/L/R) on consecutive frames would be > 1 press / 2 f
    fast = sum(1 for a, b in zip(Tr, Tr[1:]) if a["pad"] & INTENT and b["pad"] & INTENT)
    late = 0
    if commit is not None:
        late = sum(1 for a, b in zip(Tr, Tr[1:]) if b["f"] > commit and a["tgt"] != b["tgt"])
    return dict(lock=d["land"]["f"], act=act, y=d["land"]["y"], go=go, down=down["f"] if down else None, why=why,
                sa=sa_t["sa"], sa0=Tr[0]["sa"], cls=cls, frozen=any(t["lock"] == 1 for t in Tr), commit=commit, done=done,
                fast=fast, late=late, presses=sum(1 for t in Tr if t["pad"] & INTENT))


def ci_t(v):
    n = len(v)
    if n < 2:
        return (float("nan"),) * 3
    m = statistics.mean(v); se = statistics.stdev(v) / math.sqrt(n)
    return m, m - 1.96 * se, m + 1.96 * se


def ci_cluster(rows, key, B=4000, seed=20261011):
    """bootstrap over games (12 clusters): rows = [(game, value)]"""
    by = {}
    for g, v in rows:
        by.setdefault(g, []).append(v)
    gs = sorted(by)
    if len(gs) < 3:
        return float("nan"), float("nan")
    rng = random.Random(seed); out = []
    for _ in range(B):
        s = n = 0
        for g in (rng.choice(gs) for _ in gs):
            s += sum(by[g]); n += len(by[g])
        out.append(s / n)
    out.sort()
    return out[int(0.025 * B)], out[int(0.975 * B) - 1]


def main():
    args = sys.argv[1:]
    pills_out = None; nlist = 60
    if "--pills" in args:
        i = args.index("--pills"); pills_out = args[i + 1]; del args[i:i + 2]
    if "--list" in args:
        i = args.index("--list"); nlist = int(args[i + 1]); del args[i:i + 2]
    ctl = None
    if "--ctl" in args:
        i = args.index("--ctl"); ctl = args[i + 1]; del args[i:i + 2]
    runs, fw, arms = args[0], args[1], args[2].split(",")
    base = arms[0]
    if ctl:                                                 # harness control: the base cart's banked run of the same tag
        nd = np_ = 0; miss = []
        for g in GAMES:
            tag = f"{g}_{base}_{fw}_chain_garb"
            a_, b_ = (os.path.join(r, tag, f"lateflip_{tag}.log") for r in (runs, ctl))
            if not (os.path.exists(a_) and os.path.exists(b_)):
                miss.append(g); continue
            A, B = parse(a_)[0], parse(b_)[0]
            for p_ in set(A) | set(B):
                la, lb = A.get(p_, {}).get("land"), B.get(p_, {}).get("land")
                np_ += 1; nd += la != lb
        print(f"# CONTROL {base} on {fw}: this lane's rerun vs the banked a16mt run of the same cart and case file: "
              f"{nd} of {np_} pills differ in landing or lock frame" + (f"; no pair for {miss}" if miss else "")
              + (" (harness reproduces)" if nd == 0 and not miss else ""))
    R = {}                                                  # (game, p) -> {"s": strata, arm: row}
    print(f"# replays fw={fw} arms={arms} (base = {base}); lock / DOWN in frames since the spawn")
    print(f"{'game':5s} {'arm':4s} {'n':>4s} {'==final':>7s} {'pub':>4s} {'hybrid':>6s} {'frozen':>6s} {'lock mean':>9s} "
          f"{'disarmed':>8s}  summary")
    for g in GAMES:
        C = cases(g, fw)
        TL, tlpath = load_timeline(g, fw, C)
        garb_prev = {p + 1 for p in C if C[p]["garb"]}
        for a in arms:
            tag = f"{g}_{a}_{fw}_chain_garb"
            log = os.path.join(runs, tag, f"lateflip_{tag}.log")
            if not os.path.exists(log):
                print(f"{g:5s} {a:4s} MISSING"); continue
            P, summ = parse(log)
            if summ is None:
                print(f"{g:5s} {a:4s} NO SUMMARY"); continue
            rows = {}
            for p, d in P.items():
                if "land" not in d or not d["T"] or p not in C:
                    continue
                assert d.get("vc") == C[p]["vc"], (g, a, p)
                rows[p] = pill_row(d, C[p], TL[p])
                rows[p]["cycle"] = P[p + 1]["inj"] - d["inj"] if p + 1 in P and "inj" in P[p + 1] else None
                e = R.setdefault((g, p), {"s": dict(vc=C[p]["vc"], end=C[p]["vc"] < VCEND, tuck=C[p]["tuck"][0] != 255,
                                                    pg=p in garb_prev, npub=C[p]["npub"], done_f=C[p]["done_f"],
                                                    fin=C[p]["fin"], pubs=[x[3] for x in TL[p]["pubs"]],
                                                    garb=C[p]["garb"])})
                e[a] = rows[p]
            n = len(rows); cl = [r["cls"] for r in rows.values()]
            print(f"{g:5s} {a:4s} {n:4d} {cl.count('final'):7d} {cl.count('pub'):4d} {cl.count('hybrid'):6d} "
                  f"{sum(r['frozen'] for r in rows.values()):6d} {statistics.mean(r['lock'] for r in rows.values()):9.2f} "
                  f"{sum(r['sa'] == 0 for r in rows.values()):8d}  {summ[8:]}")
    STRATA = [("all pills", lambda s: True), (">= 10 viruses", lambda s: not s["end"]), ("< 10 viruses", lambda s: s["end"]),
              ("tuck pills", lambda s: s["tuck"]), ("non-tuck pills", lambda s: not s["tuck"]),
              ("post-garbage pills", lambda s: s["pg"]), ("not post-garbage", lambda s: not s["pg"])]
    print("\n## per arm, per stratum (counts / n landed)")
    print(f"{'stratum':20s} {'arm':4s} {'n':>5s} {'==final':>14s} {'pub':>4s} {'hybrid':>6s} {'frozen':>6s} "
          f"{'lock mean':>9s} {'lock med':>8s} {'GO->lock':>9s} {'DOWN mean':>9s} {'disarmed':>13s} "
          f"{'DOWN via done/stability(open,end,cross)/other/none':>48s}")
    for name, sel in STRATA:
        for a in arms:
            rs = [e[a] for e in R.values() if a in e and sel(e["s"])]
            if not rs:
                continue
            n = len(rs); cl = [r["cls"] for r in rs]; w = [r["why"] for r in rs]
            gl = [r["lock"] - r["go"] for r in rs if r["go"] is not None and r["go"] >= 1]
            dn = [r["down"] for r in rs if r["down"] is not None]
            dis = sum(r["sa"] == 0 for r in rs)
            stab = w.count("open") + w.count("end") + w.count("cross")
            print(f"{name:20s} {a:4s} {n:5d} {cl.count('final'):6d} {100 * cl.count('final') / n:6.2f}% {cl.count('pub'):4d} "
                  f"{cl.count('hybrid'):6d} {sum(r['frozen'] for r in rs):6d} {statistics.mean(r['lock'] for r in rs):9.2f} "
                  f"{statistics.median(r['lock'] for r in rs):8.1f} {statistics.mean(gl) if gl else float('nan'):6.2f}"
                  f"({len(gl):4d}) {statistics.mean(dn) if dn else float('nan'):9.2f} {dis:5d} {100 * dis / n:5.1f}%  "
                  f"{w.count('done')}/{stab}({w.count('open')},{w.count('end')},{w.count('cross')})/{w.count('other')}/"
                  f"{w.count('none')}")
    print("\n## press cadence on the cart traces (any A/B/L/R press on two consecutive frames = faster than 1 press / 2 f)")
    for a in arms:
        rs = [e[a] for e in R.values() if a in e]
        print(f"  {a}: {sum(r['presses'] for r in rs)} press frames over {len(rs)} pills, consecutive-frame presses "
              f"{sum(r['fast'] for r in rs)}")
    for a in arms[1:]:
        print(f"\n## PAIRED {a} - {base} (same case, same timeline; < 0 = {a} earlier)")
        print(f"{'stratum':20s} {'n both':>6s} {'lock diff mean [95% t] {95% game-cluster bootstrap}':>52s} {'median':>6s} "
              f"{'earlier/same/later':>18s} | {'same-landing n':>14s} {'lock diff mean [95% t]':>26s} | "
              f"{'DOWN diff mean (n)':>18s} | {'GO->lock base -> arm (n)':>24s} | {'spawn-to-next-spawn diff mean [95% t] (n)':>40s}")
        for name, sel in STRATA:
            pr = [(g, e[base], e[a]) for (g, p), e in R.items() if base in e and a in e and sel(e["s"])]
            if not pr:
                continue
            dl = [y["lock"] - x["lock"] for _, x, y in pr]
            m, lo, hi = ci_t(dl); clo, chi = ci_cluster([(g, y["lock"] - x["lock"]) for g, x, y in pr], None)
            same = [y["lock"] - x["lock"] for _, x, y in pr if x["act"] == y["act"] and x["y"] == y["y"]]
            sm, slo, shi = ci_t(same)
            dd = [y["down"] - x["down"] for _, x, y in pr if x["down"] is not None and y["down"] is not None]
            cy = [y["cycle"] - x["cycle"] for _, x, y in pr if x["cycle"] is not None and y["cycle"] is not None]
            cm, clo2, chi2 = ci_t(cy)
            gg = [(x["lock"] - x["go"], y["lock"] - y["go"]) for _, x, y in pr
                  if x["go"] is not None and y["go"] is not None and x["go"] >= 1 and y["go"] >= 1]
            print(f"{name:20s} {len(pr):6d} {m:+7.2f} [{lo:+6.2f}, {hi:+6.2f}] {{{clo:+6.2f}, {chi:+6.2f}}}".ljust(80) +
                  f"{statistics.median(dl):+6.1f} {sum(v < 0 for v in dl):6d}/{sum(v == 0 for v in dl)}/{sum(v > 0 for v in dl)}"
                  f" | {len(same):14d} {sm:+7.2f} [{slo:+6.2f}, {shi:+6.2f}] | {statistics.mean(dd) if dd else float('nan'):+7.2f} "
                  f"({len(dd)}) | {statistics.mean(v[0] for v in gg) if gg else float('nan'):6.2f} -> "
                  f"{statistics.mean(v[1] for v in gg) if gg else float('nan'):6.2f} ({len(gg)}) | "
                  f"{cm:+7.2f} [{clo2:+6.2f}, {chi2:+6.2f}] ({len(cy)})")
        # landing transitions
        tr = {}
        for (g, p), e in sorted(R.items()):
            if base in e and a in e:
                tr.setdefault((e[base]["cls"], e[a]["cls"]), []).append((g, p))
        print(f"  landing class {base} -> {a}: " + ", ".join(f"{k[0]}->{k[1]} {len(v)}" for k, v in sorted(tr.items())))
        ch = [(g, p) for (g, p), e in sorted(R.items()) if base in e and a in e and e[base]["act"] != e[a]["act"]]
        print(f"  pills whose landing action differs: {len(ch)}")
        for g, p in ch[:nlist]:
            e = R[(g, p)]; s = e["s"]; x, y = e[base], e[a]
            print(f"    {g} p{p}: vc {s['vc']}{' tuck' if s['tuck'] else ''}{' post-garb' if s['pg'] else ''} final a{s['fin']} "
                  f"pubs {s['pubs']} done {s['done_f']:.1f} f | {base}: a{x['act']} ({x['cls']}{', frozen' if x['frozen'] else ''}) "
                  f"DOWN f{x['down']} ({x['why']}) lock f{x['lock']} | {a}: a{y['act']} ({y['cls']}"
                  f"{', frozen' if y['frozen'] else ''}) DOWN f{y['down']} ({y['why']}) lock f{y['lock']} sa {y['sa']}")
    if pills_out:
        with open(pills_out, "w") as fh:
            for (g, p), e in sorted(R.items()):
                s = e["s"]
                fh.write(json.dumps(dict(game=g, fw=fw, p=p, vc=s["vc"], tuck=s["tuck"], post_garb=s["pg"], garb=s["garb"],
                                         fin=s["fin"], pubs=s["pubs"], done_f=s["done_f"],
                                         **{a: {k: e[a][k] for k in ("lock", "act", "y", "go", "down", "why", "sa", "cls",
                                                                     "frozen", "commit", "done", "late", "cycle")}
                                            for a in arms if a in e})) + "\n")


if __name__ == "__main__":
    main()
