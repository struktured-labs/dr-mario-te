"""Instrument validation. R92: a detector that CANNOT fire and a soak with no
deaths look identical, so the null test alone proves nothing -- every null here is
paired with a positive control that must fire."""
import numpy as np
from PIL import Image
import rounds, virus_ocr as v

ok = True
def check(label, cond, detail=""):
    global ok
    print("  %-58s %s%s" % (label, "PASS" if cond else "FAIL", ("  " + detail) if detail else ""))
    ok &= bool(cond)

print("\n-- A. digit templates --")
check("10 CHR digit templates, all distinct", len({g.tobytes() for g in v.TEMPLATES.values()}) == 10)
check("templates come from the SOAK cart's own CHR", v.CART.endswith("proph_cvc/proph1.nes"))

print("\n-- B. counter regions vs a HAND-READ frame --")
# soak_frame1.png was cropped, zoomed 6x/3x and read by eye as P1=44 P2=23
r = v.read_frame("hand_read_frame_p1_44_p2_23.png")
check("OCR reproduces the hand-read counts (P1=44, P2=23)", r["p1"] == 44 and r["p2"] == 23,
      "got P1=%s P2=%s" % (r["p1"], r["p2"]))
check("board fill orders the two seats as the eye does (P1 fuller)",
      r["fill"]["p1"] > r["fill"]["p2"],
      "p1=%.3f p2=%.3f" % (r["fill"]["p1"], r["fill"]["p2"]))

print("\n-- C. a corrupted frame must yield NO reading, not a guess --")
a = np.array(Image.open("hand_read_frame_p1_44_p2_23.png").convert("RGB")).astype(int)
b = a.copy(); b[v.ROW0:v.ROW1, 110:147] = 0          # black out the counter box
check("blanked counter box -> both seats None", v.read_counts(b) == {"p1": None, "p2": None})
c = a.copy(); c[v.ROW0 + 4, 112] = 255                # flip ONE pixel of P1's tens glyph
check("one flipped pixel -> that seat None (no nearest-match guess)",
      v.read_counts(c)["p1"] is None and v.read_counts(c)["p2"] == 23)

print("\n-- D. transition detector: NULL must be silent, CONTROL must fire --")
# NULL 1: a whole round, counts only ever falling.
HEALTHY = (0.2, 0.2, 0, 0, 1, 1)          # no throat, no top stack
null1 = [(i * 15.0, 48 - i, 48 - 2 * i) + HEALTHY for i in range(20)]
check("null: 20 monotonically falling samples -> 0 transitions", len(rounds.transitions(null1)) == 0)
# NULL 2: counts flat (a stalled/paused screen) -- must NOT invent a boundary.
check("null: 20 identical samples -> 0 transitions",
      len(rounds.transitions([(i * 15.0, 30, 20) + HEALTHY for i in range(20)])) == 0)
# NULL 3: unreadable stretch in the middle must not fabricate one.
null3 = null1[:8] + [(t, None, None) + HEALTHY for t in (130.0, 145.0, 160.0)] + \
        [(i * 15.0, 40 - i, 30 - i) + HEALTHY for i in range(12, 20)]
check("null: an unreadable gap mid-round -> 0 transitions", len(rounds.transitions(null3)) == 0)
# POSITIVE CONTROL: the same series with one genuine reset spliced in.
pos = null1[:10] + [(i * 15.0, 48 - (i - 10), 48 - (i - 10)) + HEALTHY for i in range(10, 20)]
check("control: one reset to 48 -> exactly 1 transition", len(rounds.transitions(pos)) == 1)
# CONTROL 2: the detector must survive missing the boundary sample itself.
pos2 = [s for s in pos if s[0] != 150.0]
check("control: reset still found with the boundary sample DELETED",
      len(rounds.transitions(pos2)) == 1)
# CONTROL 3: two rounds -> two transitions (it does not latch after the first).
pos3 = pos + [(i * 15.0, 48 - (i - 20), 48 - (i - 20)) + HEALTHY for i in range(20, 30)]
check("control: two resets -> 2 transitions", len(rounds.transitions(pos3)) == 2)

print("\n-- E. outcome classifier: every branch reachable, spawn-capsule trap held --")
PLUG, NOPLUG, CAPSULE = (1, 6), (0, 1), (1, 2)   # (throat, topcells)
def one(p1, p2, a, b):
    s = [(0.0, p1, p2, 0.3, 0.3, a[0], b[0], a[1], b[1]), (15.0, 48, 48) + HEALTHY]
    return rounds.transitions(s)[0]["outcome"]
check("P2 cleared out -> CLEAR_WIN_P2", one(20, 0, NOPLUG, NOPLUG) == "CLEAR_WIN_P2")
check("P1 cleared out -> CLEAR_WIN_P1", one(0, 20, NOPLUG, NOPLUG) == "CLEAR_WIN_P1")
check("P2's throat plugged -> TOPOUT_P2", one(20, 30, NOPLUG, PLUG) == "TOPOUT_P2")
check("P1's throat plugged -> TOPOUT_P1", one(30, 20, PLUG, NOPLUG) == "TOPOUT_P1")
check("both plugged -> AMBIGUOUS", one(20, 30, PLUG, PLUG) == "AMBIGUOUS")
check("neither plugged at the last sample -> AMBIGUOUS", one(20, 30, NOPLUG, NOPLUG) == "AMBIGUOUS")
check("a SPAWNING CAPSULE in the throat is NOT a plug (the trap)",
      one(20, 30, NOPLUG, CAPSULE) == "AMBIGUOUS")
# the RULE REVISION: near-death must be visible WITHOUT the throat, because the
# throat is only occupied in the ~2.13 s a poll cannot be relied on to catch.
STACK = (0, 8)          # tall stack in rows 0-2, throat not (yet) occupied
check("tall top-rows stack with NO throat -> still a topout (revision)",
      one(44, 12, STACK, NOPLUG) == "TOPOUT_P1")
check("the revision did NOT make the spawn capsule a plug",
      rounds.plugged(1, 2) is False)
check("a 5-cell stack is below the near-death bar", rounds.plugged(0, 5) is False)
check("a 6-cell stack meets it", rounds.plugged(0, 6) is True)

print("\n" + ("INSTRUMENT VALIDATION: ALL PASS" if ok else "INSTRUMENT VALIDATION: FAILED"))
raise SystemExit(0 if ok else 1)
