"""Trivially-correct candidates: the reference re-exported. Proves the PASS path
and documents the exact contracts a real candidate must satisfy."""
import sys
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/tmp/combo_term")
import numpy as np
from fast_rtl_x import _eval_rtl
from fast_sim_x import _expand_core

NCELL = 128


def leaf(col, vir, w, fl):
    """Level-1 contract: (col int8[128] 0/1..3, vir int8[128], w float64[16],
    fl int32[3]) -> signed-16 int."""
    return _eval_rtl(col, vir, w, fl)


def pair(pcol, pvir, variant, column, pa, pb, w, fl):
    """Pairs contract (delta-shaped): parent arrays + placement (fast_sim variant
    0..3, column 0..7, pa/pb colors 1..3) -> child leaf score. Pairs are
    guaranteed legal + no-clear. This impl is full-recompute; a real delta
    candidate computes the same number incrementally."""
    ccol = np.empty(NCELL, dtype=np.int8)
    cvir = np.empty(NCELL, dtype=np.int8)
    ok, nv, cells = _expand_core(pcol, pvir, variant, column, pa, pb, ccol, cvir)
    assert ok == 1 and nv == 0 and cells == 0
    return _eval_rtl(ccol, cvir, w, fl)
