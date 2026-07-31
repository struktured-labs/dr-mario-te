"""Pure-python leaf: per-term breakdown for failure dumps + mutant substrate.

Semantics transcribed from combo_term/fast_rtl_x._eval_rtl (which is the gate's
reference).  This copy exists for three reasons:
  1. failure dumps can show WHICH term diverged (numba gives one opaque int);
  2. gate selfcheck cross-checks it against _eval_rtl over the whole corpus
     (a transcription bug in either copy shows up as a selfcheck failure);
  3. mutants: `bug=` injects known-subtle errors; the gate must kill ALL of
     them or its corpus is too weak to be called a gate.

Boards are 128 NES bytes (see common.py).
"""
from __future__ import annotations

from common import (ROWS, COLS, NCELL, nes_to_arrays, R_BIAS, R_MAXH, R_HOLES,
                    R_TOPRISK, R_SPAWN, R_SETUP, R_MATCHED, R_BURIED, R_RDYEXT,
                    R_VRDY, R_POLL, R_CROSS,
                    FL_COLOR_AWARE, FL_NEAREST2, FL_MATCHED)

TERM_BUGS = ("nearest3", "colorblind_exempt", "spawn_r3", "toprisk_r4",
             "rdy_sum", "span_ge5", "setup_noext", "matched_any",
             "poll_incl_virus", "vrdy_linear", "holes_cap1", "cross_ungated",
             "matched_vircover")
COMBINE_BUGS = ("no_wrap", "wrap32", "saturate", "unsigned", "wrap_per_term")
ALL_BUGS = TERM_BUGS + COMBINE_BUGS


def terms(board, fl, bug=None):
    """-> dict of raw term counts (weight-independent).  bug injects a defect."""
    col, vir = nes_to_arrays(board)
    color_aware = fl[FL_COLOR_AWARE]
    nearest2 = fl[FL_NEAREST2]
    matched_on = fl[FL_MATCHED]

    maxh = holes = toprisk = spawn = buried = matched = 0
    n2cap = 3 if bug == "nearest3" else 2
    for c in range(COLS):
        seen = False; fillcnt = 0; curcol = 0; curlen = 0; vseen = 0
        col_holes = 0
        for r in range(ROWS):
            cc = col[r * COLS + c]
            if cc != 0:
                if not seen:
                    seen = True
                    h = ROWS - r
                    if h > maxh:
                        maxh = h
                if vir[r * COLS + c]:
                    same = (curcol == cc)
                    if bug == "matched_any":
                        same_m = (curcol != 0)
                    elif bug == "matched_vircover":
                        # counts a same-color VIRUS directly above as a cover too
                        same_m = same or (r > 0 and vir[(r - 1) * COLS + c]
                                          and col[(r - 1) * COLS + c] == cc)
                    else:
                        same_m = same
                    if matched_on and same_m:
                        matched += 1
                    if (nearest2 == 0) or vseen < n2cap:
                        if bug == "colorblind_exempt":
                            exempt = curlen
                        else:
                            exempt = curlen if (color_aware and same) else 0
                        buried += fillcnt - exempt
                    vseen += 1
                    curcol = 0; curlen = 0
                else:
                    if curcol == cc:
                        curlen += 1
                    else:
                        curcol = cc; curlen = 1
                fillcnt += 1
                if r < (4 if bug == "toprisk_r4" else 3):
                    toprisk += 1
                if r < (3 if bug == "spawn_r3" else 4) and (c == 3 or c == 4):
                    spawn += 1
            else:
                if seen:
                    if bug != "holes_cap1" or col_holes == 0:
                        holes += 1
                    col_holes += 1
                curcol = 0; curlen = 0

    rdy_ext = vrdy = pollution = cross = 0
    span_need = 5 if bug == "span_ge5" else 4
    for vr in range(ROWS):
        for vc in range(COLS):
            if not vir[vr * COLS + vc]:
                continue
            vcol = col[vr * COLS + vc]
            run_h = 1; p = vc
            while p != 0 and col[vr * COLS + (p - 1)] == vcol:
                run_h += 1; p -= 1
            span_lo = p
            while span_lo != 0 and (col[vr * COLS + span_lo - 1] == 0
                                    or col[vr * COLS + span_lo - 1] == vcol):
                span_lo -= 1
            p = vc
            while p != 7 and col[vr * COLS + (p + 1)] == vcol:
                run_h += 1; p += 1
            span_hi = p
            while span_hi != 7 and (col[vr * COLS + span_hi + 1] == 0
                                    or col[vr * COLS + span_hi + 1] == vcol):
                span_hi += 1
            run_v = 1; p = vr
            while p != 0 and col[(p - 1) * COLS + vc] == vcol:
                run_v += 1; p -= 1
            vspan_lo = p
            while vspan_lo != 0 and (col[(vspan_lo - 1) * COLS + vc] == 0
                                     or col[(vspan_lo - 1) * COLS + vc] == vcol):
                vspan_lo -= 1
            p = vr
            while p != 15 and col[(p + 1) * COLS + vc] == vcol:
                run_v += 1; p += 1
            vspan_hi = p
            while vspan_hi != 15 and (col[(vspan_hi + 1) * COLS + vc] == 0
                                      or col[(vspan_hi + 1) * COLS + vc] == vcol):
                vspan_hi += 1
            hq = run_h * run_h if (span_hi - span_lo + 1) >= span_need else 0
            vq = run_v * run_v if (vspan_hi - vspan_lo + 1) >= span_need else 0
            if bug == "rdy_sum":
                rdy_ext += hq + vq
            else:
                rdy_ext += hq if hq > vq else vq
            if bug == "cross_ungated":
                cross += hq if hq < vq else vq
            elif run_h >= 2 and run_v >= 2:
                cross += hq if hq < vq else vq
            vrdy += run_v if bug == "vrdy_linear" else run_v * run_v
            for pc in range(COLS):
                cx = col[vr * COLS + pc]
                if pc != vc and cx != 0 and cx != vcol and (
                        bug == "poll_incl_virus" or not vir[vr * COLS + pc]):
                    pollution += 1
            for pr in range(ROWS):
                cx = col[pr * COLS + vc]
                if pr != vr and cx != 0 and cx != vcol and (
                        bug == "poll_incl_virus" or not vir[pr * COLS + vc]):
                    pollution += 1

    setup = 0
    ext = bug != "setup_noext"
    for wr in range(ROWS):
        for wc in range(6):
            c0 = col[wr * COLS + wc]
            if c0 != 0 and col[wr * COLS + wc + 1] == c0 and col[wr * COLS + wc + 2] == c0:
                t = any(vir[wr * COLS + wc + k] and col[wr * COLS + wc + k] == c0
                        for k in range(3))
                if not t and ext and wc != 0 and vir[wr * COLS + wc - 1] and col[wr * COLS + wc - 1] == c0:
                    t = True
                if not t and ext and wc < 5 and vir[wr * COLS + wc + 3] and col[wr * COLS + wc + 3] == c0:
                    t = True
                if t:
                    setup += 1
    for wc in range(COLS):
        for wr in range(14):
            c0 = col[wr * COLS + wc]
            if c0 != 0 and col[(wr + 1) * COLS + wc] == c0 and col[(wr + 2) * COLS + wc] == c0:
                t = any(vir[(wr + k) * COLS + wc] and col[(wr + k) * COLS + wc] == c0
                        for k in range(3))
                if not t and ext and wr != 0 and vir[(wr - 1) * COLS + wc] and col[(wr - 1) * COLS + wc] == c0:
                    t = True
                if not t and ext and wr < 13 and vir[(wr + 3) * COLS + wc] and col[(wr + 3) * COLS + wc] == c0:
                    t = True
                if t:
                    setup += 1

    return dict(maxh=maxh, holes=holes, toprisk=toprisk, spawn=spawn,
                setup=setup, matched=matched, buried=buried, rdy_ext=rdy_ext,
                vrdy=vrdy, pollution=pollution, cross=cross)


def prewrap(t, w):
    """Full-precision combine (no 16-bit wrap) -- for wrap-band corpus checks."""
    return (int(w[R_BIAS])
            - int(w[R_MAXH]) * t["maxh"]
            - int(w[R_HOLES]) * t["holes"]
            - int(w[R_TOPRISK]) * t["toprisk"]
            - int(w[R_SPAWN]) * t["spawn"]
            + int(w[R_SETUP]) * t["setup"]
            + int(w[R_MATCHED]) * t["matched"]
            - int(w[R_BURIED]) * t["buried"]
            + int(w[R_RDYEXT]) * t["rdy_ext"]
            + int(w[R_VRDY]) * t["vrdy"]
            + int(w[R_CROSS]) * t["cross"]
            - int(w[R_POLL]) * t["pollution"])


def combine(t, w, bug=None):
    if bug == "wrap_per_term":
        def w16(x):
            x &= 0xFFFF
            return x - 0x10000 if x >= 0x8000 else x
        s = (w16(int(w[R_BIAS])) - w16(int(w[R_MAXH]) * t["maxh"])
             - w16(int(w[R_HOLES]) * t["holes"]) - w16(int(w[R_TOPRISK]) * t["toprisk"])
             - w16(int(w[R_SPAWN]) * t["spawn"]) + w16(int(w[R_SETUP]) * t["setup"])
             + w16(int(w[R_MATCHED]) * t["matched"]) - w16(int(w[R_BURIED]) * t["buried"])
             + w16(int(w[R_RDYEXT]) * t["rdy_ext"]) + w16(int(w[R_VRDY]) * t["vrdy"])
             + w16(int(w[R_CROSS]) * t["cross"]) - w16(int(w[R_POLL]) * t["pollution"]))
        return s
    s = prewrap(t, w)
    if bug == "no_wrap":
        return s
    if bug == "wrap32":
        s &= 0xFFFFFFFF
        return s - 0x100000000 if s >= 0x80000000 else s
    if bug == "saturate":
        return max(-32768, min(32767, s))
    s &= 0xFFFF
    if bug == "unsigned":
        return s
    return s - 0x10000 if s >= 0x8000 else s


def py_eval(board, w, fl, bug=None):
    """Full pure-python leaf.  bug in TERM_BUGS hits terms; COMBINE_BUGS the wrap."""
    tb = bug if bug in TERM_BUGS else None
    cb = bug if bug in COMBINE_BUGS else None
    return combine(terms(board, fl, bug=tb), w, bug=cb)
