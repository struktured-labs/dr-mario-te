#!/usr/bin/env python3
"""FIRMWARE GOLDEN with the DRDIST leaf (py65, WHOLE search). The DRDIST firmware (CHAIN540 + REACH + TAP + the
dist_6502 target routine) runs under py65 with the engine emulator; the engine's leaf is nes_d3_golden.leaf_d3 plus
the spec-fixed ANTIBODY HSV term plus -60 * D(target) on the leaf board, where `target` is WHATEVER THE FIRMWARE WROTE
to $70F5 this search. The golden mirror scores the same leaf with the target the Leaf6Decider rule picks on the root.
So a firmware target that disagrees with the rule, or firmware arithmetic that overflows / mis-signs on the more
negative leaf range, shows up as firmware != mirror. Non-vacuity: the term moves the mirror's decision on some boards.
Boards: every real gate-(b) game board with 1..4 viruses (L11 + L15, their own pills and gravity), the couch endgame
boards (9/27 lulu G1 stall, 9/27 match-1 G3, 9/26 control; 1..4 viruses), synthetic endgame boards, and a sample of
> 4-virus boards (term off: must equal the plain HSV mirror).
The endgame bound is dist_6502.VK (env DRDIST_VK, default 4): DRDIST_VK=16 (A16) selects the 1..16-virus boards as the
term-on set and > 16 as "big" (vk 4 selects exactly the boards and seeds it always did).
Usage: [DRDIST_VK=16] gate_dist_golden.py [--synth N] [--big N] [--workers W]"""
import argparse, json, os, random, sys, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "experiments", "reach")); sys.path.insert(0, HERE)
os.environ["DRDIST"] = "1"
import gate_reach_search as GS
import reach_6502 as RC
import gate_dist_fw as FW                      # expected(): the Leaf6Decider target rule (gate reference)
sys.path.insert(0, os.path.join(HERE, "gate"))
import gate as GG
GG.DIST_ON = True

HSV_W = 512
G3 = None
_orig_leaf = None
TGT = [0]


def hsv_count(b):
    return sum(1 for r in range(9) for c in (3, 4, 5) if b[r * 8 + c] != 0xFF and (b[r * 8 + c] & 0xF0) == 0xD0)


def leaf_hd(b):
    v = _orig_leaf(b)
    if G3._virus_count(b) == 0:
        return v
    return v - HSV_W * hsv_count(b) + GG.dist_term(b, TGT[0])


def run_fw(img, ep, board, cA, cB, nA, nB, ts=GS.TS):
    from py65.memory import ObservableMemory
    from py65_harness import Cpu
    B, D3 = GS._ST["B"], GS._ST["D3"]
    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    for i in range(16):
        cpu.mem[D3.PILLA + i] = img[B.PILL_ROM + i]
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    base = cpu.mem
    obs = ObservableMemory(subject=base)
    wrote = []

    def on_tgt(addr, value):
        TGT[0] = value & 0xFF; wrote.append(value & 0xFF)
        base[addr] = value
    obs.subscribe_to_write([0x70F5], on_tgt)
    cpu.mpu.memory = obs; cpu.mem = obs
    cpu.mem[GS.S_NA - 2] = ((int(ts) & 0x0F) << 4) | cA
    cpu.mem[GS.S_NA - 1] = (int(ts) & 0xF0) | cB
    cpu.mem[GS.S_NA], cpu.mem[GS.S_NB] = nA, nB
    TGT[0] = 0
    cpu.call(ep, max_steps=B.MAX_STEPS)
    dec = None if cpu.mem[D3.D_BO] == 0xFF else (cpu.mem[D3.D_BC], cpu.mem[D3.D_BO])
    return dec, wrote


def task(t):
    kind, nes, (cA, cB, nA, nB), (sp, su) = t
    D3 = GS._ST["D3"]
    thr = RC.SPEED_TABLE[min(80, RC.SPEED_BASE[sp] + su)]
    hiA, hiB = RC.pack_nibbles(sp, su)
    tp = 2
    hiA |= (tp & 3) << 2; hiB |= ((tp >> 2) & 3) << 2
    mask = GS.reach_eff(nes, thr, tp)
    d1, wrote = run_fw(*GS._ST["img1"], nes, cA, cB, nA | hiA, nB | hiB)
    exp_t = FW.expected(nes)
    TGT[0] = exp_t
    e1 = GS.expect(D3, nes, cA, cB, nA, nB, mask)
    TGT[0] = 0
    e0 = GS.expect(D3, nes, cA, cB, nA, nB, mask)          # the same search with no target (= ANTIBODY)
    nv = sum(1 for x in nes if x != 0xFF and (x & 0xF0) == 0xD0)
    return dict(kind=kind, ok=(d1 == e1 and wrote == [exp_t]), d1=d1, e1=e1, moved=(e1 != e0), nv=nv,
                tgt_ok=(wrote == [exp_t]), active=bool(exp_t))


def synth(n, rng):
    out = []
    for _ in range(n):
        b = [0xFF] * 128
        for c in range(8):
            h = rng.choice([1, 3, 5, 7, 9, 11])
            for r in range(16 - h, 16):
                b[r * 8 + c] = rng.choice([0x40, 0x50, 0x60, 0x70, 0x80]) | rng.randrange(3)
        for c in (3, 4):
            b[c] = b[8 + c] = 0xFF
        for _k in range(rng.randint(1, FW.DT.VK)):
            r = rng.randrange(5, 16); c = rng.randrange(8)
            b[r * 8 + c] = 0xD0 | rng.randrange(3)
        out.append(("synth", b, tuple(rng.randrange(3) for _ in range(4)), (rng.randrange(3), rng.randrange(40))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", type=int, default=120); ap.add_argument("--big", type=int, default=40)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    global G3, _orig_leaf
    GS.TAPFW = True
    B, D3 = GS.GD._load()
    G3 = D3.G3
    assert sys.modules["nes_d3_golden"] is G3, "golden module shadowed"
    _orig_leaf = G3.leaf_d3
    G3.leaf_d3 = leaf_hd
    os.environ["DRDIST"] = "1"
    GS._ST.update(B=B, D3=D3, img1=GS.image(B, D3, True))
    assert D3.DRDIST == 1, "image built without the DRDIST routine"
    rows = [json.loads(l) for f in ("game_l11.jsonl", "game_l15.jsonl")
            for l in open(os.path.join(ROOT, "experiments", "reach", "corpus", f))]
    nvir = lambda nes: sum(1 for x in nes if x != 0xFF and (x & 0xF0) == 0xD0)
    tasks = [("game", d["nes"], tuple(x - 1 for x in d["pills"]), (d["speed"], d["speedups"]))
             for d in rows if 1 <= nvir(d["nes"]) <= FW.DT.VK]
    big = [d for d in rows if nvir(d["nes"]) > FW.DT.VK]
    random.Random(5).shuffle(big)
    tasks += [("big", d["nes"], tuple(x - 1 for x in d["pills"]), (d["speed"], d["speedups"])) for d in big[:a.big]]
    couch = [(k, b) for k, b in FW.boards_real() if k.startswith("couch") and 1 <= nvir(b) <= FW.DT.VK]
    rng = random.Random(20260928)
    tasks += [("couch", b, tuple(rng.randrange(3) for _ in range(4)), (1, rng.randrange(20))) for _k, b in couch]
    tasks += synth(a.synth, rng)
    with mp.get_context("fork").Pool(a.workers) as pool:
        res = pool.map(task, tasks, chunksize=1)
    ok = True
    for kind in ("game", "couch", "synth", "big"):
        rr = [r for r in res if r["kind"] == kind]
        if not rr:
            continue
        good = sum(r["ok"] for r in rr)
        print(f"{kind:5s}: firmware(+DIST engine) == golden mirror(+DIST) {good}/{len(rr)}; target written == rule "
              f"{sum(r['tgt_ok'] for r in rr)}/{len(rr)}; active {sum(r['active'] for r in rr)}; the term moved the "
              f"decision on {sum(r['moved'] for r in rr)}")
        ok &= good == len(rr)
    for r in res:
        if not r["ok"]:
            print("  MISMATCH", r)
    ok &= sum(r["moved"] for r in res) > 0
    print("GATE_DIST_GOLDEN", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
