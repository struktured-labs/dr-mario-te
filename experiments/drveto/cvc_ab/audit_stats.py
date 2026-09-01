"""Stratified test + the R96 positive control that must FAIL."""
import math, statistics as st
import csv, os, re
import rounds, reloads
exec(open("adjudicator_audit.py").read().split('n = len(recs)')[0])

def bin_dur(r): d = r["dur"]; return 0 if d < 30 else (1 if d < 45 else 2)

def mh(records, stratfn, label):
    """Mantel-Haenszel pooled risk difference across strata, arm as exposure."""
    num = den = varsum = 0.0
    rows = []
    for s in sorted({stratfn(r) for r in records}):
        sub = [r for r in records if stratfn(r) == s]
        a1 = [r for r in sub if r["arm"] == "noproph"]; a2 = [r for r in sub if r["arm"] == "proph"]
        n1, n2 = len(a1), len(a2)
        if not n1 or not n2: continue
        x1 = sum(r["disagree"] for r in a1); x2 = sum(r["disagree"] for r in a2)
        p1, p2 = x1/n1, x2/n2
        w = n1*n2/(n1+n2)
        num += w*(p1-p2); den += w
        varsum += w**2 * (p1*(1-p1)/n1 + p2*(1-p2)/n2)
        rows.append((s, x1, n1, x2, n2, p1-p2))
    d = num/den; se = math.sqrt(varsum)/den
    print("%s" % label)
    for s, x1, n1, x2, n2, dd in rows:
        print("   stratum %-3s noproph %2d/%-3d  proph %2d/%-3d  diff %+.3f" % (s, x1, n1, x2, n2, dd))
    print("   POOLED (Mantel-Haenszel) noproph-minus-proph = %+.3f  95%% CI [%+.3f, %+.3f]  %s zero\n"
          % (d, d-1.96*se, d+1.96*se, "EXCLUDES" if (d-1.96*se)*(d+1.96*se) > 0 else "contains"))
    return d, se

print("=== ARM EFFECT ON DISAGREEMENT, STRATIFIED BY GEOMETRY ===\n")
mh(recs, bin_dur, "stratified by round DURATION (<30 / 30-45 / >=45 s):")
mh(recs, lambda r: 0 if r["tc2"] <= 80 else 1, "stratified by P2 VIRUSES LEFT (<=80 / >80):")

print("=== R96 POSITIVE CONTROL: the checker must be SHOWN ABLE TO FAIL ===")
print("A checker never observed to fail has not been shown able to fail. Inject a set where")
print("arm demonstrably does NOT predict disagreement, and one where it demonstrably does.\n")
import random
random.seed(7)
# NEGATIVE control: disagreement assigned at random, independent of arm -> must NOT detect
neg = [dict(r, disagree=random.randint(0, 1)) for r in recs]
d, se = mh(neg, bin_dur, "NEGATIVE control (disagreement randomised, arm-independent):")
print("   -> must CONTAIN zero. %s\n" % ("PASS" if (d-1.96*se)*(d+1.96*se) <= 0 else "FAIL -- checker sees an effect that is not there"))
# POSITIVE control: disagreement forced to track arm -> must detect
pos = [dict(r, disagree=1 if r["arm"] == "noproph" else 0) for r in recs]
d, se = mh(pos, bin_dur, "POSITIVE control (disagreement forced to track arm perfectly):")
print("   -> must EXCLUDE zero. %s" % ("PASS" if (d-1.96*se)*(d+1.96*se) > 0 else "FAIL -- checker cannot detect an effect that IS there"))
