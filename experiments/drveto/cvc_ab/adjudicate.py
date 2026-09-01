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


def find_death(epoch, pre=20, post=8, fps=10, tag="dz"):
    """Locate the DEATH that ends the round the poll indexed at `epoch`.

    Signature: the losing seat holds THROAT-OCCUPIED, counter still legible, for the
    whole game-over display -- measured 2.4-4.4 s. A spawning capsule sits in the
    throat for a fraction of a second, so a SUSTAINED hold cannot be mimicked.

    ⚠ DURATION IS THE DISCRIMINATOR, NOT THE CELL COUNT. My first cut also required
    topcells >= 6, borrowed from the poll rule, and MISSED a real death whose stack
    was narrow (3.9 s hold at topcells 4). The cell bar exists in the poll rule only
    because a 10 s sample has no duration to reason with; video has duration, so it
    keys on that. Bar 1.0 s = 3x the longest a capsule sits in the throat.

    ⚠⚠ AND THE SEARCH MUST BE BOUNDED BY THE RESET. At L20 rounds run 13-27 s, so any
    window wide enough to contain the boundary also contains NEIGHBOURING rounds.
    "Longest hold in the window" returned the wrong round's death (a TOPOUT_P1 for a
    round the poll indexed as a P2 boundary); "last hold in the window" then picked up
    the NEW round's brief post-reset spawn touches. The correct frame is: find the
    RESET (counts jump up), then take the last qualifying hold strictly BEFORE it.
    """
    frames = cut_and_extract(epoch, pre=pre, post=post, fps=fps, tag=tag)
    reads = [(t, p, vid_ocr.read_frame(p)) for t, p in frames]

    # locate the reset: a jump UP in either counter, scanning from the end backwards
    # so we take the boundary nearest the requested epoch.
    def legible(r):
        return r.get("ok") and r.get("p1") is not None and r.get("p2") is not None
    idx = [i for i, (_, _, r) in enumerate(reads) if legible(r)]
    reset_i = None
    for a, b in zip(idx, idx[1:]):
        if reads[b][2]["p1"] > reads[a][2]["p1"] or reads[b][2]["p2"] > reads[a][2]["p2"]:
            reset_i = b
    limit = reset_i if reset_i is not None else len(reads)

    best = None
    for seat in ("p1", "p2"):
        run_start = None
        for i in range(limit):
            r = reads[i][2]
            held = (r.get("ok") and r.get("throat_" + seat) and r.get(seat) is not None)
            if held:
                if run_start is None:
                    run_start = i
                n = i - run_start + 1
                if best is None or run_start > best[1] or (run_start == best[1] and n > best[2]):
                    best = (seat, run_start, n)
            else:
                run_start = None
    if best is None or best[2] < fps * 1.0:
        return {"verdict": "NO_PLUG_HOLD_FOUND", "n_frames": len(reads),
                "reset_found": reset_i is not None,
                "longest_hold_s": round((best[2] if best else 0) / float(fps), 2)}
    seat, i0, n = best
    t0, p0, r0 = reads[i0]
    return {"verdict": "TOPOUT_" + seat.upper(),
            "hold_s": round(n / float(fps), 2),
            "death_t": t0.strftime("%H:%M:%S.%f")[:-4] + "Z",
            "frame": p0, "read": r0,
            "topcells": r0.get("topcells_" + seat),
            "viruses_left": r0.get(seat)}
