#!/usr/bin/env python3
"""Chained (one copro process) Verilator replay of logged DRPUBLOG pills on silicon's own GO schedule.

  publog_chain.py PILLS.json OUT.jsonl SEQ[,SEQ...] [--lead 3]
For each target seq, the `lead` pills before it and the target itself are run in ONE vsim_chain process
(experiments/abortstale's sim_pubchain: board bytes ~18 NES cycles apart, the upload WAITS for the previous DONE --
cart D's driver), each GO placed at its logged hook-counter distance from the previous GO (hooks / 2 frames). The
question: does the copro's state carried over from the previous search (silicon's reality) change a search's
publications or its DONE time, compared with the fresh-process co-sim ss_cosim.py --publog uses?"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/home/struktured/projects/dr-mario-execfid-wt/experiments/abortstale")
import chain_cosim as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import publog as PL

FW = "/home/struktured/projects/dr_mario_rl/tmp/silfid/cosim/fw1488/copro_rom.hex"


def main():
    pills = {p["seq"]: p for p in json.load(open(sys.argv[1]))}
    out = sys.argv[2]
    targets = [int(x) for x in sys.argv[3].split(",")]
    lead = int(sys.argv[sys.argv.index("--lead") + 1]) if "--lead" in sys.argv else 3
    jobs = []
    for t in targets:
        seqs = [s for s in range(t - lead, t + 1) if s in pills]
        if seqs[-1] != t:
            continue
        lines = []
        for i, s in enumerate(seqs):
            if i == 0:
                go_at = 0
            else:
                dh = (pills[s]["hookctr"] - pills[seqs[i - 1]]["hookctr"]) & 0xFFFF
                go_at = int(round(dh / 2.0 * C.FRAME))
            lines.append(f"{go_at} 0 {PL.upload_line(pills[s])}")
        jobs.append((t, seqs, lines))
    with ThreadPoolExecutor(int(os.environ.get("J", "3"))) as ex:
        res = list(ex.map(lambda j: C.sim(FW, j[2], 18), jobs))
    with open(out, "a") as f:
        for (t, seqs, _), reps in zip(jobs, res):
            for s, d in zip(seqs, reps):
                r = C.record(s, d, target=t)
                r.pop("raw", None)
                f.write(json.dumps(r) + "\n")
            d = reps[-1]
            print(f"target {t}: chained DONE {d['end_clk'] / C.FRAME:.2f} f, final ({d['col']},{d['o4']}), "
                  f"pubs {C.convert(d['raw'])}", flush=True)


if __name__ == "__main__":
    main()
