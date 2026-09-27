#!/usr/bin/env python3
"""Verdict script for PREREG_FRAMEDENSE.md.

This is an INDEPENDENT SECOND IMPLEMENTATION of the pre-registered anomaly predicate,
written from the prereg text rather than transliterated from the Lua, and cross-checked
against the Lua's own counters (gate standard, part 4).  If the two disagree the run is
not reportable -- one of them is wrong and neither is trustworthy until that is resolved.

The predicate (PREREG_FRAMEDENSE.md, "PRE-REGISTERED ANOMALY PREDICATE").  A row is an
ANOMALY iff ALL of:
  1. $0381 & 15 == $0382 & 15                    (double capsule)
  2. STABLE_CT2 >= 8                             (settled publish)
  3. TGT_O2 in {1,2}
  4. TUCK_C2 == $FF AND TUCK_R2 == 16            (fixed exclusion rule, from source)
  5. the publish that produced this TGT_O2 was canonical in the arm-A stream
Denominator N = rows satisfying 1, 2 and 4.

Condition 5 is checked, not assumed: every store to TGT_O2 is logged with the copro
orient the mailbox was serving at that instant, and that value is carried on each row.

Bands (fixed before the data; NOT movable afterwards):
  k == 0 and N >= 3000        -> CLOSED-BENIGN
  1 <= k and k/N <= 0.005     -> RARE-REAL
  k/N > 0.005                 -> REAL
  arm B k/N < 0.20            -> VOID
"""
import csv, sys, os, re, collections

CANON_COPRO = {0, 2, 0xFF}          # AND #$FE on a double => even; $FF = "no result yet"


def load_summary(logpath):
    """The Lua SUMMARY line, as a dict -- the first of the two implementations."""
    txt = open(logpath, "rb").read().decode("utf8", "replace")
    line = [l for l in txt.splitlines() if l.startswith("SUMMARY tag=")]
    if not line:
        raise SystemExit(f"NO SUMMARY in {logpath} -- the arm is UNREPORTED, not zero")
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", line[-1]):
        d[k] = v
    return d


def analyse(csvpath):
    N = k_naive = k_strict = k_pubodd = 0
    N_tuckrow = k_tuckrow = 0
    plies_elig, plies_anom = set(), set()
    xtab = collections.Counter()        # (published copro orient, stored game orient)
    pcs = collections.Counter()
    anomalies = []
    match = pill = 0
    prev_py, prev_mode = -1, -1
    rows = 0
    for r in csv.DictReader(open(csvpath)):
        rows += 1
        mode = int(r["mode"])
        if mode == 4 and prev_mode != 4:
            match += 1
        prev_mode = mode
        if mode != 4:
            prev_py = -1
            continue
        py = int(r["py0386"])
        if prev_py >= 0 and py > prev_py:
            pill += 1
        prev_py = py

        cA, cB = int(r["c0381"]) & 15, int(r["c0382"]) & 15
        o2, st = int(r["tgt_o2"]), int(r["stable_ct2"])
        tc, tr = int(r["tuck_c2"]), int(r["tuck_r2"])
        pub = int(r["pub_or"])
        xtab[(pub, o2)] += 1

        dbl, settled, odd = (cA == cB), (st >= 8), (o2 in (1, 2))
        notuck = (tc == 0xFF and tr == 16)
        ply = (match, pill)
        if dbl and settled and notuck:
            N += 1
            plies_elig.add(ply)
            if odd:
                k_naive += 1
                plies_anom.add(ply)
                if pub in CANON_COPRO:
                    k_strict += 1
                    pcs[r["store_pc"]] += 1
                    if len(anomalies) < 40:
                        anomalies.append(dict(r))
                else:
                    k_pubodd += 1
        elif dbl and settled and not notuck:
            N_tuckrow += 1
            if odd:
                k_tuckrow += 1
    return dict(rows=rows, N=N, k_naive=k_naive, k_strict=k_strict, k_pubodd=k_pubodd,
                N_tuckrow=N_tuckrow, k_tuckrow=k_tuckrow,
                N_ply=len(plies_elig), k_ply=len(plies_anom),
                xtab=xtab, pcs=pcs, anomalies=anomalies)


def verdict(arm, a):
    N, k = a["N"], a["k_strict"]
    if arm == "B":
        rate = a["k_naive"] / N if N else 0.0
        return ("VOID" if rate < 0.20 else "CONTROL-OK",
                f"arm B fired {a['k_naive']}/{N} = {rate:.1%} (bar 20%)")
    if arm == "C":
        rate = a["k_tuckrow"] / a["N_tuckrow"] if a["N_tuckrow"] else 0.0
        return ("TUCK-CONFIRMS" if rate > 0 else "TUCK-INERT",
                f"descriptor-bearing settled doubles: {a['k_tuckrow']}/{a['N_tuckrow']} "
                f"= {rate:.1%} stored TGT_O2 in {{1,2}}; excluded stratum k={k}/{N}")
    if k == 0 and N >= 3000:
        return "CLOSED-BENIGN", f"k=0 at N={N} (>=3000)"
    if k == 0:
        return "UNDERPOWERED", f"k=0 but N={N} < 3000 -- the band requires N>=3000"
    if k / N <= 0.005:
        return "RARE-REAL", f"k={k}/{N} = {k/N:.4%} <= 0.5%"
    return "REAL", f"k={k}/{N} = {k/N:.4%} > 0.5%"


def main(dirs):
    print("=" * 78)
    for d in dirs:
        log, csvp = os.path.join(d, "framedense.log"), os.path.join(d, "hooks.csv")
        s = load_summary(log)
        arm = s["arm"]
        a = analyse(csvp)
        # CROSS-CHECK the two independent implementations before reporting anything.
        disagree = [(f, int(s[f]), a[f]) for f in
                    ("N", "k_naive", "k_strict", "k_pubodd", "N_tuckrow", "k_tuckrow")
                    if int(s[f]) != a[f]]
        v, why = verdict(arm, a)
        print(f"\nARM {arm}  ({os.path.basename(d)})")
        print(f"  cart={s['cart']} nonce={s['nonce']} w={s['w']} frames={s['frames']} "
              f"stalls={s['stalls']} resets={s['resets']}")
        print(f"  activity: pills={s['pills']} goes={s['goes']} dones={s['dones']} "
              f"dblsearch={s['dblsearch']} tuckpub={s['tuckpub']} stores={s['stores']} "
              f"pc_ok={s['pc_ok']} pc_fail={s['pc_fail']}")
        print(f"  N={a['N']} rows / {a['N_ply']} distinct plies   "
              f"k_naive={a['k_naive']} k_strict={a['k_strict']} k_pubodd={a['k_pubodd']} "
              f"k_ply={a['k_ply']}")
        print(f"  cross-impl: {'AGREE' if not disagree else 'DISAGREE ' + str(disagree)}")
        print(f"  VERDICT: {v} -- {why}")
        print("  published(copro) -> stored(game) cross-tab:")
        for (p, o), n in sorted(a["xtab"].items()):
            pl = "$FF" if p == 255 else ("n/a" if p < 0 else str(p))
            print(f"    pub={pl:>3}  stored={o}  n={n}")
        if a["pcs"]:
            print("  storing PCs for strict anomalies:", dict(a["pcs"]))
        for r in a["anomalies"][:10]:
            print("   ANOM", {kk: r[kk] for kk in
                              ("frame", "tgt_o2", "tgt_c2", "stable_ct2", "tuck_c2", "tuck_r2",
                               "c0381", "c0382", "pub_or", "store_pc")})
    print("\n" + "=" * 78)


if __name__ == "__main__":
    main(sys.argv[1:])
