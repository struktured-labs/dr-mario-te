"""Shared py65 harness for the DRTUCKREACH / DRROOTORD firmware gates.

Builds the ANTIBODY_DIST firmware LOGIC (the fw 1488e158 recipe: CHAIN540 + DRSTRAND 20 + DRVETO + DBLCANON + tuck
BFS tier-3 theta 400 FIXSLOT + DRREACH + DRREACHTAP + DRDIST) under py65 and runs the WHOLE decision the way the
copro does: reset vector stub $BF80 -> search -> tuck extension -> S_BEST_C/O + DONE. The engine is the py65 BoardEngine
emulator (test_search_d3.attach_engine_emu: CMD 1/2/3/4/8, golden leaf), so the image is the NON-delta build
(USE_DELTA False); the shipped hex is the delta build of the same emitter and is checked bit-for-bit on the Verilator
co-sim instead (cosim_run.py).

Instrumented observables per decision:
  final      (S_BEST_C, S_BEST_O) at DONE and the tuck descriptor (TUCK_COL, TUCK_ROW)
  pubs       every store to S_BEST_C / S_BEST_O (the live mailbox trajectory), in order, with the 6502 step index
  tuck       entry (TK2_BKIND <- 0), every commit (TK2_BKIND <- 1) with the committed (D_BC, D_BO, app, trig, BV)
  reach      R_FLT and ROK[32] as RAM holds them at the tuck-extension entry (gate: must equal the reach routine's)
"""
import hashlib
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COPRO = os.path.join(ROOT, "fpga", "copro")

RECIPE = {"DRSTRAND": "20", "DRCHAIN": "540", "DRCOPRO_ARM": "1", "DRFIX": "1", "DRCOPRO_TUCKBFS": "1",
          "DRCOPRO_TUCKBFS_TIER3": "1", "DRCOPRO_TUCKV3_THETA": "400", "DRDBLCANON": "1",
          "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRVETO": "1", "DRREACH": "1", "DRREACHTAP": "1", "DRDIST": "1",
          "DRTUCKREACH": "0", "DRROOTORD": "0", "DRTUCKLIVE": "0"}
os.environ.update(RECIPE)
for _m in ("test_search_d3", "tuck_v3", "build_copro_d3"):
    sys.modules.pop(_m, None)
sys.path.insert(0, COPRO)
import copro_bootstrap  # noqa: E402
copro_bootstrap.install(ROOT)


def _pin(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


D3 = _pin("test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
TV = _pin("tuck_v3", os.path.join(COPRO, "tuck_v3.py"))
D3.DEBUG_VAL1 = False
B = _pin("build_copro_d3", os.path.join(COPRO, "build_copro_d3.py"))
import reach_6502 as RC  # noqa: E402
from test_depth2 import S_CA, S_CB, S_NA, S_NB, S_BEST_C, S_BEST_O  # noqa: E402
assert B.D3 is D3 and B.__file__.startswith(COPRO), B.__file__

TUCK_COL, TUCK_ROW = TV.TUCK_COL, TV.TUCK_ROW
DONE = B.DONE
TAPP = 2                         # the couch / CvC carts' DRTAPP=2


def image(tuckreach=0, rootord=0, delta=False, **extra):
    """64K py65 image (or, delta=True, the shipped-style delta build) for this flag set. Env is re-read by
    build_image on every call (D3 flags) and TV.TUCKREACH is set there too, so one process can build every arm."""
    env = dict(RECIPE, DRTUCKREACH=str(tuckreach), DRROOTORD=str(rootord), **{k: str(v) for k, v in extra.items()})
    os.environ.update(env)
    D3.USE_DELTA = bool(delta)
    D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None
    img, clen, slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    D3.USE_DELTA = False
    return img


def hex_text(img):
    img = bytearray(img)
    for i in range(128):
        img[0x0500 + i] = 0xFF
    return "\n".join("%02x" % x for x in img[0x8000:0xC000]) + "\n"


def hex_md5(img):
    return hashlib.md5(hex_text(img).encode()).hexdigest()


def transport(cA, cB, nA, nB, speed, speedups, tap=TAPP, seed=0):
    """The couch cart's GO bytes: 0-based colours + DRSEED tie-break nibbles in cA/cB high nibbles, DRREACHTX gravity
    nibbles in nA/nB high nibbles, DRTAPP P in nA/nB low-nibble bits 2-3 (pubtrace_g2.upload's layout)."""
    hiA, hiB = RC.pack_nibbles(speed, speedups)
    return (cA | ((seed & 0x0F) << 4), cB | (seed & 0xF0),
            nA | ((tap & 3) << 2) | hiA, nB | (((tap >> 2) & 3) << 2) | hiB)


def thr_of(speed, speedups):
    return RC.SPEED_TABLE[min(80, RC.SPEED_BASE[speed] + speedups)]


def run(img, board, cA, cB, nA, nB, max_steps=3_000_000_000, ramscan=False):
    """One whole decision from the reset stub. cA..nB are the raw bytes the cart writes (see transport())."""
    from py65.memory import ObservableMemory
    from py65_harness import Cpu
    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    base = cpu.mem
    obs = ObservableMemory(subject=base)
    m = cpu.mpu
    st = {"pubs": [], "commits": [], "entry": None, "ram": set() if ramscan else None}

    def on_pub(addr, value):
        base[addr] = value
        st["pubs"].append((st["n"], "c" if addr == S_BEST_C else "o", value & 0xFF))

    def on_bkind(addr, value):
        base[addr] = value
        if value == 0:
            n = base[TV.TS_CNT]
            st["entry"] = dict(rflt=base[RC.R_FLT], rok=[base[RC.ROK + i] for i in range(32)],
                               bv=_s16(base[D3.D_BVL], base[D3.D_BVH]), bc=base[D3.D_BC], bo=base[D3.D_BO],
                               n=st["n"], npub=len(st["pubs"]),
                               cand=[[base[TV.CANDLIST + 5 * i + k] for k in range(5)] for i in range(n)],
                               cur_eq_live=all(base[0x0700 + i] == base[0x0500 + i] for i in range(128)),
                               cur=hashlib.md5(bytes(base[0x0700 + i] for i in range(128))).hexdigest()[:12])
        elif value == 1:
            st["commits"].append(dict(c=base[D3.D_BC], o=base[D3.D_BO], app=base[TV.TK2_APP], trig=base[TV.TK2_TRIG],
                                      v=_s16(base[D3.D_BVL], base[D3.D_BVH]), idx=base[TV.TP_IDX], n=st["n"]))

    obs.subscribe_to_write([S_BEST_C, S_BEST_O], on_pub)
    obs.subscribe_to_write([TV.TK2_BKIND], on_bkind)
    if ramscan:
        def on_any(addr, value):
            base[addr] = value
            st["ram"].add(addr)
        obs.subscribe_to_write([a for a in range(0x0000, 0x1000) if a not in (S_BEST_C, S_BEST_O, TV.TK2_BKIND)],
                               on_any)
    cpu.mpu.memory = obs
    cpu.mem = obs
    cpu.mem[S_CA], cpu.mem[S_CB], cpu.mem[S_NA], cpu.mem[S_NB] = cA, cB, nA, nB
    cpu.mem[DONE] = 0
    m.pc = B.STUB
    m.sp = 0xFF
    n = 0
    st["n"] = 0
    while n < max_steps:
        m.step()
        n += 1
        st["n"] = n
        if base[DONE] == 1:
            break
    else:
        raise RuntimeError("no DONE")
    return dict(final=(base[S_BEST_C], base[S_BEST_O]), tuck=(base[TUCK_COL], base[TUCK_ROW]), pubs=st["pubs"],
                commits=st["commits"], entry=st["entry"], steps=n, cycles=m.processorCycles, ram=st["ram"])


def _s16(lo, hi):
    v = (hi << 8) | lo
    return v - 0x10000 if v & 0x8000 else v


def color_grid(nes):
    return [[0 if nes[r * 8 + c] in (0xFF, 0x00) else 1 for c in range(8)] for r in range(16)]


def mask_o4(nes, thr, tap=TAPP):
    """reach_fw (the python spec) re-indexed to copro o4 space: m[o4*8+col], var = o4 ^ 2."""
    sys.path.insert(0, os.path.join(ROOT, "experiments", "reach"))
    import reach_fw as RF
    m = RF.reach_mask_fw(color_grid(nes), thr, tap or None)
    return [m[((i >> 3) ^ 2) * 8 + (i & 7)] for i in range(32)]


def load_corpus(n=None, step=None):
    import json
    rows = []
    for f in ("game_l11.jsonl", "game_l15.jsonl"):
        rows += [json.loads(l) for l in open(os.path.join(ROOT, "experiments", "reach", "corpus", f))]
    if step:
        rows = rows[::step]
    return rows[:n] if n else rows
