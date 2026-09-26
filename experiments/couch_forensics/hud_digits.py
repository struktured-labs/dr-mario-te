"""Read the HUD virus counters (P1 = the owner, P2 = the AI) from the couch captures.

Digit boxes (1080p pillarboxed capture, measured on 2026-09-26): each digit is one NES tile (8 x 8 NES px =
43.8 x 38.57 video px). Left edges x = 859 / 903 (P1 tens / ones), 975 / 1019 (P2 tens / ones); top y = 880.5.
A digit is reduced to an 8x8 dark-pixel mask (median of a 3x3 window at each NES-pixel centre).
Templates are harvested from P2's counter, whose value the validated board reader supplies, and then applied
to P1 (same font).

  python hud_digits.py scan VIDEO T0 DUR OUT.jsonl        # 2 fps masks (nice 19 / -threads 1 by caller)
"""
import json
import subprocess
import sys

import numpy as np

SX, SY = 5.475, 4.8214
BOX_X = {"p1t": 859.0, "p1o": 903.0, "p2t": 975.0, "p2o": 1019.0}
BOX_Y = 880.5
CX0, CY0, CW, CH = 850, 870, 230, 60        # crop that contains all four digits


def masks(im, x_off=CX0, y_off=CY0):
    out = {}
    for k, x0 in BOX_X.items():
        m = np.zeros((8, 8), np.int8)
        for j in range(8):
            for i in range(8):
                cx = int(x0 - x_off + (i + 0.5) * SX); cy = int(BOX_Y - y_off + (j + 0.5) * SY)
                p = im[cy - 1:cy + 2, cx - 1:cx + 2].reshape(-1, 3)
                m[j, i] = 1 if np.median(p.sum(1)) < 200 else 0
        out[k] = "".join(str(int(v)) for v in m.ravel())
    return out


def scan(video, t0, dur, out, fps=2):
    cmd = ["ffmpeg", "-v", "error", "-threads", "1", "-ss", str(t0), "-i", video, "-t", str(dur),
           "-vf", f"fps={fps},crop={CW}:{CH}:{CX0}:{CY0}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = CW * CH * 3; i = 0
    with open(out, "w") as fh:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            im = np.frombuffer(b, np.uint8).reshape(CH, CW, 3).astype(int)
            fh.write(json.dumps({"t": round(float(t0) + i / fps, 3), **masks(im)}) + "\n"); i += 1
    p.wait()
    print(f"{i} samples -> {out}")


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def build_templates(samples, p2_counts, tol_s=0.6):
    """samples: [{t, p1t, p1o, p2t, p2o}]; p2_counts: sorted [(t, count)] from the validated board reader,
    restricted to stable stretches. Majority mask per digit value, from P2 tens and ones."""
    import bisect
    ts = [t for t, _ in p2_counts]
    votes = {}
    for s in samples:
        i = bisect.bisect_left(ts, s["t"])
        cand = [p2_counts[j] for j in (i - 1, i) if 0 <= j < len(ts) and abs(ts[j] - s["t"]) <= tol_s]
        if not cand:
            continue
        c = cand[0][1]
        for key, dig in (("p2t", c // 10), ("p2o", c % 10)):
            votes.setdefault(dig, []).append(s[key])
    tpl = {}
    for dig, ms in votes.items():
        arr = np.array([[int(ch) for ch in m] for m in ms])
        tpl[dig] = "".join(str(int(v)) for v in (arr.mean(0) >= 0.5))
    return tpl, {d: len(v) for d, v in votes.items()}


def read_digit(mask, tpl, max_dist=6):
    best = min(tpl.items(), key=lambda kv: hamming(mask, kv[1]))
    d = hamming(mask, best[1])
    return (best[0], d) if d <= max_dist else (None, d)


if __name__ == "__main__":
    if sys.argv[1] == "scan":
        scan(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5])
