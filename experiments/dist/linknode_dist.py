#!/usr/bin/env python3
"""Link-aware NODE co-sim WITH the DRDIST term (and DRHSV, which DRDIST rides): the pinned linknode corpus
(cascade_chain_x reference: colour/virus/link planes, cells, viruses, chain, imm, sco) with a per-record target
(gate.pick_target on the PARENT, as the firmware picks at the root) and the expected leaf score adjusted by the
spec-fixed terms on the CHILD: s16(sco - 512*hsv(child) - 60*D(child, target)). This is the NODE path the bitexact
gate's PHASE2 cannot check (compact-gravity oracle): clears, gravity, cascades, a cleared target (term 0).
Usage: linknode_dist.py <LeafEval.sv> [--mut TAG]"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); GD = os.path.join(HERE, "gate")
sys.path.insert(0, GD)
import gate as G
REC = 268


def main(rtl, tag="dist"):
    T = os.path.join(HERE, "..", "..", "tmp", "ln_" + tag); os.makedirs(T, exist_ok=True)
    toks = open(os.path.join(GD, "linknode_cases.txt")).read().split()
    n = int(toks[0]); body = toks[1:]
    G.DIST_ON = True
    act = adj = 0
    with open(os.path.join(T, "cases.txt"), "w") as f:
        f.write("%d\n" % n)
        for k in range(n):
            r = body[k * REC:(k + 1) * REC]
            parent = [int(x, 16) for x in r[:128]]; child = [int(x, 16) for x in r[140:268]]
            # the corpus stores the raw NES bytes incl. link nibbles; the terms read colour/virus only
            tg = G.pick_target(parent, k)
            legal, win, sco = int(r[133]), int(r[139]), int(r[138])
            if legal and not win:
                d = G.dist_term(child, tg); h = G.hsv_count(child)
                act += d != 0
                new = G._s16(sco - 512 * h + d); adj += new != sco
                r = r[:138] + [str(new)] + r[139:]
            f.write(" ".join(r) + " %d\n" % tg)
    pp = os.path.join(T, "LeafEval.sv")
    with open(pp, "w") as f:
        subprocess.run(["verilator", "-E", "-P", "--pp-comments", "-DDRHSV", "-DDRLEV_SQREG", "-DDRLEV_WRREG",
                        "-DDRLEV_VNPF", "-DDRDIST", rtl], stdout=f, check=True)
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "4", "-O2", "-Wno-fatal", "--top-module", "LeafEval",
           "--Mdir", os.path.join(T, "obj"), "-o", "VLinkDist", "-CFLAGS", "-DHAS_TGT", pp,
           os.path.join(G.QA_COPRO, "dpram.v"), os.path.join(GD, "tb_linknode_gate.cpp")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:]); print("LINKNODE_DIST FAIL build"); return 1
    out = subprocess.run([os.path.join(T, "obj", "VLinkDist"), os.path.join(T, "cases.txt"), "0"],
                         capture_output=True, text=True).stdout
    print(out[-1600:])
    print(f"records with a non-zero D term: {act}; expected sco adjusted (HSV and/or D): {adj}")
    ok = "OVERALL: PASS" in out
    print("LINKNODE_DIST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--mut" else "dist"))
