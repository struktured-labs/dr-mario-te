#!/usr/bin/env python3
"""Publish-timeline co-sim (REAL CoproDrMario RTL + the firmware hex, Verilator) for the 10/03 couch boards, one
JSONL record per (arm, case) in the late-flip lane's record format, so its Mesen replay (gen_cases_lua.py ->
lateflip_probe.lua) and its policy metrics consume these files unchanged.

The binary is this lane's own build of the late-flip lane's sim_pubtrace.cpp (copied verbatim to
experiments/tuckreach/sim_pubtrace.cpp; RTL NES_MiSTer-dist 3b164c7 with DRHSV DRLEV_SQREG DRLEV_WRREG DRLEV_VNPF
DRDIST). It polls the mailbox like the cart (every 64 NES cycles) and logs every change of the published (col, o4)
with its master-clock stamp since GO, then DONE and the tuck descriptor. The upload bytes follow the late-flip lane's
pubtrace_g2.upload exactly: FaithfulBoard -> cosim.board_to_nes, 0-based colours, DRSEED nibbles 0, DRREACHTX
gravity (speedUps = p // 10, speed MED), DRTAPP P = 2. One fresh process per decision (zeroed copro RAM), as there.

Usage: cosim_run.py --arms ship,trtl --games G2,G3,G4 --out-dir DIR [--j 4] [--p 99,100]
  arm = a name in ARMS (hex under tmp/fw/) or name=path/to/hex
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
VSIM = os.environ.get("VSIM", os.path.join(ROOT, "tmp", "cosim", "obj_pub", "vsim_pub"))
FWDIR = os.path.join(ROOT, "tmp", "fw")
ARMS = {  # flag set beyond fw 1488e158's recipe -> hex built by experiments/reach/build_fw.py 540 _ 1 1 1 TR RO TL
    "off": "fw_tr0_ro0_tl0.hex", "tr": "fw_tr1_ro0_tl0.hex", "ro": "fw_tr0_ro1_tl0.hex", "tl": "fw_tr0_ro0_tl1.hex",
    "trro": "fw_tr1_ro1_tl0.hex", "trtl": "fw_tr1_ro0_tl1.hex", "rotl": "fw_tr0_ro1_tl1.hex",
    "ship": "fw_tr1_ro1_tl1.hex"}
FRAME = 29780.5 * 48          # master clocks per NES frame (sim bus: 48 clocks per NES CPU cycle)
SEED, TAPP, SPEED = 0, 2, 1
VAR_OF_O4 = [2, 3, 0, 1]      # cosim_farm/cosim.py VAR_OF_O4 (copro o4 -> sim var); asserted below


def load_cases(games):
    sys.path.insert(0, CF)
    import analyze_g2 as A  # noqa: F401  (pins drmario)
    sys.path.insert(0, os.path.join(ROOT, "experiments", "cosim_farm"))
    import cosim
    assert list(cosim.VAR_OF_O4) == VAR_OF_O4, cosim.VAR_OF_O4
    cat = {(c["game"], c["p"]): c for c in map(json.loads, open(os.path.join(CF, "cases_cat_dist60_20261003.jsonl")))}
    out = []
    BANKED = {"L927": "cases_lulu_20260927.jsonl", "H927": "cases_hsv2_20260927.jsonl"}   # 9/27 couch (ANTIBODY) boards
    for g in games:
        if g in BANKED:
            Q = []
            for i, l in enumerate(open(os.path.join(CF, BANKED[g]))):
                q = json.loads(l)
                q.update(game=g, p=i, sim_action=None, category=q.get("category"), heights=q.get("heights", []),
                         virus_count=None, sim=None)
                Q.append(q)
            for q in Q:
                b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
                nes = cosim.board_to_nes(b)
                q["virus_count"] = sum(1 for v in nes if v != 0xFF and (v & 0xF0) == 0xD0)
                spu = min(49, int(q.get("k_game", q.get("k", 0))) // 10)
                ca, cb = q["cur"][0] - 1, q["cur"][1] - 1
                na, nb = q["nxt"][0] - 1, q["nxt"][1] - 1
                nA = na | ((TAPP & 3) << 2) | ((spu & 0x0F) << 4)
                nB = nb | (((TAPP >> 2) & 3) << 2) | ((((spu >> 4) & 3) | ((SPEED + 1) << 2)) << 4)
                q["_line"] = "%d %d %d %d %s" % (ca, cb, nA, nB, " ".join("%02x" % v for v in nes))
                q["_spu"] = spu
                out.append(q)
            continue
        if g == "G2":
            Q = [json.loads(l) for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))]
            for q in Q:
                q["game"] = "G2"
        else:
            Q = [q for q in map(json.loads, open(os.path.join(CF, "cases_dist60_20261003.jsonl"))) if q.get("game") == g]
            for q in Q:
                c = cat.get((g, q["p"]), {})
                q["category"] = c.get("category", "?"); q["sim_action"] = q.get("dist_action")
                q["sim"] = c.get("sim"); q["heights"] = c.get("heights", [])
        for q in Q:
            b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
            nes = cosim.board_to_nes(b)
            spu = min(49, q["p"] // 10)
            ca, cb = q["cur"][0] - 1, q["cur"][1] - 1
            na, nb = q["nxt"][0] - 1, q["nxt"][1] - 1
            cA = ca | ((SEED & 0x0F) << 4)
            cB = cb | (SEED & 0xF0)
            nA = na | ((TAPP & 3) << 2) | ((spu & 0x0F) << 4)
            nB = nb | (((TAPP >> 2) & 3) << 2) | ((((spu >> 4) & 3) | ((SPEED + 1) << 2)) << 4)
            q["_line"] = "%d %d %d %d %s" % (cA, cB, nA, nB, " ".join("%02x" % v for v in nes))
            q["_spu"] = spu
            out.append(q)
    return out


def simdir(hexpath):
    md5 = hashlib.md5(open(hexpath, "rb").read()).hexdigest()
    d = os.path.join(ROOT, "tmp", "cosim", "fw_" + md5[:8])
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(os.path.join(d, "copro_rom.hex")):
        shutil.copy(hexpath, os.path.join(d, "copro_rom.hex"))
    assert hashlib.md5(open(os.path.join(d, "copro_rom.hex"), "rb").read()).hexdigest() == md5
    return d, md5


def run_one(job):
    d, line = job
    p = subprocess.run(["nice", "-n", "19", VSIM, "64"], cwd=d, input=line + "\n", capture_output=True, text=True)
    return p.stdout.strip()


def parse(reply):
    t = reply.split()
    assert t[0] == "PUB", reply
    n = int(t[1])
    pubs = [(int(t[2 + 3 * k]), int(t[3 + 3 * k]), int(t[4 + 3 * k])) for k in range(n)]
    i = 2 + 3 * n
    assert t[i] == "DONE", reply
    tuck = [int(t[i + 5]), int(t[i + 6])] if len(t) > i + 6 and t[i + 4] == "TUCK" else None
    return pubs, (int(t[i + 1]), int(t[i + 2]), int(t[i + 3])), tuck


def act_of(col, o4):
    return VAR_OF_O4[o4] * 8 + col


def record(q, arm, md5, rep):
    pubs, done, tuck = parse(rep)
    seq, seen_ff = [], False
    for clk, c, o in pubs:                      # keep valid publishes after the firmware's $FF store (as pubtrace_g2)
        if o == 0xFF:
            seen_ff = True; continue
        if seen_ff:
            seq.append((round(clk / FRAME, 2), c, o, act_of(c, o)))
    return dict(game=q["game"], p=q["p"], arm=arm, fw_md5=md5, category=q.get("category"),
                sim_action=q.get("sim_action"), actual_action=q.get("actual_action"), sim=q.get("sim"),
                actual=q.get("actual"), heights=q.get("heights"), vc=q.get("virus_count"), spu=q["_spu"],
                upload=q["_line"], stale_first=pubs[0] if pubs else None, pubs=seq, done_clk=done[0],
                done_f=round(done[0] / FRAME, 2), final=(done[1], done[2], act_of(done[1], done[2])), tuck=tuck)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True); ap.add_argument("--games", default="G2")
    ap.add_argument("--out-dir", required=True); ap.add_argument("--j", type=int, default=4)
    ap.add_argument("--p", default="")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    cases = load_cases(args.games.split(","))
    if args.p:
        want = {int(x) for x in args.p.split(",")}
        cases = [q for q in cases if q["p"] in want]
    jobs = []
    for spec in args.arms.split(","):
        arm, _, path = spec.partition("=")
        path = path or os.path.join(FWDIR, ARMS[arm])
        d, md5 = simdir(path)
        for g in args.games.split(","):
            outp = os.path.join(args.out_dir, f"pubtrace_{g}_{arm}.jsonl")
            done = set()
            if os.path.exists(outp):
                done = {json.loads(l)["p"] for l in open(outp)}
            for q in cases:
                if q["game"] == g and q["p"] not in done:
                    jobs.append((arm, md5, d, q, outp))
    print(f"{len(jobs)} co-sim decisions to run (j={args.j})", flush=True)
    with ThreadPoolExecutor(args.j) as ex:
        futs = [(j, ex.submit(run_one, (j[2], j[3]["_line"]))) for j in jobs]
        for k, (j, f) in enumerate(futs):
            arm, md5, d, q, outp = j
            rec = record(q, arm, md5, f.result())
            with open(outp, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            if k % 20 == 0:
                print(f"  {k + 1}/{len(jobs)} {arm} {q['game']} p{q['p']} final a{rec['final'][2]} DONE {rec['done_f']}f "
                      f"tuck {rec['tuck']}", flush=True)


if __name__ == "__main__":
    main()
