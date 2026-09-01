"""Adjudicate one death on the 1080p60 capture, indexed by a poll transition.

The counter poll gives a round-boundary TIMESTAMP; this cuts the video around it,
walks frames to find the exact reset, steps back to the last live frame, and reads
that board. That is the mechanism evidence the 10 s poll cannot give: which seat,
which cells, and whether the throat was plugged.

⚠ A GROWING MKV HAS NO DURATION HEADER AND NO SEEK INDEX -- `-sseof` lands at the
FILE START. Always `ffmpeg -ss <hh:mm:ss> -i <file> -c copy seg.mkv`, then work
inside the segment.
"""
import datetime, os, subprocess, sys
import vid_ocr

HOST = "blackmage"
VIDDIR = "~/Videos/drmario_sessions"
VIDEO = "20260831_182902_struktured_v6c_part2.mkv"
# OBS names the file at recording start, local time (EDT = UTC-4).
VIDEO_T0 = datetime.datetime(2026, 8, 31, 18, 29, 2) + datetime.timedelta(hours=4)
BASE = os.path.dirname(os.path.abspath(__file__))
REMOTE_TMP = "/tmp/drseg"


def sh(cmd, timeout=600):
    return subprocess.run(["ssh", HOST, cmd], capture_output=True, text=True, timeout=timeout)


def cut_and_extract(epoch, pre=25, post=10, fps=10, tag="adj"):
    """Return [(t_utc, local_png)] around `epoch`, newest cut each call."""
    t = datetime.datetime.utcfromtimestamp(epoch)
    start = (t - VIDEO_T0).total_seconds() - pre
    hh = str(datetime.timedelta(seconds=int(start)))
    dur = pre + post
    sh("mkdir -p %s && rm -f %s/%s_*.png" % (REMOTE_TMP, REMOTE_TMP, tag))
    r = sh("cd %s && ffmpeg -y -loglevel error -ss %s -i %s -t %d -c copy %s/%s.mkv"
           % (VIDDIR, hh, VIDEO, dur, REMOTE_TMP, tag))
    if r.returncode:
        raise SystemExit("cut failed: " + r.stderr[-400:])
    r = sh("cd %s && ffmpeg -y -loglevel error -i %s.mkv -vf fps=%d %s_%%04d.png && ls %s_*.png | wc -l"
           % (REMOTE_TMP, tag, fps, tag, tag))
    n = int(r.stdout.strip().split()[-1])
    local = os.path.join(BASE, "adjframes")
    os.makedirs(local, exist_ok=True)
    subprocess.run("rm -f %s/%s_*.png" % (local, tag), shell=True)
    subprocess.run(["scp", "-q", "%s:%s/%s_*.png" % (HOST, REMOTE_TMP, tag), local + "/"],
                   check=True, timeout=900)
    out = []
    t_start = VIDEO_T0 + datetime.timedelta(seconds=start)
    for i in range(1, n + 1):
        p = os.path.join(local, "%s_%04d.png" % (tag, i))
        if os.path.exists(p):
            out.append((t_start + datetime.timedelta(seconds=(i - 1) / fps), p))
    return out


def adjudicate(epoch, fps=10, tag="adj"):
    frames = cut_and_extract(epoch, fps=fps, tag=tag)
    reads = [(t, p, vid_ocr.read_frame(p)) for t, p in frames]
    live = [(t, p, r) for t, p, r in reads if r["ok"] and r["p1"] is not None and r["p2"] is not None]
    if len(live) < 3:
        return {"error": "not enough readable frames", "n": len(live)}
    # the reset: first frame whose counts jump UP versus the running minimum
    reset = None
    for i in range(1, len(live)):
        if live[i][2]["p1"] > live[i - 1][2]["p1"] or live[i][2]["p2"] > live[i - 1][2]["p2"]:
            reset = i
            break
    if reset is None:
        return {"error": "no reset inside the window",
                "first": live[0][2], "last": live[-1][2]}
    t_last, p_last, r_last = live[reset - 1]
    return {"reset_t": live[reset][0].strftime("%H:%M:%SZ"),
            "last_live_t": t_last.strftime("%H:%M:%S.%fZ")[:-4],
            "last_frame": p_last, "last_read": r_last,
            "n_frames": len(live)}


if __name__ == "__main__":
    ep = float(sys.argv[1])
    a = adjudicate(ep, tag=sys.argv[2] if len(sys.argv) > 2 else "adj")
    for k, v in a.items():
        print("%-14s %s" % (k, v))
