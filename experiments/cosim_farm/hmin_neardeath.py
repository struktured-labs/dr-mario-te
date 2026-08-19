#!/usr/bin/env python3
"""Does the garbage window ACTUALLY shrink near death?  (the near-death h_min table)

W = 264 - 16*h_min, where h_min is the stack height of the SHALLOWEST garbage-hit column.
The published claim -- "the window is shortest exactly where the AI dies" -- was measured on
FLAT synthetic stacks, where every column has the same height and h_min == h_max.  Real
near-death boards are narrow towers (gw-design: median 36% fill at stack 13-16).  This
measures h_min on the 125 REAL kill-game boards instead, and it is the measurement that
RETRACTED that claim.

VENDORED 2026-08-19 (task #137).  It previously existed only in a session scratchpad, and it
imported `garbage_columns` from `dr_mario_rl/tmp/vs_aware/vs_harness.py` -- a GITIGNORED tree.
A published table resting on a module unreachable from git is gate-standard rule 8 (the
reachability half), and its sibling rigs in that same scratchpad were ALREADY lost to a clean,
which is what killed the citation behind the flat-stack 8/8.

WHAT CHANGED FROM THE SCRATCHPAD ORIGINAL -- numerics are UNTOUCHED, and the gate below
proves it by reproducing the published medians:
  1. `garbage_columns` INLINED from the ROM contract (checkReleaseAttack $9C01, Rev 0) rather
     than imported.  That single import was the whole gitignored dependency.  The inlined form
     is byte-for-byte the same rule as `rom_attack_rule.garbage_columns`, constants included,
     and `selftest_garbage_columns()` re-derives it from the ROM's own tables.
     ⚠ Note the provenance correction: the task record said the import came FROM vs_harness.
     vs_harness only RE-EXPORTS it; the definition lives in rom_attack_rule.py, in the same
     gitignored tree.  Same hazard, one module further down -- worth stating exactly, because
     "I checked the file the ticket named" is how a wrong dependency survives an audit.
  2. Four hardcoded absolute paths replaced.  Three were sys.path pokes needed only to reach
     `transfer_check`, which now sits in THIS directory, so they are gone entirely rather than
     re-pointed.  The fourth (the corpus) is resolved by ordered search.
  3. The corpus is DATA, not code: absent, it exits 77 SKIPPED naming every path searched.
     Absence must never read as a pass.

⚠ THE FALLBACK HAZARD, inherited as a lesson not a bug.  `DRMARIO_HOSTDATA`, if set, is
AUTHORITATIVE -- if it does not exist this SKIPS rather than falling through to a different
corpus.  The sibling rig rom_gate_uneven_minmax.py acquired exactly that defect (commit
d513562) while fixing exactly this path-literal hazard: an ordered search treated the override
as merely one more candidate, so pointing it at a missing file silently measured a DIFFERENT
artifact and printed a confident PASS.  It was caught by a skip test, not by reading the code.

⚠ NOT SUBJECT TO THE #127 WORKTREE-SKEW WORRY, checked by reading the imports rather than
assuming: this rig imports only `nes_to_board` and `read_hostdata_full`, pulls in NO decider,
and computes h_min from board geometry via the locally-defined `col_heights`.  The near-death
numbers therefore cannot drift with champion code that happens to be on sys.path.

Run:  /home/struktured/projects/dr-mario-mods/.venv/bin/python hmin_neardeath.py
Gate: ... hmin_neardeath.py --gate       (reproduces the published table + kills 4 mutants)
Exit: 0 ok · 1 gate failed · 77 SKIPPED (corpus absent -- never a silent pass)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

FPS = 60.0988
RNG_SEED = 31          # the draw gate_neardeath.py itself used; changing it changes the table


class Skip(Exception):
    """Preconditions absent. Reported loudly with what was searched, never as a pass."""


# --------------------------------------------------------------- the ROM's column rule
# checkReleaseAttack ($9C01, Rev 0), transcribed from attackSize_{2,3,4}_{pos,gap}.
# Inlined so this rig has NO import out of a gitignored tree.  Identical to
# rom_attack_rule.garbage_columns, which is where the scratchpad version reached for it.
ATTACK_SIZE_MIN = 2
ATTACK_POS = {2: 0x03, 3: 0x03, 4: 0x01}     # frameCounter mask -> first column
ATTACK_GAP = {2: 0x03, 3: 0x01, 4: 0x01}     # stride is gap + 1


def garbage_columns(size, phase):
    """Row-0 columns that receive a garbage tile.  ★ size 2 can select {0,4}: columns 0
    and 4 are NOT immune.  size >= 4 all land in the 4-wide branch (cmp #$03 / bne)."""
    if size < ATTACK_SIZE_MIN:
        return []
    k = size if size in (2, 3) else 4
    start = phase & ATTACK_POS[k]
    stride = ATTACK_GAP[k] + 1
    return [start + i * stride for i in range(size)]


def selftest_garbage_columns():
    """Re-derive the rule from the ROM tables independently of the implementation above.

    This is not a restatement: it enumerates every (size, phase) the rig can draw and checks
    the column SET against the masks/strides read off the ROM, so a transcription slip in
    ATTACK_POS/ATTACK_GAP fails here rather than silently shifting the whole table."""
    expect = {}
    for phase in range(4):
        expect[(2, phase)] = [phase & 3, (phase & 3) + 4]
        expect[(3, phase)] = [(phase & 3) + 2 * i for i in range(3)]
        expect[(4, phase)] = [(phase & 1) + 2 * i for i in range(4)]
    bad = [(k, garbage_columns(*k), v) for k, v in expect.items() if garbage_columns(*k) != v]
    if bad:
        raise AssertionError(f"garbage_columns disagrees with the ROM contract: {bad[:3]}")
    if garbage_columns(1, 0) != []:
        raise AssertionError("size below attackSize_min must yield no columns")
    return len(expect)


# --------------------------------------------------------------- corpus resolution
# The 125-board kill corpus is DATA produced by the co-sim farm; it is not vendored (49 KB of
# host dumps that the farm regenerates).  Override with DRMARIO_HOSTDATA.
HOSTDATA_CANDIDATES = [
    os.path.join(HERE, "death_hostdata.txt"),
    "/mnt/data/drmario_cosim/gate/death_hostdata.txt",
]


def find_hostdata():
    """Locate the corpus.  DRMARIO_HOSTDATA, if set, is AUTHORITATIVE -- never a hint.

    ★ An explicit override that does not exist is an ERROR, not a reason to fall back.  See
    the module docstring: the sibling ROM gate acquired precisely this defect while fixing
    precisely this hazard, and reported a confident PASS against the wrong artifact."""
    env = os.environ.get("DRMARIO_HOSTDATA", "")
    if env:
        p = os.path.normpath(env)
        if not os.path.exists(p):
            raise Skip(f"DRMARIO_HOSTDATA={p} does not exist. Refusing to fall back to a "
                       "different corpus -- an explicit override is authoritative.")
        return p
    tried = []
    for p in HOSTDATA_CANDIDATES:
        p = os.path.normpath(p)
        tried.append(p)
        if os.path.exists(p):
            return p
    raise Skip("no death_hostdata.txt found. Searched, in order: " + "; ".join(tried)
               + ". Set DRMARIO_HOSTDATA, or regenerate it with the co-sim death gate.")


def load_decoder():
    """transfer_check is a sibling in this directory (repo-reachable).  Its own absolute
    sys.path literals are task #118 and are not touched here."""
    try:
        from transfer_check import nes_to_board, read_hostdata_full
    except Exception as e:                      # noqa: BLE001 -- report, never swallow
        raise Skip(f"cannot import the hostdata decoder from {HERE}/transfer_check.py: "
                   f"{type(e).__name__}: {e}")
    return nes_to_board, read_hostdata_full


# --------------------------------------------------------------- the measurement
def col_heights(b):
    """h_c = 16 - (topmost occupied row). Empty column -> 0."""
    hs = []
    for c in range(b.cols):
        top = next((r for r in range(b.rows) if b.color[r, c]), b.rows)
        hs.append(b.rows - top)
    return hs


def measure(mutant=None):
    """Returns the published table as a dict.  `mutant` names a deliberate defect.

    The mutants are not decoration -- each one is a plausible way to get this measurement
    wrong, and the gate requires every one of them to move the numbers.  A rig no mutation
    can disturb is not measuring what it claims to."""
    selftest_garbage_columns()
    nes_to_board, read_hostdata_full = load_decoder()
    path = find_hostdata()
    cases = read_hostdata_full(path)
    if not cases:
        raise Skip(f"{path} decoded to ZERO boards -- an empty corpus is not a measurement.")

    seed = 32 if mutant == "m_seed" else RNG_SEED
    rng = random.Random(seed)
    maxh, hmin, W = [], [], []
    for board, _cA, _cB, _nA, _nB in cases:
        b = nes_to_board(board)
        hs = col_heights(b)
        size, phase = rng.choice([2, 3, 4]), rng.randrange(4)
        if mutant == "m_allcols":
            hit = list(range(b.cols))                  # "the volley hits everywhere"
        elif mutant == "m_stride":
            k = size if size in (2, 3) else 4          # size-2 stride 2 instead of 4
            hit = [(phase & ATTACK_POS[k]) + i * 2 for i in range(size)]
            hit = [c for c in hit if 0 <= c < b.cols]
        else:
            hit = [c for c in garbage_columns(size, phase) if 0 <= c < b.cols]
        if not hit:
            raise Skip(f"no in-range hit columns for size={size} phase={phase}")
        h = max(hs[c] for c in hit) if mutant == "m_max" else min(hs[c] for c in hit)
        maxh.append(max(hs))
        hmin.append(h)
        W.append(264 - 16 * h)

    # worst (unluckiest) volley phase per board -- unaffected by the RNG draw
    worst = []
    for board, _cA, _cB, _nA, _nB in cases:
        b = nes_to_board(board)
        hs = col_heights(b)
        best_h = 0
        for size in (2, 3, 4):
            for phase in range(4):
                hit = [c for c in garbage_columns(size, phase) if 0 <= c < b.cols]
                best_h = max(best_h, min(hs[c] for c in hit))
        worst.append(264 - 16 * best_h)

    lo = sum(1 for w in W if w <= 56)
    return {
        "corpus": path,
        "corpus_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()[:16],
        "boards": len(cases),
        "maxh_median": statistics.median(maxh),
        "hmin_median": statistics.median(hmin),
        "hmin_min": min(hmin), "hmin_max": max(hmin),
        "W_median": statistics.median(W), "W_min": min(W), "W_max": max(W),
        "W_le56": lo, "W_le56_pct": lo / len(W) * 100.0,
        "worst_W_median": statistics.median(worst), "worst_W_min": min(worst),
    }


def report(r):
    print(f"boards: {r['boards']}   corpus: {r['corpus']}  sha256:{r['corpus_sha256']}")
    print("\n=== REAL near-death boards (matched to gate_neardeath's own RNG draw) ===")
    print(f"  tallest column   : median {r['maxh_median']:.0f}")
    print(f"  h_min (shallowest HIT column): median {r['hmin_median']:.0f}  "
          f"min {r['hmin_min']}  max {r['hmin_max']}")
    print(f"  WINDOW W=264-16*h_min : median {r['W_median']:.0f} f "
          f"({r['W_median']/FPS:.2f} s)   min {r['W_min']} f   max {r['W_max']} f")
    print(f"  boards with W <= 56 f (the 'near-death 0.93 s' figure): "
          f"{r['W_le56']}/{r['boards']} = {r['W_le56_pct']:.1f}%")
    print(f"\n  WORST volley phase per board: median W {r['worst_W_median']:.0f} f "
          f"({r['worst_W_median']/FPS:.2f} s)  min {r['worst_W_min']} f")
    print("\n=== for contrast: the published FLAT-stack cases ===")
    for h in (0, 6, 13, 15):
        print(f"  flat stack h={h:2d} -> W = {264-16*h:3d} f ({(264-16*h)/FPS:.2f} s)")


# --------------------------------------------------------------- gate
# The numbers this rig is cited for.  Reproducing them from a tree with tmp/ absent is the
# whole point of vendoring it.
PUBLISHED = {
    "boards": 125,
    "hmin_median": 4,
    "W_median": 200,
    "W_le56": 4,
    "maxh_median": 15,
    "worst_W_median": 136,
}
MUTANTS = ("m_max", "m_stride", "m_seed", "m_allcols")


def gate():
    n = selftest_garbage_columns()
    print(f"garbage_columns selftest: {n} (size,phase) pairs match the ROM contract\n")

    base = measure()
    report(base)
    print()

    ok = True
    for k, want in PUBLISHED.items():
        got = base[k]
        good = abs(got - want) < 1e-9
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'}  {k:16s} published {want:>6}  measured {got:>6}")
    if not ok:
        print("\nFAIL: the vendored rig does not reproduce the published near-death table.")

    # KILLED MUTANTS. Each must disturb at least one published figure. A mutant that leaves
    # the table intact means the table is insensitive to that axis -- which would make the
    # figure unearned, not the mutant harmless.
    print("\n=== killed mutants (each MUST move the published table) ===")
    killed = 0
    for m in MUTANTS:
        try:
            r = measure(mutant=m)
            diff = [k for k, want in PUBLISHED.items() if abs(r[k] - want) > 1e-9]
        except Skip as e:
            diff, r = [f"skipped: {e}"], None
        if diff:
            killed += 1
            shown = ", ".join(str(d) for d in diff[:4])
            print(f"  KILLED   {m:11s} moves: {shown}")
        else:
            print(f"  SURVIVED {m:11s} -- the table is blind to this axis")
            ok = False
    print(f"\n{killed}/{len(MUTANTS)} mutants killed")

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true",
                    help="reproduce the published table and run the mutant battery")
    ap.add_argument("--json", action="store_true", help="emit the measurement as JSON")
    ap.add_argument("--mutant", choices=MUTANTS, help="run one deliberate defect")
    a = ap.parse_args()
    try:
        if a.gate:
            return gate()
        r = measure(mutant=a.mutant)
        print(json.dumps(r, indent=2)) if a.json else report(r)
        return 0
    except Skip as e:
        # 77 = SKIPPED. Loud, names what was searched, and is NEVER a pass.
        print(f"SKIPPED (preconditions absent): {e}", file=sys.stderr)
        return 77


if __name__ == "__main__":
    sys.exit(main())
