"""Late-flip root cause, step 1: the REAL copro's live-publish timeline on the 10/03 G2 boards.

Runs the shipped ANTIBODY_DIST copro (RTL NES_MiSTer-dist 3b164c7 + fw 1488e158) in Verilator via
dr-mario-lateflip-wt/tmp/pubtrace/obj_pub/vsim_pub (sim_pubtrace.cpp: polls the mailbox like the cart, logs every
change of the published (col, orient) with its clock since GO). Inputs are the exact bytes the couch cart uploads:
board (FaithfulBoard -> NES bytes, cosim.board_to_nes), cA/cB/nA/nB 0-based colours + DRREACHTX gravity nibbles
(speedUps = pill//10, speed MED) + DRTAPP P=2 bits; tie-break seed nibbles = SEED (default 0, unknown on silicon).

Usage: pubtrace_g2.py OUT.jsonl [p ...]     (no p list -> every G2 case)
       FW=/path/to/copro_rom.hex  -> run that firmware (default: the shipped fw540_reachtap_dist_1488e158.hex)
       VSIM=/path/to/vsim_pub2    -> the co-sim binary (default dr-mario-lateflip-wt/tmp/pubtrace/obj_pub2/vsim_pub2,
                                     built by dr-mario-lateflip-wt/tools/lateflip/build_pubtrace.sh)
       SEED=n (tie-break seed nibbles, default 0), J=parallel jobs (default 4; keep it low, the box is shared)
       CASES=<file> GAME=G3 pubtrace_g2.py OUT.jsonl   (other 10/03 games: cases_dist60_20261003.jsonl, sim = dist_action)
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.join(HERE, "..", "couch_forensics")
sys.path.insert(0, CF)
import analyze_g2 as A  # noqa: E402  (pins drmario)
sys.path.insert(0, "/home/struktured/projects/dr-mario-lateflip-wt/experiments/cosim_farm")
from cosim import board_to_nes, VAR_OF_O4  # noqa: E402

import hashlib, shutil
FW = os.environ.get("FW", "/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60/fw540_reachtap_dist_1488e158.hex")
VSIM = os.environ.get("VSIM", "/home/struktured/projects/dr-mario-lateflip-wt/tmp/pubtrace/obj_pub2/vsim_pub2")
FW_MD5 = hashlib.md5(open(FW, "rb").read()).hexdigest()
SIMDIR = f"/home/struktured/projects/dr-mario-lateflip-wt/tmp/pubtrace/fw_{FW_MD5[:8]}"   # CWD holds copro_rom.hex
os.makedirs(SIMDIR, exist_ok=True)
if not os.path.exists(os.path.join(SIMDIR, "copro_rom.hex")):
    shutil.copy(FW, os.path.join(SIMDIR, "copro_rom.hex"))
FRAME = 29780.5 * 48          # master clocks per NES frame (sim_mister bus: 48 clocks per CPU cycle)
SEED = int(os.environ.get("SEED", "0"))
TAPP, SPEED = 2, 1


def upload(q, seed=SEED):
    b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
    nes = board_to_nes(b)
    spu = min(49, q["p"] // 10)
    ca, cb = q["cur"][0] - 1, q["cur"][1] - 1
    na, nb = q["nxt"][0] - 1, q["nxt"][1] - 1
    cA = ca | ((seed & 0x0F) << 4)
    cB = cb | (seed & 0xF0)
    nA = na | ((TAPP & 3) << 2) | ((spu & 0x0F) << 4)
    nB = nb | (((TAPP >> 2) & 3) << 2) | ((((spu >> 4) & 3) | ((SPEED + 1) << 2)) << 4)
    return cA, cB, nA, nB, nes


def act_of(col, o4):
    return VAR_OF_O4[o4] * 8 + col


def run_one(line):
    p = subprocess.run(["nice", "-n", "19", VSIM, "64"], cwd=SIMDIR,
                       input=line + "\n", capture_output=True, text=True)
    return p.stdout.strip()


def parse(reply):
    t = reply.split()
    assert t[0] == "PUB", reply
    n = int(t[1]); pubs = []
    for k in range(n):
        clk, c, o = int(t[2 + 3 * k]), int(t[3 + 3 * k]), int(t[4 + 3 * k])
        pubs.append((clk, c, o))
    i = 2 + 3 * n
    assert t[i] == "DONE"
    tuck = [int(t[i + 5]), int(t[i + 6])] if len(t) > i + 6 and t[i + 4] == "TUCK" else None
    return pubs, (int(t[i + 1]), int(t[i + 2]), int(t[i + 3])), tuck


def main():
    out = sys.argv[1]
    want = set(int(x) for x in sys.argv[2:])
    Q = [json.loads(l) for l in open(os.path.join(CF, os.environ.get("CASES", "cases_g2_dist60_20261003.jsonl")))]
    if os.environ.get("GAME"):
        cat = {(c["game"], c["p"]): c for c in map(json.loads, open(os.path.join(CF, "cases_cat_dist60_20261003.jsonl")))}
        Q = [q for q in Q if q.get("game") == os.environ["GAME"]]
        for q in Q:
            c = cat.get((q["game"], q["p"]), {})
            q["category"] = c.get("category", "?"); q["sim_action"] = q.get("dist_action")
            q["sim"] = c.get("sim"); q["heights"] = c.get("heights", [])
    Q = [q for q in Q if not want or q["p"] in want]
    lines = []
    for q in Q:
        cA, cB, nA, nB, nes = upload(q)
        lines.append("%d %d %d %d %s" % (cA, cB, nA, nB, " ".join("%02x" % v for v in nes)))
    with ThreadPoolExecutor(int(os.environ.get("J", "4"))) as ex:
        reps = list(ex.map(run_one, lines))
    with open(out, "w") as f:
        for q, line, rep in zip(Q, lines, reps):
            pubs, done, tuck = parse(rep)
            # drop the stale pre-reset value and the $FF sentinel: keep valid publishes after the firmware's FF store
            seq, seen_ff = [], False
            for clk, c, o in pubs:
                if o == 0xFF:
                    seen_ff = True; continue
                if seen_ff:
                    seq.append((round(clk / FRAME, 2), c, o, act_of(c, o)))
            rec = dict(p=q["p"], fw_md5=FW_MD5, category=q["category"], sim_action=q["sim_action"], actual_action=q["actual_action"],
                       sim=q["sim"], actual=q["actual"], heights=q["heights"], vc=q["virus_count"], upload=line,
                       stale_first=pubs[0] if pubs else None, pubs=seq,
                       done_f=round(done[0] / FRAME, 2), final=(done[1], done[2], act_of(done[1], done[2])), tuck=tuck)
            f.write(json.dumps(rec) + "\n")
            print(f"p{q['p']:3d} {q['category']:13s} sim a{q['sim_action']:2d} sil a{q['actual_action']} | "
                  f"cosim final a{rec['final'][2]:2d} DONE {rec['done_f']:5.1f}f | pubs " +
                  " ".join(f"a{a}@{t}" for t, c, o, a in seq), flush=True)


if __name__ == "__main__":
    main()
