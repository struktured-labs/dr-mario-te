#!/usr/bin/env python3
"""G3 TIER-1, ROM half (MEASURED on the real Rev-0 ROM in nes_py, 2P VS mode, P1 side):
  E1  spawn anatomy + slide/lock window W_slide vs (speedSetting, speedUps)
  E2  DAS timeline under a driver-style HELD direction (raw latch, held untouched)
  E3  latest hold-start k that still escapes a one-sided ledge
  E4  two-edge (both-sides plug) escape vs the window
  E5  speedCounter never reset by lateral motion (lock timer is hard)
Player-loop mechanics are currentP-symmetric; P1 is measured (input port 0), P2's
field is cleared at every paint so it never tops out.  All frame counts are whole
env.step frames.  Output: rom_measurements.json
"""
import json
import sys
import nespatch  # noqa: F401  numpy-2 shim
from nes_py import NESEnv

ROM = "/home/struktured/projects/dr-mario-mods/drmario.nes"
R, L, D, U, ST, SEL = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04

MODE, NBP = 0x46, 0x0727
P1 = dict(X=0x0305, Y=0x0306, NEXTACT=0x0317, SPDCNT=0x0312, SPDUPS=0x030A,
          SPDSET=0x030B, PILLS=0x0327, VLEFT=0x0324, ROT=0x0325)
FIELD1, FIELD2 = 0x0400, 0x0500

# US speedCounterTable + base indices, transcribed from the vendored disassembly
BASE = {0: 0x0F, 1: 0x19, 2: 0x1F}   # LOW MED HI
TABLE = [0x38,0x36,0x35,0x33,0x31,0x30,0x2E,0x2C,0x2B,0x29,0x27,0x26,0x24,0x22,
         0x21,0x1F,0x1D,0x1C,0x1A,0x18,0x17,0x15,0x13,0x12,0x10,0x0F,0x0E,0x0D,
         0x0C,0x0B,0x0A,0x09,0x09,0x08,0x07,0x06,0x06,0x05,0x05,0x05,0x04,0x04,
         0x04,0x04,0x03,0x03,0x03,0x03,0x03,0x03,0x02,0x02,0x02,0x02,0x02,0x02,
         0x02,0x02,0x01,0x01,0x01,0x01,0x01,0x01]

env = NESEnv(ROM)
env.reset()
ram = env.ram


def step(act=0, n=1):
    for _ in range(n):
        env.step(int(act))


def nav_to_vs():
    step(0, 240)                       # boot to title (mode 0)
    assert ram[MODE] == 0, f"not at title: mode={ram[MODE]:#x}"
    step(SEL, 2); step(0, 10)          # toggle to 2 PLAYER GAME
    assert ram[NBP] == 2, f"nbPlayers={ram[NBP]} after SELECT"
    step(ST, 2); step(0, 60)           # -> options
    step(ST, 2); step(0, 120)          # -> level intro
    for _ in range(600):
        if ram[MODE] == 4:
            return
        step(0, 1)
    raise RuntimeError(f"never reached mainLoop, mode={ram[MODE]:#x}")


def paint(fo, viruses=((15, 0),), clear_p2=True):
    """fo[c] = first open row from top for column c (16 = empty column).
    Fill rows fo[c]..15 with (r+c)%3 diagonal stripes (no 2-runs anywhere)."""
    for c in range(8):
        for r in range(16):
            a = FIELD1 + r * 8 + c
            ram[a] = ((r + c) % 3) | 0x40 if r >= fo[c] else 0xFF
    for (r, c) in viruses:
        ram[FIELD1 + r * 8 + c] = ((r + c) % 3) | 0xD0
    ram[P1["VLEFT"]] = len(viruses) + 8      # never level-clear mid-measurement
    if clear_p2:
        for i in range(128):
            ram[FIELD2 + i] = 0xFF
        ram[0x03A4] = 9                       # p2 virusLeft nonzero


def set_speed(setting, ups):
    ram[P1["SPDSET"]] = setting
    ram[P1["SPDUPS"]] = ups


def wait_lock_then(fo, setting, ups, viruses=((15, 0),)):
    """Anchor cleanly BETWEEN pills: wait for a pill to be falling (na==0), then
    for it to lock (na!=0); then paint + set speed.  The next spawn lands on the
    scenario board."""
    guard = 0
    while ram[P1["NEXTACT"]] != 0 and guard < 3000:
        step(0, 1); guard += 1
    while ram[P1["NEXTACT"]] == 0 and guard < 6000:
        step(0, 1); guard += 1
    assert guard < 6000, "no pill lock observed"
    paint(fo, viruses)
    set_speed(setting, ups)


def trace_pill(policy, max_frames=900):
    """From between-pills, run until the NEXT P1 pill locks.  t=0 is the first
    frame nextAction==0 (action_pillFalling active).  Also records t_ywrite =
    frames BEFORE t=0 at which fallingPillY was (re)written to the spawn row
    (negative = head start the driver's Y-rise detector gets)."""
    tr = []
    ywrite_pre = None
    pre = 0
    lastY = ram[P1["Y"]]
    guard = 0
    while ram[P1["NEXTACT"]] != 0 and guard < 3000:
        step(0, 1); guard += 1
        pre += 1
        y = ram[P1["Y"]]
        if y >= 14 and lastY < 12 and ywrite_pre is None:
            ywrite_pre = pre
        lastY = y
    assert guard < 3000, "no spawn observed"
    tr.append(dict(t=0, y=int(ram[P1["Y"]]), x=int(ram[P1["X"]]),
                   na=0, sc=int(ram[P1["SPDCNT"]])))
    while guard < 3000 + max_frames:
        guard += 1
        step(policy(len(tr) - 1), 1)
        d = dict(t=len(tr), y=int(ram[P1["Y"]]), x=int(ram[P1["X"]]),
                 na=int(ram[P1["NEXTACT"]]), sc=int(ram[P1["SPDCNT"]]))
        tr.append(d)
        if d["na"] != 0:
            break
    tr[0]["ywrite_pre"] = ywrite_pre
    return tr


def throat_free():
    return ram[FIELD1 + 3] == 0xFF and ram[FIELD1 + 4] == 0xFF


def lock_info(tr):
    lock_t = tr[-1]["t"]
    return dict(lock_t=lock_t, final_x=tr[-2]["x"] if len(tr) > 1 else tr[-1]["x"],
                final_y=tr[-2]["y"] if len(tr) > 1 else tr[-1]["y"],
                throat_free=throat_free())


PLUG34 = [8, 8, 8, 1, 1, 8, 8, 8]        # both spawn cols resting at fo=1
LEDGE4 = [13, 13, 13, 12, 1, 8, 8, 8]    # vetog1 class: col4 ledge fo=1, col3 open 12
LEDGE4_F2 = [13, 13, 13, 12, 2, 8, 8, 8]
PLUG34_OPEN = [10, 10, 10, 1, 1, 10, 10, 10]

NEUTRAL = [10, 10, 10, 16, 16, 10, 10, 10]   # open throat, benign shelves

def cleanup_after_lock():
    """The scenario locks IN the throat; the loss check runs at the NEXT throw
    (sendPill).  Erase the throat immediately after the measured lock so the
    round never ends."""
    paint(NEUTRAL)

out = {"E1": [], "E2": [], "E3": [], "E4": [], "E5": [], "anatomy": {}}
nav_to_vs()
print("in VS mainLoop; nbP", ram[NBP], file=sys.stderr)

# ---------------- E1: W_slide sweep ----------------
for setting in (1, 2, 0):
    for ups in (0, 5, 10, 15, 20, 25, 30, 40, 49):
        wait_lock_then(PLUG34, setting, ups)
        tr = trace_pill(lambda t: 0)
        cleanup_after_lock()
        idx = BASE[setting] + min(ups, 49)
        pred = TABLE[idx] if idx < len(TABLE) else TABLE[-1]
        li = lock_info(tr)
        sc0 = [d["sc"] for d in tr[:4]]
        out["E1"].append(dict(setting=setting, ups=ups, table=pred,
                              W_slide=li["lock_t"], sc_head=sc0,
                              ywrite_pre=tr[0].get("ywrite_pre")))
        print(f"E1 set={setting} ups={ups} table={pred} W={li['lock_t']}",
              file=sys.stderr)
        if ups == 0:
            out["anatomy"][str(setting)] = tr[:24]

# ---------------- E1b: full traces at plateau cells ----------------
for setting, ups in ((0, 25), (0, 49), (1, 10), (1, 15), (1, 25), (2, 20)):
    wait_lock_then(PLUG34, setting, ups)
    tr = trace_pill(lambda t: 0)
    cleanup_after_lock()
    out.setdefault("E1b", []).append(dict(
        setting=setting, ups=ups,
        sc=[d["sc"] for d in tr], y=[d["y"] for d in tr],
        ups_live=int(ram[P1["SPDUPS"]]), pills=int(ram[P1["PILLS"]])))
    print(f"E1b set={setting} ups={ups} sc={[d['sc'] for d in tr]}", file=sys.stderr)

# ---------------- E2: DAS timeline (hold LEFT from spawn) ----------------
for board, nm in ((LEDGE4, "ledge4_f1"), (LEDGE4_F2, "ledge4_f2")):
    wait_lock_then(board, 1, 0)
    tr = trace_pill(lambda t: L)
    li = lock_info(tr)
    cleanup_after_lock()
    moves = [d["t"] for i, d in enumerate(tr[1:], 1) if d["x"] != tr[i - 1]["x"]]
    out["E2"].append(dict(board=nm, edge_frames=moves[:6], **li))
    print(f"E2 {nm} edges={moves[:6]} lock={li}", file=sys.stderr)

# ---------------- E3: latest escape k on the one-sided ledge ----------------
for k in range(0, 22, 1):
    wait_lock_then(LEDGE4, 1, 0)
    tr = trace_pill(lambda t, k=k: L if t >= k else 0)
    li = lock_info(tr)
    cleanup_after_lock()
    escaped = li["throat_free"] and li["final_y"] < 14
    out["E3"].append(dict(k=k, escaped=bool(escaped), **li))
    print(f"E3 k={k} escaped={escaped} lock_t={li['lock_t']} fy={li['final_y']}",
          file=sys.stderr)

# ---------------- E4: both-sides plug, 2-edge escape ----------------
for setting, ups in ((1, 0), (1, 10), (2, 0)):
    wait_lock_then(PLUG34_OPEN, setting, ups)
    tr = trace_pill(lambda t: L)
    li = lock_info(tr)
    cleanup_after_lock()
    moves = [d["t"] for i, d in enumerate(tr[1:], 1) if d["x"] != tr[i - 1]["x"]]
    escaped = li["throat_free"] and li["final_y"] < 14
    out["E4"].append(dict(setting=setting, ups=ups, edges=moves[:4],
                          escaped=bool(escaped), **li))
    print(f"E4 set={setting} ups={ups} edges={moves[:4]} esc={escaped}",
          file=sys.stderr)

# ---------------- E5: lateral motion does not reset the lock timer ----------
wait_lock_then([13, 13, 13, 12, 1, 8, 8, 8], 1, 0)
tr = trace_pill(lambda t: L)
cleanup_after_lock()
out["E5"] = dict(sc_series=[d["sc"] for d in tr[:20]],
                 y_series=[d["y"] for d in tr[:20]],
                 x_series=[d["x"] for d in tr[:20]])

with open("/home/struktured/projects/dr-mario-tempo-wt/experiments/drveto/g3_tempo/rom_measurements.json", "w") as f:
    json.dump(out, f, indent=1, default=lambda o: bool(o) if hasattr(o, "__bool__") else str(o))
print("wrote rom_measurements.json", file=sys.stderr)
