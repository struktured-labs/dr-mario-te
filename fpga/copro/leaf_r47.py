#!/usr/bin/env python3
"""R47-FAITHFUL python mirror of the shipped RTL leaf eval (LeafEval.sv S_DONE2).

WHY THIS FILE EXISTS
--------------------
`tests/nes_d3_golden.py` (`leaf_d3`) is WEEKEND-ERA: it hardcodes 12*vrdy, uses the
flat `test_eval_terms.g_buried`, and has NO matched60 term. It does NOT read the R47
flags that `build_copro_d3.py` sets on it, so those flag-sets are effectively no-ops.
The shipped brain's leaf runs entirely in RTL (LeafEval.sv), and the only committed
artifact that encodes the R47 leaf scores is the pinned Verilator corpus
`leafeval_cases.txt` (regenerated at commit fd8e495 "R47 brain"). There is no committed
generator for that corpus.

This module ports the RTL leaf EXACTLY (read the RTL as the spec) and is validated to
100% cell-exact match against the pinned corpus (real RTL output). Run `python leaf_r47.py`
to reproduce the match report.

Ground truth = canonical RTL: dr-mario-mods/fpga/copro/LeafEval.sv @ incr-delta (9e040e3).
Combine (S_DONE2, lines 587-597):
  sco = 5000 - 12*maxh - 20*holes - 90*toprisk - 150*spawn + 60*setup
        + matched60 - 30*buried + 12*rdy_ext + 24*vrdy - 6*pollution        (signed 16-bit wrap)
  win = (no virus on board)

Board encoding == the corpus / tb_leafeval input == NES cells:
  0xFF          -> empty
  else          -> low nibble (0..2) = color; high nibble 0xD0 => virus
The RTL bcell is {vir, col[1:0]} with col = nibble+1 (1..3, 0=empty); col_of/occ_of/vir_of
decode from that. We decode the same way below.
"""

ROWS, COLS = 16, 8
EMPTY = 0xFF
WIN_SENTINEL = 0x7530  # 30000; RTL leaves sco don't-care on win, tb ignores it. Kept for callers.


def _decode(board):
    """NES 128-cell board -> per-cell (occ, vir, col) grids indexed [r][c].
    col in {0(empty),1,2,3}; matches RTL col_of = bcell[1:0], vir_of = bit2 & col!=0."""
    occ = [[0] * COLS for _ in range(ROWS)]
    vir = [[0] * COLS for _ in range(ROWS)]
    col = [[0] * COLS for _ in range(ROWS)]
    for i in range(128):
        x = board[i]
        r, c = i >> 3, i & 7
        if x == EMPTY:
            continue
        col[r][c] = (x & 0x0F) + 1          # 1..3
        occ[r][c] = 1
        vir[r][c] = 1 if (x & 0xF0) == 0xD0 else 0
    return occ, vir, col


def _sq(n):
    return n * n


def leaf_terms(board, *, w_vrdy=24, buried_color_aware=True,
               buried_nearest2_cap=True, matched_cover=True):
    """Return the dict of accumulator terms exactly as the RTL computes them.
    Flags default to the shipped R47 config; flip them for the reverted variants.
    - w_vrdy:               S_DONE2 vrdy coefficient (R47=24, weekend=12)
    - buried_color_aware:   R1 same-color-cover exemption in the buried charge
    - buried_nearest2_cap:  R7b charge only the 2 topmost viruses per column
    - matched_cover:        R6 matched-cover (+60 per virus with same-color cover on top)
    """
    occ, vir, col = _decode(board)

    maxh = holes = toprisk = spawn = 0
    buried = matched60 = 0
    anyvir = False

    # ---- column-major shape + buried + matched60 (RTL S_COLWALK) ----
    for c in range(COLS):
        seen = False
        fillcnt = 0          # occupied cells seen ABOVE the current cell (this column)
        curcol = 0           # color of the contiguous same-color non-virus cover run
        curlen = 0           # length of that run (0 = none)
        vseen = 0            # viruses seen so far this column (R7b cap)
        for r in range(ROWS):
            if occ[r][c]:
                if not seen:
                    seen = True
                    h = 16 - r
                    if h > maxh:
                        maxh = h
                if vir[r][c]:
                    anyvir = True
                    same = (curcol == col[r][c])
                    if matched_cover and same:
                        matched60 += 60
                    if (not buried_nearest2_cap) or vseen < 2:
                        exempt = curlen if (buried_color_aware and same) else 0
                        buried += fillcnt - exempt
                    vseen += 1
                    curcol = 0
                    curlen = 0
                else:
                    if curcol == col[r][c]:
                        curlen += 1
                    else:
                        curcol = col[r][c]
                        curlen = 1
                fillcnt += 1
                if r < 3:
                    toprisk += 1
                if r < 4 and (c == 3 or c == 4):
                    spawn += 1
            else:
                if seen:
                    holes += 1
                curcol = 0
                curlen = 0

    # ---- per-virus: rdy_ext, vrdy, pollution (RTL S_VNEXT..S_VFIN) ----
    rdy_ext = vrdy = pollution = 0
    for vr in range(ROWS):
        for vc in range(COLS):
            if not vir[vr][vc]:
                continue
            vcol = col[vr][vc]

            # horizontal run + span
            run_h = 1
            p = vc
            while p != 0 and col[vr][p - 1] == vcol and occ[vr][p - 1]:
                run_h += 1
                p -= 1
            span_lo = p
            while span_lo != 0 and ((not occ[vr][span_lo - 1]) or col[vr][span_lo - 1] == vcol):
                span_lo -= 1
            p = vc
            while p != 7 and occ[vr][p + 1] and col[vr][p + 1] == vcol:
                run_h += 1
                p += 1
            span_hi = p
            while span_hi != 7 and ((not occ[vr][span_hi + 1]) or col[vr][span_hi + 1] == vcol):
                span_hi += 1

            # vertical run + span
            run_v = 1
            p = vr
            while p != 0 and occ[p - 1][vc] and col[p - 1][vc] == vcol:
                run_v += 1
                p -= 1
            vspan_lo = p
            while vspan_lo != 0 and ((not occ[vspan_lo - 1][vc]) or col[vspan_lo - 1][vc] == vcol):
                vspan_lo -= 1
            p = vr
            while p != 15 and occ[p + 1][vc] and col[p + 1][vc] == vcol:
                run_v += 1
                p += 1
            vspan_hi = p
            while vspan_hi != 15 and ((not occ[vspan_hi + 1][vc]) or col[vspan_hi + 1][vc] == vcol):
                vspan_hi += 1

            hq = _sq(run_h) if (span_hi - span_lo + 1) >= 4 else 0
            vq = _sq(run_v) if (vspan_hi - vspan_lo + 1) >= 4 else 0
            rdy_ext += max(hq, vq)
            vrdy += _sq(run_v)

            # pollution: differently-colored non-virus occupied cells in row then column
            for pc in range(COLS):
                if pc != vc and occ[vr][pc] and not vir[vr][pc] and col[vr][pc] != vcol:
                    pollution += 1
            for pr in range(ROWS):
                if pr != vr and occ[pr][vc] and not vir[pr][vc] and col[pr][vc] != vcol:
                    pollution += 1

    # ---- setup: 3-in-a-row same color touching a same-color virus (RTL S_SETUP_H/V) ----
    setup = 0
    for wr in range(ROWS):                      # horizontal windows: rows 0..15, wc 0..5
        for wc in range(6):
            c0 = col[wr][wc]
            if c0 != 0 and col[wr][wc + 1] == c0 and col[wr][wc + 2] == c0:
                t = any(vir[wr][wc + k] and col[wr][wc + k] == c0 for k in (0, 1, 2))
                if not t and wc != 0:
                    t = vir[wr][wc - 1] and col[wr][wc - 1] == c0
                if not t and wc < 5:
                    t = vir[wr][wc + 3] and col[wr][wc + 3] == c0
                if t:
                    setup += 1
    for wc in range(COLS):                      # vertical windows: cols 0..7, wr 0..13
        for wr in range(14):
            c0 = col[wr][wc]
            if c0 != 0 and col[wr + 1][wc] == c0 and col[wr + 2][wc] == c0:
                t = any(vir[wr + k][wc] and col[wr + k][wc] == c0 for k in (0, 1, 2))
                if not t and wr != 0:
                    t = vir[wr - 1][wc] and col[wr - 1][wc] == c0
                if not t and wr < 13:
                    t = vir[wr + 3][wc] and col[wr + 3][wc] == c0
                if t:
                    setup += 1

    return dict(maxh=maxh, holes=holes, toprisk=toprisk, spawn=spawn, setup=setup,
                matched60=matched60, buried=buried, rdy_ext=rdy_ext, vrdy=vrdy,
                pollution=pollution, anyvir=anyvir, w_vrdy=w_vrdy)


def _combine(t):
    """S_DONE2 combine -> signed 16-bit sco."""
    s = (5000
         - 12 * t["maxh"]
         - 20 * t["holes"]
         - 90 * t["toprisk"]
         - 150 * t["spawn"]
         + 60 * t["setup"]
         + t["matched60"]
         - 30 * t["buried"]
         + 12 * t["rdy_ext"]
         + t["w_vrdy"] * t["vrdy"]
         - 6 * t["pollution"])
    s &= 0xFFFF                                  # 16-bit wrap
    if s >= 0x8000:
        s -= 0x10000                             # signed interpretation (tb casts to short)
    return s


def leaf_sco(board, **flags):
    """Return (sco_signed16, win). On win the sco is don't-care (RTL leaves it, tb ignores)."""
    t = leaf_terms(board, **flags)
    win = 0 if t["anyvir"] else 1
    return _combine(t), win


# ---- named variants for the eval A/B, built ON the verified mirror ----------
def leaf_r47(board):
    """Shipped R47 leaf (the config validated cell-exact vs the pinned corpus)."""
    return leaf_sco(board)


def leaf_vrdy12(board):
    """Candidate (a): W_VRDY 24 -> 12. Single-term delta from R47 (only the vrdy coeff)."""
    return leaf_sco(board, w_vrdy=12)


def leaf_weekend_burial(board):
    """Candidate (b): restore weekend burial (drop R7b nearest-2 cap + R1 same-color
    exemption). Matches the RTL revert spec, which KEEPS R6 matched-cover intact."""
    return leaf_sco(board, buried_color_aware=False, buried_nearest2_cap=False)


# ---- validation vs the pinned corpus (real RTL output) ----------------------
def _parse_corpus(path):
    with open(path) as f:
        toks = f.read().split()
    n = int(toks[0])
    toks = toks[1:]
    cases = []
    for k in range(n):
        base = k * 130
        board = [int(x, 16) for x in toks[base:base + 128]]
        sco = int(toks[base + 128])
        win = int(toks[base + 129])
        cases.append((board, sco, win))
    return cases


def _validate(path, label):
    cases = _parse_corpus(path)
    ok = 0
    fails = []
    for k, (board, exp_sco, exp_win) in enumerate(cases):
        got_sco, got_win = leaf_r47(board)
        if got_win != exp_win:
            fails.append((k, "win", got_win, exp_win))
            continue
        if exp_win or got_sco == exp_sco:
            ok += 1
        else:
            fails.append((k, "sco", got_sco, exp_sco))
    print(f"{label}: {ok}/{len(cases)} exact")
    for k, kind, got, exp in fails[:12]:
        t = leaf_terms(cases[k][0])
        print(f"  case {k} {kind} MISMATCH got={got} exp={exp} terms={t}")
    return ok, len(cases)


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    tot_ok = tot = 0
    lp = os.path.join(here, "leafeval_cases.txt")
    if os.path.exists(lp):
        a, b = _validate(lp, "leafeval_cases (direct leaf)")
        tot_ok += a
        tot += b
    print(f"\nR47 MIRROR vs RTL corpus: {tot_ok}/{tot} exact "
          f"({'PASS' if tot_ok == tot and tot else 'FAIL'})")
