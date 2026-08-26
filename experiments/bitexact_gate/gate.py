#!/usr/bin/env python3
"""BIT-EXACTNESS VALIDATION GATE for the Dr. Mario leaf eval kernel.

Reference chain this gate proves:
    candidate (delta-eval port / Rust)  ==  numba _eval_rtl (fast_rtl_x.py)
    numba _eval_rtl                     ==  live RTL (LeafEval.sv, Verilator)
so a candidate that passes is transitively bit-identical to silicon.

Commands
  corpus      build + PIN the board corpus (refuses to overwrite w/o --force)
  selfcheck   prove the gate itself: RTL parse, pyleaf==numba, leaf_r47 anchor,
              wrap-band coverage, mutant kill matrix (ALL mutants must die)
  candidate   level 1: a candidate leaf vs numba _eval_rtl over corpus x variants
              --py file.py:fn   in-process, fn(col int8[128], vir int8[128],
                                w float64[16], fl int32[3]) -> int
              --cmd 'prog'      subprocess, line protocol (see README)
  pairs       level 1b (delta-shaped candidates): (parent, placement) -> child sco
              --py file.py:fn   fn(pcol, pvir, variant, column, pa, pb, w, fl) -> int
              (fast_sim variant convention 0..3, pa/pb 1..3; NO-CLEAR pairs only)
  rtl         level 2: numba _eval_rtl vs the actual RTL via Verilator co-sim
              (parses LeafEval.sv for its baked weights; leaf + node + optional
               CMD6/7 delta cross-check)
              NOTE: its node oracle is COMPACT gravity. A link-aware engine will
              fail PHASE2 NODE on clearing placements BY DESIGN -- that is the
              lnk1 payload, not a defect. Use `linknode` for those.
  linknode    level 2b: link-aware node co-sim -- colour, virus AND LINK planes
              plus CHAIN depth, vs cascade_chain_x, on its own pinned corpus
              (linkcorpus.py). Includes its own mutant selfcheck.
  repro       replay one dumped failure case with full term breakdown

Verdict lines are machine-greppable:  GATE PASS ... / GATE FAIL ...
Exit codes: 0 pass, 1 fail, 2 configuration/parse error.
"""
from __future__ import annotations
import argparse
import itertools
import json
import os
import subprocess
import sys
import time

import numpy as np

from common import (HERE, COMBO_TERM, RTL_DEFAULT, QA_COPRO, NCELL, ROWS, COLS,
                    NRW, LEAF_W_IDX, LEAF_W_NAMES, make_w, make_fl,
                    nes_to_arrays, arrays_to_nes, board_hex, parse_board_hex,
                    virus_count, write_corpus, read_corpus, file_md5,
                    R_WVIR, R_WCELLS)
import pyleaf
import rtlparse

CORPUS = os.path.join(HERE, "corpus.txt")
RESULTS = os.path.join(HERE, "results")
BUILD = os.path.join(HERE, "build")

sys.path.insert(0, COMBO_TERM)
from fast_rtl_x import _eval_rtl, variant as named_variant          # noqa: E402
from fast_sim_x import _expand_core                                  # noqa: E402

_CANON_COPRO = "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro"


# ---------------------------------------------------------------- reference
def eval_ref(board, w, fl):
    col, vir = nes_to_arrays(board)
    return int(_eval_rtl(col, vir, w, fl))


def _ref_hash():
    """sha256 of the _eval_rtl SOURCE actually imported.  fast_rtl_x.py is being
    edited concurrently (delta-eval work lands in the same file), so level-1
    verdicts are only meaningful against the exact reference the RTL co-sim
    blessed -- this hash ties the two together."""
    import inspect, hashlib
    src = inspect.getsource(_eval_rtl.py_func)
    return hashlib.sha256(src.encode()).hexdigest()


BLESSING = os.path.join(RESULTS, "reference_blessing.json")


def check_blessing(require=True):
    h = _ref_hash()
    if not os.path.exists(BLESSING):
        print("WARN: reference _eval_rtl (sha %s) has NOT been RTL-blessed yet -- "
              "run gate.py rtl first; level-1 passes are provisional" % h[:16])
        return not require
    b = json.load(open(BLESSING))
    if b["eval_rtl_sha256"] != h:
        print("GATE FAIL: reference _eval_rtl source CHANGED since its RTL blessing\n"
              "  blessed %s (rtl %s @ %s)\n  current %s\n"
              "  -> re-run gate.py rtl to re-prove the reference against silicon RTL"
              % (b["eval_rtl_sha256"][:16], b["rtl_md5"][:8], b["when"], h[:16]))
        return False
    return True


# ---------------------------------------------------------------- variants
def variant_suite(rtl_path):
    """[(name, w, fl)] for level-1 candidate testing."""
    out = []
    for name in ("r47", "winner", "vrdy12", "weekend_burial", "combined", "cross8"):
        w, fl = named_variant(name)
        out.append((name, w, fl))
    try:
        p = rtlparse.parse_leafeval(rtl_path)
        out.append(("parsed_rtl", p["w"], p["fl"]))
    except rtlparse.RtlParseError as e:
        print("WARN: parsed_rtl variant unavailable: %s" % e)
    # single-term isolation: any term miscount fails EXACTLY one of these
    for nm in LEAF_W_NAMES:
        out.append(("iso_" + nm, make_w(**{nm: 7 if nm != "bias" else 1}), make_fl()))
    out.append(("iso_buried_noflags", make_w(buried=7), make_fl(0, 0, 1)))
    out.append(("iso_matched_floff", make_w(matched=7), make_fl(1, 1, 0)))
    # wrap stress: big coefficients force multi-wrap both signs on ordinary boards
    out.append(("wrapmax", make_w(bias=31337, maxh=997, holes=991, toprisk=983,
                                  spawn=977, setup=971, matched=967, buried=953,
                                  rdyext=947, vrdy=941, poll=937, cross=929), make_fl()))
    out.append(("negheavy", make_w(poll=4999, buried=4993, holes=4987), make_fl()))
    return out


# ---------------------------------------------------------------- candidates
def load_py_candidate(spec):
    path, fn = spec.rsplit(":", 1)
    import importlib.util
    spec_ = importlib.util.spec_from_file_location("gate_candidate", path)
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    return getattr(mod, fn)


def run_cmd_candidate(cmd, lines):
    """Subprocess protocol: one request line in, one integer line out."""
    proc = subprocess.run(cmd, shell=True, input="\n".join(lines) + "\n",
                          capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0:
        raise RuntimeError("candidate cmd failed rc=%d stderr=%s"
                           % (proc.returncode, proc.stderr[-2000:]))
    out = proc.stdout.split()
    if len(out) != len(lines):
        raise RuntimeError("candidate emitted %d values for %d cases"
                           % (len(out), len(lines)))
    return [int(x) for x in out]


def _req_line(w, fl, board, extra=None):
    toks = ["%d" % int(w[i]) for i in LEAF_W_IDX] + ["%d" % f for f in fl]
    if extra:
        toks += ["%d" % x for x in extra]
    return " ".join(toks) + " " + board_hex(board)


# ---------------------------------------------------------------- fail dumps
def dump_failure(tag, name, vname, w, fl, board, expected, got, extra=None):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "fail_%s_%s.txt" % (tag, name))
    t = pyleaf.terms(board, fl)
    with open(path, "w") as f:
        f.write("# bitexact_gate failure reproducer -- replay: gate.py repro %s\n" % path)
        f.write("variant %s\n" % vname)
        f.write("weights %s\n" % " ".join("%s=%d" % (n, int(w[i]))
                                          for n, i in zip(LEAF_W_NAMES, LEAF_W_IDX)))
        f.write("flags color_aware=%d nearest2=%d matched=%d\n" % tuple(fl))
        if extra:
            f.write("placement variant=%d column=%d pa=%d pb=%d\n" % tuple(extra))
        f.write("expected %d\n" % expected)
        f.write("got %d\n" % got)
        f.write("terms %s\n" % json.dumps(t))
        f.write("prewrap %d\n" % pyleaf.prewrap(t, w))
        f.write("board %s\n" % board_hex(board))
    return path


# ---------------------------------------------------------------- level 1
def gate_candidate(args):
    if not check_blessing(require=not args.unblessed):
        return 1
    boards, classes = read_corpus(CORPUS)
    suite = variant_suite(args.rtl)
    name = args.name or "candidate"
    print("level-1 gate: %d boards x %d weight variants = %d comparisons"
          % (len(boards), len(suite), len(boards) * len(suite)))

    if args.py:
        f = load_py_candidate(args.py)
        def scores_for(w, fl):
            out = []
            for b in boards:
                col, vir = nes_to_arrays(b)
                out.append(int(f(col, vir, w, fl)))
            return out
    elif args.cmd:
        def scores_for(w, fl):
            return run_cmd_candidate(args.cmd, [_req_line(w, fl, b) for b in boards])
    else:
        print("need --py or --cmd"); return 2

    t0 = time.time()
    per_class = {}
    for vname, w, fl in suite:
        got = scores_for(w, fl)
        for k, b in enumerate(boards):
            exp = eval_ref(b, w, fl)
            if got[k] != exp:
                path = dump_failure("cand", name, vname, w, fl, b, exp, got[k])
                print("GATE FAIL candidate=%s variant=%s case=%d class=%s "
                      "expected=%d got=%d\n  reproducer: %s"
                      % (name, vname, k, classes[k], exp, got[k], path))
                return 1
            per_class[classes[k]] = per_class.get(classes[k], 0) + 1
    dt = time.time() - t0
    print("GATE PASS candidate=%s cases=%d variants=%d (%.1fs)"
          % (name, len(boards), len(suite), dt))
    print("coverage by class (comparisons):")
    for k in sorted(per_class):
        print("  %-18s %d" % (k, per_class[k]))
    return 0


# ---------------------------------------------------------------- pairs (delta)
def _load_pairs(path):
    toks = open(path).read().split()
    n = int(toks[0]); toks = toks[1:]
    recs = []
    for k in range(n):
        r = toks[k * 266:(k + 1) * 266]
        board = [int(x, 16) for x in r[:128]]
        o4, colu, ca, cb, legal, cells, vir, imm, sco, win = [int(x) for x in r[128:138]]
        child = [int(x, 16) for x in r[138:266]]
        recs.append((board, o4, colu, ca, cb, legal, cells, vir, imm, sco, win, child))
    return recs


def gate_pairs(args):
    if not check_blessing(require=not args.unblessed):
        return 1
    path = os.path.join(HERE, "pairs_noclear.txt")
    recs = _load_pairs(path)
    # FULL level-1 variant suite (delta-eval's suggestion, 2026-07-30): the isolation
    # vectors self-attribute a delta that miscounts ONE term -- exactly the failure
    # mode a delta engine has and a full rescan doesn't. 3147 x 23 runs in ~1s.
    suite = variant_suite(args.rtl)
    name = args.name or "candidate"
    print("pairs gate (delta-shaped): %d no-clear pairs x %d variants"
          % (len(recs), len(suite)))
    if args.py:
        f = load_py_candidate(args.py)
    else:
        print("pairs mode: need --py"); return 2
    for vname, w, fl in suite:
        for k, (board, var, colu, ca, cb, legal, cells, vir, imm, sco, win, child) in enumerate(recs):
            pcol, pvir = nes_to_arrays(board)
            exp = eval_ref(child, w, fl)
            got = int(f(pcol, pvir, var, colu, ca + 1, cb + 1, w, fl))
            if got != exp:
                path = dump_failure("pairs", name, vname, w, fl, board, exp, got,
                                    extra=(var, colu, ca + 1, cb + 1))
                print("GATE FAIL pairs candidate=%s variant=%s case=%d "
                      "expected=%d got=%d\n  reproducer: %s"
                      % (name, vname, k, exp, got, path))
                return 1
    print("GATE PASS pairs candidate=%s cases=%d variants=%d"
          % (name, len(recs), len(suite)))
    return 0


# ---------------------------------------------------------------- o4 mapping
# Link high-nibbles, per linkcorpus.to_nes: {unlinked: 0x8, UP: 0x5, DOWN: 0x4,
# LEFT: 0x7, RIGHT: 0x6}. 0x8 and 0x4 are the two spellings this corpus uses for an
# UNLINKED pill cell; 0x5/0x6/0x7 are genuine pair links.
_TRUE_LINK_HI = (0x50, 0x60, 0x70)


def _norm_unlinked(board):
    """Collapse the two spellings of an unlinked pill cell (0x8x and 0x4x) onto one.

    `arrays_to_nes` renders every non-virus pill as 0x4x because the compact (col, vir)
    representation has no link plane to render from. The corpus spells the same cells
    0x8x. Both mean "unlinked pill of colour c" -- and the LEAF agrees, since it reads
    colour from the low nibble and virus from a 0xD0 high nibble, ignoring the rest. So
    the high nibble here carries no information the compact oracle is being tested on,
    and collapsing it compares the thing that actually differs: occupancy and colour.
    """
    return [x if (x == 0xFF or (x & 0xF0) == 0xD0) else (0x40 | (x & 0x0F))
            for x in board]


def _assert_no_true_links(recs):
    """Hard-stop if a record carries a REAL pair link (0x5x/0x6x/0x7x).

    That is the case where the compact oracle genuinely cannot represent the board, and
    normalising would paper over a real divergence rather than an encoding difference.
    This corpus has none (measured: parent high-nibbles are exactly {0x40, 0x80, 0xD0,
    0xF0}); `gate.py linknode` is the level that owns link-aware mechanics.
    """
    n = sum(1 for r in recs
            for b in (r[0], r[11])
            for x in b if (x & 0xF0) in _TRUE_LINK_HI)
    if n:
        raise RuntimeError(
            "%d cells carry a REAL pair link (0x5x/0x6x/0x7x) in the compact node corpus. "
            "_expand_core cannot represent those, and normalising the high nibble would "
            "hide a genuine mechanics divergence. Use gate.py linknode for link-aware "
            "mechanics, or regenerate this corpus without links." % n)


def recover_o4_map(verbose=False):
    """Empirically recover RTL a_o4 <-> fast_sim variant from the pinned node
    corpus (mechanics are eval-independent, so the old corpus is authoritative).

    ★ The corpus was regenerated at fd8e495 (R47 brain) from 250 cases to 436, and 169 of
    those spell unlinked pill cells 0x8x where `arrays_to_nes` renders 0x4x. Compared raw,
    NO permutation is perfect (best (2,3,0,1) at 162 bad) -- which reads as mechanics
    drift and is not: collapsing the two spellings makes (2,3,0,1) uniquely perfect across
    ALL 436, next best 151.

    ⚠ CORRECTION (2026-08-09). An earlier version of this function FILTERED those 169 out
    and justified it as "the compact oracle cannot represent the link plane". That reached
    the right map for the wrong reason: this corpus contains NO pair links at all (parent
    high-nibbles are exactly {0x40, 0x80, 0xD0, 0xF0}) and 0x8x means UNLINKED, not linked.
    The mismatch was never about links -- it was two spellings of the same unlinked cell.
    Filtering also threw away 39% of the evidence and narrowed the separation from 151 to
    70. Normalising uses every record and compares what actually differs; the true-link
    assertion below is what guards the case filtering was wrongly claiming to guard.
    """
    pinned = os.path.join(QA_COPRO, "leafeval_node_cases.txt")
    recs = _load_pairs(pinned)
    _assert_no_true_links(recs)
    if len(recs) < 100:
        raise RuntimeError(
            "only %d node cases -- too few to pin a 4-element o4 map." % len(recs))
    ccol = np.empty(NCELL, dtype=np.int8); cvir = np.empty(NCELL, dtype=np.int8)
    perfect = []
    for perm in itertools.permutations(range(4)):
        ok_all = True
        for (board, o4, colu, ca, cb, legal, cells, vir, imm, sco, win, child) in recs:
            pcol, pvir = nes_to_arrays(board)
            ok, nv, ncells = _expand_core(pcol, pvir, perm[o4], colu, ca + 1, cb + 1,
                                          ccol, cvir)
            if int(ok) != legal:
                ok_all = False; break
            # child is only defined when the placement is legal -- _expand_core leaves
            # ccol/cvir untouched otherwise, so comparing them on an illegal record reads
            # stale buffer contents and manufactures "occupancy differences" that are not
            # real. (Measured: all 7 records that looked like mechanics divergence were
            # legal=0.)
            if legal and (int(nv) != vir or int(ncells) != cells
                          or _norm_unlinked(arrays_to_nes(ccol, cvir))
                          != _norm_unlinked(child)):
                ok_all = False; break
        if ok_all:
            perfect.append(perm)
    if verbose:
        print("o4->variant maps reproducing all %d node cases (unlinked-spelling "
              "normalised): %s" % (len(recs), perfect))
    if not perfect:
        raise RuntimeError("NO o4->variant mapping reproduces the %d node cases "
                           "-- _expand_core mechanics differ from RTL; gate cannot "
                           "trust its pair oracles" % len(recs))
    if (0, 1, 2, 3) in perfect:
        return (0, 1, 2, 3), perfect
    if len(perfect) > 1:
        raise RuntimeError("ambiguous o4 maps %s -- need more pinned cases" % perfect)
    return perfect[0], perfect


# ---------------------------------------------------------------- corpus/pairs build
def build_all(args):
    import corpus as corpus_mod
    if os.path.exists(CORPUS) and not args.force:
        print("corpus already pinned at %s (use --force to rebuild)" % CORPUS); return 2
    boards, classes = corpus_mod.build_corpus()
    write_corpus(CORPUS, boards, classes)
    print("pinned %d boards -> %s" % (len(boards), CORPUS))

    # pairs: parents from mechanics-relevant classes, seeded placements
    o4map, _ = recover_o4_map(verbose=True)
    inv = [o4map.index(v) for v in range(4)]   # variant -> RTL o4
    p = rtlparse.parse_leafeval(args.rtl)
    iv, ic = p["meta"]["imm"] or (180, 10)
    rng = np.random.RandomState(20260730)
    keep = [i for i, c in enumerate(classes)
            if c.startswith("real_") or c in ("rand_settled", "cascade", "near_win",
                                              "buried_suite", "no_clear", "exact4")]
    ccol = np.empty(NCELL, dtype=np.int8); cvir = np.empty(NCELL, dtype=np.int8)
    node_lines, noclear_lines = [], []
    for i in keep:
        board = boards[i]
        pcol, pvir = nes_to_arrays(board)
        picks = rng.choice(32, size=6, replace=False)
        for a in picks:
            var, colu = int(a) // 8, int(a) % 8
            pa, pb = int(rng.randint(3)) + 1, int(rng.randint(3)) + 1
            ok, nv, cells = _expand_core(pcol, pvir, var, colu, pa, pb, ccol, cvir)
            if ok:
                child = arrays_to_nes(ccol, cvir)
                sco = int(_eval_rtl(ccol, cvir, p["w"], p["fl"]))
                win = 1 if virus_count(child) == 0 else 0
                imm = iv * int(nv) + ic * int(cells)
            else:
                child = board; sco = 0; win = 0; imm = 0; nv = 0; cells = 0
            rec = "%s %d %d %d %d %d %d %d %d %d %d %s" % (
                board_hex(board), inv[var], colu, pa - 1, pb - 1, int(ok),
                int(cells), int(nv), imm, sco, win, board_hex(child))
            node_lines.append(rec)
            if ok and cells == 0 and nv == 0:
                # pairs file keeps fast_sim variant convention (NOT RTL o4)
                noclear_lines.append("%s %d %d %d %d %d %d %d %d %d %d %s" % (
                    board_hex(board), var, colu, pa - 1, pb - 1, 1, 0, 0, imm,
                    sco, win, board_hex(child)))
    for path, lines in ((os.path.join(HERE, "node_cases.txt"), node_lines),
                        (os.path.join(HERE, "pairs_noclear.txt"), noclear_lines)):
        with open(path, "w") as f:
            f.write("%d\n" % len(lines))
            for l in lines:
                f.write(l + "\n")
        print("pinned %d records -> %s" % (len(lines), path))
    return 0


# ---------------------------------------------------------------- selfcheck
def selfcheck(args):
    boards, classes = read_corpus(CORPUS)
    print("== selfcheck on %d boards ==" % len(boards))
    rc = 0

    # 1. RTL parse (all live copies; the target one must parse)
    for path in (args.rtl, _CANON_COPRO + "/LeafEval.sv", QA_COPRO + "/LeafEval.sv"):
        try:
            p = rtlparse.parse_leafeval(path)
            print("parse OK  %s\n  md5=%s weights=%s flags=%s imm=%s delta=%s"
                  % (path, p["meta"]["md5"][:8], p["meta"]["weights"],
                     p["meta"]["flags"], p["meta"]["imm"],
                     p["meta"]["has_delta_engine"]))
        except (rtlparse.RtlParseError, FileNotFoundError) as e:
            print("parse %s: %s" % ("FAIL" if path == args.rtl else "note", e))
            if path == args.rtl:
                return 2

    suite = variant_suite(args.rtl)

    # 2. pyleaf (independent transcription) == numba reference, everywhere
    t0 = time.time(); bad = 0
    for vname, w, fl in suite:
        for k, b in enumerate(boards):
            if pyleaf.py_eval(b, w, fl) != eval_ref(b, w, fl):
                print("SELFCHECK FAIL pyleaf!=numba variant=%s case=%d class=%s"
                      % (vname, k, classes[k])); bad += 1; rc = 1
                if bad > 5: return 1
    print("pyleaf == numba _eval_rtl: %d x %d comparisons clean (%.1fs)"
          % (len(boards), len(suite), time.time() - t0))

    # 3. leaf_r47 anchor (the historically RTL-validated mirror, independent lineage)
    sys.path.insert(0, _CANON_COPRO)
    try:
        import leaf_r47
        anchors = [("r47", leaf_r47.leaf_r47), ("vrdy12", leaf_r47.leaf_vrdy12),
                   ("weekend_burial", leaf_r47.leaf_weekend_burial),
                   ("combined", leaf_r47.leaf_combined)]
        for vname, fn in anchors:
            w, fl = named_variant(vname)
            for k, b in enumerate(boards):
                sco, win = fn(b)
                if sco != eval_ref(b, w, fl) or win != (1 if virus_count(b) == 0 else 0):
                    print("SELFCHECK FAIL leaf_r47 anchor variant=%s case=%d class=%s"
                          % (vname, k, classes[k])); rc = 1
                    break
        print("leaf_r47 anchor (4 variants): clean")
    except ImportError as e:
        print("note: leaf_r47 anchor skipped (%s)" % e)

    # 4. wrap-band coverage at fixed-weight points (what level 2 can exercise)
    for vname in ("parsed_rtl", "winner", "r47"):
        w, fl = next((w, fl) for n, w, fl in suite if n == vname)
        bands = dict((k, 0) for k in ("neg_wrap", "in_range", "wrap1", "wrap2", "wrap3+"))
        for b in boards:
            pw = pyleaf.prewrap(pyleaf.terms(b, fl), w)
            if pw < -32768: bands["neg_wrap"] += 1
            elif pw <= 32767: bands["in_range"] += 1
            elif pw <= 98303: bands["wrap1"] += 1
            elif pw <= 163839: bands["wrap2"] += 1
            else: bands["wrap3+"] += 1
        print("wrap bands @%s: %s" % (vname, bands))
        if vname == "parsed_rtl" and bands["wrap1"] == 0:
            print("SELFCHECK FAIL: no wrap-exercising boards at the RTL weight point"); rc = 1

    # 5. mutant kill matrix: every known-subtle bug must fail the gate
    survivors = []
    for bug in pyleaf.ALL_BUGS:
        killed = None
        for vname, w, fl in suite:
            for k, b in enumerate(boards):
                if pyleaf.py_eval(b, w, fl, bug=bug) != eval_ref(b, w, fl):
                    killed = (vname, k, classes[k]); break
            if killed: break
        if killed:
            print("mutant %-18s KILLED by variant=%s case=%d (%s)"
                  % (bug, killed[0], killed[1], killed[2]))
        else:
            print("mutant %-18s SURVIVED -- corpus too weak!" % bug)
            survivors.append(bug); rc = 1

    # 6. o4 mapping + pair-oracle mechanics vs pinned RTL node corpus
    try:
        o4map, perfect = recover_o4_map(verbose=True)
        print("o4->variant map: %s (mechanics reproduce the pinned RTL node corpus)"
              % (o4map,))
    except RuntimeError as e:
        print("SELFCHECK FAIL: %s" % e); rc = 1

    print("GATE-SELFCHECK %s" % ("PASS" if rc == 0 else
          "FAIL (survivors: %s)" % survivors if survivors else "FAIL"))
    return rc


# ---------------------------------------------------------------- level 2 (RTL)
def gate_rtl(args):
    boards, classes = read_corpus(CORPUS)
    p = rtlparse.parse_leafeval(args.rtl)
    print("RTL co-sim vs %s\n  md5=%s weights=%s flags=%s"
          % (args.rtl, p["meta"]["md5"][:8], p["meta"]["weights"], p["meta"]["flags"]))

    os.makedirs(BUILD, exist_ok=True)
    # leaf cases at the PARSED weight point
    lc = os.path.join(BUILD, "leafeval_cases.txt")
    with open(lc, "w") as f:
        f.write("%d\n" % len(boards))
        for b in boards:
            win = 1 if virus_count(b) == 0 else 0
            f.write("%s %d %d\n" % (board_hex(b), eval_ref(b, p["w"], p["fl"]), win))
    # node cases: regenerate at the parsed weight point (RTL o4 convention)
    if not os.path.exists(os.path.join(HERE, "node_cases.txt")):
        print("node_cases.txt missing -- run gate.py corpus first"); return 2
    # mechanics (placement/legal/cells/child) are pinned; sco/imm/win are
    # RECOMPUTED at the parsed weight point so any LeafEval variant can be gated
    nc_src = _load_pairs(os.path.join(HERE, "node_cases.txt"))
    iv, ic = p["meta"]["imm"] or (180, 10)
    nc = os.path.join(BUILD, "node_cases.txt")
    with open(nc, "w") as f:
        f.write("%d\n" % len(nc_src))
        for (board, o4, colu, ca, cb, legal, cells, vir, imm, sco, win, child) in nc_src:
            if legal:
                imm = iv * vir + ic * cells
                sco = eval_ref(child, p["w"], p["fl"])
                win = 1 if virus_count(child) == 0 else 0
            f.write("%s %d %d %d %d %d %d %d %d %d %d %s\n" % (
                board_hex(board), o4, colu, ca, cb, legal, cells, vir, imm, sco,
                win, board_hex(child)))

    # build the tb against the TARGET .sv (never touching the source trees)
    rtl_dir = os.path.dirname(args.rtl)
    dpram = None
    if "dpram" in open(args.rtl).read():
        for cand in (os.path.join(rtl_dir, "dpram.v"),
                     os.path.join(rtl_dir, "..", "dpram.v"),
                     os.path.join(QA_COPRO, "dpram.v")):
            if os.path.exists(cand):
                dpram = cand; break
        if dpram is None:
            print("LeafEval instantiates dpram but no dpram.v found"); return 2
    srcs = [args.rtl] + ([dpram] if dpram else [])
    cflags = "-DHAS_DELTA" if p["meta"]["has_delta_engine"] else ""
    cmd = (["verilator", "--cc", "--exe", "--build", "-j", "2", "-O2", "-Wno-fatal",
            "--top-module", "LeafEval", "--Mdir", os.path.join(BUILD, "obj_leafeval"),
            "-o", "VLeafEvalGate"]
           + (["-CFLAGS", cflags] if cflags else [])
           + srcs + [os.path.join(HERE, "tb_leafeval_gate.cpp")])
    print("verilator build:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:]); print(r.stderr[-3000:])
        print("GATE FAIL rtl: verilator build failed"); return 1

    exe = os.path.join(BUILD, "obj_leafeval", "VLeafEvalGate")
    run = [exe, lc, nc] + (["delta"] if p["meta"]["has_delta_engine"] and not args.no_delta else [])
    print("running:", " ".join(run))
    r = subprocess.run(run, capture_output=True, text=True, cwd=BUILD, timeout=3600)
    print(r.stdout)
    if r.stderr.strip():
        print("stderr:", r.stderr[-1000:])
    os.makedirs(RESULTS, exist_ok=True)
    meta_out = dict(rtl=p["meta"], corpus_md5=file_md5(CORPUS),
                    fast_rtl_x_md5=file_md5(os.path.join(COMBO_TERM, "fast_rtl_x.py")),
                    n_leaf=len(boards), n_node=len(nc_src), rc=r.returncode)
    json.dump(meta_out, open(os.path.join(RESULTS, "rtl_run.json"), "w"), indent=2)
    if r.returncode == 0:
        json.dump(dict(eval_rtl_sha256=_ref_hash(), rtl_md5=p["meta"]["md5"],
                       rtl_path=args.rtl, when=time.strftime("%Y-%m-%d %H:%M:%S")),
                  open(BLESSING, "w"), indent=2)
        print("reference blessed: _eval_rtl sha %s <-> RTL md5 %s"
              % (_ref_hash()[:16], p["meta"]["md5"][:8]))
        print("GATE PASS rtl: numba _eval_rtl == LeafEval.sv (md5 %s) on %d leaf + %d node cases"
              % (p["meta"]["md5"][:8], len(boards), len(nc_src)))
        return 0
    print("GATE FAIL rtl: see mismatch lines above (board indices refer to corpus.txt)")
    return 1


# ---------------------------------------------------------------- repro
def repro(args):
    lines = dict()
    board = None
    for l in open(args.file):
        if l.startswith("#") or not l.strip():
            continue
        k, _, v = l.partition(" ")
        lines[k] = v.strip()
    w = make_w(**dict((kv.split("=")[0], int(kv.split("=")[1]))
                      for kv in lines["weights"].split()))
    fl = make_fl(*[int(kv.split("=")[1]) for kv in lines["flags"].split()])
    board = parse_board_hex(lines["board"])
    t = pyleaf.terms(board, fl)
    print("terms:", json.dumps(t))
    print("prewrap:", pyleaf.prewrap(t, w))
    print("reference _eval_rtl:", eval_ref(board, w, fl))
    print("pyleaf:", pyleaf.py_eval(board, w, fl))
    if "expected" in lines:
        print("dumped expected=%s got=%s" % (lines["expected"], lines["got"]))
    return 0


# ---------------------------------------------- level 2b: LINK-AWARE node co-sim
LINKCASES = os.path.join(HERE, "linknode_cases.txt")
LINK_BLESSING = os.path.join(RESULTS, "linknode_blessing.json")
# token offsets into a record:
#   128 parent | o4 col ca cb fix | legal cells vir chain imm sco win | 128 child
_LINK_FIELDS = {"legal": 133, "cells": 134, "vir": 135, "chain": 136,
                "imm": 137, "sco": 138, "win": 139}
_LINK_REC = 268


def _link_build(rtl_path, out_dir):
    """Verilate the target .sv with the link-aware node testbench."""
    rtl_dir = os.path.dirname(rtl_path)
    srcs = [rtl_path]
    if "dpram" in open(rtl_path).read():
        for cand in (os.path.join(rtl_dir, "dpram.v"),
                     os.path.join(rtl_dir, "..", "dpram.v"),
                     os.path.join(QA_COPRO, "dpram.v")):
            if os.path.exists(cand):
                srcs.append(cand); break
        else:
            return None, "LeafEval instantiates dpram but no dpram.v found"
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "2", "-O2", "-Wno-fatal",
           "--top-module", "LeafEval", "--Mdir", out_dir, "-o", "VLinkNodeGate"] \
          + srcs + [os.path.join(HERE, "tb_linknode_gate.cpp")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stdout[-2500:] + r.stderr[-2500:])
    return os.path.join(out_dir, "VLinkNodeGate"), None


def gate_linknode(args):
    """RTL vs the LINK-AWARE reference: colour, virus AND link planes, plus chain depth.

    The pinned compact corpus cannot do this job -- it stores no link nibbles (measured:
    its parent high-nibble histogram is exactly {4, 13, 15}) -- so this level has its own
    corpus, built from real self-play boards by linkcorpus.py, and its own blessing.
    node_cases.txt is left alone deliberately: other lanes' blessings are tied to its md5.
    """
    if not os.path.exists(LINKCASES):
        print("no pinned link corpus -- run: linkcorpus.py"); return 2
    if "blink" not in open(args.rtl).read():
        print("GATE FAIL linknode: %s has no link plane (`blink` absent) -- this level "
              "only applies to the link-aware engine" % args.rtl)
        return 1
    os.makedirs(BUILD, exist_ok=True)
    exe, err = _link_build(args.rtl, os.path.join(BUILD, "obj_linknode"))
    if exe is None:
        print(err); print("GATE FAIL linknode: verilator build failed"); return 1

    toks = open(LINKCASES).read().split()
    n = int(toks[0]); body = toks[1:]
    os.makedirs(RESULTS, exist_ok=True)
    # dose 0 is the identity arm (must reproduce lnk1/fixpoint-no-reward exactly); doses
    # 180 and 360 are the measured ones. The tb refuses a dose run over a chain-free
    # corpus, so a passing dose run cannot be vacuous.
    for chw, label in ((0, "dose 0 (identity)"), (45, "dose 180"), (90, "dose 360")):
        r = subprocess.run([exe, LINKCASES, str(chw)], capture_output=True, text=True,
                           timeout=7200)
        print("--- %s ---" % label)
        print(r.stdout)
        if r.stderr.strip():
            print("stderr:", r.stderr[-1000:])
        if r.returncode != 0:
            print("GATE FAIL linknode: RTL != cascade_chain_x reference at %s" % label)
            return 1

    # SELFCHECK: a gate that cannot fail proves nothing. Corrupt one field at a time in a
    # small slice and require the tb to notice EVERY one. `chain` and the LINK plane are
    # the fields this level exists for, so they get explicit mutants.
    import tempfile
    slice_n = min(400, n)
    rec0 = body[:slice_n * _LINK_REC]
    tgt = None
    for k in range(slice_n):                 # a legal, actually-clearing record
        if rec0[k * _LINK_REC + 133] == "1" and int(rec0[k * _LINK_REC + 134]) > 0:
            tgt = k; break
    if tgt is None:
        print("GATE FAIL linknode: no clearing record in the selfcheck slice"); return 1
    base = tgt * _LINK_REC
    muts = list(_LINK_FIELDS.items()) + [("child_colour", None), ("child_link", None)]
    killed, missed = 0, []
    for fname, off in muts:
        rec = list(rec0)
        if off is not None:
            rec[base + off] = str(int(rec[base + off]) + 1)
        elif fname == "child_colour":
            for j in range(128):             # blank the first occupied child cell
                if rec[base + 140 + j] != "ff":
                    rec[base + 140 + j] = "ff"; break
        else:                                # child_link: retag a linked half as an orphan
            for j in range(128):
                if rec[base + 140 + j][0] in "4567":
                    rec[base + 140 + j] = "8" + rec[base + 140 + j][1]; break
            else:
                missed.append(fname + " (no linked child cell)"); continue
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
            tf.write("%d\n" % slice_n)
            for k in range(slice_n):
                tf.write(" ".join(rec[k * _LINK_REC:(k + 1) * _LINK_REC]) + "\n")
            mpath = tf.name
        mr = subprocess.run([exe, mpath], capture_output=True, text=True, timeout=3600)
        os.unlink(mpath)
        if mr.returncode != 0:
            killed += 1
        else:
            missed.append(fname)
    print("linknode selfcheck: %d/%d mutants killed%s"
          % (killed, len(muts), "" if not missed else "   SURVIVORS: " + ", ".join(missed)))
    if missed:
        print("GATE FAIL linknode: mutants survived -- the comparison is not checking "
              "every field it claims to")
        return 1

    json.dump(dict(rtl_path=args.rtl, rtl_md5=file_md5(args.rtl),
                   corpus_md5=file_md5(LINKCASES), n_cases=n,
                   cascade_chain_x_md5=file_md5(os.path.join(COMBO_TERM,
                                                             "cascade_chain_x.py")),
                   cascade_link_x_md5=file_md5(os.path.join(COMBO_TERM,
                                                            "cascade_link_x.py")),
                   when=time.strftime("%Y-%m-%d %H:%M:%S")),
              open(LINK_BLESSING, "w"), indent=2)
    print("GATE PASS linknode: LeafEval.sv (md5 %s) == cascade_chain_x on %d cases, "
          "%d/%d mutants killed" % (file_md5(args.rtl)[:8], n, killed, len(muts)))
    return 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["corpus", "selfcheck", "candidate", "pairs",
                                     "rtl", "linknode", "repro"])
    ap.add_argument("--rtl", default=RTL_DEFAULT, help="LeafEval.sv to gate against")
    ap.add_argument("--py", help="candidate python file.py:fn")
    ap.add_argument("--cmd", help="candidate subprocess command")
    ap.add_argument("--name", help="candidate name for reports")
    ap.add_argument("--file", help="repro file")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-delta", action="store_true",
                    help="skip the CMD6/7 delta cross-check in rtl mode")
    ap.add_argument("--unblessed", action="store_true",
                    help="allow level-1 runs against a not-yet-RTL-blessed reference")
    args = ap.parse_args()
    if args.mode != "corpus" and not os.path.exists(CORPUS):
        print("no pinned corpus -- run: gate.py corpus"); return 2
    return {"corpus": build_all, "selfcheck": selfcheck, "candidate": gate_candidate,
            "pairs": gate_pairs, "rtl": gate_rtl, "linknode": gate_linknode,
            "repro": repro}[args.mode](args)


if __name__ == "__main__":
    sys.exit(main())
