#!/usr/bin/env python3
"""tuck_bfs enumerator gates, re-run against the INTEGRATED theta400 firmware image.

The standalone gates (tests/test_tuck_bfs_6502.py on the tuck-bfs-6502 branch, merged to
cosim-farm) assembled the routine fresh and ran that. This runner executes the BYTES OF
THE SHIPPED IMAGE instead:

  1. parses the theta400 copro_rom.hex (md5 pinned below) into the $8000-$BFFF ROM image,
  2. re-emits the enumerator at its integrated origin (TUCK_BFS_ROM=$9000, the first
     thing build_copro_d3.py's EMIT_TUCK_BFS block emits) and requires the image to
     carry those exact bytes at that offset -- so the label map applies to shipped bytes,
  3. asserts the stub's descriptor-default guard (LDA #$FF; STA $6139; STA $613A) is
     present in the image -- the init a DRTUCK cart depends on before the first search,
  4. re-runs the OFFICIAL gates with the py65 CPU executing the image bytes:
       stage 3: 200-board real-L11 corpus, bit-exact (cells+orient+colours) vs
                tuck_enum.enumerate(mode="free", union_straight_drops=False), plus the
                "no real board hits OUT_CAP" check,
       stage 4: capacity-64 depth-descending truncation policy on the synthetic
                110-candidate overflow board.

Import provenance is PINNED (the dr-mario-copro-build-provenance trap): every module is
loaded from the cosim-farm worktree that built the image, and __file__ is asserted.

Usage: verify_tuckbfs_fw_image.py [copro_rom.hex] [--limit N]
"""
import hashlib
import os
import sys

FW = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else \
    "/mnt/data/drmario_cosim/fw/theta_sweep/th400/copro_rom.hex"
LIMIT = None
if "--limit" in sys.argv:
    LIMIT = int(sys.argv[sys.argv.index("--limit") + 1])

COSIM_WT = "/home/struktured/projects/dr-mario-cosimfarm-wt"
TESTS = os.path.join(COSIM_WT, "tests")
FW_MD5 = "f78f1e9376405dc996404f68dfa9dfb8"   # theta400, RECIPE-reproduced this session
TUCK_BFS_ROM = 0x9000                          # build_copro_d3.py: TUCK_BFS_ROM = TUCK_V3_ROM

raw = open(FW, "rb").read()
assert hashlib.md5(raw).hexdigest() == FW_MD5, f"not the theta400 image: {FW}"
rom = [int(x, 16) for x in raw.decode().split()]
assert len(rom) == 0x4000, len(rom)

sys.path.insert(0, TESTS)

# INTEGRATED BINDING (the dr-mario-import-mutates-board trap, deliberately reproduced):
# in the real firmware build, importing test_search_d3 sets primitives.LIVE_BOARD = CUR
# ($0700) before build_copro_d3 imports tuck_bfs_6502, so the SHIPPED enumerator reads the
# board from CUR (seeded from $0500 by cp_live_cur at the call site). Bind the same way
# BEFORE importing the emitter; gate A below fails byte-for-byte if this binding is wrong.
sys.path.insert(0, "/home/struktured/projects/dr-mario-mods/tests")
sys.path.insert(0, "/home/struktured/projects/dr-mario-mods")
import primitives as PRIM                      # noqa: E402
PRIM.LIVE_BOARD = 0x0700
BOARD_AT = 0x0700

import test_tuck_bfs_6502 as T                 # noqa: E402  (pulls TB, tuck_enum, Cpu)
import py65_harness as H                       # noqa: E402
H.HALT = 0x4FF0                                # default $9000 collides with TUCK_BFS_ROM

TB = T.TB
assert TB.LIVE_BOARD == BOARD_AT, hex(TB.LIVE_BOARD)
assert os.path.samefile(TB.__file__, os.path.join(TESTS, "tuck_bfs_6502.py")), TB.__file__
assert os.path.samefile(T.__file__, os.path.join(TESTS, "test_tuck_bfs_6502.py")), T.__file__

# ---- gate A: the image carries the enumerator's exact bytes at $9000 --------
a = TB.build(base=TUCK_BFS_ROM)
code = a.assemble()
off = TUCK_BFS_ROM - 0x8000
got = bytes(rom[off:off + len(code)])
assert got == bytes(code), \
    f"image bytes at ${TUCK_BFS_ROM:04X} != enumerator emission ({len(code)} B)"
print(f"[gateA] integrated image carries the enumerator byte-exact at ${TUCK_BFS_ROM:04X} "
      f"({len(code)} B); label map applies to shipped bytes")

# ---- gate B: stub descriptor-default guard ----------------------------------
guard = bytes([0xA9, 0xFF, 0x8D, 0x39, 0x61, 0x8D, 0x3A, 0x61])
b = bytes(rom)
occ = []
j = b.find(guard)
while j >= 0:
    occ.append(0x8000 + j)
    j = b.find(guard, j + 1)
# exactly two legitimate sites: the reset stub (STUB=$BF80, runs before every search) and
# tuck_root_extension's own no-winner reset (tuck_v3.py:762, inside the $9000 tuck block)
assert len(occ) == 2, f"descriptor-default guard found {len(occ)}x at {occ}, expected 2"
assert any(x >= 0xBF80 for x in occ) and any(0x9000 <= x < 0xA800 for x in occ), occ
print(f"[gateB] TUCK_COL/TUCK_ROW ($6139/$613A) default-$FF writes present at "
      f"{['$%04X' % x for x in occ]}: stub pre-search init + tuck_root_extension "
      f"no-winner reset -- both halves of the descriptor-liveness contract")

# ---- run the official gates on the IMAGE bytes ------------------------------
addr = TUCK_BFS_ROM + a.labels["tuck_bfs"]


def image_cpu():
    cpu = T.Cpu()
    cpu.load(0x8000, rom)                      # the whole shipped image, not a re-emission
    return cpu


def call_bfs_at(cpu, grid, ca, cb):
    """T.call_bfs, but the board goes where the INTEGRATED routine reads it (CUR=$0700)."""
    board = T.fb_to_nes(grid)
    for i, b in enumerate(board):
        cpu.mem[BOARD_AT + i] = b & 0xFF
    cpu.set_zp(TB.PILL_A, ca)
    cpu.set_zp(TB.PILL_B, cb)
    return cpu.call(addr, max_steps=4_000_000)


# stage 3 -- 200-board corpus, bit-exact vs tuck_enum
import json                                     # noqa: E402
corpus = json.load(open(os.path.join(TESTS, "tuck_bfs_corpus_200.json")))
boards = corpus["boards"][:LIMIT] if LIMIT else corpus["boards"]
cpu = image_cpu()
bad = at_cap = 0
cand_counts = []
for i, rec in enumerate(boards):
    call_bfs_at(cpu, rec["col"], rec["ca"], rec["cb"])
    n, cand = T.read_candidates(cpu, a)
    cand_counts.append(n)
    if n >= TB.OUT_CAP:
        at_cap += 1
    if set(cand) != T.reference_set(rec["col"], rec["ca"], rec["cb"]):
        bad += 1
        print(f"  MISMATCH board id={rec.get('id')}")
    if (i + 1) % 25 == 0:
        print(f"  ... {i + 1}/{len(boards)} boards", flush=True)
cand_counts.sort()
print(f"[stage3/IMAGE] BIT-EXACT vs tuck_enum (cells+orient+colours): "
      f"{len(boards) - bad}/{len(boards)} boards match; candidates/board "
      f"min={cand_counts[0]} median={cand_counts[len(cand_counts) // 2]} "
      f"max={cand_counts[-1]} (cap={TB.OUT_CAP}, at/over cap={at_cap})")
assert bad == 0 and at_cap == 0

# stage 4 -- capacity-64 depth-descending policy on the overflow board
grid = json.load(open(os.path.join(TESTS, "overflow_board.json")))
full = T.reference_set(grid, 1, 2)
cpu = image_cpu()
call_bfs_at(cpu, grid, 1, 2)
n, cand = T.read_candidates(cpu, a)
got = set(cand)
exp = T.expected_after_capacity(grid, 1, 2, cap=TB.OUT_CAP)
assert n == TB.OUT_CAP, n
assert got == exp, "capacity policy mismatch"
_IS_H = (True, False, True, False)


def anchor_row(cells, o):
    return cells[0] if _IS_H[o] else cells[2]


dropped = full - got
min_kept = min(anchor_row(c, o) for c, o, _ in got)
max_dropped = max(anchor_row(c, o) for c, o, _ in dropped)
assert min_kept >= max_dropped, (min_kept, max_dropped)
print(f"[stage4/IMAGE] capacity policy: {len(full)} reachable -> {n} kept == "
      f"depth-descending reference truncation exactly; row invariant holds "
      f"(min_kept_row={min_kept} >= max_dropped_row={max_dropped})")

print("\nALL FIRMWARE-IMAGE GATES PASS:", FW)
