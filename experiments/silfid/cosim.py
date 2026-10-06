"""silfid co-sim runner: the shipped copro (RTL 3b164c7 + fw 1488e158) publish timeline for lulu 10/05 boards, with
overrides: SEED (tie-break seed byte), SPU_OFF (speedUps = (p + SPU_OFF)//10). Same upload encoding as h16
experiments/lateflip/pubtrace_g2.py. Usage: cosim.py OUT.jsonl game:p[,p...] [game:p ...]  env SEED, SPU_OFF, J"""
import json, os, subprocess, sys, hashlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics")
import analyze_g2 as A  # noqa
sys.path.insert(0, "/home/struktured/projects/dr-mario-lateflip-wt/experiments/cosim_farm")
from cosim import board_to_nes, VAR_OF_O4  # noqa
import load
FW = "/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60/fw540_reachtap_dist_1488e158.hex"
VSIM = "/home/struktured/projects/dr-mario-lateflip-wt/tmp/pubtrace/obj_pub2/vsim_pub2"
FW_MD5 = hashlib.md5(open(FW, "rb").read()).hexdigest()
SIMDIR = os.environ.get("FWDIR") or f"/home/struktured/projects/dr-mario-lateflip-wt/tmp/pubtrace/fw_{FW_MD5[:8]}"
assert os.path.exists(os.path.join(SIMDIR, "copro_rom.hex"))
FRAME = 29780.5 * 48
TAPP, SPEED = 2, 1

def upload(q, seed, spu_off):
    b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
    nes = board_to_nes(b)
    spu = min(49, max(0, (q["p"] + spu_off) // 10))
    ca, cb = q["cur"][0] - 1, q["cur"][1] - 1
    na, nb = q["nxt"][0] - 1, q["nxt"][1] - 1
    cA = ca | ((seed & 0x0F) << 4); cB = cb | (seed & 0xF0)
    nA = na | ((TAPP & 3) << 2) | ((spu & 0x0F) << 4)
    nB = nb | (((TAPP >> 2) & 3) << 2) | ((((spu >> 4) & 3) | ((SPEED + 1) << 2)) << 4)
    return "%d %d %d %d %s" % (cA, cB, nA, nB, " ".join("%02x" % v for v in nes))

def run_one(line):
    p = subprocess.run(["nice", "-n", "19", VSIM, "64"], cwd=SIMDIR, input=line + "\n", capture_output=True, text=True)
    return p.stdout.strip()

def parse(reply):
    t = reply.split(); assert t[0] == "PUB", reply
    n = int(t[1]); pubs = []
    for k in range(n):
        pubs.append((int(t[2 + 3 * k]), int(t[3 + 3 * k]), int(t[4 + 3 * k])))
    i = 2 + 3 * n; assert t[i] == "DONE"
    tuck = [int(t[i + 5]), int(t[i + 6])] if len(t) > i + 6 and t[i + 4] == "TUCK" else None
    seq, seen = [], False
    for clk, c, o in pubs:
        if o == 0xFF: seen = True; continue
        if seen: seq.append((round(clk / FRAME, 2), c, o, VAR_OF_O4[o] * 8 + c))
    return seq, (round(int(t[i + 1]) / FRAME, 2), int(t[i + 2]), int(t[i + 3]), VAR_OF_O4[int(t[i + 3])] * 8 + int(t[i + 2])), tuck

def main():
    out = sys.argv[1]
    seed = int(os.environ.get("SEED", "0")); spu_off = int(os.environ.get("SPU_OFF", "0"))
    jobs = []
    for spec in sys.argv[2:]:
        g, ps = spec.split(":"); Q = load.cases(g)
        for p in ps.split(","):
            q = Q[int(p)]; jobs.append((g, int(p), upload(q, seed, spu_off)))
    with ThreadPoolExecutor(int(os.environ.get("J", "5"))) as ex:
        reps = list(ex.map(run_one, [j[2] for j in jobs]))
    with open(out, "a") as f:
        for (g, p, line), rep in zip(jobs, reps):
            seq, done, tuck = parse(rep)
            f.write(json.dumps(dict(game=g, p=p, seed=seed, spu_off=spu_off, fwdir=os.environ.get("FWDIR", ""), upload=line, pubs=seq, done_f=done[0],
                                    final=list(done[1:]), tuck=tuck)) + "\n")

if __name__ == "__main__":
    main()
