"""DRPROPH CvC A/B: alternating-block soak with a virus-counter poller.

ARMS differ ONLY in DRPROPH. Both are built by the SAME emitter, so the 3-byte
FC_STAB relocation that separates this lineage from silicon's 70a857cc is COMMON
to both arms and cancels. (Using 70a857cc as the control would have confounded the
flag with the lineage.)

ONE STABLE MGL, REWRITTEN PER BLOCK. freeze_watch is pointed at
/media/fat/dblcanon_ab_soak.mgl once and never touched again; each block rewrites
that file's <file> line to name the current arm's cart. So if the watcher
auto-reloads after a freeze it reloads the CURRENT arm, and no watcher restart is
ever needed mid-run (a restart is the step most likely to wedge the box).

⛔ Never `input dpad`/`button` -- that kills MiSTer main with no self-recovery.
Core loads go through ssh + /dev/MiSTer_cmd, menu-cycled (a bare reload
mid-invocation is the BUSY-latch soft-brick trigger).
"""
import base64, csv, os, subprocess, sys, time
import virus_ocr

HOST = "bluemage"
MGL = "/media/fat/dblcanon_ab_soak.mgl"
RBF = "_Console/NES_theta400dblcanon_veto2fixa_20260830"
ARMS = {"proph": "drmario_prophcvc_f2a16c00.nes",
        "noproph": "drmario_cvc_noproph_858990bf.nes"}
BASE = os.path.dirname(os.path.abspath(__file__))
CSVP = os.path.join(BASE, "ab_samples.csv")
TMPPNG = os.path.join(BASE, ".poll.png")
POLL_S = 15
BLOCK_S = int(os.environ.get("BLOCK_MIN", "30")) * 60


def sh(cmd, timeout=60):
    return subprocess.run(["ssh", HOST, cmd], capture_output=True, text=True, timeout=timeout)


def log(msg):
    print("%s %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def note(msg):
    """Mark the shared freeze_watch log so the soak record and the A/B agree."""
    sh("echo '=== %s %s ===' >> /media/fat/freeze_watch.log"
       % (msg, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))


def set_arm(arm):
    cart = ARMS[arm]
    sh("printf '%%s\\n' '<mistergamedescription>' "
       "'    <rbf>%s</rbf>' "
       "'    <file delay=\"2\" type=\"f\" index=\"1\" path=\"%s\"/>' "
       "'</mistergamedescription>' > %s; chmod 755 %s" % (RBF, cart, MGL, MGL))
    got = sh("cat %s" % MGL).stdout
    assert cart in got, "mgl did not take the arm cart: %r" % got
    sh("echo 'load_core /media/fat/menu.rbf' > /dev/MiSTer_cmd"); time.sleep(12)
    sh("echo 'load_core %s' > /dev/MiSTer_cmd" % MGL); time.sleep(20)
    note("AB BLOCK arm=%s cart=%s" % (arm, cart))
    log("arm -> %s (%s)" % (arm, cart))


def sample():
    """One (counts, fill) reading. Returns None on any failure -- a failed sample
    is a gap, and the detector tolerates gaps by construction."""
    r = sh("echo screenshot > /dev/MiSTer_cmd; sleep 3; "
           "f=$(ls -t /media/fat/screenshots/NES/*.png 2>/dev/null | head -1); "
           "[ -n \"$f\" ] && base64 \"$f\"", timeout=45)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        open(TMPPNG, "wb").write(base64.b64decode(r.stdout))
        return virus_ocr.read_frame(TMPPNG)
    except Exception:
        return None


def main():
    order = sys.argv[1:] or ["proph", "noproph"]
    new = not os.path.exists(CSVP)
    f = open(CSVP, "a", newline="")
    w = csv.writer(f)
    if new:
        w.writerow(["t_epoch", "iso", "arm", "block", "p1", "p2", "fill_p1", "fill_p2",
                    "throat_p1", "throat_p2", "topcells_p1", "topcells_p2"])
        f.flush()
    note("AB SOAK START arms=%s block=%dmin poll=%ds" % ("/".join(order), BLOCK_S // 60, POLL_S))
    block = 0
    try:
        while True:
            arm = order[block % len(order)]
            set_arm(arm)
            t_end = time.time() + BLOCK_S
            n = bad = 0
            while time.time() < t_end:
                s = sample()
                if s is None or not s.get("ok"):
                    bad += 1
                else:
                    w.writerow([round(time.time(), 1),
                                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                arm, block, s["p1"], s["p2"],
                                round(s["fill"]["p1"], 4), round(s["fill"]["p2"], 4),
                                int(s["throat_p1"]), int(s["throat_p2"]),
                                s["topcells_p1"], s["topcells_p2"]])
                    f.flush(); n += 1
                time.sleep(POLL_S)
            log("block %d (%s) done: %d samples, %d failed" % (block, arm, n, bad))
            block += 1
    except KeyboardInterrupt:
        note("AB SOAK STOPPED")
    finally:
        f.close()


if __name__ == "__main__":
    main()
