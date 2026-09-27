"""Tiered blunder detection, validated against the film review's adjudicated set.

The owner's worry -- false positives -- is the whole design constraint. A single
"blunder rate" from engine disagreement is known-poisoned here: the vocabulary wall
says the engine is least trustworthy near death, joint-dig closed as REFUTED, and
struktured's 47.9% clear-decline rate was adjudicated as STYLE, not error. So the
metric is tiered by how the evidence is obtained, and the tiers are never merged.

TIER M -- MECHANICAL. Engine-free. Execution visibly diverged from intent, using the
film review's own three correction classes verbatim (analysis/rotations.md):
    reversal      two consecutive opposite-direction tokens, frame gap <= 12
                  ('tog' is a monocolor pill, undirectable, never counted)
    overshoot     a run of 3+ consecutive same-direction tokens
    late-flurry   2+ tokens with lock_frame - f <= 15
VALIDATION: these definitions have already been applied by hand-verified analysis to
struktured's 331-pill corpus, per match. Reproducing those counts exactly IS the
precision check -- it is agreement with an adjudicated label set, not a self-test.

TIER F -- FATAL / OUTCOME-ANCHORED and TIER E -- ENGINE-ADJUDICATED are NOT implemented
here. Both need per-placement board state (seal episodes; engine value gaps on a real
board), which the per-pill CSVs do not carry. Reporting them from what is available
would be exactly the false positive the owner asked to avoid. See the verdict printed
at the end.
"""
import csv
import os
import sys

EVAL47 = os.path.dirname(os.path.abspath(__file__))
LE = os.path.join(EVAL47, "results", "latency_events")

REVERSAL_GAP = 12
LATE_WINDOW = 15
OVERSHOOT_RUN = 3

# Hand-verified counts from analysis/rotations.md, per match. These are the labels.
PUBLISHED = {
    "m1": {"reversal": 0, "overshoot": 2, "late": 6, "any": 8, "pills": 92},
    "m2": {"reversal": 2, "overshoot": 0, "late": 4, "any": 5, "pills": 47},
    "m3": {"reversal": 0, "overshoot": 2, "late": 3, "any": 4, "pills": 55},
    "m4": {"reversal": 0, "overshoot": 6, "late": 3, "any": 7, "pills": 137},
}


def tokens(row):
    """-> [(direction, frame)] in order."""
    out = []
    for tok in row["rotation_seq"].split(","):
        if not tok:
            continue
        d, _, f = tok.partition("@")
        out.append((d, int(f.lstrip("f"))))
    return out


def classes_for(row, gap=REVERSAL_GAP, late=LATE_WINDOW, run=OVERSHOOT_RUN,
                count_tog_reversal=False):
    toks = tokens(row)
    lock = int(row["lock_frame"])
    hits = set()

    for (d0, f0), (d1, f1) in zip(toks, toks[1:]):
        directed = {d0, d1} <= {"cw", "ccw"} or count_tog_reversal
        if directed and d0 != d1 and (f1 - f0) <= gap:
            hits.add("reversal")

    streak = 1
    for (d0, _), (d1, _) in zip(toks, toks[1:]):
        streak = streak + 1 if d1 == d0 else 1
        if streak >= run:
            hits.add("overshoot")

    if sum(1 for _d, f in toks if lock - f <= late) >= 2:
        hits.add("late-flurry")
    return hits


def tally(rows, **kw):
    t = {"reversal": 0, "overshoot": 0, "late-flurry": 0, "any": 0, "pills": len(rows)}
    for r in rows:
        h = classes_for(r, **kw)
        for k in h:
            t[k] += 1
        if h:
            t["any"] += 1
    return t


def load(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def validate():
    """Agreement with the adjudicated per-match counts. This is the precision table."""
    print("TIER M VALIDATION -- reproduce analysis/rotations.md's hand-verified counts")
    print(f"  {'match':6s} {'pills':>6s}  {'reversal':>16s} {'overshoot':>16s} "
          f"{'late-flurry':>16s} {'any':>14s}")
    allok = True
    pooled = {"reversal": 0, "overshoot": 0, "late-flurry": 0, "any": 0, "pills": 0}
    for m, exp in PUBLISHED.items():
        rows = load(os.path.join(LE, "film_20260804", f"{m}.csv"))
        got = tally(rows)
        for k in pooled:
            pooled[k] += got[k]
        cells = []
        for key, expkey in (("reversal", "reversal"), ("overshoot", "overshoot"),
                            ("late-flurry", "late"), ("any", "any")):
            ok = got[key] == exp[expkey]
            allok &= ok
            cells.append(f"{got[key]:>3d} vs {exp[expkey]:<3d} {'OK ' if ok else 'MISMATCH'}")
        npok = got["pills"] == exp["pills"]
        allok &= npok
        print(f"  {m:6s} {got['pills']:>6d}  " + " ".join(f"{c:>15s}" for c in cells))
    print(f"  {'POOLED':6s} {pooled['pills']:>6d}  "
          f"reversal {pooled['reversal']} (pub 2)  overshoot {pooled['overshoot']} (pub 10)  "
          f"late {pooled['late-flurry']} (pub 16)  any {pooled['any']} (pub 24)")
    allok &= (pooled["reversal"], pooled["overshoot"], pooled["late-flurry"],
              pooled["any"]) == (2, 10, 16, 24)
    print(f"  VALIDATION: {'PASS -- detector agrees with the adjudicated set' if allok else 'FAIL'}")
    return allok


def mutants():
    print("\nKILLED-MUTANT GATE")
    rows = [r for m in PUBLISHED for r in load(os.path.join(LE, "film_20260804", f"{m}.csv"))]
    base = tally(rows)
    ok = True
    for tag, kw, key in (
        ("reversal gap 12 -> 0 frames", dict(gap=0), "reversal"),
        ("overshoot run 3 -> 2 tokens", dict(run=2), "overshoot"),
        ("late window 15 -> 0 frames", dict(late=0), "late-flurry"),
    ):
        got = tally(rows, **kw)
        hit = got[key] != base[key]
        ok &= hit
        print(f"  mutant: {tag:36s} {'KILLED' if hit else '*** SURVIVED'} "
              f"({key} {base[key]} -> {got[key]})")

    # The tog-exclusion guard has NO discriminating case in this corpus: no pill
    # contains a tog token adjacent to a directed one inside the gap. Mutating it
    # against the corpus therefore proves nothing (2 -> 2, a survivor by absence of
    # input, not by correctness). Exercise it on a constructed row instead, which is
    # what the mutant was for.
    synth = {"rotation_seq": "tog@f10,cw@f14", "lock_frame": "400"}
    strict = "reversal" in classes_for(synth)
    loose = "reversal" in classes_for(synth, count_tog_reversal=True)
    hit = (not strict) and loose
    ok &= hit
    print(f"  mutant: {'tog counted as directional (synthetic)':36s} "
          f"{'KILLED' if hit else '*** SURVIVED'} "
          f"(guard on -> {strict}, guard off -> {loose}; corpus has no such pair)")
    return ok


def main():
    v = validate()
    m = mutants()
    if not (v and m):
        print("\nGATE FAILED -- not publishing per-player rates")
        return 1

    print("\nTIER M RATES PER 100 PILLS")
    srcs = {
        "struktured": [os.path.join(LE, "film_20260804", f"{m}.csv") for m in PUBLISHED],
        "dr. lulu": [os.path.join(LE, "film_20260808", "p1_m3.csv")],
    }
    for name, paths in srcs.items():
        rows = [r for p in paths for r in load(p)]
        t = tally(rows)
        n = t["pills"]
        print(f"  {name:12s} n={n:4d}  reversal {100*t['reversal']/n:5.2f}  "
              f"overshoot {100*t['overshoot']/n:5.2f}  late-flurry {100*t['late-flurry']/n:5.2f}"
              f"   ANY {100*t['any']/n:5.2f}  ({t['any']} pills)")

    print("\nTIER F / TIER E: NOT COMPUTED.")
    print("  Both need per-placement board state -- seal episodes that never reopen (F)")
    print("  and engine value gaps on a real board (E). The per-pill CSVs carry neither.")
    print("  Emitting them from what IS available would manufacture the false positives")
    print("  this design exists to avoid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
