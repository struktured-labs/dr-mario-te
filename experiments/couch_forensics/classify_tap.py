"""Classify TAP-build placements (analyze_tap.py output) against the brain that matches the build.

  python classify_tap.py ANALYSIS.jsonl RAW.jsonl BRAIN(masked|hsv) OUT.jsonl

Categories (first match wins), same meanings as classify_g2.py:
  MATCH, TUCK (non-straight-drop landing), PROPH-ESCAPE (DRPROPH fired, landed on the pulse side, brain target on
  the other side), LATE-FLIP (held the brain's exact pose >= 4 frames then changed), SHORT-LANDING (same
  orientation, strictly between spawn col 3 and the brain's column), OTHER.
"""
import json
import sys


def main(an, raw, brain, out):
    A = [json.loads(l) for l in open(an)]
    R = {json.loads(l)["k"]: json.loads(l) for l in open(raw)}
    rows = []
    for a in A:
        tgt = a["hsv"] if brain == "hsv" else a["masked"]
        act = a["actual"]
        traj = R[a["k"]]["traj"]
        cat = None
        if tgt == act:
            cat = "MATCH"
        elif a["actual_action"] is None:
            cat = "TUCK"
        elif a["proph"] in ("L", "R") and tgt is not None:
            side = lambda c: "L" if c < 3 else ("R" if c > 3 else "C")
            if side(act[1]) == a["proph"] and side(tgt[1]) != a["proph"]:
                cat = "PROPH-ESCAPE"
        if cat is None and tgt is not None:
            held = [t for (t, o, r, c, cl) in traj if o == tgt[0] and c == tgt[1] and cl == tgt[2]]
            if len(held) >= 4:
                cat = "LATE-FLIP"
            elif act[0] == tgt[0] and min(3, tgt[1]) <= act[1] <= max(3, tgt[1]) and act[1] != tgt[1]:
                cat = "SHORT-LANDING"
        rows.append({**a, "brain": brain, "category": cat or "OTHER"})
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    from collections import Counter
    print(out, dict(Counter(r["category"] for r in rows)))


if __name__ == "__main__":
    main(*sys.argv[1:5])
