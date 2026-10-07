#!/usr/bin/env python3
"""a16mt lane: side-by-side table of chained + garbage Mesen replays (execfid_probe.lua logs) of several carts on the
same case files.

Per game and arm: landed pills, landing == silicon, landing == copro final, HYBRID (a landing that is neither the copro
final nor any published candidate), LATEGUARD-frozen pills, and the lock frame (LAND f, frames since the spawn).
Tempo: on pills where an arm lands on the SAME action as the first (base) arm, the lock-frame difference arm - base;
and on every pill both arms committed (first ROT_DONE2 frame), the commit-frame difference.
Then every pill whose landing differs between arms, with the silicon landing, the copro final and the publish list.
Optional --ctl GAME=LOG: a banked run of the base cart on the same case file; its landings must equal the base arm's
(reproducibility control of the harness).

Usage: replay_table.py RUNS FWTAG ARM[,ARM...] GAME=PUBTRACE [GAME=PUBTRACE ...] [--ctl GAME=LOG ...]"""
import json, os, statistics, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lateflip"))
import parse_lateflip as PL


def summary(log):
    for line in open(log, errors="replace"):
        if line.startswith("SUMMARY"):
            return line.strip()
    return None


def main():
    args = sys.argv[1:]
    ctl = {}
    while "--ctl" in args:
        i = args.index("--ctl"); g, p = args[i + 1].split("=", 1); ctl[g] = p; del args[i:i + 2]
    runs, fw, arms = args[0], args[1], args[2].split(",")
    games = [a.split("=", 1) for a in args[3:]]
    tot = {a: dict(n=0, sil=0, fin=0, hyb=0, frz=0) for a in arms}
    tempo = {a: [] for a in arms[1:]}
    ctempo = {a: [] for a in arms[1:]}
    diffs = []
    print(f"# replays fw={fw} arms={arms} (base = {arms[0]})")
    print(f"{'game':6s} {'arm':10s} {'n':>4s} {'==sil':>6s} {'==final':>8s} {'hybrid':>7s} {'frozen':>7s} {'lockf med':>9s} "
          f"{'cmtf med':>8s}  summary")
    for g, pub in games:
        P = {t["p"]: t for t in map(json.loads, open(pub))}
        L = {}
        for a in arms:
            tag = f"{g}_{a}_{fw}_chain_garb"
            log = os.path.join(runs, tag, f"lateflip_{tag}.log")
            if not os.path.exists(log) or summary(log) is None:
                print(f"{g:6s} {a:10s} MISSING {log}"); continue
            L[a] = PL.load(log)
            C = L[a]; t = tot[a]
            lands = {p: c["land"] for p, c in C.items() if c["land"]}
            hyb = [p for p, ld in lands.items() if p in P and ld["act"] != P[p]["final"][2]
                   and ld["act"] not in [x[3] for x in P[p]["pubs"]]]
            n = len(lands); sil = sum(str(ld["act"]) == ld["sil"] for ld in lands.values())
            fin = sum(ld["act"] == ld["fin"] for ld in lands.values()); frz = sum(C[p]["frozen"] for p in lands)
            for k, v in (("n", n), ("sil", sil), ("fin", fin), ("hyb", len(hyb)), ("frz", frz)):
                t[k] += v
            lf = statistics.median([ld["f"] for ld in lands.values()]) if lands else 0
            cf = [C[p]["commit_f"] for p in lands if C[p]["commit_f"] is not None]
            cf = statistics.median(cf) if cf else 0
            print(f"{g:6s} {a:10s} {n:4d} {sil:6d} {fin:8d} {len(hyb):7d} {frz:7d} {lf:9.1f} {cf:8.1f}  {summary(log)[8:]}"
                  + (f"  hybrids {sorted(hyb)}" if hyb else ""))
        if arms[0] not in L:
            continue
        B = L[arms[0]]
        for a in arms[1:]:
            if a not in L:
                continue
            for p, c in L[a].items():
                b = B.get(p)
                if c["land"] and b and b["land"] and c["land"]["act"] == b["land"]["act"]:
                    tempo[a].append(c["land"]["f"] - b["land"]["f"])
                if b and c["commit_f"] is not None and b["commit_f"] is not None:
                    ctempo[a].append(c["commit_f"] - b["commit_f"])
        for p in sorted(set().union(*[set(C) for C in L.values()])):
            acts = {a: (L[a][p]["land"]["act"] if p in L[a] and L[a][p]["land"] else None) for a in L}
            if len(set(acts.values())) > 1:
                ld = next(L[a][p]["land"] for a in L if p in L[a] and L[a][p]["land"])
                pubs = [x[3] for x in P[p]["pubs"]] if p in P else []
                fin = P[p]["final"][2] if p in P else None
                lab = {a: ("final" if v == fin else ("pub" if v in pubs else "HYBRID")) for a, v in acts.items() if v is not None}
                diffs.append(f"  {g} p{p}: vc {P[p]['vc'] if p in P else '?'} silicon a{ld['sil']} final a{fin} pubs {pubs} | "
                             + " | ".join(f"{a}: a{v} ({lab.get(a, '-')}) f={L[a][p]['land']['f'] if v is not None else '-'}"
                                          for a, v in acts.items()))
        if g in ctl:
            K = PL.load(ctl[g])
            dif = [p for p in B if B[p]["land"] and (p not in K or not K[p]["land"] or K[p]["land"]["act"] != B[p]["land"]["act"]
                                                      or K[p]["land"]["f"] != B[p]["land"]["f"])]
            print(f"{g:6s} CONTROL {arms[0]} vs banked {os.path.basename(ctl[g])}: {len(dif)} pills differ in landing or lock frame"
                  + (f" {dif[:12]}" if dif else " (harness reproduces)"))
    print("TOTAL")
    for a in arms:
        t = tot[a]
        print(f"  {a:10s} n={t['n']} ==silicon {t['sil']} ==final {t['fin']} hybrid {t['hyb']} frozen {t['frz']}")
    for a, v in tempo.items():
        if v:
            print(f"  tempo {a} - {arms[0]} on same-landing pills: n={len(v)} mean {statistics.mean(v):+.2f} f "
                  f"median {statistics.median(v):+.1f} f (earlier lock < 0); faster {sum(x < 0 for x in v)} slower {sum(x > 0 for x in v)}")
    for a, v in ctempo.items():
        if v:
            print(f"  commit {a} - {arms[0]} on pills both committed: n={len(v)} mean {statistics.mean(v):+.2f} f "
                  f"median {statistics.median(v):+.1f} f; earlier {sum(x < 0 for x in v)} later {sum(x > 0 for x in v)}")
    print(f"landing differences between arms ({len(diffs)}):")
    print("\n".join(diffs))


if __name__ == "__main__":
    main()
