#!/usr/bin/env python
"""Phase-2 silicon fingerprint tool for the theta400 tuck cart on MiSTer.

Subcommands:
  decode <ss...>            -- full driver/game readout per save-state
  patch  <template> <out>   -- inject board+pill+search-reset (rig recipe + tuck invalidation)
  diff   <ss> <boardhex>    -- board $0500 diff vs an injected 128-byte hex board

Layout (dr-mario-savestate-layout + phase-1 decode_liveness.py):
  IRAM $0000 at ss+0x102B08, cart WRAM $6000 at ss+0x103308; bases re-verified by
  NAV_MAGIC $A5 at wram+0x149 signature per file.
"""
import sys

SS_SIZE = 1327112
IRAM_HINT = 0x102B08
WRAM_HINT = 0x103308

# driver bytes, offsets relative to $6000
ARMED2   = 0x161
WDOG2    = 0x162
WDOGH2   = 0x166
PEND2    = 0x14F
DELAY2   = 0x15F
ROT_DONE2= 0x16E
STABLE2  = 0x171
SLAM_ARM = 0x172
LASTY2   = 0x155
TGT_C2   = 0x152
TGT_O2   = 0x153
TUCK_C2  = 0x179
TUCK_R2  = 0x17A
BUSY     = 0x176
BUSYSKP  = 0x192
MATCH_A  = 0x164
NAV_T    = 0x147
NAV_MAGIC= 0x149

O4_TO_GAME = {0:3, 1:1, 2:0, 3:2}


def find_bases(b):
    cands = [off for off in range(0x100000, min(len(b), 0x110000)) if b[off + NAV_MAGIC] == 0xA5]
    wram = WRAM_HINT if WRAM_HINT in cands else (cands[0] if cands else None)
    return (wram - 0x800 if wram is not None else None), wram, len(cands)


def bcd(x):
    return (x >> 4) * 10 + (x & 0x0F)


def load(path):
    b = bytearray(open(path, 'rb').read())
    if len(b) != SS_SIZE:
        print(f"WARN {path}: size {len(b)} != {SS_SIZE}")
    iram, wram, n = find_bases(b)
    if wram is None:
        raise SystemExit(f"{path}: NAV_MAGIC signature not found")
    return b, iram, wram, n


def board_str(b, base):
    return "".join("%02x" % v for v in b[base + 0x500: base + 0x580])


def decode(path):
    b, iram, wram, n = load(path)
    W = lambda o: b[wram + o]
    I = lambda o: b[iram + o]
    occ = sum(1 for v in b[iram+0x500:iram+0x580] if v != 0xFF)
    vir = sum(1 for v in b[iram+0x500:iram+0x580] if v in (0xD0, 0xD1, 0xD2))
    print(f"== {path} (wram={wram:#x} cands={n})")
    print(f"  mode$46=${I(0x46):02X} MATCH_ACTIVE={W(MATCH_A)} NAV_T=${W(NAV_T):02X} "
          f"BUSY=${W(BUSY):02X} BUSYSKP=${W(BUSYSKP):02X}")
    print(f"  P2 pill: cur=({I(0x381)},{I(0x382)}) next=({I(0x39A)},{I(0x39B)}) "
          f"x={I(0x385)} y$0386={I(0x386)} orient$03A5={I(0x3A5)} virus_ctr={bcd(I(0x3A4))}")
    print(f"  driver: ARMED2={W(ARMED2)} WDOG2={W(WDOG2)} WDOGH2={W(WDOGH2)} PEND2={W(PEND2)} "
          f"DELAY2={W(DELAY2)} ROT_DONE2={W(ROT_DONE2)} STABLE={W(STABLE2)} SLAM={W(SLAM_ARM)} "
          f"LASTY2={W(LASTY2)}")
    print(f"  committed: TGT_C2={W(TGT_C2)} TGT_O2={W(TGT_O2)} TUCK_C2={W(TUCK_C2)} TUCK_R2={W(TUCK_R2)}")
    print(f"  P2 board: occ={occ} viruses={vir}")
    print(f"  boardhex: {board_str(b, iram)}")


def patch(template, out, boardhex, cA, cB, nA, nB):
    b, iram, wram, n = load(template)
    if boardhex != "keep":
        board = bytes.fromhex(boardhex)
        assert len(board) == 128
        b[iram+0x500:iram+0x580] = board
    if cA >= 0:
        b[iram+0x381] = cA; b[iram+0x382] = cB
        b[iram+0x39A] = nA; b[iram+0x39B] = nB
    # rig reset recipe (fresh P2 search) + tuck-latch invalidation
    for off, v in ((ARMED2,0),(WDOG2,0),(WDOGH2,0),(PEND2,1),(DELAY2,0),
                   (ROT_DONE2,0),(STABLE2,0),(SLAM_ARM,0),
                   (LASTY2, b[iram+0x386]), (TUCK_C2,0xFF), (TUCK_R2,0xFF)):
        b[wram + off] = v
    open(out, 'wb').write(bytes(b))
    print(f"patched {out}: board={'kept' if boardhex=='keep' else 'injected'} "
          f"pill=({b[iram+0x381]},{b[iram+0x382]}) next=({b[iram+0x39A]},{b[iram+0x39B]}) "
          f"LASTY2={b[wram+LASTY2]}")


def diff(path, boardhex):
    b, iram, wram, n = load(path)
    inj = bytes.fromhex(boardhex)
    cur = bytes(b[iram+0x500:iram+0x580])
    added, removed, changed = [], [], []
    for i in range(128):
        r, c = i // 8, i % 8
        if inj[i] == cur[i]:
            continue
        if inj[i] == 0xFF:
            added.append((r, c, cur[i]))
        elif cur[i] == 0xFF:
            removed.append((r, c, inj[i]))
        else:
            changed.append((r, c, inj[i], cur[i]))
    W = lambda o: b[wram + o]
    print(f"== diff {path} vs injected")
    print(f"  added   ({len(added)}): " + " ".join(f"({r},{c})={v:02x}" for r, c, v in added))
    print(f"  removed ({len(removed)}): " + " ".join(f"({r},{c})={v:02x}" for r, c, v in removed))
    print(f"  changed ({len(changed)}): " + " ".join(f"({r},{c})={a:02x}->{b_:02x}" for r, c, a, b_ in changed))
    print(f"  committed: TGT_C2={W(TGT_C2)} TGT_O2={W(TGT_O2)} TUCK_C2={W(TUCK_C2)} TUCK_R2={W(TUCK_R2)} "
          f"ARMED2={W(ARMED2)} WDOG2={W(WDOG2)}")
    vir = sum(1 for v in cur if v in (0xD0, 0xD1, 0xD2))
    inv = sum(1 for v in inj if v in (0xD0, 0xD1, 0xD2))
    print(f"  viruses: injected={inv} now={vir} ctr={bcd(b[iram+0x3A4])}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "decode":
        for p in sys.argv[2:]:
            decode(p)
    elif cmd == "patch":
        t, o, bh = sys.argv[2], sys.argv[3], sys.argv[4]
        if len(sys.argv) > 5:
            cA, cB, nA, nB = (int(x) for x in sys.argv[5:9])
        else:
            cA = -1; cB = nA = nB = 0
        patch(t, o, bh, cA, cB, nA, nB)
    elif cmd == "diff":
        diff(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit("usage: fp_tool.py decode|patch|diff ...")
