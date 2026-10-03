#!/usr/bin/env python3
"""BRAIN-GAP instrument (2026-10-03): the SHIPPED copro firmware LOGIC under py65, with an RTL-FAITHFUL engine.

Why: the py65 firmware gates (gate_reach_search / gate_dist_golden / fwlib) run the firmware against
test_search_d3.attach_engine_emu, whose engine is the WEEKEND golden (nes_d3_golden.leaf_d3 + targeted cap-1
resolve, no links, no chain, no HSV) -- fine for testing search CONTROL, useless for VALUES. Here every engine
command is answered by the sim brain's own RTL-gated python node:
  CMD 4 NODE   land (fast_sim_x._resting) + place with link + link-aware resolve to fixpoint (cascade_chain_x
               _expand_chain, maxpass 0 = DRFIX 1) -> legal / rv_cells / rv_vir / imm = 180 v + 10 c +
               chw*4*(chain-1) (chain>1, chain capped 15, 16-bit) / sco = wrap16(_leafv_ship + _x5(HSV512) +
               _x6(DIST, from the $70F5 target the firmware wrote)) / win
  CMD 1 LEAF   the same leaf on CUR
  CMD 2/3      slot copies;  CMD 8  #47 stranded count (== cascade_stranded_x._g_stranded47)
  CMD 6/7      BASE / DELTA (only if a delta image is run): DELTA = the full node on a non-clearing child (CUR kept),
               dv_fallback = 1 on a clearing placement (the firmware then re-runs CMD 4)
So "py65 + this engine" isolates the FIRMWARE SEARCH STRUCTURE with sim-brain leaf/node arithmetic. Compared with
(a) the Verilator co-sim final (real RTL) and (b) the python sim brain it splits the brain gap into
"engine (RTL vs python node)" and "search structure (firmware vs Leaf6Decider)".

Image: build_copro_d3 at the fw 1488e158 recipe (CHAIN540 STRAND20 VETO DBLCANON tuck-BFS tier3 theta400 FIXSLOT
REACH REACHTAP DIST), from the te worktree TE (default dr-mario-braingap-wt @ 395973c5). delta=True reproduces the
shipped hex byte-for-byte (checked by selftest()); the default run uses the NON-delta build (CMD 4 everywhere), the
same choice fwlib makes.  DEBUG_VAL1=True images add the per-root ring dump (C1,O1,V1,B2 / I1,L1,AD) -- read back
here as per-root components.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys

import numpy as np

H16 = "/home/struktured/projects/dr-mario-h16-wt"
CVX = H16 + "/experiments/cvx"
TE = os.environ.get("TE", "/home/struktured/projects/dr-mario-braingap-wt")
os.environ.setdefault("NUMBA_CACHE_DIR", H16 + "/tmp/braingap/nbcache")
sys.path.insert(0, CVX)
import import_pin  # noqa: E402
import_pin.pin()
from fast_sim_x import NCELL, _resting, _virus_count  # noqa: E402
from fast_rtl_x import _leafv_ship  # noqa: E402
import fast_rtl_x as FX  # noqa: E402
from cascade_chain_x import _expand_chain  # noqa: E402
from cascade_leaf5b_x import _x5  # noqa: E402
from cascade_leaf6_x import _x6  # noqa: E402
from cascade_stranded_x import _g_stranded47  # noqa: E402

W_LEAF, FL_LEAF = FX.variant("winner")
W5 = np.array([0, 0, 0, 512], dtype=np.int64)
VAR_OF_O4 = (2, 3, 0, 1)
HI2LNK = {0x4: 2, 0x5: 1, 0x6: 4, 0x7: 3, 0x8: 0}          # NES high nibble -> cascade_link_x LINK_*
LNK2HI = {2: 0x4, 1: 0x5, 4: 0x6, 3: 0x7, 0: 0x8}

# ------------------------------------------------------------------------------------------------ te firmware
RECIPE = {"DRSTRAND": "20", "DRCHAIN": "540", "DRCOPRO_ARM": "1", "DRFIX": "1", "DRCOPRO_TUCKBFS": "1",
          "DRCOPRO_TUCKBFS_TIER3": "1", "DRCOPRO_TUCKV3_THETA": "400", "DRDBLCANON": "1",
          "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRVETO": "1", "DRREACH": "1", "DRREACHTAP": "1", "DRDIST": "1"}
os.environ.update(RECIPE)
COPRO = os.path.join(TE, "fpga", "copro")
for _m in ("test_search_d3", "tuck_v3", "build_copro_d3"):
    sys.modules.pop(_m, None)
sys.path.insert(0, COPRO)
import copro_bootstrap  # noqa: E402
copro_bootstrap.install(TE)


def _pin(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


D3 = _pin("test_search_d3", os.path.join(TE, "tests", "test_search_d3.py"))
TV = _pin("tuck_v3", os.path.join(COPRO, "tuck_v3.py"))
D3.DEBUG_VAL1 = False
B = _pin("build_copro_d3", os.path.join(COPRO, "build_copro_d3.py"))
import reach_6502 as RC  # noqa: E402
from test_depth2 import S_CA, S_CB, S_NA, S_NB, S_BEST_C, S_BEST_O  # noqa: E402
assert B.D3 is D3 and B.__file__.startswith(COPRO), B.__file__
SHIP_MD5 = "1488e1583ab7ad8b2011d4c136926faf"
LEV_TGT = 0x70F5
LEV_A_FIX, LEV_A_CHW = D3.LEV_A_FIX, D3.LEV_A_CHW


def image(delta=False, debug=False):
    os.environ.update(RECIPE)
    D3.USE_DELTA = bool(delta)
    D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None
    D3.DEBUG_VAL1 = bool(debug)
    img, _clen, _slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    D3.USE_DELTA = False
    D3.DEBUG_VAL1 = False
    return img


def hex_md5(img):
    img = bytearray(img)
    for i in range(128):
        img[0x0500 + i] = 0xFF
    return hashlib.md5(("\n".join("%02x" % x for x in img[0x8000:0xC000]) + "\n").encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ board codec
def dec(nes):
    a = np.asarray(nes, dtype=np.int64)
    col = np.zeros(NCELL, np.int8); vir = np.zeros(NCELL, np.int8); lnk = np.zeros(NCELL, np.int8)
    occ = (a != 0xFF) & (a != 0x00)
    col[occ] = (a[occ] & 0x0F) + 1
    hi = a >> 4
    vir[occ & (hi == 0xD)] = 1
    for h, l in HI2LNK.items():
        lnk[occ & (hi == h)] = l
    return col, vir, lnk


def enc(col, vir, lnk):
    out = [0xFF] * NCELL
    for i in range(NCELL):
        c = int(col[i])
        if c == 0:
            continue
        if vir[i]:
            out[i] = 0xD0 | (c - 1)
        else:
            out[i] = (LNK2HI.get(int(lnk[i]), 0x8) << 4) | (c - 1)
    return out


def wrap16(x):
    y = int(x) & 0xFFFF
    return y - 0x10000 if y >= 0x8000 else y


def w6_of(tgt):
    w6 = np.zeros(6, dtype=np.int64); w6[1] = 16; w6[2] = -1
    if tgt & 0x80:
        w6[0] = 60; w6[2] = tgt & 0x7F
    return w6


def leaf_of(col, vir, w6):
    if _virus_count(vir) == 0:
        return 0, 1
    lv = _leafv_ship(col, vir, W_LEAF, FL_LEAF) + _x5(col, vir, FL_LEAF, W5) + _x6(col, vir, w6)
    return wrap16(lv), 0


_SCR = [np.empty(NCELL, np.int8) for _ in range(4)]


def node(cur, o4, colm, ca, cb, maxpass, chw, w6):
    """-> (legal, cells, vir, imm, sco, win, child_nes, chain)"""
    pcol, pvir, plnk = dec(cur)
    var = VAR_OF_O4[o4 & 3]
    ccol, cvir, clnk, mask = _SCR
    ok, nv, cells, ch = _expand_chain(pcol, pvir, plnk, var, colm & 7, (ca & 3) + 1, (cb & 3) + 1,
                                      ccol, cvir, clnk, mask, maxpass)
    if ok == 0:
        return 0, 0, 0, 0, 0, 0, None, 0
    ch = min(int(ch), 15)
    imm = 180 * int(nv) + 10 * int(cells) + (chw * 4 * (ch - 1) if ch > 1 else 0)
    sco, win = leaf_of(ccol, cvir, w6)
    return 1, int(cells), int(nv), imm & 0xFFFF, sco, win, enc(ccol, cvir, clnk), ch


class Engine:
    def __init__(self, cpu, log=None):
        from py65.memory import ObservableMemory
        self.base = base = cpu.mem
        obs = ObservableMemory(subject=base)
        self.slots = [[0xFF] * 128 for _ in range(4)]
        self.st = dict(wslot=0, o4=0, col=0, ca=0, cb=0, sl=0, fix=0, chw=0, tgt=0)
        self.log = log
        self.ncmd = 0

        def wr_board(addr, value):
            self.slots[self.st["wslot"]][addr - D3.LEV_BOARD] = value & 0xFF

        def wr_wslot(addr, value):
            self.st["wslot"] = value & 3

        def wr_arg(addr, value):
            self.st[("o4", "col", "ca", "cb", "sl")[addr - D3.LEV_A_O4]] = value & 0xFF

        def wr_fix(addr, value):
            self.st["fix"] = value & 0xFF

        def wr_chw(addr, value):
            self.st["chw"] = value & 0xFF

        def wr_tgt(addr, value):
            self.st["tgt"] = value & 0xFF

        obs.subscribe_to_write(range(D3.LEV_BOARD, D3.LEV_BOARD + 128), wr_board)
        obs.subscribe_to_write([D3.LEV_WSLOT], wr_wslot)
        obs.subscribe_to_write(range(D3.LEV_A_O4, D3.LEV_A_SL + 1), wr_arg)
        obs.subscribe_to_write([LEV_A_FIX], wr_fix)
        obs.subscribe_to_write([LEV_A_CHW], wr_chw)
        obs.subscribe_to_write([LEV_TGT], wr_tgt)
        obs.subscribe_to_write([D3.LEV_CMD], self.cmd)
        cpu.mpu.memory = obs
        cpu.mem = obs
        self.base_board = None

    def post(self, legal, cells=0, vir=0, imm=0, sco=0, win=0, dvfb=0):
        b = self.base
        b[D3.LEV_LEGAL] = legal; b[D3.LEV_RVC] = cells & 0xFF; b[D3.LEV_RVV] = vir & 0xFF
        b[D3.LEV_IMM] = imm & 0xFF; b[D3.LEV_IMM + 1] = (imm >> 8) & 0xFF
        b[D3.LEV_SCO] = sco & 0xFF; b[D3.LEV_SCO + 1] = (sco >> 8) & 0xFF
        b[D3.LEV_WIN_R] = win; b[D3.LEV_DVFB] = dvfb; b[D3.LEV_GO] = 1

    def cmd(self, addr, value):
        c = value & 0x0F
        st = self.st
        self.ncmd += 1
        w6 = w6_of(st["tgt"])
        maxpass = 0 if st["fix"] else 1
        cur = self.slots[0]
        if c == 2:
            self.slots[0] = list(self.slots[st["sl"] & 3]); self.base[D3.LEV_GO] = 1
        elif c == 3:
            self.slots[st["sl"] & 3] = list(cur); self.base[D3.LEV_GO] = 1
        elif c == 1:
            col, vir, _l = dec(cur)
            sco, win = leaf_of(col, vir, w6)
            self.post(1, 0, 0, 0, sco, win)
        elif c == 4:
            legal, cells, nv, imm, sco, win, child, ch = node(cur, st["o4"], st["col"], st["ca"], st["cb"],
                                                              maxpass, st["chw"], w6)
            if not legal:
                self.post(0); return
            self.slots[0] = child
            self.post(1, cells, nv, imm, sco, win)
            if self.log is not None:
                self.log.append(("N", st["o4"] & 3, st["col"] & 7, st["ca"] & 3, st["cb"] & 3, cells, nv, imm,
                                 sco, win, ch))
        elif c == 6:
            self.base_board = list(cur); self.base[D3.LEV_GO] = 1
        elif c == 7:
            legal, cells, nv, imm, sco, win, child, ch = node(cur, st["o4"], st["col"], st["ca"], st["cb"],
                                                              maxpass, st["chw"], w6)
            if not legal:
                self.post(0); return
            if cells:
                self.post(1, cells, nv, imm, sco, win, dvfb=1)       # clearing -> firmware re-runs CMD 4
            else:
                self.post(1, 0, 0, 0, sco, win, dvfb=0)              # CUR stays = parent
        elif c == 8:
            col, vir, _l = dec(cur)
            self.base[D3.LEV_STRAND_R] = int(_g_stranded47(col, vir)); self.base[D3.LEV_GO] = 1
        else:
            raise RuntimeError(f"unhandled engine CMD {c}")


def _s16(lo, hi):
    v = (hi << 8) | lo
    return v - 0x10000 if v & 0x8000 else v


def run(img, board, cA, cB, nA, nB, debug=False, max_steps=3_000_000_000, nodelog=False):
    """One whole decision from the reset stub ($BF80): search -> tuck extension -> DONE.
    Returns final (col, o4), tuck descriptor, live-publish trajectory, and (debug image) per-root components."""
    from py65.memory import ObservableMemory
    from py65_harness import Cpu
    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    cpu.set_board(board)
    log = [] if nodelog else None
    eng = Engine(cpu, log)
    base = cpu.mem
    st = {"pubs": [], "roots": [], "n": 0, "strand": {}, "veto": {}}
    obs = ObservableMemory(subject=cpu.mem)          # chain ON TOP of the engine's observer

    def on_pub(addr, value):
        st["pubs"].append((st["n"], "c" if addr == S_BEST_C else "o", value & 0xFF))

    obs.subscribe_to_write([S_BEST_C, S_BEST_O], on_pub)
    if debug:
        R1, R2 = D3.DBG_RING, D3.DBG_RING2
        b0 = eng.base

        def on_ring(addr, value):           # the LAST write of a root's 12-byte dump is ring2+5 (called pre-write)
            x = addr - (R2 + 5)
            r = dict(c=b0[R1 + x], o=b0[R1 + x + 1], v1=_s16(b0[R1 + x + 2], b0[R1 + x + 3]),
                     b2=_s16(b0[R1 + x + 4], b0[R1 + x + 5]), i1=_s16(b0[R2 + x], b0[R2 + x + 1]),
                     l1=_s16(b0[R2 + x + 2], b0[R2 + x + 3]), ad=_s16(b0[R2 + x + 4], value & 0xFF),
                     strand=b0[D3.D_STR], veto=b0[D3.D_VETO], j1=x // 8)
            st["roots"].append(r)
        obs.subscribe_to_write([R2 + 5 + 8 * j for j in range(32)], on_ring)
    cpu.mpu.memory = obs
    cpu.mem = obs
    cpu.mem[S_CA], cpu.mem[S_CB], cpu.mem[S_NA], cpu.mem[S_NB] = cA, cB, nA, nB
    cpu.mem[B.DONE] = 0
    m = cpu.mpu
    m.pc = B.STUB
    m.sp = 0xFF
    n = 0
    eb = eng.base
    while n < max_steps:
        m.step()
        n += 1
        st["n"] = n
        if eb[B.DONE] == 1:
            break
    else:
        raise RuntimeError("no DONE")
    return dict(final=(eb[S_BEST_C], eb[S_BEST_O]), tuck=(eb[TV.TUCK_COL], eb[TV.TUCK_ROW]), pubs=st["pubs"],
                roots=st["roots"], steps=n, cycles=m.processorCycles, ncmd=eng.ncmd,
                rflt=eb[RC.R_FLT], rok=[eb[RC.ROK + i] for i in range(32)], tgt=eng.st["tgt"], nodes=log)


def parse_upload(line):
    t = line.split()
    cA, cB, nA, nB = (int(x) for x in t[:4])
    nes = [int(x, 16) for x in t[4:]]
    assert len(nes) == 128
    return nes, cA, cB, nA, nB


def selftest():
    img = image(delta=True)
    md5 = hex_md5(img)
    print("delta image md5", md5, "== shipped 1488e158" if md5 == SHIP_MD5 else "!= SHIPPED")
    return md5 == SHIP_MD5


if __name__ == "__main__":
    sys.exit(0 if selftest() else 1)
