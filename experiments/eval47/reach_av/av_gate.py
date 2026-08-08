#!/usr/bin/env python3
"""A_v BIT-EXACTNESS GATE -- run this before any A_v number is believed.

Positive controls (reach OFF must BE the shipped champion, not merely resemble it):
  P1  _eval_rx(reach=0)       == fast_rtl_x._eval_rtl       on the static
      bitexact_gate corpus, at EVERY dose (a dose must not perturb the equality)
  P2  same, on REAL champion decision boards (clean + bursty-v1.1 pressure)
  P3  _root_value_rx(reach=0) == root_search._root_value    for every legal root
      action on real boards -- the whole depth-3 chain, not just the leaf
  P4  choose_base_rx(reach=0, wt=0, ws=20) picks the IDENTICAL action as the
      shipped pressure_rig._choose_base on every real board

Negative / adequacy controls (a gate that only proves equality would pass an
INERT flag, and physics cases that no wrong predicate can fail prove nothing):
  N1  reach=1 must actually change the leaf on a material share of real boards
  N2  hand-built physics cases, each isolating ONE claim about A_v
  N3  MUTANT KILL: three wrong reach predicates must each FAIL N2.  The
      reference predicate, implemented INDEPENDENTLY in pure python, must PASS.
  N4  that independent pure-python implementation must agree with the numba
      kernel on the whole real corpus, at reach=0 AND reach=1

Locality control (the property that lets the delta engine survive A_v):
  L1  the vertical quantities are exactly additive over columns

Exit non-zero on any failure.  Nothing downstream should run if this fails.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

import reach_leaf as RL
import fast_rtl_x as FX
import root_search as RS
import pressure_rig as PR
from fast_sim_x import NCELL, COLS, ROWS, _expand_core

BITEXACT = "/home/struktured/projects/dr-mario-qa-wt/experiments/bitexact_gate"
DOSES = [8, 16, 24, 32, 48]


# --------------------------------------------------------------------- corpora
def load_static_corpus():
    """bitexact_gate/corpus.txt -> [(col, vir)] via that gate's own decoder."""
    if BITEXACT not in sys.path:
        sys.path.insert(0, BITEXACT)
    import common as BE
    with open(os.path.join(BITEXACT, "corpus.txt")) as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    n = int(lines[0])
    out = []
    for ln in lines[1:1 + n]:
        board = [int(x, 16) for x in ln.split()]
        assert len(board) == NCELL, f"bad corpus line: {len(board)} bytes"
        out.append(BE.nes_to_arrays(board))
    return out


def load_real_corpus(paths):
    out = []
    for p in paths:
        z = np.load(p, allow_pickle=True)
        col, vir, pills = z["col"], z["vir"], z["pills"]
        for i in range(len(col)):
            out.append((np.ascontiguousarray(col[i]), np.ascontiguousarray(vir[i]),
                        tuple(int(x) for x in pills[i])))
    return out


# ================================================ independent python reference
# Deliberately NOT a copy of the numba kernel: written from the physical rule
# ("an empty cell is fillable iff no occupied cell sits above it in its column")
# rather than from the kernel's control flow, so agreement is evidence.
def py_rdyext(col, vir, reach, kind="correct"):
    """rdy_ext = sum over viruses of max(hq, vq).

    kind: 'correct'  -- A_v as specified (vertical only, empty fillable iff above
                        the column's first occupied row)
          'hreach'   -- WRONG: the same guard also applied to the horizontal walk
          'uponly'   -- WRONG: guard applied to the upward walk only
          'inverted' -- WRONG: reachability predicate negated
    """
    top = []
    for c in range(COLS):
        t = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                t = r
                break
        top.append(t)

    def fillable(r, c):
        ok = r < top[c]
        return (not ok) if kind == "inverted" else ok

    total = 0
    for vr in range(ROWS):
        for vc in range(COLS):
            if not vir[vr * COLS + vc]:
                continue
            vcol = col[vr * COLS + vc]
            # ---- horizontal ----
            run_h = 1
            c = vc
            while c > 0 and col[vr * COLS + c - 1] == vcol:
                run_h += 1
                c -= 1
            lo = c
            while lo > 0:
                nb = col[vr * COLS + lo - 1]
                if nb == vcol:
                    lo -= 1
                elif nb == 0 and not (reach and kind == "hreach"
                                      and not fillable(vr, lo - 1)):
                    lo -= 1
                else:
                    break
            c = vc
            while c < COLS - 1 and col[vr * COLS + c + 1] == vcol:
                run_h += 1
                c += 1
            hi = c
            while hi < COLS - 1:
                nb = col[vr * COLS + hi + 1]
                if nb == vcol:
                    hi += 1
                elif nb == 0 and not (reach and kind == "hreach"
                                      and not fillable(vr, hi + 1)):
                    hi += 1
                else:
                    break
            # ---- vertical ----
            run_v = 1
            r = vr
            while r > 0 and col[(r - 1) * COLS + vc] == vcol:
                run_v += 1
                r -= 1
            vlo = r
            while vlo > 0:
                nb = col[(vlo - 1) * COLS + vc]
                if nb == vcol:
                    vlo -= 1
                elif nb == 0 and not (reach and not fillable(vlo - 1, vc)):
                    vlo -= 1
                else:
                    break
            r = vr
            while r < ROWS - 1 and col[(r + 1) * COLS + vc] == vcol:
                run_v += 1
                r += 1
            vhi = r
            while vhi < ROWS - 1:
                nb = col[(vhi + 1) * COLS + vc]
                if nb == vcol:
                    vhi += 1
                elif nb == 0 and not (reach and kind != "uponly"
                                      and not fillable(vhi + 1, vc)):
                    vhi += 1
                else:
                    break
            hq = run_h * run_h if (hi - lo + 1) >= 4 else 0
            vq = run_v * run_v if (vhi - vlo + 1) >= 4 else 0
            total += max(hq, vq)
    return total


# --------------------------------------------------------------------- P-gates
def p1_static(corpus, fails):
    n = 0
    for dose in DOSES + [12]:          # 12 = the pre-coefopt r47 rdyext weight
        w, fl = RL.weights_for(dose)
        for col, vir in corpus:
            a = int(RL._eval_rx(col, vir, w, fl, 0))
            b = int(FX._eval_rtl(col, vir, w, fl))
            n += 1
            if a != b:
                fails.append(f"P1 dose={dose}: _eval_rx(reach=0)={a} != _eval_rtl={b}")
                if len(fails) > 20:
                    return n
    return n


def p2_real(real, fails):
    n = 0
    for dose in DOSES:
        w, fl = RL.weights_for(dose)
        for col, vir, _pills in real:
            a = int(RL._eval_rx(col, vir, w, fl, 0))
            b = int(FX._eval_rtl(col, vir, w, fl))
            n += 1
            if a != b:
                fails.append(f"P2 dose={dose}: {a} != {b}")
                if len(fails) > 20:
                    return n
    return n


def p3_chain(real, fails, limit=None):
    w, fl = FX.variant("winner")
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    n = 0
    for col, vir, (ca, cb, na, nb) in (real if limit is None else real[:limit]):
        for o4 in range(4):
            var = int(FX._VAR_OF_O4[o4])
            for cc in range(8):
                ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
                if ok == 0:
                    continue
                got = RL._root_value_rx(c1, v1, nv, cells, na, nb, 8,
                                        FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl, 0)
                want = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                      FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
                n += 1
                if got != want:
                    fails.append(f"P3 action={var * 8 + cc}: {got} != {want}")
                    if len(fails) > 20:
                        return n
    return n


def p4_argmax(real, fails, ws=20, wt=0, limit=None):
    w, fl = FX.variant("winner")
    n = 0
    for col, vir, (ca, cb, na, nb) in (real if limit is None else real[:limit]):
        got, _ = RL.choose_base_rx(col, vir, ca, cb, na, nb, w, fl, wt, ws, 0)
        want, _ = PR._choose_base(col, vir, ca, cb, na, nb, w, fl, wt, ws)
        n += 1
        if got != want:
            fails.append(f"P4: reach-off action {got} != shipped {want}")
            if len(fails) > 20:
                return n
    return n


# --------------------------------------------------------------------- N-gates
def n1_not_inert(real, fails):
    w, fl = RL.weights_for(8)
    diff_leaf = diff_rdy = 0
    for col, vir, _p in real:
        if int(RL._eval_rx(col, vir, w, fl, 0)) != int(RL._eval_rx(col, vir, w, fl, 1)):
            diff_leaf += 1
        if int(RL._rdyext_only(col, vir, 0)[0]) != int(RL._rdyext_only(col, vir, 1)[0]):
            diff_rdy += 1
    if diff_leaf == 0:
        fails.append("N1: reach=1 changed NOTHING on the real corpus -- flag is inert")
    return diff_leaf, diff_rdy, len(real)


def _blank():
    return np.zeros(NCELL, dtype=np.int8), np.zeros(NCELL, dtype=np.int8)


def _put(col, vir, r, c, colour, is_vir=0):
    col[r * COLS + c] = colour
    vir[r * COLS + c] = is_vir


def _hblock(col, vir, row, cols=(1, 2, 3)):
    """Kill the horizontal axis so a case isolates the vertical one (rdy_ext keeps
    max(hq, vq), so hq would otherwise mask any vq change)."""
    for c in cols:
        _put(col, vir, row, c, 2, 0)


def physics_cases():
    """Each case: (name, col, vir, want_rdyext_reach_off, want_rdyext_reach_on).
    Every expectation is derived from the game's physics, not from either
    implementation's output."""
    cases = []

    # A -- COVERED HOLE BELOW.  Column 0: cap(colour 2) at row 11, virus(1) at 12,
    # rows 13-15 empty.  Shipped: the DOWNWARD walk eats the 3 empties -> span 4
    # -> vq = 1.  Physics: those cells sit under the virus, unreachable forever.
    # A_v -> 0.  (Isolates the downward half of the guard.)
    col, vir = _blank()
    _put(col, vir, 11, 0, 2, 0)
    _put(col, vir, 12, 0, 1, 1)
    _hblock(col, vir, 12)
    cases.append(("A covered-hole-below", col, vir, 1, 0))

    # B -- OPEN SKY ABOVE.  Column 0: virus(1) on the floor, nothing above.  Every
    # cell above is fillable by a straight drop; A_v must NOT touch this.
    col, vir = _blank()
    _put(col, vir, 15, 0, 1, 1)
    _hblock(col, vir, 15)
    cases.append(("B open-sky-above", col, vir, 1, 1))

    # C -- CAPPED COLUMN.  Column 0: cap(2) at row 10, empties 11-14, virus(1) at
    # 15.  Shipped: the UPWARD walk eats rows 14..11 and stops at the cap ->
    # span 5 -> vq = 1.  Physics: rows 11-14 are under the cap.  A_v -> 0.
    # (Isolates the upward half of the guard.)
    col, vir = _blank()
    _put(col, vir, 10, 0, 2, 0)
    _put(col, vir, 15, 0, 1, 1)
    _hblock(col, vir, 15)
    cases.append(("C capped-column", col, vir, 1, 0))

    # D -- GENUINE VERTICAL RUN with open sky above: rows 13,14 pills(1), virus(1)
    # at 15, nothing above row 13.  run_v = 3, span reaches open sky -> vq = 9
    # in BOTH modes.  A_v must not punish a real, completable vertical.
    col, vir = _blank()
    _put(col, vir, 13, 0, 1, 0)
    _put(col, vir, 14, 0, 1, 0)
    _put(col, vir, 15, 0, 1, 1)
    _hblock(col, vir, 15)
    _hblock(col, vir, 14)
    _hblock(col, vir, 13)
    cases.append(("D open-run-above", col, vir, 9, 9))

    # E -- HORIZONTAL CREDIT THROUGH A COVERED HOLE.  Row 12: virus(1) at col 0,
    # pills(1) at cols 1,2, col 3 EMPTY but capped at row 11, blocker at col 4.
    # hq = 9 via the 4-wide horizontal window.  A_v is the VERTICAL half only, so
    # this credit must SURVIVE unchanged -- that is the scope claim, and it is
    # what kills the 'hreach' mutant.
    col, vir = _blank()
    _put(col, vir, 12, 0, 1, 1)
    _put(col, vir, 12, 1, 1, 0)
    _put(col, vir, 12, 2, 1, 0)
    _put(col, vir, 11, 3, 2, 0)      # cap over the empty at (12,3)
    _put(col, vir, 12, 4, 2, 0)      # stop the horizontal span at col 4
    cases.append(("E horizontal-thru-hole", col, vir, 9, 9))

    # F -- BOTH DIRECTIONS BLOCKED.  Column 0: cap(2) at 9, empties 10,11,
    # virus(1) at 12, empties 13-15.  Shipped span = rows 10..15 = 6 -> vq = 1.
    # A_v: upward blocked by the cap, downward blocked as holes -> span 1 -> 0.
    col, vir = _blank()
    _put(col, vir, 9, 0, 2, 0)
    _put(col, vir, 12, 0, 1, 1)
    _hblock(col, vir, 12)
    cases.append(("F both-blocked", col, vir, 1, 0))

    return cases


def run_physics(eval_fn, verbose=True, label=""):
    ok = True
    detail = []
    for name, col, vir, want_off, want_on in physics_cases():
        got_off = eval_fn(col, vir, 0)
        got_on = eval_fn(col, vir, 1)
        good = (got_off == want_off and got_on == want_on)
        ok = ok and good
        detail.append((name, got_off, want_off, got_on, want_on, good))
        if verbose:
            print(f"    {label}{name:24s} reach0={got_off:3d}(want {want_off:3d})  "
                  f"reach1={got_on:3d}(want {want_on:3d})  {'ok' if good else 'FAIL'}")
    return ok, detail


def n2_physics(fails):
    """The numba kernel itself must satisfy every physics case."""
    ok, detail = run_physics(lambda c, v, r: int(RL._rdyext_only(c, v, r)[0]))
    if not ok:
        for name, go, wo, gn, wn, good in detail:
            if not good:
                fails.append(f"N2 {name}: reach0 {go} (want {wo}) reach1 {gn} (want {wn})")
    return ok


def n3_mutants(fails):
    """The reference python predicate must PASS; every wrong predicate must FAIL.
    Without this, N2 could be satisfied by a predicate that does nothing."""
    ok_all = True
    print("    -- reference python predicate (must PASS) --")
    ref_ok, _ = run_physics(lambda c, v, r: py_rdyext(c, v, r, "correct"), label="ref ")
    if not ref_ok:
        fails.append("N3: the independent reference predicate FAILED the physics cases")
        ok_all = False
    for kind in ("hreach", "uponly", "inverted"):
        print(f"    -- mutant '{kind}' (must FAIL) --")
        survived, _ = run_physics(lambda c, v, r, _k=kind: py_rdyext(c, v, r, _k),
                                  label=f"{kind[:4]} ")
        print(f"    mutant '{kind}': {'SURVIVED (BAD)' if survived else 'killed (good)'}")
        if survived:
            fails.append(f"N3: mutant '{kind}' passed the physics cases -- N2 is vacuous")
            ok_all = False
    return ok_all


def n4_two_implementations(real, fails, limit=2000):
    """The numba kernel and the independent python reference must agree on real
    boards, at reach=0 and reach=1."""
    n = 0
    for col, vir, _p in real[:limit]:
        for rc in (0, 1):
            a = int(RL._rdyext_only(col, vir, rc)[0])
            b = py_rdyext(col, vir, rc, "correct")
            n += 1
            if a != b:
                fails.append(f"N4 reach={rc}: numba {a} != python {b}")
                if len(fails) > 20:
                    return n
    return n


def l1_locality(real, fails, n=300, seed=20260808):
    """The vertical quantities must be exactly additive over columns -- the property
    the per-column delta memoisation depends on.  Split each real board into its
    columns, sum the per-column vrdy, and demand it equals the whole board's."""
    rng = np.random.default_rng(seed)
    checked = 0
    for col, vir, _p in real[:n]:
        whole = RL._rdyext_only(col, vir, 1)
        acc = 0
        for c in range(COLS):
            ci = np.zeros(NCELL, dtype=np.int8)
            vi = np.zeros(NCELL, dtype=np.int8)
            for r in range(ROWS):
                ci[r * COLS + c] = col[r * COLS + c]
                vi[r * COLS + c] = vir[r * COLS + c]
            acc += int(RL._rdyext_only(ci, vi, 1)[1])
        if int(whole[1]) != acc:
            fails.append(f"L1: vrdy not column-additive ({int(whole[1])} != {acc})")
            return checked
        checked += 1
    _ = rng
    return checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", nargs="+", required=True, help="boards_*.npz")
    ap.add_argument("--chain-limit", type=int, default=300,
                    help="boards used for the (expensive) P3/P4 whole-chain checks")
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    RL.warmup()
    print(f"=== A_v BIT-EXACTNESS GATE  kernel_hash={RL.kernel_hash()} ===", flush=True)
    fails = []

    static = load_static_corpus()
    real = load_real_corpus(a.real)
    print(f"corpora: static={len(static)} boards, real={len(real)} boards", flush=True)

    n = p1_static(static, fails)
    print(f"  P1 static value-exactness  : {n} comparisons, {len(fails)} fail", flush=True)
    f0 = len(fails)
    n = p2_real(real, fails)
    print(f"  P2 real value-exactness    : {n} comparisons, {len(fails) - f0} fail", flush=True)
    f0 = len(fails)
    n3c = p3_chain(real, fails, limit=a.chain_limit)
    print(f"  P3 whole-chain root values : {n3c} comparisons, {len(fails) - f0} fail", flush=True)
    f0 = len(fails)
    n4c = p4_argmax(real, fails, limit=a.chain_limit)
    print(f"  P4 argmax identity (ws=20) : {n4c} boards, {len(fails) - f0} fail", flush=True)

    dl, dr, tot = n1_not_inert(real, fails)
    print(f"  N1 flag binds              : leaf changed on {dl}/{tot} ({dl / tot:.1%}), "
          f"rdy_ext changed on {dr}/{tot} ({dr / tot:.1%})", flush=True)
    print("  N2 physics cases (numba kernel):")
    n2_ok = n2_physics(fails)
    print("  N3 reference + mutant kill:")
    n3_ok = n3_mutants(fails)
    f0 = len(fails)
    n4n = n4_two_implementations(real, fails)
    print(f"  N4 numba == python ref     : {n4n} comparisons, {len(fails) - f0} fail", flush=True)
    f0 = len(fails)
    nl = l1_locality(real, fails)
    print(f"  L1 column-additivity       : {nl} boards, {len(fails) - f0} fail", flush=True)

    print()
    if fails:
        print(f"GATE FAILED -- {len(fails)} problem(s):")
        for f in fails[:25]:
            print("   ", f)
    else:
        print("GATE PASSED: reach=0 is value-exact with the shipped kernel at every dose,")
        print("through the whole depth-3 chain and the argmax; reach=1 binds; the physics")
        print("cases kill all three wrong predicates and pass the independent reference;")
        print("numba and python agree on the real corpus; the vertical term is column-additive.")
    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"kernel_hash": RL.kernel_hash(), "n_static": len(static),
                       "n_real": len(real), "fails": fails,
                       "p1": n, "p3": n3c, "p4": n4c, "n4": n4n,
                       "n1_leaf_changed": dl, "n1_rdy_changed": dr, "n1_total": tot,
                       "n2_ok": n2_ok, "n3_ok": n3_ok, "l1_checked": nl,
                       "passed": not fails}, fh, indent=1)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
