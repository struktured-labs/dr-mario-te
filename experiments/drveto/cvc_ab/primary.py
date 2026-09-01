"""The PRE-REGISTERED PRIMARY: ADDRESSABLE champion deaths per completed round, by arm,
on the video-confirmed endpoint, over the T_stop-truncated data.

Reports the effect estimate WITH ITS CI REGARDLESS OF N (PREREG_READ.md amendment 2 rule 3):
a wide CI containing both zero and the gated 66.7% is an honest, useful result; "null" is not.
"""
import csv, math, os, re, sys
import rounds, reloads

# rounds per arm, truncated + reload-excluded -- the DENOMINATOR
R = reloads.reload_epochs()
rows = []
for i, f in enumerate(("ab_samples_L20_seg1_TRUNC.csv", "ab_samples_L20_TRUNC.csv")):
    if os.path.exists(f):
        for r in csv.DictReader(open(f)):
            r["block"] = "s%d_%s" % (i, r["block"]); rows.append(r)
blocks = {}
for r in rows:
    blocks.setdefault((r["arm"], r["block"]), []).append(
        (float(r["t_epoch"]),
         int(r["p1"]) if r["p1"] not in ("", "None") else None,
         int(r["p2"]) if r["p2"] not in ("", "None") else None,
         float(r["fill_p1"]), float(r["fill_p2"]),
         int(r["throat_p1"]), int(r["throat_p2"]),
         int(r["topcells_p1"]), int(r["topcells_p2"])))
den, excl = {}, {}
for (a, b), ser in blocks.items():
    kept, dropped = reloads.drop_reload_rounds(rounds.transitions(ser), R)
    den[a] = den.get(a, 0) + len(kept); excl[a] = excl.get(a, 0) + len(dropped)

# NUMERATOR: ADDRESSABLE, video-confirmed, per arm -- parsed from the stratify --unblind log
num = {a: 0 for a in den}
strat = {}
for line in open("stratify_primary.log"):
    m = re.search(r"arm=(\S+)\s.*-> (ADDRESSABLE|UNADDRESSABLE|OTHER)", line)
    if m:
        a, st = m.group(1), m.group(2)
        strat[(a, st)] = strat.get((a, st), 0) + 1
        if st == "ADDRESSABLE":
            num[a] = num.get(a, 0) + 1
dis = len(re.findall(r"SKIPPED \(poll/video disagree\)", open("stratify_primary.log").read()))

print("T_stop = %s\n" % open("T_STOP.txt").read().split("\n")[1])
print("%-9s %-8s %-10s %-12s %s" % ("arm", "rounds", "excluded", "reloads", "strata (video-confirmed)"))
for a in sorted(den):
    st = ", ".join("%s %d" % (s, strat.get((a, s), 0))
                   for s in ("ADDRESSABLE", "UNADDRESSABLE", "OTHER"))
    nrl = sum(1 for e in R for (x, b), ser in blocks.items()
              if x == a and ser[0][0] <= e <= ser[-1][0])
    print("%-9s %-8d %-10d %-12d %s" % (a, den[a], excl.get(a, 0), nrl, st))
print("\npoll/video disagreements excluded: %d" % dis)

print("\n== PRIMARY: ADDRESSABLE champion deaths per completed round ==")
for a in sorted(den):
    print("  %-9s %d / %d = %.4f" % (a, num.get(a, 0), den[a], num.get(a, 0) / den[a]))

if len(den) == 2:
    a_c, a_t = "noproph", "proph"
    x1, n1 = num.get(a_c, 0), den[a_c]
    x2, n2 = num.get(a_t, 0), den[a_t]
    p1, p2 = x1 / n1, x2 / n2
    d = p2 - p1
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    lo, hi = d - 1.959964 * se, d + 1.959964 * se
    print("\n  absolute difference (proph - noproph) = %+.4f" % d)
    print("  95%% CI = [%+.4f, %+.4f]   (SE %.4f)" % (lo, hi, se))
    if p1 > 0:
        rr = p2 / p1
        print("  relative rate proph/noproph = %.2f  (gated prediction: 0.333)" % rr)
        gated = -0.667 * p1
        print("  gated effect would be %+.4f; CI %s it"
              % (gated, "CONTAINS" if lo <= gated <= hi else "EXCLUDES"))
    print("  CI %s zero" % ("CONTAINS" if lo <= 0 <= hi else "EXCLUDES"))
    print("\n  n bought: noproph %d, proph %d rounds" % (n1, n2))
    print("  n needed: 120 floor  -> %s" % ("MET" if min(n1, n2) >= 120 else "NOT MET"))
    print("            186 conservative target -> %s" % ("MET" if min(n1, n2) >= 186 else "NOT MET"))
