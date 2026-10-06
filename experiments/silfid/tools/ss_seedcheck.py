#!/usr/bin/env python3
"""silfid: are the usable save-state samples SEED-SENSITIVE? Re-run each usable sample's upload with the seed nibbles
forced to 0 (and, optionally, on a second firmware dir), and judge silicon's live answer against those timelines too.
  ss_seedcheck.py IN.json OUT.json      (IN = ss_cosim.py --json output; env FWDIR2 = optional extra firmware dir)"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ss_cosim as SC

def zero_seed(line):
    t = line.split(); t[0] = str(int(t[0]) & 0x0F); t[1] = str(int(t[1]) & 0x0F); return " ".join(t)

def main():
    rows = json.load(open(sys.argv[1])); out = sys.argv[2]
    use = [r for r in rows if r.get("upload")]
    jobs = [("seed0", zero_seed(r["upload"]), SC.FWDIR) for r in use]
    fw2 = os.environ.get("FWDIR2")
    if fw2:
        jobs += [("fw2", r["upload"], fw2) for r in use]
    def run(j):
        tag, line, fwdir = j
        old = SC.FWDIR; SC.FWDIR = fwdir
        try:
            return SC.cosim(line)
        finally:
            SC.FWDIR = old
    with ThreadPoolExecutor(int(os.environ.get("J", "5"))) as ex:
        res = list(ex.map(run, jobs))
    n = len(use)
    for k, r in enumerate(use):
        for i, tag in enumerate(["seed0"] + (["fw2"] if fw2 else [])):
            pubs, done = res[k + i * n]
            r[f"{tag}_status"] = SC.judge(pubs, done, r["t_frames"], r["col"], r["o4"], 1.0)
            r[f"{tag}_pubs"] = [(round(tt, 2), c, o) for tt, c, o in pubs]
            r[f"{tag}_done"] = (round(done[0], 2), done[1], done[2])
            r[f"{tag}_same_timeline"] = ([(c, o) for _, c, o in pubs] == [(c, o) for _, c, o in r["cosim_pubs"]]
                                         and r[f"{tag}_done"][1:] == tuple(r["cosim_done"][1:]))
    json.dump(rows, open(out, "w"), indent=1)
    for r in use:
        print(r["file"], r["status"], "| seed0:", r["seed0_status"], "same" if r["seed0_same_timeline"] else "DIFF",
              "" if not fw2 else f"| fw2: {r['fw2_status']} {'same' if r['fw2_same_timeline'] else 'DIFF'}")
    for tag in ["seed0"] + (["fw2"] if fw2 else []):
        diff = [r for r in use if not r[f"{tag}_same_timeline"]]
        print(f"{tag}: timeline differs from the real-seed one on {len(diff)}/{n}; silicon status under {tag}:",
              {s: sum(1 for r in use if r[f'{tag}_status'] == s) for s in set(r[f'{tag}_status'] for r in use)})

if __name__ == "__main__":
    main()
