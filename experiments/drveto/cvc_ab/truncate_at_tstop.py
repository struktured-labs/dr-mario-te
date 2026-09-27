"""Truncate the dataset at T_stop. Determined BLIND (find_tstop.py, round counts only)
and applied BEFORE anything is unblinded -- which is what keeps it legitimate."""
import csv, os
T = float(open("T_STOP.txt").read().split("\n")[0])
for f in ("ab_samples_L20_seg1.csv", "ab_samples_L20.csv"):
    if not os.path.exists(f):
        continue
    rows = list(csv.DictReader(open(f)))
    keep = [r for r in rows if float(r["t_epoch"]) <= T]
    out = f.replace(".csv", "_TRUNC.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(keep)
    print("%-28s %5d -> %5d samples kept (%d dropped as out of protocol)"
          % (f, len(rows), len(keep), len(rows) - len(keep)))
