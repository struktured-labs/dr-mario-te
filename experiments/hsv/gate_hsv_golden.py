#!/usr/bin/env python3
"""FIRMWARE GOLDEN with the DRHSV leaf (py65). The copro firmware is UNCHANGED by DRHSV (the term lives in the RTL
leaf), but the firmware must handle the much more negative leaf scores the engine now returns: the Pass-0 key
(imm + sco), the ply-1/ply-2 temporal discount ((best2 - leaf1) >> 1), the 4-pill expectimax sums, the WIN
comparisons and the reach pre-filter all run on them.

Engine emulator AND golden mirror both use nes_d3_golden.leaf_d3 patched with the spec-fixed HSV term
(-512 per virus in cols 3..5 at row < 9), so any firmware arithmetic that overflows or mis-signs on the new range
shows up as a firmware != mirror decision.
Firmware = the CHAIN540 + REACH + TAP image (DRREACH=1 DRREACHTAP=1, 77ec742c), the P=2 tap transport.
Boards: the 1,412 real couch-steering gate-(b) game boards (their own pills and gravity) + synthetic HSV-heavy boards
(the high spawn columns loaded with viruses, the regime the term targets).
Usage: gate_hsv_golden.py [--game N] [--synth N] [--workers W]
"""
import argparse, json, os, random, sys, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "experiments", "reach"))
import gate_reach_search as GS               # run_fw, mirror, reach_eff, image (recipe env: CHAIN540 ship)
import reach_6502 as RC

HSV_W = 512
G3 = None            # nes_d3_golden, taken from the LOADED search emitter (a top-level import can resolve a stale copy
_orig_leaf = None    # on sys.path and shadow the module decide_mirror and the engine emu actually read)


def hsv_count(b):
    return sum(1 for r in range(9) for c in (3, 4, 5) if b[r * 8 + c] != 0xFF and (b[r * 8 + c] & 0xF0) == 0xD0)


def leaf_hsv(b):
    v = _orig_leaf(b)
    if G3._virus_count(b) == 0:
        return v
    return v - HSV_W * hsv_count(b)


def synth_boards(n, rng):
    out = []
    for i in range(n):
        b = [0xFF] * 128
        for c in range(8):
            h = rng.choice([2, 4, 6, 8, 10])
            for r in range(16 - h, 16):
                b[r * 8 + c] = 0x40 | rng.randrange(3)
        k = rng.randint(4, 27)                           # load the HSV zone
        cells = [(r, c) for r in range(9) for c in (3, 4, 5)]
        rng.shuffle(cells)
        for r, c in cells[:k]:
            b[r * 8 + c] = 0xD0 | rng.randrange(3)
        for r in range(9):
            for c in (3, 4):
                if r < 2:
                    b[r * 8 + c] = 0xFF                  # spawn cells free
        # a couple of low viruses elsewhere
        for _ in range(rng.randint(0, 6)):
            b[rng.randrange(10, 16) * 8 + rng.choice([0, 1, 2, 6, 7])] = 0xD0 | rng.randrange(3)
        out.append(("synth", b, tuple(rng.randrange(3) for _ in range(4)), (rng.randrange(3), rng.randrange(50))))
    return out


def task(t):
    kind, nes, (cA, cB, nA, nB), (sp, su) = t
    D3 = GS._ST["D3"]
    thr = RC.SPEED_TABLE[min(80, RC.SPEED_BASE[sp] + su)]
    hiA, hiB = RC.pack_nibbles(sp, su)
    tp = 2
    hiA |= (tp & 3) << 2; hiB |= ((tp >> 2) & 3) << 2
    mask = GS.reach_eff(nes, thr, tp)
    d1, m1 = GS.run_fw(*GS._ST["img1"], nes, cA, cB, nA | hiA, nB | hiB)
    e1 = GS.expect(D3, nes, cA, cB, nA, nB, mask)
    # and the same board WITHOUT HSV (does the term move the decision here?)
    G3.leaf_d3 = _orig_leaf
    e0 = GS.expect(D3, nes, cA, cB, nA, nB, mask)
    G3.leaf_d3 = leaf_hsv
    return dict(kind=kind, ok=(d1 == e1 and m1 < 16), d1=d1, e1=e1, moved=(e1 != e0), hsv=hsv_count(nes),
                minleaf=None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", type=int, default=160); ap.add_argument("--synth", type=int, default=100)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    global G3, _orig_leaf
    GS.TAPFW = True
    B, D3 = GS.GD._load()
    G3 = D3.G3
    assert sys.modules["nes_d3_golden"] is G3, "golden module shadowed"
    _orig_leaf = G3.leaf_d3
    G3.leaf_d3 = leaf_hsv                         # BOTH the engine emu and decide_mirror read G3.leaf_d3
    GS._ST.update(B=B, D3=D3, img1=GS.image(B, D3, True))
    rng = random.Random(20260926)
    rows = [json.loads(l) for f in ("game_l11.jsonl", "game_l15.jsonl")
            for l in open(os.path.join(ROOT, "experiments", "reach", "corpus", f))]
    rows.sort(key=lambda d: -hsv_count(d["nes"]))       # the HSV-heavy real boards first
    tasks = [("game", d["nes"], tuple(x - 1 for x in d["pills"]), (d["speed"], d["speedups"])) for d in rows[:a.game]]
    tasks += synth_boards(a.synth, rng)
    with mp.get_context("fork").Pool(a.workers) as pool:
        res = pool.map(task, tasks, chunksize=1)
    ok = True
    for kind in ("game", "synth"):
        rr = [r for r in res if r["kind"] == kind]
        good = sum(r["ok"] for r in rr)
        print(f"{kind:5s}: firmware(+HSV engine) == golden mirror(+HSV) {good}/{len(rr)}; HSV count median "
              f"{sorted(r['hsv'] for r in rr)[len(rr) // 2]} max {max(r['hsv'] for r in rr)}; HSV moved the decision on "
              f"{sum(r['moved'] for r in rr)}")
        ok &= good == len(rr)
    for r in res:
        if not r["ok"]:
            print("  MISMATCH", r)
    print("GATE_HSV_GOLDEN", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
