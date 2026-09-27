#!/usr/bin/env python3
"""G3 tempo scenario bank (population declared, R63):
  B1  the 5 vetog1 fatal-board reconstructions (min-fo<=2 spawn-rest, ledge class)
  B2  owner-match G2/G3 parents (the 2/2 predicate boards)
  B3  PC4cap0 (argmax-vetoed positive control family)
  B4  synthetic one/two-sided ledges + no-escape control (stripes, 3 deep viruses)
Each board x 3 pill combos (latency varies with pill colors).  No py65 reference
needed -- this bank feeds the timestamped latency sim only."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DRV = os.path.abspath(os.path.join(HERE, ".."))
VETOG1 = os.path.join(DRV, "g1_cosim", "vetog1_parents")
CMAP = {"Y": 0, "R": 1, "B": 2}
V, J = 0xD0, 0x40


def load_vetog1(path):
    d = json.load(open(path))
    vs = {tuple(x) for x in d["virus_cells"]}
    b = [0xFF] * 128
    for r in range(16):
        for c in range(8):
            ch = d["grid"][r][c]
            if ch != ".":
                b[r * 8 + c] = CMAP[ch] | (0xD0 if (r, c) in vs else 0x40)
    return b


def load_owner(path, n_virus, virus_rows):
    grid = json.load(open(path))
    b = [0xFF] * 128
    for r in range(16):
        for c in range(8):
            ch = grid[r][c]
            if ch != ".":
                b[r * 8 + c] = CMAP[ch] | 0x40
    marked = 0
    for r in virus_rows:
        for c in range(8):
            i = r * 8 + c
            if b[i] != 0xFF and marked < n_virus:
                b[i] = (b[i] & 0x03) | 0xD0
                marked += 1
    assert marked == n_virus
    return b


def pc4_board(cap):
    def fill(b, col, fo, colors):
        for k, r in enumerate(range(fo, 16)):
            b[r * 8 + col] = colors[k]
    b = [0xFF] * 128
    oth = [c for c in (0, 1, 2) if c != cap]
    for c in (0, 1, 2, 5, 6, 7):
        fill(b, c, 0, [J | oth[0], J | oth[1], J | oth[0], J | oth[1]] * 4)
    fill(b, 3, 2, [V | cap, J | oth[0], J | oth[1], J | oth[0]] * 4)
    fill(b, 4, 4, [V | oth[1], J | oth[0], J | oth[1], J | oth[0]] * 3)
    return b


def synth(fo, virus_cols=(0, 1, 7)):
    b = [0xFF] * 128
    for c in range(8):
        for r in range(16):
            if r >= fo[c]:
                b[r * 8 + c] = ((r + c) % 3) | 0x40
    for c in virus_cols:
        if fo[c] <= 14:
            i = 15 * 8 + c
            b[i] = (b[i] & 0x03) | 0xD0
    return b


SYNTH = {
    "synth_L4f1":         [13, 13, 13, 12, 1, 8, 8, 8],   # vetog1 archetype
    "synth_L3f1":         [8, 8, 8, 1, 12, 13, 13, 13],   # mirrored
    "synth_L4f2":         [13, 13, 13, 12, 2, 8, 8, 8],
    "synth_L3f2":         [8, 8, 8, 2, 12, 13, 13, 13],
    "synth_L4f1_gateblk": [13, 13, 0, 12, 1, 8, 8, 8],    # left gate full -> 1 edge fails
    "synth_B34f1":        [10, 10, 10, 1, 1, 10, 10, 10], # both-sides plug, 2-edge class
    "synth_B34f2":        [10, 10, 10, 2, 2, 10, 10, 10],
    "synth_none":         [0, 0, 0, 1, 1, 0, 0, 0],       # no escape exists (control)
    "synth_L4f1_shallow": [4, 4, 4, 3, 1, 8, 8, 8],
}

PILLS = [(1, 0, 0, 1), (0, 2, 2, 2), (2, 1, 1, 1)]

cases = []
for nm in ("parent_s1A", "parent_s1B", "parent_s2A", "parent_s3A", "parent_s4A"):
    b = load_vetog1(os.path.join(VETOG1, nm + ".json"))
    for i, p in enumerate(PILLS):
        cases.append((f"{nm}_p{i}", b, p))
for nm, nv, vr in (("g2_parent", 2, [15, 14]), ("g3_parent", 15, [15, 14, 13, 12])):
    b = load_owner(os.path.join(DRV, nm + ".json"), nv, vr)
    for i, p in enumerate(PILLS):
        cases.append((f"{nm[:2]}_p{i}", b, p))
b = pc4_board(0)
for i, p in enumerate(PILLS):
    cases.append((f"PC4cap0_p{i}", b, p))
for nm, fo in SYNTH.items():
    for i, p in enumerate(PILLS[:2]):
        cases.append((f"{nm}_p{i}", synth(fo), p))

# shard into 4 files for parallel sims
NSH = 4
shards = [[] for _ in range(NSH)]
for k, c in enumerate(cases):
    shards[k % NSH].append(c)
for s, sh in enumerate(shards):
    lines = [str(len(sh))]
    for (name, board, (cA, cB, nA, nB)) in sh:
        lines.append(f"{name} {cA} {cB} {nA} {nB} 0 0")
        lines.append(" ".join("%02x" % x for x in board))
    open(os.path.join(HERE, f"g3cases_{s}.txt"), "w").write("\n".join(lines) + "\n")
    print(f"shard {s}: {len(sh)} cases")
print(f"total {len(cases)} cases")
