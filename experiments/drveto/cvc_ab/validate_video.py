"""Validation for the 1080p60 video decoder (R92: measure the null).

The MiSTer-grab decoder and this one are INDEPENDENT instruments -- different
capture path, different resolution, different matcher -- so their agreement on the
same instant is the strongest check available, and it is the one that matters
before any death is adjudicated from footage.
"""
import glob
import numpy as np
from PIL import Image
import vid_ocr as V

ok = True
def check(label, cond, detail=""):
    global ok
    print("  %-58s %s%s" % (label, "PASS" if cond else "FAIL", ("  " + detail) if detail else ""))
    ok &= bool(cond)

print("\n-- A. hand-read 1080p frame --")
r = V.read_frame("vid_f300.png")
check("decoder reproduces the hand-read (P1=46, P2=43)", r["p1"] == 46 and r["p2"] == 43,
      "got %s/%s" % (r["p1"], r["p2"]))

print("\n-- B. CROSS-INSTRUMENT: video vs the MiSTer poller, same instant --")
# poller logged 00:05:24Z -> p1=47 p2=25; video frames xv_002..xv_006 span 00:05:21-25Z
agree = [V.read_frame(f) for f in sorted(glob.glob("xv_00[23456].png"))]
check("video reads 47/25 where the poller read 47/25",
      all(x["p1"] == 47 for x in agree) and any(x["p2"] == 25 for x in agree),
      "p2 values %s" % [x["p2"] for x in agree])

print("\n-- C. monotonicity null over 100 consecutive live frames --")
fs = sorted(glob.glob("adjframes/d1_*.png"))[:100]
reads = [V.read_frame(f) for f in fs]
readable = sum(1 for x in reads if x["p1"] is not None and x["p2"] is not None)
viol = 0
for seat in ("p1", "p2"):
    seq = [x[seat] for x in reads if x[seat] is not None]
    viol += sum(1 for i in range(1, len(seq)) if seq[i] > seq[i - 1])
check("100%% of live frames readable", readable == len(fs), "%d/%d" % (readable, len(fs)))
check("ZERO mid-round count increases (each would be a misread)", viol == 0, "%d" % viol)

print("\n-- D. rejection: a non-digit cell must return None --")
a = np.array(Image.open("vid_f300.png").convert("RGB")).astype(int)
b = a.copy(); b[880:940, 850:1080] = 0
check("blanked counter box -> both seats None", V.read_counts(b) == {"p1": None, "p2": None})

print("\n-- E. the adjudicated death frame --")
d = V.read_frame("adjframes/d1_0070.png")
check("counts read 47/19 as the image plainly shows", d["p1"] == 47 and d["p2"] == 19)
check("P1 throat occupied with a full top (the plug)", d["throat_p1"] and d["topcells_p1"] >= 12,
      "topcells=%d" % d["topcells_p1"])
check("P2 top rows empty (it did not die)", d["topcells_p2"] == 0)

print("\n" + ("VIDEO DECODER VALIDATION: ALL PASS" if ok else "VIDEO DECODER VALIDATION: FAILED"))
raise SystemExit(0 if ok else 1)
