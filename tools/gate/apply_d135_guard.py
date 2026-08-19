#!/usr/bin/env python3
"""apply_d135_guard.py -- #135 adoption of the #131 START-leak fix across the probe family.

THE DEFECT (harness-side, dispatch-131).  The probes drive menus by pressing START on a frame
cadence, gated on `modeCache` -- a value sampled ONCE PER FRAME in the endFrame callback.  The
input poll runs in NMI at the TOP of a frame, so during a frame modeCache still holds the
PREVIOUS frame's mode.  Mode 8 (intro) is the only predecessor of mode 4 (play), and the ROM
advances 8->4 later in the same frame -- so a press permitted at mode 8 is still sitting in the
P1 newly-pressed latch $F5 when the stock pause routine $978E runs, already in mode 4.  $97A7
accepts it and the match pauses at spawn; on a P1-native cart that pause is UNEXITABLE (#133),
so the run wedges forever.

THE RULE: a mode-gated input arm must exclude the PREDECESSOR mode, read LIVE.

THREE SHAPES, because the probes do not all mean the same thing by a mode-4 press:

  U  (uniform)   block when live mode is 8, or when live mode is 4 AND the press carries START.
                 For every probe whose only in-play input would be an accidental START.
  E  (entry-only) block when live mode is 8 ONLY.  For probes that press START during mode 4 ON
                 PURPOSE -- fieldplay_hold dismisses a stage-clear hold, stomp_pc pauses into the
                 STUDY screen.  Blocking their mode-4 START would make each instrument VACUOUS,
                 which is the failure mode dr-mario-tuck-mailbox-vacuous-gate names.  Mode 8 is
                 where the LEAK lives, so shape E closes #131 without disarming the probe.
  U  also covers p1live, whose deliberate in-play input is left/right (P1DRIVE) and never START:
                 the `i.start` term preserves the walk while still killing the pause.

NOT TOUCHED, deliberately (see the report): probe_soak_fixed and probe_rotpause carry #131's own
experimental arms -- their guards are the variables under test, and "fixing" them would destroy
the killed-mutant pairs that produced the finding.
"""
import re
import sys
import pathlib

GATE = pathlib.Path(__file__).resolve().parent

# Shape U predicate: START is what pauses, mode 8 is what leaks.
PRED_U = "live == 8 or (live == 4 and i.start)"
# Shape E predicate: entry frame only; this probe's mode-4 START is intentional.
PRED_E = "live == 8"

BLOCK = """-- ---- #131/#135 START-leak guard (adopted from probe_rotwedge; gate gate_d135_adopt.sh) ----
-- modeCache is sampled once per frame at endFrame, but this poll runs in NMI at the TOP of the
-- frame and the ROM advances 8->4 LATER in that same frame.  A press permitted here at mode 8 is
-- therefore still in the P1 newly-pressed latch $F5 when the stock pause routine $978E runs,
-- already in mode 4.  $97A7 accepts it, the match pauses at spawn, and on a P1-native cart that
-- pause is UNEXITABLE (#133) -- the run wedges forever.  Mode 8 is the only predecessor of 4.
-- D135_LEAK=1 restores the pre-fix behaviour: that is the KILLED MUTANT, and it must make
-- leaked > 0.  `blocked` is the non-vacuity control -- a fixed run that never blocked anything
-- did not exercise the guard, and the gate FAILS it rather than reading it as clean.
local D135_LEAK = (os.getenv("D135_LEAK") == "1")
local D135_OUT  = os.getenv("D135_OUT")
local d135_blocked, d135_leaked = 0, 0
local function d135_report()
  if not D135_OUT then return end
  local f = io.open(D135_OUT .. "/d135_census.txt", "w")
  if not f then return end
  f:write(string.format("D135 blocked=%d leaked=%d guard=%s\\n",
    d135_blocked, d135_leaked, D135_LEAK and "OFF" or "ON"))
  f:close()
end
d135_report()   -- write at load, so "probe never ran" is distinguishable from "no hazard seen"
local function d135_block(i)
  local live = emu.read(0x46, emu.memType.nesMemory, false)
  if not (%PRED%) then return false end
  if D135_LEAK then
    d135_leaked = d135_leaked + 1
    if d135_leaked <= 10 or d135_leaked %% 500 == 0 then d135_report() end
    return false
  end
  d135_blocked = d135_blocked + 1
  if d135_blocked <= 10 or d135_blocked %% 500 == 0 then d135_report() end
  return true
end
"""

# (file, shape, exact old delivery line, new delivery line)
# Every one of these sites was read individually before being listed here -- the shapes differ,
# so a blind regex over the family would have silently disarmed three instruments.
OLD_CACHED = "  if inCur and frame < inUntil and modeCache ~= 4 then emu.setInput(inCur, 0) end"
NEW_CACHED = ("  if inCur and frame < inUntil and modeCache ~= 4 and not d135_block(inCur) then\n"
              "    emu.setInput(inCur, 0)\n  end")
OLD_PLAIN = "  if inCur and frame < inUntil then emu.setInput(inCur, 0) end"
NEW_PLAIN = ("  if inCur and frame < inUntil and not d135_block(inCur) then\n"
             "    emu.setInput(inCur, 0)\n  end")

TARGETS = [
    # cached-mode-4 guard: the classic leak.  All presses in these probes are START-only.
    ("probe2.lua",           "U", OLD_CACHED, NEW_CACHED),
    ("probe3.lua",           "U", OLD_CACHED, NEW_CACHED),
    ("probe4.lua",           "U", OLD_CACHED, NEW_CACHED),
    ("probe5.lua",           "U", OLD_CACHED, NEW_CACHED),
    ("probe6.lua",           "U", OLD_CACHED, NEW_CACHED),
    ("probe7.lua",           "U", OLD_CACHED, NEW_CACHED),
    ("probe8.lua",           "U", OLD_CACHED, NEW_CACHED),
    ("probe_soak.lua",       "U", OLD_CACHED, NEW_CACHED),
    ("probe_framedense.lua", "U", OLD_CACHED, NEW_CACHED),
    ("probe_rotpc.lua",      "U", OLD_CACHED, NEW_CACHED),
    # startpause keeps its INJ==3 mode-4 injector ABOVE this line untouched -- that injector is
    # the seed-30011 killed mutant and is supposed to reach mode 4.
    ("probe_startpause.lua", "U", OLD_CACHED, NEW_CACHED),
    # no mode gate at all -- strictly leakier than the cached family.
    ("fieldplay.lua",        "U", OLD_PLAIN,  NEW_PLAIN),
    ("p1live.lua",           "U", OLD_PLAIN,  NEW_PLAIN),
    # intentional mode-4 START: entry-frame-only guard, or the instrument goes vacuous.
    ("fieldplay_hold.lua",   "E", OLD_PLAIN,  NEW_PLAIN),
    ("stomp_pc.lua",         "E", OLD_PLAIN,  NEW_PLAIN),
]

ANCHOR = re.compile(r"^emu\.addEventCallback\(function\(\)\n", re.M)


def patch(path, shape, old, new):
    src = path.read_text()
    if "d135_block" in src:
        return "already-adopted"
    n = src.count(old)
    if n != 1:
        return f"REFUSED: delivery line appears {n} times (expected exactly 1)"
    src2 = src.replace(old, new)
    # insert the guard immediately before the inputPolled callback that owns this line
    idx = src2.index(new)
    head = src2.rfind("emu.addEventCallback(function()", 0, idx)
    if head < 0:
        return "REFUSED: no addEventCallback above the delivery line"
    pred = PRED_U if shape == "U" else PRED_E
    block = BLOCK.replace("%PRED%", pred).replace("%%", "%")
    src2 = src2[:head] + block + src2[head:]
    path.write_text(src2)
    return f"patched (shape {shape})"


def main():
    rc = 0
    for name, shape, old, new in TARGETS:
        p = GATE / name
        if not p.exists():
            print(f"{name:24s} MISSING"); rc = 1; continue
        r = patch(p, shape, old, new)
        print(f"{name:24s} {r}")
        if r.startswith("REFUSED"):
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
