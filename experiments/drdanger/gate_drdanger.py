#!/usr/bin/env python3
"""DRDANGER gate (py65, WHOLE search, A16 recipe = CHAIN540 + REACH + TAP + DRDIST VK16 + DRVETO + DRDANGER).

Reference = the STEER14/tapout SIM's rule, not a re-derivation: the per-root n is computed with the sim's own
`_soft_b1` (braingap "Firmware eh_terms b1") + max height of cols 2..5, exactly as tapout_run._danger_pen, and fed
into the verbatim golden whole-search mirror (gate_drveto.decide_mirror) after the DRVETO penalty, before the jitter.
WIN roots get no penalty (firmware skips eh_terms on WIN; documented divergence from the sim, WIN dominates).
Checks per board: (a) every firmware D_DNG write for a root (keyed by zp D_C1/D_O1 at the write) == sim n for that
root; (b) firmware decision == mirror decision.  Non-vacuity: the term moves the mirror decision on some boards.
Mutants (one emitter knob each, see test_search_d3._DANGER_MUT) must FAIL on the mutant board sample.
Usage: gate_drdanger.py --arm D4|D1 [--mut NAME] [--synth N] [--big N] [--workers W] [--limit N]"""
import argparse, inspect, json, os, random, sys, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
# the SIM first (its import pin must see a clean path), exactly the modules tapout_run uses
CVX = os.environ.get("TAPOUT_CVX", "/home/struktured/projects/grok-tapout-wt/experiments/cvx")
sys.path.insert(0, CVX)
import import_pin; import_pin.pin()
sys.path.insert(0, os.path.join(os.path.dirname(CVX), "braingap"))
import numpy as np
from cascade_leaf6fw_braingap_20261003 import _soft_b1   # the sim's soft b1 (tapout_run imports the same)
sys.path.insert(0, os.path.join(ROOT, "experiments", "dist"))
os.environ.setdefault("DRDIST_VK", "16")
import gate_dist_golden as GDG                  # A16 golden harness (leaf + HSV + DIST target)
GS, FW = GDG.GS, GDG.FW
GD = GS.GD
VAR_OF_O4 = (2, 3, 0, 1)                                   # cosim.VAR_OF_O4: golden o4 -> sim variant

ARM = None


def sim_n(nes, o4, col, pA, pB):
    pcol = np.zeros(128, dtype=np.int8); pvir = np.zeros(128, dtype=np.int8)
    for i, x in enumerate(nes):
        if x != 0xFF:
            pcol[i] = (x & 0x0F) + 1; pvir[i] = 1 if (x & 0xF0) == 0xD0 else 0
    bc = np.empty(128, dtype=np.int8); bv = np.empty(128, dtype=np.int8)
    if _soft_b1(pcol, pvir, VAR_OF_O4[o4], col, pA + 1, pB + 1, bc, bv) == 0:
        return None
    h = 0
    for c in range(2, 6):
        for r in range(16):
            if bc[r * 8 + c] != 0:
                h = max(h, 16 - r); break
    h0 = GS._ST["D3"].DANGER_ARMS[ARM]["h0"]
    return h - h0 if h > h0 else 0


ROOTN = {}


def _patch_mirror():
    """gate_drveto.decide_mirror + the DANGER line (text insertion before the jitter; nothing else changes)."""
    src = inspect.getsource(GD.decide_mirror)
    anchor = "        val += G._jitter(seed, o4, col)\n"
    assert src.count(anchor) == 1
    ins = ("        if _DANGER_ON[0] and not win1:\n"
           "            _n = _SIM_N(board, o4, col, pA, pB)\n"
           "            _ROOTN[(col, o4)] = _n\n"
           "            val = D3.danger_val(val, _n, _ARM[0])\n")
    src = src.replace(anchor, ins + anchor)
    ns = GD.__dict__
    ns.update(_DANGER_ON=[True], _SIM_N=sim_n, _ROOTN=ROOTN, _ARM=[None])
    exec(compile(src, GD.__file__ + ":decide_mirror+danger", "exec"), ns)
    return ns


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
    dng = []

    def on_tgt(addr, value):
        GDG.TGT[0] = value & 0xFF; base[addr] = value

    def on_dng(addr, value):
        dng.append((base[D3.D_C1], base[D3.D_O1], value & 0xFF)); base[addr] = value
    obs.subscribe_to_write([0x70F5], on_tgt)
    obs.subscribe_to_write([D3.D_DNG], on_dng)
    cpu.mpu.memory = obs; cpu.mem = obs
    cpu.mem[GS.S_NA - 2] = ((int(ts) & 0x0F) << 4) | cA
    cpu.mem[GS.S_NA - 1] = (int(ts) & 0xF0) | cB
    cpu.mem[GS.S_NA], cpu.mem[GS.S_NB] = nA, nB
    GDG.TGT[0] = 0
    n0 = cpu.mpu.processorCycles
    cpu.call(ep, max_steps=B.MAX_STEPS)
    cyc = cpu.mpu.processorCycles - n0
    dec = None if cpu.mem[D3.D_BO] == 0xFF else (cpu.mem[D3.D_BC], cpu.mem[D3.D_BO])
    return dec, dng, cyc


def task(t):
    kind, nes, (cA, cB, nA, nB), (sp, su) = t
    D3, RC = GS._ST["D3"], GDG.RC
    thr = RC.SPEED_TABLE[min(80, RC.SPEED_BASE[sp] + su)]
    hiA, hiB = RC.pack_nibbles(sp, su)
    tp = 2
    hiA |= (tp & 3) << 2; hiB |= ((tp >> 2) & 3) << 2
    mask = GS.reach_eff(nes, thr, tp)
    d1, dng, cyc = run_fw(*GS._ST["img1"], nes, cA, cB, nA | hiA, nB | hiB)
    exp_t = FW.expected(nes)
    GDG.TGT[0] = exp_t
    ns = GS._ST["ns"]
    ns["_DANGER_ON"][0] = GS._ST["on"]; ROOTN.clear()
    e1 = GS.expect(D3, nes, cA, cB, nA, nB, mask)
    rootn = dict(ROOTN)
    ns["_DANGER_ON"][0] = False
    e0 = GS.expect(D3, nes, cA, cB, nA, nB, mask)
    # (a) per-root: the LAST write per root visit is the scan's n (the first is the per-root clear to 0)
    bad = []
    seen = {}
    for (c, o, v) in dng:
        seen.setdefault((c, o), []).append(v)
    for k, vs in seen.items():
        nz = [v for v in vs if v != 0]
        want = rootn.get(k)
        if want is None:
            if nz:
                bad.append((k, vs, None))
        elif nz and any(v != want for v in nz) or (not nz and want != 0):
            bad.append((k, vs, want))
    fired = sum(1 for v in rootn.values() if v)
    hit = sum(1 for k, vs in seen.items() if rootn.get(k) and rootn[k] in vs)   # non-vacuity of the per-root check
    ok = (d1 == e1) and not bad and hit == fired and (GS._ST["on"] or not dng)   # OFF: nothing touches $0287
    return dict(kind=kind, ok=ok, d1=d1, e1=e1, moved=(e1 != e0), bad=bad[:3], fired=fired, hit=hit, ndng=len(dng),
                nroot_fw=len(seen), nroot_mir=len(rootn), cyc=cyc)


def synth_tall(n, rng):
    """Tall-throat boards: cols 2..5 stacked to 9..14, so the term is live (n 0..4 for D4 h0 10)."""
    out = []
    for _ in range(n):
        b = [0xFF] * 128
        for c in range(8):
            h = rng.choice([3, 5, 7, 9, 10, 11, 12, 13, 14] if 2 <= c <= 5 else [1, 3, 5, 7, 9])
            for r in range(16 - h, 16):
                b[r * 8 + c] = rng.choice([0x40, 0x50, 0x60, 0x70, 0x80]) | rng.randrange(3)
        for c in (3, 4):
            b[c] = b[8 + c] = 0xFF
        for _k in range(rng.randint(1, 20)):
            r = rng.randrange(5, 16); c = rng.randrange(8)
            b[r * 8 + c] = 0xD0 | rng.randrange(3)
        out.append(("tall", b, tuple(rng.randrange(3) for _ in range(4)), (rng.randrange(3), rng.randrange(40))))
    return out


def synth_win(n, rng):
    """WIN-root boards (kill the no_clear mutant: a WIN root skips eh_terms, so a stale D_DNG would leak into it):
    a tall throat (live term) + ONE virus at the bottom of col 0 under two same-colour halves -- a vertical pill of
    that colour dropped in col 0 clears the last virus (WIN), while the other roots still fire."""
    out = []
    for _ in range(n):
        b = [0xFF] * 128
        for c in range(1, 8):
            h = rng.choice([10, 11, 12, 13, 14] if 2 <= c <= 5 else [1, 3, 5, 7])
            for r in range(16 - h, 16):
                b[r * 8 + c] = rng.choice([0x40, 0x50, 0x60, 0x70, 0x80]) | rng.randrange(3)
        for c in (3, 4):
            b[c] = b[8 + c] = 0xFF
        k = rng.randrange(3)
        b[15 * 8] = 0xD0 | k; b[14 * 8] = 0x80 | k; b[13 * 8] = 0x80 | k
        for r in range(16):                          # the only virus on the board
            for c in range(1, 8):
                if (b[r * 8 + c] & 0xF0) == 0xD0:
                    b[r * 8 + c] = 0x80 | (b[r * 8 + c] & 3)
        out.append(("win", b, (k, k, rng.randrange(3), rng.randrange(3)), (rng.randrange(3), rng.randrange(40))))
    return out


def setup(arm, mut):
    global ARM
    ARM = arm
    GS.TAPFW = True
    B, D3 = GS.GD._load()
    GDG.G3 = D3.G3
    # module split (#127): the emitter binds the golden it was BUILT against (D3.G3); the mirror must score with the
    # same module, so alias it (the OFF control run proves the aliased mirror == the shipped firmware).
    sys.modules["nes_d3_golden"] = D3.G3
    GDG._orig_leaf = D3.G3.leaf_d3
    D3.G3.leaf_d3 = GDG.leaf_hd
    os.environ["DRDIST"] = "1"
    on = arm != "OFF"
    D3.DRDANGER = int(on); D3.DANGER_ARM = arm if on else "D4"; D3._DANGER_MUT = mut
    os.environ["DRDANGER"] = str(int(on)); os.environ["DRDANGER_ARM"] = D3.DANGER_ARM
    ARM = D3.DANGER_ARM
    ns = _patch_mirror(); ns["_ARM"][0] = D3.DANGER_ARM; GS._ST["on"] = on
    # two patch_vs_cpu copies are live in one process (the emitter pins dr-mario-mods'; the builder's Asm is this
    # tree's): share the opcode table (constants only, cannot change a byte -- the OFF control checks the md5)
    for m in [D3.patch_vs_cpu] + [m for k, m in list(sys.modules.items()) if k == "patch_vs_cpu"]:
        for k, v in D3.patch_vs_cpu.OPS.items():
            m.OPS.setdefault(k, v)
    img = GS.image(B, D3, True)
    GS._ST.update(B=B, D3=D3, img1=img, ns=ns)
    assert D3.DRDIST == 1 and D3.DRDANGER == int(on)
    import hashlib
    return hashlib.md5(bytes(img[0][0x8000:0x9000])).hexdigest()[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="D4"); ap.add_argument("--mut", default=None)
    ap.add_argument("--synth", type=int, default=150); ap.add_argument("--big", type=int, default=60)
    ap.add_argument("--workers", type=int, default=8); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=None); ap.add_argument("--win", type=int, default=0)
    a = ap.parse_args()
    tag = setup(a.arm, a.mut)
    rows = [json.loads(l) for f in ("game_l11.jsonl", "game_l15.jsonl")
            for l in open(os.path.join(ROOT, "experiments", "reach", "corpus", f))]
    tasks = [("game", d["nes"], tuple(x - 1 for x in d["pills"]), (d["speed"], d["speedups"])) for d in rows]
    random.Random(7).shuffle(tasks)
    tasks = tasks[:a.big]
    rng = random.Random(20261013)
    tasks += synth_tall(a.synth, rng)
    tasks += synth_win(a.win, random.Random(20261014))
    if a.limit:
        tasks = tasks[:a.limit]
    print(f"arm={a.arm} mut={a.mut} img8000={tag} tasks={len(tasks)}", flush=True)
    with mp.get_context("fork").Pool(a.workers) as pool:
        res = pool.map(task, tasks, chunksize=1)
    ok = all(r["ok"] for r in res)
    for kind in ("game", "tall", "win"):
        rr = [r for r in res if r["kind"] == kind]
        if rr:
            cy = sorted(r["cyc"] for r in rr)
            print(f"{kind:5s}: fw == mirror(+sim DANGER) {sum(r['ok'] for r in rr)}/{len(rr)}; per-root n bad "
                  f"{sum(1 for r in rr if r['bad'])}; boards with a firing root {sum(1 for r in rr if r['fired'])}; "
                  f"live roots fw==sim {sum(r['hit'] for r in rr)}/{sum(r['fired'] for r in rr)}; "
                  f"D_DNG writes {sum(r['ndng'] for r in rr)}; decision moved {sum(r['moved'] for r in rr)}; cycles median {cy[len(cy)//2]} max {cy[-1]}")
    for r in res:
        if not r["ok"]:
            print("  MISMATCH", {k: r[k] for k in ("kind", "d1", "e1", "bad", "nroot_fw", "nroot_mir")})
    moved = sum(r["moved"] for r in res)
    verdict = "PASS" if ok and (moved > 0 or a.arm == "OFF") else "FAIL"
    print("GATE_DRDANGER", a.arm, a.mut or "-", verdict, flush=True)
    if a.out:
        json.dump(dict(arm=a.arm, mut=a.mut, verdict=verdict, res=res), open(a.out, "w"))


if __name__ == "__main__":
    main()
