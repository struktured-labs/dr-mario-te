#!/usr/bin/env python3
"""DRBUSYESC gate: the trampoline frees a STALE BUSY latch instead of soft-bricking (task #41).

Per the house rule this REPRODUCES THE DEFECT: silicon 2026-08-02 -- a core reload interrupted
an in-flight driver invocation, so warm sticky PRG-RAM held NAV_MAGIC=$A5 AND BUSY=1; the
trampoline bailed on every hook forever (NAV_T frozen at $28 across captures, driver dead
through 4 boots and 2 builds). The cold-boot bootstrap can't fire (NAV_MAGIC is warm) and the
only code that clears BUSY is behind the guard itself.

Drives the REAL build_wrapper bytes in py65 against a stub main that counts entries:

  A  THE BRICK: warm ($A5) + BUSY=1 inherited -> without the flag, 600 calls and main NEVER
     runs; with DRBUSYESC main first runs on call 255 (the ~2 s escape) and every call after
  B  genuine re-entrancy: BUSY=1 for 3 calls -> zero entries, BUSY untouched; once the outer
     invocation clears it, the next call enters and the streak resets
  C  normal path: BUSY==1 *inside* main (guard armed), BUSY==0 after the wrapper returns
  D  cold boot (NAV_MAGIC != $A5): garbage BUSY=1 cleared by the bootstrap, main runs on call 1
  E  flag-off wrapper emission is deterministic and unchanged (the flag is real and opt-in)

    tests/test_busyesc.py            # asserts; exit 1 on failure
"""
import os
import sys
import importlib.util

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMITTER = os.path.join(REPO, "patch_cartridge_copro.py")
sys.path.insert(0, REPO)

SENT = 0x4FF2
STUB_MAIN = 0x9000          # LDA BUSY; STA $02F0; INC $02F1; RTS  (records guard state + counts)
_FLAGS = ("DRBUSYESC", "DRREENTRY", "DRNOFREEZE", "DRCOLDINIT", "DRP1NATIVE", "DRHUMAN")
_seq = [0]


def build(flags):
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "busyesc_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    return P, bytes(P.build_wrapper(STUB_MAIN))


def machine(P, wrap, warm=True, busy=1):
    m = MPU()
    m.memory[P.WRAP_CPU:P.WRAP_CPU + len(wrap)] = wrap
    m.memory[STUB_MAIN:STUB_MAIN + 10] = bytes([
        0xAD, P.BUSY & 0xFF, P.BUSY >> 8,        # LDA BUSY
        0x8D, 0xF0, 0x02,                        # STA $02F0  (BUSY as seen inside main)
        0xEE, 0xF1, 0x02,                        # INC $02F1  (entry count)
        0x60])                                   # RTS
    m.memory[P.NAV_MAGIC] = 0xA5 if warm else 0x00
    m.memory[P.BUSY] = busy
    return m


def call(m, P):
    m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
    m.sp = 0xFD
    m.pc = P.WRAP_CPU
    n = 0
    while m.pc != SENT and n < 5000:
        m.step()
        n += 1
    assert m.pc == SENT, "runaway pc=%04X" % m.pc


def main():
    base = {"DRNOFREEZE": "1"}
    P, wrap_on = build(dict(base, DRBUSYESC="1"))
    P0, wrap_off = build(dict(base))

    # A: THE BRICK. Warm + inherited BUSY=1.
    m = machine(P0, wrap_off, warm=True, busy=1)
    for _ in range(600):
        call(m, P0)
    assert m.memory[0x2F1] == 0, "flag-off control: a bricked latch should never enter main"
    m = machine(P, wrap_on, warm=True, busy=1)
    first = None
    for i in range(1, 401):
        call(m, P)
        if first is None and m.memory[0x2F1] > 0:
            first = i
    assert first == 255, "escape entered on call %r, expected 255 (~2 s of bails)" % first
    assert m.memory[0x2F1] == 400 - 254, \
        "after the escape every call should enter (got %d entries)" % m.memory[0x2F1]
    assert m.memory[P.BUSY] == 0 and m.memory[P.BUSYSKP] == 0, "latch/streak not clean after healing"

    # B: genuine re-entrancy -- BUSY held by a live outer invocation for 3 calls.
    m = machine(P, wrap_on, warm=True, busy=1)
    for _ in range(3):
        call(m, P)
    assert m.memory[0x2F1] == 0, "re-entrant call entered main -- guard broken"
    assert m.memory[P.BUSY] == 1, "guard cleared a LIVE latch"
    m.memory[P.BUSY] = 0                      # outer invocation's epilogue
    call(m, P)
    assert m.memory[0x2F1] == 1 and m.memory[P.BUSYSKP] == 0, "post-release entry must reset the streak"

    # C: normal path -- guard armed inside main, released after.
    m = machine(P, wrap_on, warm=True, busy=0)
    call(m, P)
    assert m.memory[0x2F0] == 1, "main did not observe BUSY=1 (guard not armed during the body)"
    assert m.memory[P.BUSY] == 0, "BUSY not released after the invocation"

    # D: cold boot -- bootstrap clears garbage BUSY, first call enters.
    m = machine(P, wrap_on, warm=False, busy=1)
    call(m, P)
    assert m.memory[0x2F1] == 1, "cold-boot bootstrap failed to clear garbage BUSY"

    # E: flag-off identity.
    _, off2 = build(dict(base))
    assert wrap_off == off2, "flag-off wrapper emission not deterministic"
    assert wrap_off != wrap_on, "DRBUSYESC=1 changed nothing -- the escape was not emitted"

    print("BUSYESC gate: A brick healed@255 OK, B live-latch respected OK, C arm/release OK, "
          "D cold bootstrap OK, E flag-off identity OK")


if __name__ == "__main__":
    main()
