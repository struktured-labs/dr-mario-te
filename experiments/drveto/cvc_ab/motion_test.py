"""Does the video adjudicator's HOLD detector behave differently on a PULSING capsule?

⚠ WHY GEOMETRY WAS THE WRONG AXIS: DRPROPH's effect is on MOTION, not on static board
features. By construction (Amendment B) it PULSES the direction 1 frame on / 1 frame off,
phase-keyed to $43 parity. Two boards can be geometrically identical while one contains a
capsule twitching at 30 Hz -- invisible to geometry matching, and precisely the input most
likely to confuse a persistence ("hold") test.

MEASURE: per-frame lateral position of P2's active capsule in the settle window at 60 fps,
then the PERIOD-2 ALTERNATION rate -- the pulse's signature, not merely "movement".
BLIND: motion is computed with the arm stripped; the label is joined back only at analysis.
"""
import csv, os, random, re, sys
import numpy as np
from PIL import Image
import adjudicate as A, vid_ocr as V, rounds, reloads

def occ_cols(g, rows=(0, 1, 2), t=0.25):
    return [c for r in rows for c in range(8) if g[r][c] > t]

def motion_profile(epoch, tag, pre=3.0, fps=60):
    """Return (n_frames, alternation_rate, mean_abs_step) for P2's top-rows centroid."""
    frames = A.cut_and_extract(epoch, pre=pre, post=0.5, fps=fps, tag=tag)
    cent = []
    for t, p in frames:
        a = np.array(Image.open(p).convert("RGB")).astype(int)
        cs = occ_cols(V.cell_grid(a, "p2", 3))
        cent.append(sum(cs) / len(cs) if cs else None)
    seq = [c for c in cent if c is not None]
    if len(seq) < 8:
        return None
    steps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    moves = [s for s in steps if abs(s) > 0.05]
    # PERIOD-2 ALTERNATION: consecutive non-zero steps that reverse sign = a pulse, not drift
    alt = sum(1 for i in range(len(steps) - 1)
              if abs(steps[i]) > 0.05 and abs(steps[i + 1]) > 0.05
              and steps[i] * steps[i + 1] < 0)
    return dict(n=len(seq), alt=alt,
                alt_rate=alt / max(1, len(steps) - 1),
                move_rate=len(moves) / max(1, len(steps)))

if __name__ == "__main__":
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
    deaths = [(a, rec) for (a, b), ser in sorted(blocks.items(), key=lambda kv: kv[0][1])
              for rec in rounds.transitions(ser) if rec["outcome"] == "TOPOUT_P2"]
    log = open("stratify_primary.log").read()
    dis = {m.group(1) for m in re.finditer(r"epoch=(\d+)\s+video says", log)}
    random.seed(23)
    by = {}
    for i, (a, rec) in enumerate(deaths):
        by.setdefault(a, []).append((i, a, rec))
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    sel = [x for a in sorted(by) for x in random.sample(by[a], min(N, len(by[a])))]
    print("motion-profiling %d deaths (%d per arm), 60 fps\n" % (len(sel), N), flush=True)
    for i, a, rec in sel:
        ep = "%.0f" % rec["end"]
        mp = motion_profile(rec["end"], "M%02d" % i)
        d = "DISAGREE" if ep in dis else "agree"
        if mp is None:
            print("  M%02d arm=%-8s %-8s  (too few readable frames)" % (i, a, d), flush=True); continue
        print("  M%02d arm=%-8s %-8s  n=%-3d alt=%-3d alt_rate=%.3f move_rate=%.3f"
              % (i, a, d, mp["n"], mp["alt"], mp["alt_rate"], mp["move_rate"]), flush=True)
