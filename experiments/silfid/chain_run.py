"""Run chain_cosim.py `run` with GO frames taken from a silfid probe log's GO lines (case + prefetch GOs mapped to pills)."""
import sys, re
sys.path.insert(0, "/home/struktured/projects/dr-mario-execfid-wt/experiments/abortstale")
import chain_cosim as C

def go_frames(log):
    go, last_inj, pending_pref = {}, None, None
    for ln in open(log, errors="replace"):
        m = re.match(r"^INJECT p(\d+) at f=(\d+)", ln)
        if m:
            last_inj = int(m.group(1))
            if pending_pref is not None and last_inj not in go:
                go[last_inj] = pending_pref
            pending_pref = None
            continue
        m = re.match(r"^GO n=\d+ f=(\d+) kind=(\w+)", ln)
        if m:
            f, kind = int(m.group(1)), m.group(2)
            if kind == "prefetch":
                pending_pref = f
            elif kind == "case" and last_inj is not None and last_inj not in go:
                go[last_inj] = f
    return go

C.mesen_go_frames = go_frames
if __name__ == "__main__":
    fw, tl, out, log = sys.argv[1:5]
    g = go_frames(log)
    print("GO frames for", len(g), "pills")
    C.cmd_run(fw, tl, out, "mesen:" + log, False, 18, None)
