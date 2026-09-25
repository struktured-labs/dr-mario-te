#!/usr/bin/env python3
"""GATES G1 + G3 for DRREACH: the WHOLE firmware search under py65 (engine emu), ship recipe env (CHAIN540 +
DRSTRAND 20 + DRVETO + DBLCANON + tuck knobs), against the verbatim nes_d3_golden replica with the reach mask.

  S   STATIC: every instruction in the DRREACH=1 image with an absolute operand $6126/$6127 (S_NA/S_NB) is an
      LDA immediately followed by AND #$0F (the only way the transport nibbles could leak into the search).
  G1a TRANSPORT INERT (DRREACH=0): random high nibbles in S_NA/S_NB change NO decision vs zero nibbles, and every
      value the search writes to the engine colour args (LEV_A_CA/CB) is < 16.
  G1b OLD CART (DRREACH=1, zero nibbles) == DRREACH=0 decisions exactly -> an old cart runs today's search.
  G3  SEARCH (DRREACH=1, real transport nibbles) == mirror(skip every root candidate masked by reach_fw; if none of
      the legal candidates is allowed, unfiltered), and colour-arg writes stay < 16. Boards: real gate-(b) game
      boards (L11 + L15, their own pills) at their own gravity AND at fast gravity (mask bites harder), plus
      make_fewlegal boards. NON-VACUITY: the filter moves the argmax on some boards.
Mutants (each must be KILLED): PENALTY (o_cand -20000 instead of the skip) on a synthesized masked-winner board;
  NOAND (one S_NA read without AND #$0F) -> colour-arg write >= 16 and/or S fails.
Usage: gate_reach_search.py [--game N] [--fast N] [--few N] [--g1 N] [--workers W]
"""
import argparse, json, os, sys, random, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro")); sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "experiments", "drveto"))
RECIPE_ENV = {"DRSTRAND": "20", "DRCHAIN": "540", "DRCOPRO_ARM": "1", "DRFIX": "1", "DRCOPRO_TUCKBFS": "1",
              "DRCOPRO_TUCKBFS_TIER3": "1", "DRCOPRO_TUCKV3_THETA": "400", "DRDBLCANON": "1",
              "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRVETO": "1", "DRREACH": "0"}
os.environ.update(RECIPE_ENV)
import gate_drveto as GD                      # run_fw conventions, decide_mirror (verbatim golden + STRAND + VETO)
os.environ.update(RECIPE_ENV)                  # gate_drveto's import sets DRCHAIN=180; restore the ship recipe
import reach_6502 as RC
import reach_fw as RF

TS = (0x10 | 1) ^ 0xA4
S_NA, S_NB = 0x6126, 0x6127
_ST = {}


def image(B, D3, reach):
    os.environ["DRREACH"] = "1" if reach else "0"
    img, clen, _ = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    _code, labels = D3.build()
    return img, 0x8000 + labels["search"]


def run_fw(img, ep, board, cA, cB, nA, nB, ts=TS):
    """GD.run_fw + an observer on the engine colour-arg registers: returns (decision, max value written)."""
    from py65.memory import ObservableMemory
    from py65_harness import Cpu
    B, D3 = _ST["B"], _ST["D3"]
    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    for i in range(16):
        cpu.mem[D3.PILLA + i] = img[B.PILL_ROM + i]
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    base = cpu.mem
    obs = ObservableMemory(subject=base)
    mx = [0]

    def on_arg(addr, value):
        mx[0] = max(mx[0], value & 0xFF)
        base[addr] = value
    obs.subscribe_to_write([D3.LEV_A_CA, D3.LEV_A_CB], on_arg)
    cpu.mpu.memory = obs; cpu.mem = obs
    cpu.mem[S_NA - 2] = ((int(ts) & 0x0F) << 4) | cA          # S_CA
    cpu.mem[S_NA - 1] = (int(ts) & 0xF0) | cB                 # S_CB
    cpu.mem[S_NA], cpu.mem[S_NB] = nA, nB
    cpu.call(ep, max_steps=B.MAX_STEPS)
    dec = None if cpu.mem[D3.D_BO] == 0xFF else (cpu.mem[D3.D_BC], cpu.mem[D3.D_BO])
    return dec, mx[0]


def color_grid(nes):
    return [[0 if nes[r * 8 + c] in (0xFF, 0x00) else 1 for c in range(8)] for r in range(16)]


def reach_eff(nes, thr):
    m = RF.reach_mask_fw(color_grid(nes), thr)
    return [m[((i >> 3) ^ 2) * 8 + (i & 7)] for i in range(32)]


def mirror(D3, board, pA, pB, nA, nB, seed, mask=None):
    import nes_d3_golden as G
    if mask is None:
        return GD.decide_mirror(D3, board, pA, pB, nA, nB, seed, veto=True)
    orig = G._placements4
    state = {"root": True}

    def filtered(b, a_, b_):
        pl = orig(b, a_, b_)
        if state["root"]:
            state["root"] = False
            keep = [p for p in pl if mask[p[0] * 8 + p[1]]]
            return keep if keep else pl
        return pl
    G._placements4 = filtered
    try:
        return GD.decide_mirror(D3, board, pA, pB, nA, nB, seed, veto=True)
    finally:
        G._placements4 = orig


def expect(D3, board, cA, cB, nA, nB, mask, ts=TS):
    k = mirror(D3, board, cA, cB, nA, nB, ts & 0xFF, mask)
    if k is None:
        return None
    col, o4 = k
    return (col, D3.canon_o4(o4, cA, cB))


def task(t):
    D3 = _ST["D3"]
    kind, nes, (cA, cB, nA, nB), (sp, su), do_g1 = t
    thr = RC.SPEED_TABLE[min(80, RC.SPEED_BASE[sp] + su)]
    hiA, hiB = RC.pack_nibbles(sp, su)
    out = {"kind": kind, "sp": sp, "su": su, "thr": thr}
    img0, ep0 = _ST["img0"]; img1, ep1 = _ST["img1"]
    if do_g1:
        r = random.Random(sum(nes) * 7 + cA)
        d0, m0 = run_fw(img0, ep0, nes, cA, cB, nA, nB)
        d0r, m0r = run_fw(img0, ep0, nes, cA, cB, nA | (r.randrange(1, 16) << 4), nB | (r.randrange(1, 16) << 4))
        d1o, m1o = run_fw(img1, ep1, nes, cA, cB, nA, nB)
        out.update(g1a=(d0 == d0r and m0r < 16), g1b=(d1o == d0), d0=d0)
    mask = reach_eff(nes, thr)
    d1, m1 = run_fw(img1, ep1, nes, cA, cB, nA | hiA, nB | hiB)
    e1 = expect(D3, nes, cA, cB, nA, nB, mask)
    e0 = expect(D3, nes, cA, cB, nA, nB, None)
    out.update(g3=(d1 == e1 and m1 < 16), d1=d1, e1=e1, e0=e0, masked=32 - sum(mask), moved=(e1 != e0), argmax=m1)
    return out


def static_audit(img):
    """Every absolute-operand instruction touching $6126/$6127 must be LDA abs followed by AND #$0F."""
    absops = {0xAD, 0xBD, 0xB9, 0xAE, 0xBE, 0xAC, 0xBC, 0x6D, 0x7D, 0x79, 0xED, 0xFD, 0xF9, 0xCD, 0xDD, 0xD9, 0x2D,
              0x3D, 0x39, 0x0D, 0x1D, 0x19, 0x4D, 0x5D, 0x59, 0xEE, 0xFE, 0xCE, 0xDE, 0x0E, 0x1E, 0x4E, 0x5E, 0x2E, 0x3E,
              0x6E, 0x7E, 0xEC, 0xCC, 0x2C, 0x8D, 0x9D, 0x99, 0x8E, 0x8C}
    hits, bad = [], []
    for i in range(0x8000, 0xC000 - 2):
        if img[i] in absops and img[i + 1] in (0x26, 0x27) and img[i + 2] == 0x61:
            if RC.REACH_ROM <= i < RC.REACH_ROM + 0x800:
                continue          # the reach routine's own transport decode reads the HIGH nibble by design
            ok = img[i] == 0xAD and img[i + 3] == 0x29 and img[i + 4] == 0x0F
            hits.append(i)
            if not ok:
                bad.append((hex(i), hex(img[i]), bytes(img[i:i + 5]).hex(" ")))
    return hits, bad


def reach_decode_reads(img):
    """The reach routine must read S_NB then S_NA exactly once each (the transport decode)."""
    out = []
    for i in range(RC.REACH_ROM, RC.REACH_ROM + 0x800 - 2):
        if img[i] == 0xAD and img[i + 2] == 0x61 and img[i + 1] in (0x26, 0x27):
            out.append((hex(i), hex(img[i + 1])))
    return out


def init_worker():
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", type=int, default=80); ap.add_argument("--fast", type=int, default=60)
    ap.add_argument("--few", type=int, default=20); ap.add_argument("--g1", type=int, default=60)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    B, D3 = GD._load()
    _ST.update(B=B, D3=D3, img0=image(B, D3, False), img1=image(B, D3, True))
    rng = random.Random(20260925)
    # ---- S static audit
    hits, bad = static_audit(_ST["img1"][0])
    rd = reach_decode_reads(_ST["img1"][0])
    print(f"S   static: {len(hits)} abs refs to S_NA/S_NB in search/tuck/stub of the DRREACH=1 image, non-(LDA;AND #$0F): "
          f"{bad or 'none'}; reach decode reads {rd}")
    ok = not bad and len(hits) > 0 and len(rd) == 2
    # ---- task list
    rows = [json.loads(l) for f in ("game_l11.jsonl", "game_l15.jsonl") for l in open(os.path.join(HERE, "corpus", f))]
    step = max(1, len(rows) // args.game)
    tasks = []
    for j, d in enumerate(rows[::step][:args.game]):
        p = [x - 1 for x in d["pills"]]
        tasks.append(("game", d["nes"], tuple(p), (d["speed"], d["speedups"]), j < args.g1))
    fastsp = [(2, 30), (2, 40), (2, 49), (1, 40), (1, 49)]
    for j, d in enumerate(rows[step // 2::step][:args.fast]):
        p = [x - 1 for x in d["pills"]]
        tasks.append(("fast", d["nes"], tuple(p), fastsp[j % len(fastsp)], False))
    from test_search_d3 import make_fewlegal
    FSIM = "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim"
    for pth in (os.path.join(FSIM, "src"), os.path.join(FSIM, "tmp")):
        if pth not in sys.path:
            sys.path.insert(0, pth)
    from drmario.faithful_game import FaithfulBoard
    from xcheck_terms import faithful_to_nes
    for j in range(args.few):
        nes = list(faithful_to_nes(make_fewlegal(rng, FaithfulBoard)))
        tasks.append(("few", nes, tuple(rng.randint(0, 2) for _ in range(4)), fastsp[j % len(fastsp)], True))
    with mp.get_context("fork").Pool(args.workers, initializer=init_worker) as pool:
        res = pool.map(task, tasks, chunksize=1)
    g1 = [r for r in res if "g1a" in r]
    g1a = sum(r["g1a"] for r in g1); g1b = sum(r["g1b"] for r in g1)
    g3 = sum(r["g3"] for r in res)
    print(f"G1a transport inert (DRREACH=0, random nibbles; colour args < 16): {g1a}/{len(g1)}")
    print(f"G1b old cart (DRREACH=1, no nibbles) == DRREACH=0:              {g1b}/{len(g1)}")
    for kind in ("game", "fast", "few"):
        rr = [r for r in res if r["kind"] == kind]
        print(f"G3  {kind:4s}: firmware == masked mirror {sum(r['g3'] for r in rr)}/{len(rr)}; mask non-trivial on "
              f"{sum(r['masked'] > 0 for r in rr)}; filter moved the argmax on {sum(r['moved'] for r in rr)}")
    for r in res:
        if not r["g3"] or ("g1a" in r and not (r["g1a"] and r["g1b"])):
            print("   MISMATCH", r)
    moved = sum(r["moved"] for r in res)
    ok &= g1a == len(g1) and g1b == len(g1) and g3 == len(res) and moved > 0
    # ---- masked-winner board + PENALTY mutant
    E = 0xFF
    mw = [E] * 128; mw[15 * 8 + 0] = 0xD0; mw[14 * 8 + 0] = 0xD0
    pc = (0, 0, 1, 2); sp = (2, 49)
    thr = RC.SPEED_TABLE[80]; hiA, hiB = RC.pack_nibbles(*sp); mk = reach_eff(mw, thr)
    e_skip = expect(D3, mw, *pc, mk); e_open = expect(D3, mw, *pc, None)
    d_ok, _ = run_fw(*_ST["img1"], mw, pc[0], pc[1], pc[2] | hiA, pc[3] | hiB)
    print(f"masked-winner board: unfiltered {e_open}  skip {e_skip}  firmware {d_ok}")
    ok &= d_ok == e_skip and e_skip != e_open
    D3._REACH_PENALTY_MUT = True
    imgp = image(B, D3, True); D3._REACH_PENALTY_MUT = False
    d_pen, _ = run_fw(*imgp, mw, pc[0], pc[1], pc[2] | hiA, pc[3] | hiB)
    kp = d_pen != e_skip
    print(f"   mutant PENALTY: firmware {d_pen} vs skip {e_skip} -> {'KILLED' if kp else 'SURVIVED'}")
    # ---- NOAND mutant: static audit + colour-arg observer
    D3._REACH_NOAND_MUT = True
    imgn = image(B, D3, True); D3._REACH_NOAND_MUT = False
    _, badn = static_audit(imgn[0])
    few = [t for t in tasks if t[0] == "game"][:3]
    leak = 0
    for t in few:
        _, (cA, cB, nA, nB), (sp_, su_) = t[1], t[2], t[3]
        hA, hB = RC.pack_nibbles(sp_, su_)
        _, mxn = run_fw(*imgn, t[1], cA, cB, nA | hA, nB | hB)
        leak += int(mxn >= 16)
    kn = bool(badn) and leak > 0
    print(f"   mutant NOAND: static audit flags {len(badn)} site(s); colour-arg writes >= 16 on {leak}/3 boards -> {'KILLED' if kn else 'SURVIVED'}")
    ok &= kp and kn
    print("GATE_REACH_SEARCH", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
