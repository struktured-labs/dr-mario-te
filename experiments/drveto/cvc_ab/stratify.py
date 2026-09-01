"""Score every champion death into the pre-registered strata (PREREG_STRATA.md)."""
import csv, glob, os, sys
import sys
import adjudicate as A, eligibility as E, rounds

# ⚠ BLINDED BY DEFAULT. Printing each death with its ARM, or strata per arm,
# hands over the endpoint numerator per arm just as surely as printing the rate.
UNBLIND = "--unblind" in sys.argv

rows = [r for f in ("ab_samples_L20_seg1_TRUNC.csv", "ab_samples_L20_TRUNC.csv")
        if os.path.exists(f) for r in csv.DictReader(open(f))]
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
# ⚠⚠ REFUSES TO RUN BELOW THE FLOOR. This is an ANALYSIS tool, not a status tool, and
# it has the same repetition leak as a pooled tally: run it twice across a block and the
# NEW deaths that appear all belong to the arm that was live -- a single-arm numerator,
# recovered by differencing two runs. Suppressing the arm column does not help, because
# WHICH ARM WAS LIVE is knowable from the clock. Gate the whole tool instead.
FLOOR = 120
_rounds = {}
for (a, b), ser in blocks.items():
    _rounds[a] = _rounds.get(a, 0) + len(rounds.transitions(ser))
if not UNBLIND and any(n < FLOOR for n in _rounds.values()):
    print("STRATIFY WITHHELD -- below the %d-round floor (%s)." % (
        FLOOR, ", ".join("%s %d" % kv for kv in sorted(_rounds.items()))))
    print("Re-running this across a block boundary and differencing recovers the live")
    print("arm's death counts, so the tool is gated whole rather than field-by-field.")
    print("Use --unblind at the stop; its use is stamped into UNBLIND_LOG.txt.")
    raise SystemExit(0)
if UNBLIND:
    import datetime as _dt
    open("UNBLIND_LOG.txt", "a").write("%s  stratify --unblind; rounds=%s\n" % (
        _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), _rounds))
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
        print("  %s %sepoch=%.0f  video says %s -- SKIPPED (poll/video disagree)"
              % (tag, ("arm=%-8s " % arm) if UNBLIND else "", ep, d.get("verdict")))
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
    print("  %s %sv_left=%-3s hold=%-4ss span[win=%ss hold=%sf back=%sf] "
          "fo3=%-2d fo4=%-2d trig=%-5s gateL=%-5s gateR=%-5s dir=%-5s -> %s"
          % (tag, ("arm=%-8s " % arm) if UNBLIND else "", vleft, d["hold_s"],
             sp.get("window_s"), sp.get("hold_frames"), pspan.get("walked_back_frames"),
             ev["fo3"], ev["fo4"], ev["trigger"], ev["gate_l"], ev["gate_r"],
             ev["direction"], ev["stratum"]))

print("\nSTRATA (pre-registered), POOLED ACROSS ARMS unless --unblind:", tally)
if not UNBLIND:
    print("Per-arm strata are WITHHELD below the floor -- see PREREG_READ.md. The arm")
    print("column is suppressed for the same reason: it is the endpoint numerator.")
n = sum(v for k, v in tally.items() if k in ("ADDRESSABLE", "UNADDRESSABLE", "OTHER"))
if n:
    a = tally.get("ADDRESSABLE", 0)
    print("EXPOSURE: %d/%d = %.0f%% of champion deaths are ones DRPROPH could ever touch."
          % (a, n, 100.0 * a / n))
