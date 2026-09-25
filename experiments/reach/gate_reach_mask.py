#!/usr/bin/env python3
"""GATE G2 for DRREACH: the 6502 reach routine (fpga/copro/reach_6502.emit_reach, run under py65) produces EXACTLY
reach_fw.reach_mask_fw's mask on every corpus board, with thr decoded from the real DRREACHTX transport nibbles.

Checks
  T  transport: for every (speed 0..2, speedUps 0..49) the 6502-decoded thr == speedCounterTable[base+su];
     old cart (NB high nibble 0) -> R_FLT = 0 (no filter); invalid speed field -> R_FLT = 0.
  M  mask: effective mask (ROK if R_FLT else all-ones) == reach_fw (re-indexed var = o4 ^ 2) for every legal
     candidate, both empty encodings ($FF and $00), on the game corpus (L11 + L15 couch-steering gate-b boards) and
     a synthetic stress set (all speeds, overhangs, PROPH throats, wells).
Mutants (each must FAIL M): tlat_m1, tlat_p1, no_distgate, no_fallback.
Usage: gate_reach_mask.py [--synth N] [--mut-boards N]      exit 0 = all pass AND all mutants killed.
"""
import argparse, json, os, sys, glob, random, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro")); sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, HERE)
sys.path.insert(0, "/home/struktured/projects/dr-mario-mods/tests"); sys.path.insert(0, "/home/struktured/projects/dr-mario-mods")
from patch_vs_cpu import Asm6502
from py65_harness import Cpu
import reach_6502 as R
import reach_fw as RF

S_NA, S_NB = 0x6126, 0x6127


TAPBUILD = False          # --tap: gate the DRREACHTAP routine (P decoded from the colour low-nibble bits 2-3)


def build(mut="none"):
    R._MUT = mut
    a = Asm6502(R.REACH_ROM)
    R.emit_reach(a, S_NA, S_NB, tap=TAPBUILD)
    code = a.assemble()
    assert a.labels["reach_mask"] == 0, "entry must be the first byte"
    R._MUT = "none"
    return code


def run(code, live, na, nb):
    cpu = Cpu()
    cpu.load(R.REACH_ROM, code)
    for i, b in enumerate(live):
        cpu.mem[R.LIVE + i] = b
    cpu.mem[S_NA], cpu.mem[S_NB] = na, nb
    cyc = cpu.call(R.REACH_ROM, max_steps=5_000_000)
    rok = [cpu.mem[R.ROK + i] for i in range(32)]
    return rok, cpu.mem[R.R_FLT], cpu.mem[R.R_THR], cyc


def to_live(color, empty=0xFF, rng=None):
    out = []
    for r in range(16):
        for c in range(8):
            if color[r][c] == 0:
                out.append(empty)
            else:
                k = (color[r][c] - 1) % 3
                out.append((0xD0 | k) if (rng and rng.random() < 0.3) else (rng.choice([0x40, 0x50, 0x60, 0x70, 0x80]) | k if rng else 0x80 | k))
    return out


def ref_eff(color, thr, tap=0):
    m = RF.reach_mask_fw(color, thr, tap or None)
    return [m[((i >> 3) ^ 2) * 8 + (i & 7)] for i in range(32)]


def load_corpus(synth_n):
    game = [json.loads(l) for f in sorted(glob.glob(os.path.join(HERE, "corpus", "game_*.jsonl"))) for l in open(f)]
    synth = [json.loads(l) for l in open(os.path.join(HERE, "corpus", "synth.jsonl"))][:synth_n]
    return game, synth


def check_transport(code):
    bad = 0
    for sp in range(3):
        for su in range(50):
            hi_a, hi_b = R.pack_nibbles(sp, su)
            want = R.SPEED_TABLE[min(80, R.SPEED_BASE[sp] + su)]
            assert R.thr_from_nibbles(hi_a | 1, hi_b | 2) == want
            _, flt, thr, _ = run(code, [0xFF] * 128, hi_a | 1, hi_b | 2)
            bad += int(thr != want)
    rok, flt, _, _ = run(code, [0xFF] * 128, 0x01, 0x02)          # old cart: high nibbles 0
    old_ok = flt == 0
    _, flt_bad, _, _ = run(code, [0xFF] * 128, 0x01, 0x12)        # NB hi = 1: speed field 0 -> speed -1 = invalid
    return bad, old_ok and flt_bad == 0


def check_mask(code, boards, rng, both_empty=True, tap=0):
    n = bad = 0; cyc_max = 0; first_bad = None
    for d in boards:
        ref = ref_eff(d["color"], d["thr"], tap)
        hi_a, hi_b = R.pack_nibbles(d["speed"], d["speedups"])
        lo_a, lo_b = (tap & 3) << 2, ((tap >> 2) & 3) << 2         # the DRTAPP transport (0 = DAS)
        for emp in ((0xFF, 0x00) if both_empty else (0xFF,)):
            live = to_live(d["color"], emp, rng)
            rok, flt, thr, cyc = run(code, live, hi_a | lo_a | rng.randrange(3), hi_b | lo_b | rng.randrange(3))
            assert thr == d["thr"], (thr, d["thr"])
            eff = rok if flt else [1] * 32
            legal = [i for i in range(32) if _legal(d["color"], i)]
            mm = sum(int(eff[i] != ref[i]) for i in legal)
            n += len(legal); bad += mm; cyc_max = max(cyc_max, cyc)
            if mm and first_bad is None:
                first_bad = (d.get("seed"), d.get("k"), d["thr"], emp)
    return n, bad, cyc_max, first_bad


def _legal(color, idx):
    o4, col = idx >> 3, idx & 7
    top = RF.tops(color)
    vert = (o4 & 2) == 0
    if not vert and col >= 7:
        return False
    return (top[col] >= 2) if vert else (min(top[col], top[col + 1]) >= 1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--synth", type=int, default=1500); ap.add_argument("--mut-boards", type=int, default=400)
    ap.add_argument("--tap", action="store_true", help="gate the DRREACHTAP routine at --taps periods")
    ap.add_argument("--taps", default="0,2,3")
    args = ap.parse_args()
    global TAPBUILD
    TAPBUILD = args.tap
    taps = [int(x) for x in args.taps.split(",")] if args.tap else [0]
    rng = random.Random(7)
    game, synth = load_corpus(args.synth)
    code = build()
    print(f"reach routine: {len(code)} B at ${R.REACH_ROM:04X} (md5 {hashlib.md5(code).hexdigest()[:8]}); RAM ${R.ROK:04X}-${R.REACH_RAM_END - 1:04X}")
    tb, old_ok = check_transport(code)
    print(f"T  transport: thr mismatches {tb}/150; old cart (NB hi = 0) -> no filter: {old_ok}")
    ok = tb == 0 and old_ok
    for tp in taps:
        for name, boards in (("game", game), ("synth", synth)):
            n, bad, cyc, fb = check_mask(code, boards, rng, tap=tp)
            print(f"M  {name} {'P=' + str(tp) if args.tap else 'DAS'}: {len(boards)} boards, {n} legal candidate checks (x2 empty encodings), mismatches {bad}, max {cyc} cycles{'' if not fb else ' first bad ' + str(fb)}")
            ok &= bad == 0
    killed = True
    mb = (game + synth)[:: max(1, (len(game) + len(synth)) // args.mut_boards)]
    muts = ("tlat_m1", "tlat_p1", "no_distgate", "no_fallback") + (("rot_das",) if args.tap else ())
    for mut in muts:
        mc = build(mut)
        tp = next((t for t in taps if t), 0) if mut == "rot_das" else taps[-1]
        n, bad, _, _ = check_mask(mc, mb, rng, both_empty=False, tap=tp)
        print(f"   mutant {mut:12s} (P={tp}): mismatches {bad}/{n} -> {'KILLED' if bad else 'SURVIVED'}")
        killed &= bad > 0
    print("GATE_REACH_MASK", "PASS" if ok and killed else "FAIL")
    sys.exit(0 if ok and killed else 1)


if __name__ == "__main__":
    main()
