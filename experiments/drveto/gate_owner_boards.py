#!/usr/bin/env python3
"""GATE 3: OWNER-BOARD REPLAY -- the two reconstructed owner-match suicide parents.

Boards: g2_parent.json / g3_parent.json, decoded from the OBS VOD frames in the
measurement-1 rig (scratchpad/plugpred; grid calibration validated there):
  G2 parent = g2d/f0023.png  -- col3 fo==2, (0,3)/(0,4) free, fatal = VERTICAL col3
              locking rows 0-1 (top Y, bottom B), no clear.  2 viruses left.
  G3 parent = g3d/f0030.png  -- col3 fo==1, cols 0-2 heights 1/2/4, fatal = VERTICAL
              col3 locking at rows -1/0 (bottom B plugging (0,3), top discarded).
              15 viruses left.  NOT GENERABLE by the enumerator (R29 world (a)):
              the covered generable family is the horizontals H23/H34 (min fo==1).

MEASURED here: the geometry predicate veto_plug fires on the fatal placements; the
full (a+) predicate (geometry + rv==0 + win==0 + viruses-remain) fires in the
mirror; firmware(DRVETO=1) parity against the mirror ON THESE BOARDS; and the
DRVETO=1 decision never lands a cell in (0,3)/(0,4).
INFERRED (disclosed): virus FLAGS -- the VOD decoder reads colour, not sprite
type, so virus positions are assigned (bottom rows) to make virus counts match
the documented 2 (G2) / 15 (G3); colour map Y=0, R=1, B=2 is a bijection choice.
Both only perturb leaf scores, never the veto predicate itself.  The next pill
is unknown from the frames, so all criteria are swept over 3 next-pill pairs x
4 tie-break seeds (incl. 0) and must hold for EVERY combination.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_drveto as GG  # noqa: E402  (sets the recipe env before builder import)

CMAP = {"Y": 0, "R": 1, "B": 2}


def load_board(path, n_virus, virus_rows):
    grid = json.load(open(path))
    b = [0xFF] * 128
    for r in range(16):
        for c in range(8):
            ch = grid[r][c]
            if ch != ".":
                b[r * 8 + c] = CMAP[ch]
    # INFERRED virus flags: mark occupied cells in the given rows (bottom-up,
    # left-to-right) until n_virus are placed.
    marked = 0
    for r in virus_rows:
        for c in range(8):
            i = r * 8 + c
            if b[i] != 0xFF and marked < n_virus:
                b[i] |= 0xD0
                marked += 1
    assert marked == n_virus, (marked, n_virus)
    return b


def plugs_throat(D3, board, col, o4):
    """Does the DECIDED placement put a cell in (0,3)/(0,4)?  (geometry arm on the
    real parent -- the criterion for 'picked a safe alternative')."""
    return D3.veto_plug(board, o4, col)


def main():
    B, D3 = GG._load()
    img_on, ep_on, _ = GG.image_for(B, D3, True)
    img_off, ep_off, _ = GG.image_for(B, D3, False)

    g2 = load_board(os.path.join(HERE, "g2_parent.json"), 2, [15, 14])
    g3 = load_board(os.path.join(HERE, "g3_parent.json"), 15, [15, 14, 13, 12])

    tseeds = [0, (0x10 | 1) ^ 0xA4, (0x28 | 1) ^ 0xA4, (0x3A | 1) ^ 0xA4]
    nexts = [(0, 1), (1, 2), (2, 2)]
    fails = []

    # ---- MEASURED, colour-free: the geometry arm on the fatal placements
    geo = {
        "G2 fatal vertical col3 (o4=0)": D3.veto_plug(g2, 0, 3),
        "G2 fatal vertical col3 (o4=1)": D3.veto_plug(g2, 1, 3),
        "G3 fatal vertical col3 fo==1 (o4=0, non-generable)": D3.veto_plug(g3, 0, 3),
        "G3 generable horizontal 2-3 (o4=2)": D3.veto_plug(g3, 2, 2),
        "G3 generable horizontal 3-4 (o4=2)": D3.veto_plug(g3, 2, 3),
    }
    for k, v in geo.items():
        print(f"  geometry: {k}: {'FIRES' if v else 'no fire'}")
        if not v:
            fails.append(("geometry", k))

    # ---- full (a+) predicate + decision sweep
    for name, board, fatal_cols in (("G2", g2, (3,)), ("G3", g3, (2, 3))):
        # G2's fatal capsule was (Y,B) = (0,2); G3's bottom half was B=2, top unknown
        caps = [(0, 2)] if name == "G2" else [(2, 0), (2, 1), (2, 2)]
        for (cA, cB) in caps:
            for (nA, nB) in nexts:
                for ts in tseeds:
                    m_fired, f_fired = [], []
                    e_on = GG.decide_mirror(D3, board, cA, cB, nA, nB, ts, veto=True,
                                            fired_out=m_fired)
                    g_on = GG.run_fw(B, D3, img_on, ep_on, board, cA, cB, nA, nB, ts,
                                     fired=f_fired)
                    e_off = GG.decide_mirror(D3, board, cA, cB, nA, nB, ts, veto=False)
                    g_off = GG.run_fw(B, D3, img_off, ep_off, board, cA, cB, nA, nB, ts)
                    e_on_c = (e_on[0], D3.canon_o4(e_on[1], cA, cB)) if e_on else None
                    e_off_c = (e_off[0], D3.canon_o4(e_off[1], cA, cB)) if e_off else None
                    tag = f"{name} cap=({cA},{cB}) next=({nA},{nB}) ts={ts:02x}"
                    if g_on != e_on_c or g_off != e_off_c:
                        fails.append(("parity", tag, g_on, e_on_c, g_off, e_off_c))
                    if sorted(set(f_fired)) != sorted(set(m_fired)):
                        fails.append(("flagset", tag, sorted(set(f_fired)),
                                      sorted(set(m_fired))))
                    if name == "G2" and not any(c == 3 and o < 2 for (c, o) in m_fired):
                        fails.append(("predicate-miss", tag, m_fired))
                    if g_on is None:
                        fails.append(("no-decision", tag))
                    elif plugs_throat(D3, board, g_on[0], g_on[1]):
                        fails.append(("picked-plug", tag, g_on))
                    if ts == tseeds[0] and (nA, nB) == nexts[0]:
                        print(f"  {tag}: OFF={g_off} ON={g_on} fired={sorted(set(m_fired))}")
    print()
    if fails:
        print(f"OWNER-BOARD GATE: FAIL ({len(fails)})")
        for f in fails[:12]:
            print("   ", f)
        return 1
    print("OWNER-BOARD GATE: PASS -- predicate fires on both parents, firmware ==")
    print("mirror on both, and the DRVETO=1 decision never plugs the throat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
