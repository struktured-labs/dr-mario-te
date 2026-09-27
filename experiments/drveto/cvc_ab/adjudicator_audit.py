"""Is the poll/video disagreement explained by GEOMETRY, or by ARM after conditioning on it?

⚠ THE CONFOUND: "the adjudicator is arm-dependent" and "the treatment changed what deaths
LOOK like" both predict a higher disagreement rate on one arm. Testing BY ARM cannot
separate them. So classify each death by features visible WITHOUT the arm, then ask whether
disagreement is predicted by GEOMETRY, or still by ARM once geometry is matched.

FEATURES = the poll's own decision inputs at the last pre-reset sample (banked CSV, no
video): both seats' topcells/throat/fill, both virus counts, round duration. If the
treatment moved death geometry, these move with it.

BLINDING IS STRUCTURAL (R97): features and verdicts are assembled with the arm stripped and
joined back by an opaque key only at the analysis step.
"""
import csv, math, os, re, sys
import rounds, reloads

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

# rebuild the champion-death list in EXACTLY stratify's order so S-index maps to a round
deaths = [(a, rec) for (a, b), ser in sorted(blocks.items(), key=lambda kv: kv[0][1])
          for rec in rounds.transitions(ser) if rec["outcome"] == "TOPOUT_P2"]

log = open("stratify_primary.log").read()
dis_epoch = {m.group(1) for m in re.finditer(r"epoch=(\d+)\s+video says", log)}

recs = []
for i, (arm, rec) in enumerate(deaths):
    ep = "%.0f" % rec["end"]
    recs.append(dict(key="S%02d" % i, arm=arm,
                     disagree=1 if ep in dis_epoch else 0,
                     tc2=rec["last_p2"], tc1=rec["last_p1"],
                     dur=rec["dur_s"], f1=rec["fill_p1"], f2=rec["fill_p2"],
                     plug1=int(bool(rec["plug_p1"])), plug2=int(bool(rec["plug_p2"]))))

n = len(recs); nd = sum(r["disagree"] for r in recs)
print("champion-death candidates: %d ; poll/video disagreements: %d (%.0f%%)\n" % (n, nd, 100*nd/n))

def rate(sub):
    return (sum(r["disagree"] for r in sub), len(sub))

print("-- A. BY ARM (the confounded view -- cannot separate the two explanations) --")
for a in ("noproph", "proph"):
    x, m = rate([r for r in recs if r["arm"] == a])
    print("   %-9s %2d/%-3d = %.0f%%" % (a, x, m, 100*x/m if m else 0))

print("\n-- B. BY GEOMETRY, arm-blind --")
def show(label, keyfn):
    print("  %s" % label)
    groups = {}
    for r in recs:
        groups.setdefault(keyfn(r), []).append(r)
    for g in sorted(groups):
        x, m = rate(groups[g])
        print("     %-22s %2d/%-3d = %3.0f%%" % (g, x, m, 100*x/m if m else 0))
show("by P2 viruses left at the last sample:", lambda r: "%d-%d" % (10*(r["tc2"]//10), 10*(r["tc2"]//10)+9))
show("by whether the poll saw P2 plugged:", lambda r: "plug_p2=%d" % r["plug2"])
show("by whether the poll ALSO saw P1 plugged:", lambda r: "plug_p1=%d" % r["plug1"])
show("by round duration:", lambda r: "<40s" if r["dur"] < 40 else ("40-80s" if r["dur"] < 80 else ">=80s"))

print("\n-- C. ARM WITHIN MATCHED GEOMETRY (the decisive test) --")
print("   If geometry explains it, arm should NOT predict disagreement inside a stratum.")
for gname, keyfn in (("plug_p1", lambda r: r["plug1"]),):
    for g in sorted({keyfn(r) for r in recs}):
        sub = [r for r in recs if keyfn(r) == g]
        line = "   %s=%s :" % (gname, g)
        for a in ("noproph", "proph"):
            x, m = rate([r for r in sub if r["arm"] == a])
            line += "  %-8s %2d/%-3d=%3.0f%%" % (a, x, m, 100*x/m if m else 0)
        print(line)
