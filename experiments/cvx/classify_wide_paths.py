"""Classify a quartus_sta per-ENDPOINT report (report_timing -nworst 1, see chain540_reach_tap_hsv_paths.tcl)
for the DRHSV fit: which failing endpoints the timing fallback removes, and what floor it leaves.

  python classify_wide_paths.py worst_paths_seedN.txt.wide [bar]

Removed by the fallback:
  DSP        endpoint is a DSP input-register enable/data (Mult*~..|ENA_DFF*): DRLEV_SQREG feeds sq() from
             enable-free copies, so these endpoints stop being driven by the walk's update decision.
  HOSTWR     source in copro6502 (the 6502 bus decode), endpoint in LeafEval bcell/blink/slot: DRLEV_WRREG
             registers the host write, so the path ends at the h_* flops instead.
NOT removed (the floor):
  everything else, grouped by (source kind -> endpoint register base name).
"""
import re
import sys
from collections import defaultdict

ROW = re.compile(r"^;\s*(-?\d+\.\d+)\s*;\s*([^;]+?)\s*;\s*([^;]+?)\s*;")


def base(node):
    leaf = node.split("|")[-1]
    leaf = re.sub(r"_OTERM\d+.*|_NEW_REG\d+.*|~DUPLICATE.*|~_Duplicate_\d+|~\d+", "", leaf)
    return re.sub(r"\[\d+\]", "[]", leaf)


def kind(src, dst):
    if "ENA_DFF" in dst or re.search(r"\|Mult\d+", dst):
        return "DSP"
    if ("cpu6502" in src or "copro6502" in src) and ("leafeval" in dst.lower()):
        return "HOSTWR"
    return "FLOOR"


def main():
    path = sys.argv[1]; bar = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10
    rows = [(float(m.group(1)), m.group(2), m.group(3)) for m in map(ROW.match, open(path, errors="replace")) if m]
    if not rows:
        print("no rows parsed from", path); return 2
    fail = [r for r in rows if r[0] < bar]
    print("%s: %d endpoints parsed, %d below the +%.2f bar, worst %.3f" % (path, len(rows), len(fail), bar, rows[0][0]))
    by = defaultdict(list)
    for s, a, b in fail:
        k = kind(a, b)
        grp = k if k != "FLOOR" else "FLOOR %s -> %s" % ("copro6502" if "cpu6502" in a or "copro6502" in a
                                                           else base(a), base(b))
        by[grp].append(s)
    for g, v in sorted(by.items(), key=lambda kv: min(kv[1])):
        print("  %-60s n=%-4d worst %.3f" % (g, len(v), min(v)))
    floor = [s for s, a, b in rows if kind(a, b) == "FLOOR"]
    print("PREDICTED post-fallback floor (worst endpoint the fallback does not remove, SAME placement): %.3f"
          % (min(floor) if floor else float("nan")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
