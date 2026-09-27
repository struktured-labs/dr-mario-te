"""Synthetic stress boards for the DRREACH gate: every (speed, speedUps) pair, tall/holey/overhung boards, PROPH-armed
throats, narrow wells. Writes corpus/synth.jsonl (same schema as the game corpus; mask = reach_fw)."""
import sys, os, json, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "fpga", "copro"))
sys.path.insert(0, "/home/struktured/projects/dr-mario-mods/tests"); sys.path.insert(0, "/home/struktured/projects/dr-mario-mods")
import reach_fw as RF, reach_6502 as R

def board(rng):
    kind = rng.randrange(6)
    color = [[0] * 8 for _ in range(16)]
    for c in range(8):
        h = rng.choice([0, 0, 1, 2, 3, 4, 6, 8, 10, 12, 13, 14, 15]) if kind != 3 else rng.choice([10, 12, 13, 14, 15, 16])
        for r in range(16 - h, 16):
            color[r][c] = 1 + rng.randrange(3)
        if kind in (1, 2):                       # holes / overhangs
            for _ in range(rng.randrange(4)):
                r = rng.randrange(max(1, 16 - h), 16) if h else 15
                color[r][c] = 0
    if kind == 2:                                # floating ledges
        for _ in range(rng.randrange(1, 5)):
            color[rng.randrange(2, 14)][rng.randrange(8)] = 1 + rng.randrange(3)
    if kind == 4:                                # PROPH throat armed
        for c in (3, 4):
            if rng.random() < 0.7:
                for r in range(rng.randrange(1, 3), 16):
                    color[r][c] = 1 + rng.randrange(3)
        for c in (2, 5):
            if rng.random() < 0.3:
                color[rng.randrange(0, 2)][c] = 1
    if kind == 5:                                # narrow wells
        for c in range(8):
            if c % 2 == rng.randrange(2):
                for r in range(rng.randrange(3, 8), 16):
                    color[r][c] = 1 + rng.randrange(3)
    return color

if __name__ == "__main__":
    rng = random.Random(20260925); n = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    with open(os.path.join(HERE, "corpus", "synth.jsonl"), "w") as fh:
        for i in range(n):
            sp = i % 3; su = (i // 3) % 50
            thr = R.SPEED_TABLE[min(80, R.SPEED_BASE[sp] + su)]
            color = board(rng)
            fh.write(json.dumps({"level": -1, "seed": i, "k": su * 10, "speed": sp, "speedups": su, "thr": thr,
                                 "color": color, "mask": RF.reach_mask_fw(color, thr)}) + "\n")
    print("wrote", n)
