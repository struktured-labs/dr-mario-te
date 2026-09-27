"""Did proph_pulse actually PRESS, or did the trigger merely arm?

⚠⚠ RESULT: INDETERMINATE, and this file is kept as the record of WHY, plus a warning.

FIRST IMPLEMENTATION PRODUCED CONFIDENT GARBAGE. It took "the last contiguous run of
occupied spawn rows" as the lock window and any change in the occupied-column SET as
lateral motion. That returned FIRED_AND_FAILED for both deaths -- with a "lock window"
of 462 frames (7.7 s), which is the GAME-OVER HOLD, and with "motion" that was really
(3,4) -> (3,) decode flicker while min(col) never moved off 3. Two confident labels, both
artifacts.

BOUNDED PROPERLY (find the lock = first throat occupancy that persists, then look
BACKWARD), the honest answer is that the question cannot be asked of this footage:
**the fatal capsule is visible in the throat for ZERO frames before it locks, at 60 fps,
on BOTH deaths.** It appears in its final cells in a single frame transition -- spawn
position IS lock position, on a row-1 ledge (fo3 = 1). So there is no pre-lock trajectory
to inspect, and a press that was issued but had no time to take effect is
indistinguishable from no press at all.

Per PREREG_READ.md this is an INSTRUMENT LIMIT and is NOT converted into evidence for
either branch. What it does establish, and is worth its own line, is the death class:
the capsule spawns ALREADY AT REST and locks with no observable travel -- the spawn-plug
parking class in its purest form.
"""
_ORIGINAL_DOCSTRING = """Did proph_pulse actually PRESS, or did the trigger merely arm?

Pre-specified in PREREG_READ.md. Trigger arming is board-determined and already known;
proph_pulse presses only inside the driver's no-answer window, so arming does not imply
pressing. The observable consequence of a press is LATERAL MOTION of the fatal capsule
in the throat before it locks. Track the active capsule's column at 60 fps from spawn
to lock.
"""
import glob, os, sys
import numpy as np
from PIL import Image
import adjudicate as A, vid_ocr as V, eligibility as E

OCC = 0.25

def top_cols(grid, rows=(0, 1)):
    """columns occupied in the spawn rows -- the active capsule while it is up there."""
    return {c for r in rows for c in range(8) if grid[r][c] > OCC}

def firecheck(epoch, tag, fps=60, pre=6, post=2):
    frames = A.cut_and_extract(epoch, pre=pre, post=post, fps=fps, tag=tag)
    seq = []
    for t, p in frames:
        a = np.array(Image.open(p).convert("RGB")).astype(int)
        g = V.cell_grid(a, "p2", 16)
        seq.append((t, p, g, top_cols(g)))
    # the lock: last frames before the throat stays occupied. Walk to the END of the
    # window and find the final contiguous stretch where the spawn rows are occupied.
    occupied = [i for i, s in enumerate(seq) if s[3]]
    if not occupied:
        return {"verdict": "INDETERMINATE", "why": "capsule never resolved in the spawn rows"}
    # contiguous run ending at the last occupied frame
    end = occupied[-1]
    start = end
    while start - 1 >= 0 and seq[start - 1][3]:
        start -= 1
    cols = [tuple(sorted(seq[i][3])) for i in range(start, end + 1)]
    n = end - start + 1
    if n < 3:
        return {"verdict": "INDETERMINATE", "why": "lock window %d frames (<3)" % n}
    moved = len({c for c in cols}) > 1
    # a lateral MOVE means the occupied column SET shifts sideways, not just grows
    mins = [min(c) for c in cols if c]
    lateral = len(set(mins)) > 1
    return {"verdict": "FIRED_AND_FAILED" if lateral else "NEVER_ENGAGED",
            "window_frames": n, "window_s": round(n / float(fps), 3),
            "col_sets": cols[:12], "min_col_track": mins[:12], "any_change": moved}

if __name__ == "__main__":
    for ep, tag in [(int(x.split(":")[0]), x.split(":")[1]) for x in sys.argv[1:]]:
        r = firecheck(ep, tag)
        print("epoch %d -> %-17s %s" % (ep, r["verdict"],
              {k: v for k, v in r.items() if k != "verdict"}))
