"""gate_d.py — killed-mutant suite for the stratum D reader (A3.2).

Runs against a hand-built VALID row plus one deliberately wrong variant per
gate; every mutant MUST void with the right class.  Run (and pass) before any
stratum D state is labeled.  Exit 0 = all mutants killed + the valid row
builds an env.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import garbcore as G

# a small legal board: two viruses on the floor + one settled horizontal pair
VALID = {
    "game": 1, "decision_idx": 0, "ts_video": 0.0,
    "nes": [0xFF] * 128, "hud_virus": 2,
    "cur": [0, 1], "nxt": [2, 2], "played": {"col": 3, "o4": 0},
}
VALID["nes"][15 * 8 + 0] = 0xD0        # virus, floor col 0
VALID["nes"][15 * 8 + 7] = 0xD2        # virus, floor col 7
VALID["nes"][15 * 8 + 3] = 0x61        # left half
VALID["nes"][15 * 8 + 4] = 0x72        # right half

ok = True


def check(name, got, want):
    global ok
    good = got == want
    print(f"[gate_d] {name}: {'PASS' if good else 'FAIL'} "
          f"(class={got} want={want})", flush=True)
    ok &= good


def void_class(rec):
    try:
        st = G.read_d_row(rec)
        G.build_env(*G.decode_planes(st["nes"]), st["cur"], st["nxt"], 99)
        return None
    except G.ImportVoid as ex:
        return ex.cls


check("valid_row", void_class(VALID), None)

m = copy.deepcopy(VALID); m["nes"][10] = 0xFE
check("m_unreadable", void_class(m), "unreadable")
m = copy.deepcopy(VALID); m["hud_virus"] = 3
check("m_counter", void_class(m), "counter")
m = copy.deepcopy(VALID); m["nes"][13 * 8 + 1] = 0x80  # floating tile (14,1)/(15,1) empty below
check("m_settle", void_class(m), "settle")
m = copy.deepcopy(VALID); m["nes"][15 * 8 + 4] = 0x82  # orphan the left half
check("m_links", void_class(m), "links")
m = copy.deepcopy(VALID); m["cur"] = [9, 0]
check("m_pills", void_class(m), "pills")
m = copy.deepcopy(VALID); del m["played"]
check("m_played", void_class(m), "played")
m = copy.deepcopy(VALID); m["nes"][12] = 0xF0          # mid-clear tile
check("m_tile", void_class(m), "tile")

print("GATE_D", "PASS" if ok else "FAIL", flush=True)
sys.exit(0 if ok else 1)
