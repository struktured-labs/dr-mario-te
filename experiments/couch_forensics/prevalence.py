"""Prevalence of driver overrides across the recorded CHAIN540 couch games (AI = P2).

Inputs: cases_<tag>_<game>.jsonl (classify_g2.py output per game) + mech_<tag>_<game>.txt (mech_check.py
last line: unexplained steps). A placement is UNVERIFIED if the mechanics step into it or out of it is
unexplained (S_k or its landing may be misread). Rates are reported over VERIFIED placements, with the
all-placements number beside them.

Driver override = SHORT-LANDING (DISTGATE clamp-consistent) + PROPH-ESCAPE + LATE-FLIP.
Usage: python prevalence.py TMPDIR OUT_ALL.jsonl
"""
import json
import random
import statistics as st
import sys
from collections import Counter

GAMES = [("n24", "G1", "won"), ("n24", "G2", "won"), ("n24", "G3", "won"),
         ("m25", "G1", "won"), ("m25", "G2", "LOST (tap-out)"), ("m25", "G3", "won"), ("m25", "G4", "won")]
OVR = ("SHORT-LANDING", "PROPH-ESCAPE", "LATE-FLIP")


def is_override(c):
    if c["category"] == "SHORT-LANDING":
        return bool(c["detail"].get("dist_clamp"))
    return c["category"] in ("PROPH-ESCAPE", "LATE-FLIP")


def lane(c):
    h = c["heights"]
    return max(h[3], h[4])


def fomin(c):
    return min(c["fo3"], c["fo4"])


def load(tmp):
    allc = []
    for tag, g, res in GAMES:
        C = [json.loads(l) for l in open(f"cases_{tag}_{g}.jsonl")]
        mech = json.loads(open(f"{tmp}/mech_{tag}_{g}.txt").read().strip().splitlines()[-1])
        bad = set(mech["unexplained_k"])
        ks = [c["k"] for c in C]
        for i, c in enumerate(C):
            prev_k = ks[i - 1] if i > 0 else None
            c["game"] = f"{tag}_{g}"; c["result"] = res; c["idx"] = i
            c["verified"] = not (c["k"] in bad or (prev_k is not None and prev_k in bad))
            allc.append(c)
    return allc


def boot(xs, n=4000, seed=1):
    rng = random.Random(seed); k = len(xs)
    o = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return o[int(.025 * n)], o[int(.975 * n)]


def main(tmp, out):
    A = load(tmp)
    with open(out, "w") as fh:
        for c in A:
            fh.write(json.dumps(c) + "\n")
    print("== 1. override rates (verified placements; all placements in brackets)")
    print(f"{'game':8s} {'result':15s} {'n':>4} {'MATCH':>6} {'clamp':>6} {'PROPH-esc':>9} {'late':>5} {'OVR%':>6} "
          f"{'PROPHfired':>10} {'PROPH->MATCH':>12} {'tuck':>5} {'other':>6} {'shortNoClamp':>12}")
    tot = Counter(); totall = Counter()
    for tag, g, res in GAMES:
        C = [c for c in A if c["game"] == f"{tag}_{g}"]
        V = [c for c in C if c["verified"]]
        cnt = Counter(c["category"] for c in V)
        clamp = sum(1 for c in V if c["category"] == "SHORT-LANDING" and c["detail"].get("dist_clamp"))
        noclamp = cnt["SHORT-LANDING"] - clamp
        ovr = sum(is_override(c) for c in V); ovr_all = sum(is_override(c) for c in C)
        pf = sum(1 for c in V if c["proph_dir"] in ("L", "R"))
        pm = sum(1 for c in V if c["proph_dir"] in ("L", "R") and c["category"] == "MATCH")
        print(f"{tag}_{g:5s} {res:15s} {len(V):4d} {cnt['MATCH']:6d} {clamp:6d} {cnt['PROPH-ESCAPE']:9d} {cnt['LATE-FLIP']:5d} "
              f"{100*ovr/len(V):5.1f}% [{100*ovr_all/len(C):4.1f}% of {len(C)}] {pf:6d} {pm:12d} {cnt['TUCK']:5d} {cnt['OTHER']:6d} {noclamp:12d}")
        tot.update(dict(n=len(V), ovr=ovr, clamp=clamp, pesc=cnt["PROPH-ESCAPE"], late=cnt["LATE-FLIP"], pf=pf, pm=pm,
                        match=cnt["MATCH"], tuck=cnt["TUCK"], other=cnt["OTHER"]))
        totall.update(dict(n=len(C), ovr=ovr_all))
    won = [c for c in A if c["verified"] and c["result"] == "won"]
    print(f"POOLED verified n={tot['n']}: overrides {tot['ovr']} ({100*tot['ovr']/tot['n']:.1f}%) = clamp {tot['clamp']} + "
          f"PROPH-escape {tot['pesc']} + late-flip {tot['late']}; MATCH {tot['match']} ({100*tot['match']/tot['n']:.1f}%); "
          f"PROPH fired {tot['pf']} -> escapes AGAINST the brain {tot['pesc']}, MATCH {tot['pm']}  [all placements: "
          f"{totall['ovr']}/{totall['n']} = {100*totall['ovr']/totall['n']:.1f}%]")
    print(f"WON games only: overrides {sum(is_override(c) for c in won)}/{len(won)} "
          f"({100*sum(is_override(c) for c in won)/len(won):.1f}%), PROPH-escapes {sum(c['category']=='PROPH-ESCAPE' for c in won)}")

    print("\n== 2. what follows an override (spawn-lane height = max(h3,h4); fo_min = min first-occupied row c3/c4)")
    by_game = {}
    for c in A:
        by_game.setdefault(c["game"], []).append(c)
    for H in (3, 5):
        diffs, dl_o, dl_m, ledge_o, ledge_m = [], [], [], [], []
        pool = []
        for gm, C in by_game.items():
            for i, c in enumerate(C):
                if i + H < len(C) and c["verified"] and C[i + H]["verified"]:
                    pool.append((c, lane(C[i + H]) - lane(c), fomin(C[i + H]) <= 2))
        ctrl = [p for p in pool if p[0]["category"] == "MATCH"]
        for c, d, lg in pool:
            if not is_override(c):
                continue
            m = [dd for (cc, dd, _) in ctrl if abs(lane(cc) - lane(c)) <= 0 and cc["game"] != "" ]
            if len(m) < 3:
                m = [dd for (cc, dd, _) in ctrl if abs(lane(cc) - lane(c)) <= 1]
            ml = [l2 for (cc, dd, l2) in ctrl if abs(lane(cc) - lane(c)) <= 1]
            if not m:
                continue
            diffs.append(d - st.mean(m)); dl_o.append(d); dl_m.append(st.mean(m))
            ledge_o.append(float(lg)); ledge_m.append(st.mean(float(x) for x in ml))
        lo, hi = boot(diffs)
        print(f"  +{H} pills: n_overrides={len(diffs)}  d(lane) override {st.mean(dl_o):+.2f} vs matched MATCH {st.mean(dl_m):+.2f}  "
              f"=> excess {st.mean(diffs):+.2f} rows [95% {lo:+.2f},{hi:+.2f}];  P(ledge fo_min<=2 at +{H}) "
              f"override {st.mean(ledge_o):.2f} vs matched {st.mean(ledge_m):.2f}")
        for cat in OVR:
            sub = [(c, d) for c, d, _ in pool if is_override(c) and c["category"] == cat]
            if sub:
                ex = []
                for c, d in sub:
                    m = [dd for (cc, dd, _) in ctrl if abs(lane(cc) - lane(c)) <= 1]
                    if m:
                        ex.append(d - st.mean(m))
                print(f"     {cat:14s} n={len(ex):3d} excess d(lane) {st.mean(ex):+.2f}")

    print("\n== 3. steering timing (frames from preview change to first lateral move)")
    fm_np = [c["lateral_move_frames"][0] for c in A if c["proph_dir"] not in ("L", "R") and c["lateral_move_frames"]]
    fm_p = [c["lateral_move_frames"][0] for c in A if c["proph_dir"] in ("L", "R") and c["lateral_move_frames"]]
    h = Counter(fm_np)
    print(f"  no-PROPH n={len(fm_np)} median {st.median(fm_np)} min {min(fm_np)} max {max(fm_np)}; <10 f: {sum(x < 10 for x in fm_np)}")
    print("  histogram:", dict(sorted(h.items())))
    print(f"  PROPH-fired n={len(fm_p)} first move frames: {dict(sorted(Counter(fm_p).items()))}")

    print("\n== 4. override density: G2 death window vs sliding 12-placement windows in the won games")
    def dens(C):
        return sum(is_override(c) for c in C if c["verified"]) / max(1, sum(c["verified"] for c in C))
    g2 = by_game["m25_G2"]
    print(f"  G2 whole game {dens(g2):.2f} (n={len(g2)}); G2 last 12 {dens(g2[-12:]):.2f} "
          f"({sum(is_override(c) for c in g2[-12:])}/12)")
    wins = []
    for gm, C in by_game.items():
        if C[0]["result"] != "won":
            continue
        for i in range(0, len(C) - 11):
            wins.append((sum(is_override(c) for c in C[i:i + 12]), gm, i))
    wins.sort(reverse=True)
    top = wins[:5]
    ge = sum(1 for w in wins if w[0] >= sum(is_override(c) for c in g2[-12:]))
    print(f"  won-game 12-windows: n={len(wins)}, max overrides {top[0][0]} ({top[0][1]} from idx {top[0][2]}), "
          f"windows with >= G2's {sum(is_override(c) for c in g2[-12:])}: {ge};  mean {st.mean(w[0] for w in wins):.2f}")
    pe = [(sum(c['category'] == 'PROPH-ESCAPE' for c in C[i:i + 12]), gm) for gm, C in by_game.items()
          if C[0]['result'] == 'won' for i in range(0, len(C) - 11)]
    print(f"  PROPH-escapes in any won-game 12-window: max {max(p[0] for p in pe)}; G2 last 12: "
          f"{sum(c['category']=='PROPH-ESCAPE' for c in g2[-12:])}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
