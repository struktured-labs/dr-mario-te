"""Stream a window of the couch recording through reader.Reader at full 60 fps, no frame files.

Usage: python scan_frames.py VIDEO T_START DURATION OUT.jsonl
One JSON line per frame: t (s, = T_START + i/60), color/virus/link as 128-char strings (row-major),
prev (preview colours), prev_link.
"""
import json
import subprocess
import sys

import numpy as np

import reader as R

X_OFF, Y_OFF, W, H = 1120, 190, 380, 790


def main(video, t0, dur, out):
    rd = R.Reader(X_OFF, Y_OFF)
    cmd = ["ffmpeg", "-v", "error", "-threads", "1", "-ss", str(t0), "-i", video, "-t", str(dur),
           "-vf", f"crop={W}:{H}:{X_OFF}:{Y_OFF}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    i = 0
    with open(out, "w") as fh:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            im = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(int)
            x = rd.read(im)
            fh.write(json.dumps({
                "i": i, "t": round(float(t0) + i / 60.0, 4),
                "color": "".join(str(int(v)) for v in x["color"].ravel()),
                "virus": "".join("1" if v else "0" for v in x["virus"].ravel()),
                "link": "".join(str(int(v)) for v in x["link"].ravel()),
                "prev": x["prev"], "prev_link": x["prev_link"]}) + "\n")
            i += 1
    p.wait()
    print(f"frames {i}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4])
