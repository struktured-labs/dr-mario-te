#!/usr/bin/env python3
"""DRDANGER Verilator co-sim: the REAL copro RTL (vsim_pub2 = NES_MiSTer-dist 3b164c7 mappers + the shipped defines,
built by tools/lateflip/build_pubtrace.sh) runs each firmware hex on the py65 gate's exact boards/uploads (same
task list, same seed nibbles, same reach/tap/speed bits), DELTA path included (py65 cannot run it).
Usage: cosim_drdanger.py OUT.jsonl HEX [--big N] [--synth N] [-j J]
Each line: idx, kind, final (col, o), done_clk, first valid publish clk, publishes."""
import argparse, hashlib, json, os, random, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
VSIM = os.environ.get("VSIM", "/home/struktured/projects/dr-mario-lateflip-wt/tmp/pubtrace/obj_pub2/vsim_pub2")
TS = (0x10 | 1) ^ 0xA4                     # gate_reach_search.TS


def tasks(big, nsynth):
    sys.path.insert(0, HERE)
    import gate_drdanger as G                # task list + synth_tall (identical construction to the py65 gate)
    rows = [json.loads(l) for f in ("game_l11.jsonl", "game_l15.jsonl")
            for l in open(os.path.join(ROOT, "experiments", "reach", "corpus", f))]
    t = [("game", d["nes"], tuple(x - 1 for x in d["pills"]), (d["speed"], d["speedups"])) for d in rows]
    random.Random(7).shuffle(t)
    t = t[:big]
    t += G.synth_tall(nsynth, random.Random(20261013))
    RC = G.GDG.RC
    out = []
    for kind, nes, (cA, cB, nA, nB), (sp, su) in t:
        hiA, hiB = RC.pack_nibbles(sp, su); tp = 2
        hiA |= (tp & 3) << 2; hiB |= ((tp >> 2) & 3) << 2
        line = "%d %d %d %d %s" % (((TS & 0x0F) << 4) | cA, (TS & 0xF0) | cB, nA | hiA, nB | hiB,
                                   " ".join("%02x" % v for v in nes))
        out.append((kind, line))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("hex")
    ap.add_argument("--big", type=int, default=60); ap.add_argument("--synth", type=int, default=150)
    ap.add_argument("-j", type=int, default=8)
    a = ap.parse_args()
    md5 = hashlib.md5(open(a.hex, "rb").read()).hexdigest()
    simdir = os.path.join(ROOT, "tmp", "drdanger", "vsim", md5[:8]); os.makedirs(simdir, exist_ok=True)
    shutil.copy(a.hex, os.path.join(simdir, "copro_rom.hex"))
    T = tasks(a.big, a.synth)

    def run(line):
        p = subprocess.run(["nice", "-n", "19", VSIM, "64"], cwd=simdir, input=line + "\n", capture_output=True, text=True)
        return p.stdout.strip()
    with ThreadPoolExecutor(a.j) as ex:
        reps = list(ex.map(run, [l for _k, l in T]))
    with open(a.out, "w") as f:
        for i, ((kind, line), rep) in enumerate(zip(T, reps)):
            t = rep.split(); assert t[0] == "PUB", rep
            n = int(t[1]); pubs = [(int(t[2 + 3 * k]), int(t[3 + 3 * k]), int(t[4 + 3 * k])) for k in range(n)]
            j = 2 + 3 * n; assert t[j] == "DONE", rep
            seq, ff = [], False
            for clk, c, o in pubs:
                if o == 0xFF:
                    ff = True; continue
                if ff:
                    seq.append((clk, c, o))
            f.write(json.dumps(dict(i=i, kind=kind, md5=md5, final=[int(t[j + 2]), int(t[j + 3])], done_clk=int(t[j + 1]),
                                    first_clk=seq[0][0] if seq else None, pubs=seq)) + "\n")
    print("COSIM", a.hex, md5[:8], len(T), "boards ->", a.out)


if __name__ == "__main__":
    main()
