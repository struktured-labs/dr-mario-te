"""Dev check: reach_6502.mirror_mask == reach_fw.reach_mask_fw on the corpus (effective masks, legal candidates)."""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro")); sys.path.insert(0, HERE)
sys.path.insert(0, "/home/struktured/projects/dr-mario-mods/tests"); sys.path.insert(0, "/home/struktured/projects/dr-mario-mods")
import reach_6502 as R, reach_fw as RF

def to_live(color, empty=0xFF):
    return [empty if color[r][c] == 0 else (0x80 | ((color[r][c] - 1) & 3)) for r in range(16) for c in range(8)]

def eff_ref(color, thr):
    m = RF.reach_mask_fw(color, thr)          # var-space, all-ones fallback
    return [m[((i >> 3) ^ 2) * 8 + (i & 7)] for i in range(32)]   # -> o4 space

def eff_mir(live, thr):
    rok, flt = R.mirror_mask(live, thr)
    return rok if flt else [1] * 32

if __name__ == "__main__":
    n = bad = boards = 0
    for f in sorted(glob.glob(os.path.join(HERE, "corpus", "*.jsonl"))):
        for l in open(f):
            d = json.loads(l); boards += 1
            ref = eff_ref(d["color"], d["thr"])
            for emp in (0xFF, 0x00):
                mir = eff_mir(to_live(d["color"], emp), d["thr"])
                n += 32; bad += sum(int(x != y) for x, y in zip(ref, mir))
    print(f"boards {boards} candidates {n} mismatches {bad}")
