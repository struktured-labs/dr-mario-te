#!/usr/bin/env python3
"""Build a FULL depth-2 (atomic, sim-exact) copro firmware to replace the incremental
machine (a 9/12 approximation whose suboptimal picks likely gate the endgame full-clear
chains). Same eval (spawn term included via emit_combine), same handshake:
  host -> board@$0500 (LIVE), colors@$6124-27; GO=reset pulse; stub JSRs search
  (copies LIVE->CUR, searches, writes $6134/5), sets DONE($61FF)=1; host polls DONE.
Emits copro_rom.hex (the $8000-$BFFF 16KB ROM slice) and VALIDATES it in py65 by driving
the reset->search->DONE handshake and comparing the move to decide_d2_4 (the full-d2 golden)."""
import sys, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, ROOT)
import build_firmware as BF
from py65_harness import Cpu
import test_depth2 as D2
from test_depth2 import S_CA, S_CB, S_NA, S_NB, S_BEST_C, S_BEST_O, decide_d2_4, _rand_board

EMPTY = 0xFF
STUB = 0xC000
DONE = 0x61FF


def main():
    # CRITICAL: the MiSTer copro's reset vector is hardcoded (by mapper logic) to $BF80,
    # INSIDE the 16KB ROM window. build_firmware defaults the stub to $C000 (OUTSIDE the
    # $8000-$BFFF slice we ship) -> copro resets into garbage -> hangs. Relocate to $BF80,
    # matching the working incremental build (build_firmware_incr).
    BF.STUB = 0xBF80
    # ROM image with EMPTY board (host supplies it at runtime, like the mapper)
    img, clen, slen = BF.build_image([EMPTY]*128, 0, 0, 0, 0)
    for i in range(128):
        img[0x0500 + i] = EMPTY
    rom = img[0x8000:0xC000]                      # 16KB copro ROM window
    with open(os.path.join(HERE, "copro_rom.hex"), "w") as f:
        f.write("\n".join("%02x" % x for x in rom) + "\n")
    print(f"copro_rom.hex written: full-d2 search={clen}B stub={slen}B, rom={len(rom)}B (fits 16384)")

    # ---- validate the search picks vs decide_d2_4 (the full-d2 golden) ----
    # The stub spins (never RTSes — it waits for the next reset pulse), so call the search
    # entry directly (it RTSes). search reads board@LIVE($0500), writes move@$6134/5.
    _code, labels = D2.build_search(resolve="full")
    search_ep = 0x8000 + labels["search"]
    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    rng = random.Random(2026); fails = 0; N = 4
    for t in range(N):
        b = _rand_board(rng); cA, cB, nA, nB = (rng.randint(0, 2) for _ in range(4))
        cpu.set_board(b)                          # host uploads board -> $0500 (LIVE)
        cpu.mem[S_CA] = cA; cpu.mem[S_CB] = cB; cpu.mem[S_NA] = nA; cpu.mem[S_NB] = nB
        cpu.call(search_ep, max_steps=80_000_000)  # search RTSes (full-d2 is ~15M+ steps)
        got = (cpu.mem[S_BEST_C], cpu.mem[S_BEST_O])
        exp = decide_d2_4(b, cA, cB, nA, nB)
        if got != exp:
            fails += 1
            if fails <= 5:
                print(f"  MISMATCH t={t}: got={got} exp={exp}")
    print(f"search validation: {N-fails}/{N} match decide_d2_4  ({'PASS' if not fails else 'FAIL'})")

    # ---- validate the HARDWARE path: copro resets to $BF80 -> stub -> search -> DONE=1 ----
    # (this is what actually failed before: the stub was at $C000, outside the ROM)
    cpu2 = Cpu()
    for a, v in enumerate(img):
        cpu2.mem[a] = v
    m = cpu2.mpu
    rng2 = random.Random(99); sfails = 0; SN = 3
    for t in range(SN):
        b = _rand_board(rng2); cA, cB, nA, nB = (rng2.randint(0, 2) for _ in range(4))
        cpu2.set_board(b)
        cpu2.mem[S_CA] = cA; cpu2.mem[S_CB] = cB; cpu2.mem[S_NA] = nA; cpu2.mem[S_NB] = nB
        cpu2.mem[DONE] = 0
        m.pc = 0xBF80; m.sp = 0xFF          # simulate the copro reset (mapper -> $BF80)
        steps = 0; ok = False
        while steps < 80_000_000:
            m.step(); steps += 1
            if cpu2.mem[DONE] == 1:
                ok = True; break
        got = (cpu2.mem[S_BEST_C], cpu2.mem[S_BEST_O])
        exp = decide_d2_4(b, cA, cB, nA, nB)
        if not ok or got != exp:
            sfails += 1
            print(f"  STUB-FLOW FAIL t={t}: reachedDONE={ok} got={got} exp={exp} steps={steps}")
        else:
            print(f"  stub-flow t={t}: DONE set, move={got} correct, {steps} steps")
    print(f"stub-flow ($BF80 reset -> DONE): {SN-sfails}/{SN}  ({'PASS' if not sfails else 'FAIL'})")
    sys.exit(1 if (fails or sfails) else 0)


if __name__ == "__main__":
    main()
