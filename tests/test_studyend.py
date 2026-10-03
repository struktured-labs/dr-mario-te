#!/usr/bin/env python3
"""DRSTUDYEND -- keep both final boards on the 2P round-end screen (owner request 2026-10-03).

Measured mechanism (Mesen, c960dd49; see the DRSTUDYEND flag block in patch_cartridge_copro.py):
anyPlayerLoses calls emptyLowerFieldOnLose_2P ($96C0) from $954F (P1 lost) / $9579 (P2 lost),
which writes 64 x $FF over the loser's field rows 8-15 in RAM; the X-sign + red virus are
sprites drawn every end-screen frame by updateSprites_2p_endGame's whoFailed!=0 branch ($8890).
The fix retargets the two JSRs to the routine's own tail ($96CF: LDA #$0F / STA $80 / RTS) and
turns $8890 TAX into RTS. On the MATCH FINAL (3rd win) playerLoses_endScreen then waits 128 frames,
fills both fields with $FF, stamps GAME OVER into both and sets whoFailed=0 / whoWon=winner (Dr.
Mario dances over the winner's bottle); the fix rewrites the 2P-only block at $95BD (12 B) to
`LDA #$0B / STA $06F5 / LDA #$80 / JSR $9701 / BEQ $9607`: same music, same wait, then the START loop.

Builds the CURRENT couch candidate's flag set (experiments/cvx/sota_20260927_couch_flags.env +
the study/transport flags of sota_20260927_reproduce.sh + DRSPAWNEDGE=1) with the emitter alone
(no TE branding), then checks -- two-sided, testing the DEFECT and not only the fix:

  A. OFF IDENTITY: DRSTUDYEND unset == DRSTUDYEND=0, byte for byte.
  B. EXACT FOOTPRINT: ON differs from OFF in exactly 15 bytes, all in bank 0 (unit-0 low half,
     single copy): JSR $96C0 -> $96CF at the P1 and P2 call sites, TAX -> RTS at $8890, and the
     12-byte match-final block at $95BD.
  C. FIELD (py65, executing the real call sites): OFF wipes the loser's rows 8-15 to $FF (the
     defect reproduces), ON leaves all 128 cells intact; BOTH arms still set $80 = $0F (the
     status redraw the tail provides), for P1 ($58=$04) and P2 ($58=$05).
  D. SPRITES (py65, real updateSprites_2p_endGame): whoFailed=1 -> OFF writes the X-sign/virus
     into the OAM shadow page (defect), ON writes nothing. whoFailed=0 (every play frame) ->
     both arms write nothing and take the SAME cycle count (play timing unchanged).
  E. GUARD: DRSTUDYEND=1 with DRSTUDY=0 REFUSES (exit != 0, names DRSTUDYEND); DRSTUDYEND=1 on a
     DRHUMAN=1 cart that leaves DRSTUDY unset (STUDY defaults ON there) builds and emits -- with
     DRSTUDYCOUNTS=1 still set (its guard entry's false refusal is fixed; tests/test_gated_flags.py).
  F. MATCH FINAL (py65, the real playerLoses_endScreen from $958A; the NMI wait $B654 is stubbed to
     one call = one frame, START held): BOTH arms reach the START loop after the SAME 192 frame
     waits with the same music ($06F5=$0B). There, OFF has wiped both fields + stamped GAME OVER and
     set whoWon=winner/whoFailed=0 (the defect reproduces); ON has both boards byte-intact,
     whoWon=0, whoFailed=loser. After START both arms run the stock tail (fields all $FE, mode 1,
     $54=$FF, $F5=0) and the RAM differs ONLY in $55/$61 (+ $0300/$0380, which only the NMI drains
     and py65 does not run -- the Mesen run shows they converge); level init ($8206) then zeroes
     $55/$61 and rewrites $0300/$0380: $0000-$07FF is then identical (stack page excluded).
  G. 1P GAME OVER UNTOUCHED (py65): $0727=1 enters at $95C9 -> both arms produce the identical write
     trace and identical RAM, through START.
Run: python tests/test_studyend.py   (needs py65 and the untracked drmario_v28cs.nes)
"""
import os
import subprocess
import sys

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(REPO, "tmp", "studyend_test")
COUCH_ENV = os.path.join(REPO, "experiments", "cvx", "sota_20260927_couch_flags.env")
EXTRA = dict(DRSTUDY="1", DRSTUDY2P="1", DRSTUDY2P_INV="1", DRSTUDYCOUNTS="1", DRSTUDY_Y="0x98",
             DRNMITMP="1", DRREACHTX="1", DRTAPP="2", DRSPAWNEDGE="1")
JSR_P1, JSR_P2, RV = 0x954F, 0x9579, 0x8890        # measured sites (CPU, bank 0)
EMPTY, TAIL = 0x96C0, 0x96CF
FINAL_SITE = 0x95BD
FINAL_OLD = bytes.fromhex("ad2707c902d005a90b8df506")  # LDA $0727/CMP #2/BNE/LDA #$0B/STA $06F5
FINAL_NEW = bytes.fromhex("a90b8df506a980200197f03e")  # LDA #$0B/STA $06F5/LDA #$80/JSR $9701/BEQ $9607
END_SCREEN, START_LOOP, NMI_WAIT, LEVEL_INIT = 0x958A, 0x9607, 0xB654, 0x8206


def couch_flags(**over):
    flags = dict(kv.split("=", 1) for kv in open(COUCH_ENV).read().split())
    flags.update(EXTRA)
    for k, v in over.items():
        if v is None:
            flags.pop(k, None)
        else:
            flags[k] = str(v)
    return flags


def build(name, flags, expect_ok=True):
    os.makedirs(TMP, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DR")}
    env.update(flags)
    r = subprocess.run([sys.executable, "patch_cartridge_copro.py"], cwd=REPO, env=env,
                       capture_output=True, text=True)
    if not expect_ok:
        return None, r
    assert r.returncode == 0, f"emitter failed for {name}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}"
    path = os.path.join(TMP, f"{name}.nes")
    os.replace(os.path.join(REPO, "drmario_copro.nes"), path)
    return bytes(open(path, "rb").read()), r


def mpu_for(cart):
    """Unit 0 (the base game, 32 KB) mapped at $8000-$FFFF; RAM zeroed."""
    m = MPU()
    m.memory[0x8000:0x10000] = list(cart[0x10:0x10 + 0x8000])
    return m


def call(m, target, limit=200000):
    """Run from `target` until PC == stop (a JSR stub in RAM supplies the return)."""
    m.memory[0x0700:0x0703] = [0x20, target & 0xFF, target >> 8]   # JSR target
    m.pc = 0x0700
    c0 = m.processorCycles
    for _ in range(limit):
        if m.pc == 0x0703:
            return m.processorCycles - c0
        m.step()
    raise AssertionError(f"${target:04X} did not return within {limit} steps (pc=${m.pc:04X})")


def scen_A(off_unset, off0):
    assert off_unset == off0, "A FAIL: DRSTUDYEND unset != DRSTUDYEND=0"
    print("A PASS  OFF identity (unset == 0)")


def scen_B(off, on):
    d = [(i, off[i], on[i]) for i in range(len(off)) if off[i] != on[i]]
    want = {0x10 + JSR_P1 + 1 - 0x8000: (EMPTY & 0xFF, TAIL & 0xFF),
            0x10 + JSR_P2 + 1 - 0x8000: (EMPTY & 0xFF, TAIL & 0xFF),
            0x10 + RV - 0x8000: (0xAA, 0x60)}
    for k in range(12):
        if FINAL_OLD[k] != FINAL_NEW[k]:
            want[0x10 + FINAL_SITE + k - 0x8000] = (FINAL_OLD[k], FINAL_NEW[k])
    got = {i: (a, b) for i, a, b in d}
    assert len(off) == len(on) and got == want, f"B FAIL: diff {[(hex(i), hex(a), hex(b)) for i, a, b in d]}"
    assert all(0x10 <= i < 0x4010 for i in got), "B FAIL: a changed byte is outside bank 0"
    print(f"B PASS  exactly {len(got)} bytes, bank 0: " + ", ".join(f"0x{i:05X} {a:02X}->{b:02X}" for i, (a, b) in sorted(got.items())))


def scen_C(off, on):
    for site, page in ((JSR_P1, 0x04), (JSR_P2, 0x05)):
        for arm, cart in (("OFF", off), ("ON", on)):
            m = mpu_for(cart)
            board = [(0x40 + i) & 0xFF for i in range(128)]          # distinct, non-$FF cells
            m.memory[page << 8:(page << 8) + 128] = board
            m.memory[0x58] = page                                     # currentP field pointer hi
            m.memory[0x80] = 0x00
            # execute the REAL call site (one JSR) by running from it to the next instruction
            m.memory[0x0700:0x0703] = [0x4C, site & 0xFF, site >> 8]  # JMP site
            m.pc = 0x0700
            for _ in range(5000):
                if m.pc == site + 3:
                    break
                m.step()
            assert m.pc == site + 3, f"C: {arm} ${site:04X} did not return"
            after = list(m.memory[page << 8:(page << 8) + 128])
            assert m.memory[0x80] == 0x0F, f"C FAIL: {arm} ${site:04X} did not set the $80=$0F status redraw"
            if arm == "OFF":
                assert after[:64] == board[:64] and after[64:] == [0xFF] * 64, \
                    f"C FAIL: OFF ${site:04X} did not wipe rows 8-15 -- the defect no longer reproduces"
            else:
                assert after == board, f"C FAIL: ON ${site:04X} changed the field"
    print("C PASS  OFF wipes the loser's rows 8-15 (P1+P2 sites); ON keeps all 128 cells; $80=$0F both")


def scen_D(off, on):
    res = {}
    for arm, cart in (("OFF", off), ("ON", on)):
        for wf in (0, 1, 2):
            m = mpu_for(cart)
            m.memory[0x0200:0x0300] = [0xFF] * 256
            m.memory[0x55] = 0                                        # whoWon
            m.memory[0x61] = wf                                       # whoFailed
            m.memory[0x43] = 0x05                                     # frame counter
            cyc = call(m, 0x886C)
            res[(arm, wf)] = (sum(1 for b in m.memory[0x0200:0x0300] if b != 0xFF), cyc)
    for wf in (1, 2):
        assert res[("OFF", wf)][0] > 0, f"D FAIL: OFF whoFailed={wf} drew nothing -- the defect no longer reproduces"
        assert res[("ON", wf)][0] == 0, f"D FAIL: ON whoFailed={wf} still writes OAM"
    assert res[("OFF", 0)] == res[("ON", 0)] and res[("ON", 0)][0] == 0, \
        f"D FAIL: whoFailed=0 (play) differs: OFF {res[('OFF', 0)]} ON {res[('ON', 0)]}"
    print(f"D PASS  whoFailed=1/2: OFF writes {res[('OFF', 1)][0]}/{res[('OFF', 2)][0]} OAM bytes, ON 0; "
          f"whoFailed=0: both 0 bytes, {res[('ON', 0)][1]} cycles each")


def scen_E():
    _, r = build("refuse", couch_flags(DRSTUDY="0", DRSTUDYCOUNTS="0", DRSTUDYEND="1"), expect_ok=False)
    assert r.returncode != 0 and "##SUPPRESSED-FLAG## DRSTUDYEND" in r.stdout, \
        f"E FAIL: DRSTUDY=0 + DRSTUDYEND=1 was not refused (rc={r.returncode})"
    _, r2 = build("human_default_study", couch_flags(DRSTUDY=None, DRSTUDYEND="1"))
    assert "DRSTUDYEND: round-end lower-field wipe skipped" in r2.stdout, \
        "E FAIL: DRHUMAN=1 with DRSTUDY unset did not emit DRSTUDYEND"
    print("E PASS  DRSTUDY=0 refuses (names DRSTUDYEND); DRHUMAN=1 + DRSTUDY unset builds and emits")


class TraceMem(list):
    """py65 memory that logs every write as (addr, value)."""

    def __init__(self, data):
        super().__init__(data)
        self.log = []

    def __setitem__(self, a, v):
        if isinstance(a, int):
            self.log.append((a, v))
        list.__setitem__(self, a, v)


BOARD1 = [(0x40 + i) & 0xFF for i in range(128)]
BOARD2 = [(0x90 + 3 * i) & 0x7F for i in range(128)]


def end_screen(cart, players, p1_wins, p2_wins, who_failed, level_init=False, limit=3_000_000):
    """Run the real playerLoses_endScreen ($958A) with START held. NMI wait stubbed (1 call = 1 frame).
    Returns (frames before the START loop, RAM at the START loop, RAM at return, write trace)."""
    m = mpu_for(cart)
    m.memory[NMI_WAIT] = 0x60                                     # stub: no NMI in py65
    ram = m.memory
    ram[0x0400:0x0480] = BOARD1; ram[0x0480:0x0500] = [0xFF] * 128
    ram[0x0500:0x0580] = BOARD2; ram[0x0580:0x0600] = [0xFF] * 128
    ram[0x0727] = players; ram[0x0725] = 3; ram[0x031E] = p1_wins; ram[0x039E] = p2_wins
    ram[0x61] = who_failed; ram[0x55] = 0; ram[0x0731] = 0; ram[0x43] = 5; ram[0xF5] = 0x10
    ram[0x58] = 0x05; ram[0x80] = 0x0F; ram[0x0300] = 0xFF; ram[0x0380] = 0xFF   # as anyPlayerLoses leaves them
    m.memory = TraceMem(m.memory)
    m.memory[0x0700:0x0703] = [0x20, END_SCREEN & 0xFF, END_SCREEN >> 8]
    m.pc = 0x0700
    frames, at_loop = 0, None
    for _ in range(limit):
        if m.pc == NMI_WAIT:
            frames += 1
        if m.pc == START_LOOP and at_loop is None:
            at_loop = (frames, list(m.memory[0:0x800]))
        if m.pc == 0x0703:
            break
        m.step()
    assert m.pc == 0x0703, f"end screen did not return (pc=${m.pc:04X})"
    end = list(m.memory[0:0x800])
    init = None
    if level_init:
        m.memory[0x0700:0x0703] = [0x20, LEVEL_INIT & 0xFF, LEVEL_INIT >> 8]
        m.pc = 0x0700
        for _ in range(limit):
            if m.pc == 0x0703:
                break
            m.step()
        assert m.pc == 0x0703, f"level init did not return (pc=${m.pc:04X})"
        init = list(m.memory[0:0x800])
    return at_loop, end, init, list(m.memory.log)


def ramdiff(a, b):
    """Addresses that differ, ignoring the stack page (stale return addresses below SP are not state)."""
    return sorted(i for i in range(0x800) if a[i] != b[i] and not (0x100 <= i < 0x200))


def scen_F(off, on):
    o_loop, o_end, o_init, _ = end_screen(off, 2, 0, 3, 1, level_init=True)
    n_loop, n_end, n_init, _ = end_screen(on, 2, 0, 3, 1, level_init=True)
    assert o_loop and n_loop, "F: an arm never reached the START loop"
    assert o_loop[0] == n_loop[0] == 192, f"F FAIL: frames to the START loop OFF {o_loop[0]} ON {n_loop[0]} (stock 64+128)"
    o, n = o_loop[1], n_loop[1]
    assert o[0x06F5] == n[0x06F5] == 0x0B, "F FAIL: final-victory music differs"
    for page in (0x0400, 0x0500):                                 # stock: wiped + GAME OVER box rows 2-8
        f = o[page:page + 0x80]
        assert f[:16] == [0xFF] * 16 and f[72:] == [0xFF] * 56 and all(v != 0xFF for v in f[16:72]) \
            and f[34:38] == [0x10, 0x0A, 0x16, 0x0E], f"F FAIL: OFF ${page:04X} is not wipe+GAME OVER (defect gone?)"
    assert (o[0x55], o[0x61]) == (2, 0), f"F FAIL: OFF whoWon/whoFailed {o[0x55]}/{o[0x61]}"
    assert n[0x0400:0x0480] == BOARD1 and n[0x0500:0x0580] == BOARD2, "F FAIL: ON changed a final board"
    assert (n[0x55], n[0x61]) == (0, 1), f"F FAIL: ON whoWon/whoFailed {n[0x55]}/{n[0x61]}"
    for arm, r in (("OFF", o_end), ("ON", n_end)):
        assert r[0x0400:0x0600] == [0xFE] * 0x200 and r[0x46] == 1 and r[0x54] == 0xFF and r[0xF5] == 0, \
            f"F FAIL: {arm} post-START state is not the stock tail"
    d_end = ramdiff(o_end, n_end)
    assert d_end == [0x55, 0x61, 0x0300, 0x0380], f"F FAIL: post-START RAM diff {[hex(x) for x in d_end]}"
    d_init = ramdiff(o_init, n_init)
    assert d_init == [] and o_init[0x55] == n_init[0x55] == 0 and o_init[0x61] == n_init[0x61] == 0, \
        f"F FAIL: after level init RAM diff {[hex(x) for x in d_init]}"
    print("F PASS  match final: both reach START loop after 192 frames, music $0B; OFF wipes+GAME OVER, "
          "whoWon=2; ON boards intact, whoWon=0/whoFailed=1; post-START diff = $55,$61 (+NMI-drained "
          "$0300/$0380); after level init $0000-$07FF identical (stack page excluded)")


def scen_G(off, on):
    o_loop, o_end, _, o_log = end_screen(off, 1, 0, 0, 0)
    n_loop, n_end, _, n_log = end_screen(on, 1, 0, 0, 0)
    assert o_log == n_log and o_end == n_end and o_loop == n_loop, "G FAIL: 1P game over differs"
    assert o_loop[1][0x0400:0x0480] != BOARD1, "G: 1P stock path did not run the wipe (unexpected)"
    print(f"G PASS  1P game over: identical write trace ({len(o_log)} writes) and RAM through START")


def main():
    off_unset, _ = build("off_unset", couch_flags())
    off0, _ = build("off0", couch_flags(DRSTUDYEND="0"))
    on, _ = build("on", couch_flags(DRSTUDYEND="1"))
    scen_A(off_unset, off0)
    scen_B(off0, on)
    scen_C(off0, on)
    scen_D(off0, on)
    scen_E()
    scen_F(off0, on)
    scen_G(off0, on)
    print("ALL PASS test_studyend")


if __name__ == "__main__":
    main()
