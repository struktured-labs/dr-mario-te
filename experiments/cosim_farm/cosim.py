#!/usr/bin/env python3
"""Client for the persistent co-sim server (sim_farm.cpp), plus the board encoding.

The RTL is the decision-maker. Everything in this module is transport and encoding --
there is deliberately NO fallback path that computes a move in Python, because a fallback
is exactly how the py65-vs-RTL fidelity gap (CANDIDATE_TIER3.md sec 10: py65 agrees with
real RTL on 13.3% of real-L11 base-search moves) would leak back in unnoticed. If the
server dies or times out, callers get an exception, not a move.
"""
from __future__ import annotations

import hashlib
import os
import subprocess

EMPTY_NES = 0xFF
NCELL = 128
ROWS, COLS = 16, 8

# RTL a_o4 -> faithful-sim variant. Empirically recovered by
# experiments/bitexact_gate/gate.py:recover_o4_map() against the pinned RTL node corpus,
# and asserted (not assumed) in experiments/bitexact_gate/linkcorpus.py. Getting it
# backwards silently swaps horizontal for vertical and every case still "runs".
VAR_OF_O4 = (2, 3, 0, 1)

# faithful-sim variant -> (orientation, flipped). Mirrors FaithfulDrMarioEnv._decode:
#   0 = horizontal (a left,  b right)      2 = vertical (a top,    b bottom)
#   1 = horizontal (b left,  a right)      3 = vertical (b top,    a bottom)
VARIANT_IS_VERTICAL = (False, False, True, True)
VARIANT_IS_FLIPPED = (False, True, False, True)


def board_to_nes(board) -> list[int]:
    """FaithfulBoard -> the 128 NES playfield bytes the copro's $5000 window expects.

    Encoding per MECHANICS_NES.md and CoproDrMario.sv's own lev_enc/lev_lnk decode:
      empty          0xFF
      virus          0xD0 | (color-1)
      vertical pair  0x4x top / 0x5x bottom
      horizontal     0x6x left / 0x7x right
      orphaned half  0x8x
    The HIGH nibble carries the capsule-half link, and CoproDrMario.sv's lev_lnk decodes
    it -- so dropping links here would feed the chain/link engine a board of orphans and
    silently change the eval. The link plane is threaded through, not flattened.
    """
    from drmario.faithful_game import (
        EMPTY, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT,
    )
    hi_of_link = {LINK_UP: 0x5, LINK_DOWN: 0x4, LINK_LEFT: 0x7, LINK_RIGHT: 0x6}
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            color = int(board.color[r, c])
            if color == EMPTY or color == 0:
                out.append(EMPTY_NES)
            elif board.is_virus[r, c]:
                out.append(0xD0 | (color - 1))
            else:
                out.append((hi_of_link.get(int(board.link[r, c]), 0x8) << 4) | (color - 1))
    return out


class CosimError(RuntimeError):
    pass


class Cosim:
    """One persistent verilated CoproDrMario, fed decisions over a pipe.

    The firmware is selected by CWD, because CoproDrMario.sv does
    `initial $readmemh("copro_rom.hex", rom)` -- resolved at RUNTIME relative to the
    process working directory. `fw_md5` records the hash of the file the process actually
    opened, so the arm is verified from content and never inferred from a directory name.
    """

    def __init__(self, binary: str, fw_dir: str):
        rom = os.path.join(fw_dir, "copro_rom.hex")
        if not os.path.exists(rom):
            raise CosimError(f"no copro_rom.hex in {fw_dir}")
        self.fw_md5 = hashlib.md5(open(rom, "rb").read()).hexdigest()
        self.fw_dir = fw_dir
        self.binary = binary
        self.n_decisions = 0
        self.total_clocks = 0
        self.proc = subprocess.Popen(
            [binary], cwd=fw_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )

    def decide(self, board128, cA, cB, nA, nB):
        """-> dict(col, o4, tcol, trow, clocks). tcol == 0xFF means 'no tuck'."""
        # The copro's OWN convention is 0-BASED colour ids 0..2 -- the faithful sim's 1..3
        # minus one. Asserted, not documented-and-hoped, because getting it wrong is
        # SILENT: lev_a_ca/cb are 2-bit, so 1..3 is accepted as valid-looking, every
        # colour shifts by one, and the only symptom is that the AI plays badly. That bug
        # cost this lane a full 2x2 run (results/INVALID_1based_colors/README.txt).
        # Authority: fpga/copro/gen_corpus.py draws rng.randint(0, 2); gen_m3_hostdata.py
        # documents "0-based ... matching sim_mister.cpp's cA/cB/nA/nB fields directly".
        for _n, _v in (("cA", cA), ("cB", cB), ("nA", nA), ("nB", nB)):
            if not 0 <= _v <= 2:
                raise CosimError(
                    f"{_n}={_v} out of range: the copro takes 0-BASED colours 0..2. "
                    f"The faithful sim's Pill colours are 1..3 -- subtract one.")
        if len(board128) != NCELL:
            raise CosimError(f"board has {len(board128)} cells, expected {NCELL}")
        if self.proc.poll() is not None:
            raise CosimError(f"co-sim server exited rc={self.proc.returncode}")
        line = "%d %d %d %d %s\n" % (
            cA, cB, nA, nB, " ".join("%02x" % b for b in board128))
        self.proc.stdin.write(line)
        self.proc.stdin.flush()
        reply = self.proc.stdout.readline()
        if not reply:
            raise CosimError("co-sim server closed stdout (crashed?)")
        parts = reply.split()
        if parts and parts[0] == "ERR":
            raise CosimError("co-sim: " + reply.strip())
        if len(parts) != 5:
            raise CosimError("co-sim bad reply: %r" % reply)
        col, o4, tcol, trow, clocks = (int(x) for x in parts)
        self.n_decisions += 1
        self.total_clocks += clocks
        return {"col": col, "o4": o4, "tcol": tcol, "trow": trow, "clocks": clocks}

    def close(self):
        try:
            if self.proc.poll() is None:
                self.proc.stdin.write("BYE\n")
                self.proc.stdin.flush()
                self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def read_hostdata(path):
    """Parse the project's hostdata.txt corpus format into decision inputs."""
    toks = open(path).read().split()
    i = 0
    n = int(toks[i]); i += 1
    cases = []
    for _ in range(n):
        cA, cB, nA, nB, ec, eo = (int(toks[i + k]) for k in range(6))
        i += 6
        board = [int(toks[i + k], 16) for k in range(NCELL)]
        i += NCELL
        cases.append({"cA": cA, "cB": cB, "nA": nA, "nB": nB,
                      "expect_col": ec, "expect_o4": eo, "board": board})
    return cases
