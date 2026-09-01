"""Score every champion death into the pre-registered strata (PREREG_STRATA.md)."""
import csv, glob, os, sys
import adjudicate as A, eligibility as E, rounds

rows = list(csv.DictReader(open("ab_samples_L20.csv")))
blocks = {}
for r in rows:
    blocks.setdefault((r["arm"], r["block"]), []).append(
        (float(r["t_epoch"]),
         int(r["p1"]) if r["p1"] not in ("", "None") else None,     # unreadable frame
         int(r["p2"]) if r["p2"] not in ("", "None") else None,     # -> a gap, by design
         float(r["fill_p1"]), float(r["fill_p2"]),
         int(r["throat_p1"]), int(r["throat_p2"]),
         int(r["topcells_p1"]), int(r["topcells_p2"])))

deaths = []
for (arm, b), ser in sorted(blocks.items(), key=lambda kv: kv[0][1]):
    for rec in rounds.transitions(ser):
        if rec["outcome"] == "TOPOUT_P2":
            deaths.append((arm, rec["end"], rec["last_p2"]))
print("champion deaths indexed by the poll: %d\n" % len(deaths))

tally = {}
for i, (arm, ep, vleft) in enumerate(deaths):
    tag = "S%02d" % i
    d = A.find_death(ep, tag=tag)
    sp = d.get("span", {})
    if not sp.get("span_plausible", True):
        print("  %s ⚠ SPAN REVIEW FAILED: %s -- verdict withheld" % (tag, sp.get("span_warning")))
        tally["SPAN_REJECT"] = tally.get("SPAN_REJECT", 0) + 1
        continue
    if d.get("verdict") != "TOPOUT_P2":
        print("  %s arm=%-8s epoch=%.0f  video says %s -- SKIPPED (poll/video disagree)"
              % (tag, arm, ep, d.get("verdict")))
        tally["DISAGREE"] = tally.get("DISAGREE", 0) + 1
        continue
    frames = sorted(glob.glob(os.path.join(os.path.dirname(d["frame"]), tag + "_*.png")))
    hold_i = frames.index(d["frame"])
    pi, grid, pspan = E.parent_board(frames, hold_i)
    if grid is None:
        print("  %s arm=%-8s no clear-throat parent frame in window -- SKIPPED" % (tag, arm))
        tally["NO_PARENT"] = tally.get("NO_PARENT", 0) + 1
        continue
    ev = E.evaluate(grid)
    tally[ev["stratum"]] = tally.get(ev["stratum"], 0) + 1
    print("  %s arm=%-8s v_left=%-3s hold=%-4ss span[win=%ss hold=%sf back=%sf] "
          "fo3=%-2d fo4=%-2d trig=%-5s gateL=%-5s gateR=%-5s dir=%-5s -> %s"
          % (tag, arm, vleft, d["hold_s"], sp.get("window_s"), sp.get("hold_frames"),
             pspan.get("walked_back_frames"), ev["fo3"], ev["fo4"], ev["trigger"],
             ev["gate_l"], ev["gate_r"], ev["direction"], ev["stratum"]))

print("\nSTRATA (pre-registered):", tally)
n = sum(v for k, v in tally.items() if k in ("ADDRESSABLE", "UNADDRESSABLE", "OTHER"))
if n:
    a = tally.get("ADDRESSABLE", 0)
    print("EXPOSURE: %d/%d = %.0f%% of champion deaths are ones DRPROPH could ever touch."
          % (a, n, 100.0 * a / n))
