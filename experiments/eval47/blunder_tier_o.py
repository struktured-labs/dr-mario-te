"""TIER O -- EVAPORATED OPPORTUNITY.  A big clear was on the board, was declined,
and then the player closed it off without ever cashing it.

THE CLASS (owner's words, followed literally):
    "available immediate clear OR settle-cascade of top-decile size; player took a
     non-clearing move; FLAG only if within 3 pills the opportunity was destroyed
     uncashed AND the alternative never cashed."

WHY IT IS NOT JUST "DECLINED A CLEAR".  struktured's 47.9% decline rate was
ADJUDICATED AS STYLE, not error (film_review_20260804/analysis/oversetup.md; the
tiering rationale is in blunder_tiers.py).  Declining is only a blunder if the
thing declined was (a) big and (b) subsequently thrown away.  Tier O is that
conjunction and nothing else: it fires on the SUBSET of declines that evaporate.

SIZE = SUMMED ACROSS CASCADE STEPS, per the ROM rule.
    Function used: cascade_x._expand_core_casc(pcol, pvir, variant, column, ca, cb,
    ccol, cvir, maxpass=0).  maxpass<=0 means resolve to FIXPOINT (that module's own
    docstring): targeted clear -> gravity -> full clear step -> ... until stable.
    Its `cells` return is the RUNNING SUM over every step (cascade_x._resolve_cascade
    does `cells += n2` per extra round).  That is the ROM-true accounting -- the
    comboCounter SUMS across cascade steps (dr-mario-rom-attack-rule).  "Size" counts
    ALL removed cells, virus and pill half alike, over ALL steps -- not viruses only,
    not the first step only.
    maxpass=1 is bit-identical to fast_rtl_x._expand_core (the instant, first-step
    rule the adjudicated prior art used); it is killed mutant (a).

TOP-DECILE.  One sample per pill = the MAXIMUM available cascade size over that
pill's 32 legal placements, taken over every resting_ok pill that has at least one
clearing placement, POOLED ACROSS BOTH PLAYERS (struktured's 4 matches + dr. lulu's
1 match).  Pooling is deliberate: a single threshold is what makes the two players'
Tier-O rates comparable at all.  The threshold is computed, printed, never hardcoded.
    HONEST NOTE ON THE ATOM: the size distribution is discrete and lumpy (a 4-cell
    line and its linked-half cascade land on a small set of totals).  The 90th
    percentile falls exactly ON a large atom, so ">= p90" selects rather more than a
    literal tenth of the corpus.  Both the threshold and the fraction of the corpus
    it actually admits are printed, so the reader can see the gap instead of trusting
    the word "decile".

DESTROYED UNCASHED.  Re-evaluated against each subsequent pill's OWN freshly-read
board -- never by simulating forward.  The film review proved forward simulation
compounds vision noise into >50%-of-pills landing-row disagreement
(analysis/oversetup.md "Method note"); per-pill fresh reads are the house method.
The opportunity's identity is its COLOUR PAIR: it is "this board is one (ca,cb) pill
away from a clear of at least T cells".  It is DESTROYED at pill k+j if no placement
of (ca,cb) on board(k+j) still reaches T, and UNCASHED if no clear happened over
pills k..k+j-1 (board(k+j) is read before pill k+j spawns, so it reflects exactly
the placements of pills k..k+j-1).

ALTERNATIVE NEVER CASHED.  Evaluated over the FULL window k..k+3, not merely up to
the destruction point.  That is what keeps the clause from being a tautology: if
destruction happens at j=1, pills k+2 and k+3 can still cash the line the player
switched to, and then it was a plan, not a blunder.  An "alternative" clause scoped
to the same k..k+j-1 span as "uncashed" would be an EQUIVALENT mutant -- structurally
unable to change any answer -- and would prove nothing.

DID A CLEAR HAPPEN?  Two independent instruments, and the detector is their
conservative UNION (any evidence of a clear counts as a clear, which can only remove
flags, never manufacture them):
    ENGINE     the pill's own chosen placement, run through the same cascade engine
               on the pill's own freshly-read board.  Only meaningful where the pill
               is resting_ok.
    OCCUPANCY  engine-free.  A pill adds exactly 2 cells and the smallest clear
               removes 4, so a NON-clearing pill must leave the next freshly-read
               board strictly fuller, and a clearing pill cannot.  Defined for every
               pill, resting_ok or not.
CONTROL 2 measures how far these two agree; that agreement is the honest bound on
how much the "uncashed" leg can be trusted.  Using the union is also what lets the
window keep pills that fail resting_ok: an earlier revision excluded any candidate
whose 3-pill window contained a non-resting_ok pill and lost a THIRD of the
candidates to an exclusion the occupancy instrument does not need.

A MUTANT DELIBERATELY NOT USED.  Swapping (ca,cb) -> (cb,ca) in the re-test looks
like a mutant and is EQUIVALENT: variants 0/1 (H a-first / b-first) and 2/3 (V a-top
/ b-top) already enumerate both colour orders, so the max over 32 placements is
invariant under the swap.  Killed mutant (e) rotates the colours (R->Y->B->R)
instead, which genuinely changes which structure is being asked about.

BOARDS.  vision.classify_cells on frame spawn_frame-5 of the player's own P1 60fps
clip with the crop-shifted P1 grid -- byte-for-byte the recipe of
scratch3/reconstruct2.py.  That is what makes CONTROL 1's reproduction of the
adjudicated 47.9% a real check rather than a restatement.
"""
import collections
import csv
import glob
import os
import re
import sys

import numpy as np

ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
FILM = os.path.join(ROOT, "tmp", "film_review_20260804")
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src",
           QA, QA + "/tuck_v3", QA + "/eval47", FILM):
    if _p not in sys.path:
        sys.path.append(_p)

from PIL import Image        # noqa: E402
import fast_sim_x as FS      # noqa: E402
import cascade_x as CX       # noqa: E402
import vision                # noqa: E402

EVAL47 = os.path.join(QA, "eval47")
LE = os.path.join(EVAL47, "results", "latency_events")
CROP_DX, CROP_DY = 392, 348
P1_CROP = dict(vision.P1, x0=vision.P1["x0"] - CROP_DX, y0=vision.P1["y0"] - CROP_DY)

ROWS, COLS, NCELL = 16, 8, 128
COLOR_ID = {"R": 1, "Y": 2, "B": 3}
ORIENT_VARIANT = {"H": 0, "HF": 1, "V": 2, "VF": 3}
PRE_SPAWN_MARGIN = 5

SOURCES = {
    "struktured": [(m, os.path.join(LE, "film_20260804", f"{m}.csv"),
                    os.path.join(FILM, "p1_60fps", m)) for m in ("m1", "m2", "m3", "m4")],
    "dr. lulu": [("m3", os.path.join(LE, "film_20260808", "p1_m3.csv"),
                  os.path.join(EVAL47, "tmp", "dr_lulu_20260808", "p1_60fps", "m3"))],
}

# Adjudicated prior art (analysis/oversetup.md) -- struktured only.
ADJUDICATED = dict(pills=330, resting_ok=297, available=213, declined=102, rate=47.9)

TOP_DECILE = 90.0
DESTROY_WINDOW = 3
ANY_CLEAR = 1.0                            # the reference band: any clear at all
COLOUR_ROT = {0: 0, 1: 2, 2: 3, 3: 1}      # mutant (e): R->Y->B->R


# ---------------------------------------------------------------- board reading
def n_frames_in(frames_dir):
    return len(glob.glob(os.path.join(frames_dir, "f*.jpg")))


def read_board(frames_dir, frame_idx):
    path = os.path.join(frames_dir, f"f{frame_idx:06d}.jpg")
    arr = np.asarray(Image.open(path).convert("RGB"))[..., :3].astype(int)
    colors, isvirus = vision.classify_cells(arr, P1_CROP)
    col = np.zeros(NCELL, dtype=np.int8)
    vir = np.zeros(NCELL, dtype=np.int8)
    for r in range(ROWS):
        for c in range(COLS):
            ch = colors[r][c]
            if ch == ".":
                continue
            col[r * COLS + c] = COLOR_ID[ch]
            vir[r * COLS + c] = 1 if isvirus[r][c] else 0
    return col, vir


def parse_cells(s):
    return [(int(a), int(b)) for a, b in re.findall(r"\((\d+),(\d+)\)", s)]


def drop_level_tail(rows):
    """m4 pill 137: viruses_left jumps to the NEXT level's board. Same running-min
    rule as reconstruct2.py / analysis/endgame.md."""
    running, kept, dropped = None, [], []
    for r in rows:
        v = int(r["viruses_left_p1"])
        if running is not None and v > running + 5:
            dropped.append(r)
            continue
        running = v if running is None else min(running, v)
        kept.append(r)
    return kept, dropped


# ---------------------------------------------------------------- the corpus
class Pill:
    __slots__ = ("player", "match", "pill_id", "spawn_frame", "lock_frame", "ca", "cb",
                 "variant", "column", "final_cells", "col", "vir", "resting_ok",
                 "tuck_like", "occ", "viruses_left", "_best", "_chosen")

    def best(self, ca, cb, maxpass):
        """-> (size, variant, column) of the biggest clear a (ca,cb) pill can make on
        THIS pill's board. (0, -1, -1) if none."""
        key = (ca, cb, maxpass)
        hit = self._best.get(key)
        if hit is None:
            ccol = np.zeros(NCELL, dtype=np.int8)
            cvir = np.zeros(NCELL, dtype=np.int8)
            size, bv, bc = 0, -1, -1
            for variant in range(4):
                for column in range(COLS):
                    ok, _nv, cells = CX._expand_core_casc(
                        self.col, self.vir, variant, column, ca, cb, ccol, cvir, maxpass)
                    if ok == 1 and cells > size:
                        size, bv, bc = int(cells), variant, column
            hit = (size, bv, bc)
            self._best[key] = hit
        return hit

    def chosen_size(self, maxpass):
        """Cells removed by the placement the player ACTUALLY made."""
        hit = self._chosen.get(maxpass)
        if hit is None:
            ccol = np.zeros(NCELL, dtype=np.int8)
            cvir = np.zeros(NCELL, dtype=np.int8)
            ok, _nv, cells = CX._expand_core_casc(self.col, self.vir, self.variant,
                                                  self.column, self.ca, self.cb,
                                                  ccol, cvir, maxpass)
            hit = int(cells) if ok == 1 else 0
            self._chosen[maxpass] = hit
        return hit


def load_match(player, name, csv_path, frames_dir):
    rows_all = list(csv.DictReader(open(csv_path)))
    rows, dropped = drop_level_tail(rows_all)
    nf = n_frames_in(frames_dir)
    pills = []
    for row in rows:
        p = Pill()
        p.player, p.match = player, name
        p.pill_id = int(row["pill_id"])
        p.spawn_frame = int(row["spawn_frame"])
        p.lock_frame = int(row["lock_frame"])
        ca_l, cb_l = row["colors"].split("-")
        p.ca, p.cb = COLOR_ID[ca_l], COLOR_ID[cb_l]
        p.final_cells = row["final_cells"]
        cells = parse_cells(row["final_cells"])
        p.variant = ORIENT_VARIANT[row["final_orient"]]
        p.column = min(c for _r, c in cells)
        p.viruses_left = int(row["viruses_left_p1"])
        fidx = min(max(1, p.spawn_frame - PRE_SPAWN_MARGIN), nf)
        p.col, p.vir = read_board(frames_dir, fidx)
        p.occ = int((p.col != 0).sum())
        ok_r, rr0, rc0, rr1, rc1 = FS._resting(p.col, p.variant, p.column)
        want = tuple(x for rc in sorted(cells) for x in rc)
        p.resting_ok = bool(int(ok_r) == 1
                            and (int(rr0), int(rc0), int(rr1), int(rc1)) == want)
        p.tuck_like = bool((not p.resting_ok) and int(ok_r) == 1
                           and (int(rr0) < want[0] or int(rr1) < want[2]))
        p._best, p._chosen = {}, {}
        pills.append(p)
    return pills, [int(r["pill_id"]) for r in dropped]


def load_corpus():
    corpus, dropped = {}, {}
    for player, srcs in SOURCES.items():
        corpus[player] = []
        for name, csv_path, frames_dir in srcs:
            pills, drp = load_match(player, name, csv_path, frames_dir)
            corpus[player].append((name, pills))
            dropped[(player, name)] = drp
    return corpus, dropped


def cleared_flags(pills, maxpass=1, use_engine=True, use_occ=True):
    """Conservative UNION clear detector, one bool per pill (see module docstring).
    The last pill of a match has no following board, so the occupancy leg cannot
    speak for it; the engine leg still can."""
    out = []
    for k, p in enumerate(pills):
        eng = use_engine and p.resting_ok and p.chosen_size(maxpass) > 0
        occ = (use_occ and k + 1 < len(pills)
               and (pills[k + 1].occ - p.occ) <= 0)
        out.append(bool(eng or occ))
    return out


# ---------------------------------------------------------------- control
def control_block(corpus, dropped):
    print("CONTROL 1 -- reconstruction fidelity (resting_ok: the engine's physics")
    print("             landing row == the tracker's own final_cells) and the")
    print("             adjudicated cross-check")
    ok = True
    for player, matches in corpus.items():
        tot = okc = 0
        for name, pills in matches:
            n = len(pills)
            k = sum(1 for p in pills if p.resting_ok)
            tck = sum(1 for p in pills if p.tuck_like)
            tot += n
            okc += k
            print(f"  {player[:10]:10s}/{name:3s} pills {n:4d}  resting_ok {k:4d} "
                  f"({100*k/n:5.1f}%)  tuck_like {tck:3d}  "
                  f"level-tail dropped {dropped[(player, name)]}")
        print(f"  {player[:10]:10s}/ALL pills {tot:4d}  resting_ok {okc:4d} "
              f"({100*okc/tot:5.1f}%)  -> {tot-okc} pills EXCLUDED from Tier O")

    st = corpus["struktured"]
    n_pills = sum(len(p) for _n, p in st)
    n_ok = sum(1 for _n, ps in st for p in ps if p.resting_ok)
    avail = decl = 0
    per_match = {}
    for name, pills in st:
        a = d = 0
        for p in pills:
            if not p.resting_ok:
                continue
            if p.best(p.ca, p.cb, 1)[0] > 0:       # INSTANT rule = the prior art
                a += 1
                d += int(p.chosen_size(1) == 0)
        per_match[name] = (a, d)
        avail += a
        decl += d
    rate = 100.0 * decl / avail if avail else float("nan")
    print("\n  ADJUDICATED CROSS-CHECK (analysis/oversetup.md; struktured, instant rule,")
    print("  over resting_ok pills, m4 pill 137 dropped by the running-min level-tail rule)")
    pub = {"m1": (64, 31), "m2": (30, 16), "m3": (32, 16), "m4": (87, 39)}
    for name, (a, d) in per_match.items():
        pa, pd = pub[name]
        hit = (a, d) == (pa, pd)
        ok &= hit
        print(f"    {name}: available {a:3d} (pub {pa:3d})  declined {d:3d} (pub {pd:3d})  "
              f"{100*d/a:5.1f}%  {'OK' if hit else '*** MISMATCH'}")
    for label, got, want in (("pills analysed", n_pills, ADJUDICATED["pills"]),
                             ("resting_ok", n_ok, ADJUDICATED["resting_ok"]),
                             ("available-clear opportunities", avail, ADJUDICATED["available"]),
                             ("declined", decl, ADJUDICATED["declined"])):
        hit = got == want
        ok &= hit
        print(f"    {label:32s} got {got:4d}  published {want:4d}  "
              f"{'OK' if hit else '*** MISMATCH'}")
    hit = abs(rate - ADJUDICATED["rate"]) < 0.05
    ok &= hit
    print(f"    {'decline rate':32s} got {rate:4.1f}%  published "
          f"{ADJUDICATED['rate']:4.1f}%  {'OK' if hit else '*** MISMATCH'}")
    verdict = ("PASS -- re-derived from the frames, reproduces the adjudicated set exactly"
               if ok else "FAIL")
    print(f"  CONTROL 1: {verdict}")

    print("\nCONTROL 2 -- the two legs of the clear detector, against each other")
    print("             (engine: chosen placement clears on its own board;")
    print("              occupancy: next freshly-read board is NOT fuller)")
    agree = tot = 0
    for player, matches in corpus.items():
        cm = collections.Counter()
        for _name, pills in matches:
            for k in range(len(pills) - 1):
                a, b = pills[k], pills[k + 1]
                if not (a.resting_ok and b.resting_ok):
                    continue
                cm[(a.chosen_size(1) > 0, (b.occ - a.occ) <= 0)] += 1
        n = sum(cm.values())
        ag = cm[(True, True)] + cm[(False, False)]
        agree += ag
        tot += n
        print(f"  {player[:10]:10s} resting_ok pairs {n:4d}   both say CLEAR "
              f"{cm[(True, True)]:3d}   both say NO-CLEAR {cm[(False, False)]:3d}   "
              f"engine-only {cm[(True, False)]:3d}   occupancy-only {cm[(False, True)]:3d}"
              f"   agree {100*ag/n:5.1f}%")
    print(f"  pooled agreement {100*agree/tot:.1f}% ({agree}/{tot}).  REPORTED, NOT GATED:")
    print("  the disagreements are vision miscounts (a cell or two per frame) and orphan")
    print("  halves falling after a clear, not proof either leg is wrong. Tier O takes")
    print("  the UNION, so every one of these disagreements REMOVES a candidate flag.")
    return ok


# ---------------------------------------------------------------- tier O
def size_threshold(corpus, maxpass, pct):
    """Per-pill BEST available cascade size, over resting_ok pills with >=1 clearing
    placement, pooled across both players. -> (threshold, sizes)."""
    sizes = []
    for _player, matches in corpus.items():
        for _name, pills in matches:
            for p in pills:
                if p.resting_ok and p.best(p.ca, p.cb, maxpass)[0] > 0:
                    sizes.append(p.best(p.ca, p.cb, maxpass)[0])
    return float(np.percentile(sizes, pct)), sizes


def analyse(corpus, thresh, maxpass=0, window=DESTROY_WINDOW, alt_clause=True,
            recolor=False, use_engine=True, use_occ=True):
    out, flags = {}, {}
    for player, matches in corpus.items():
        f = collections.Counter()
        fl = []
        for _name, pills in matches:
            cleared = cleared_flags(pills, 1, use_engine, use_occ)
            for k, p in enumerate(pills):
                f["pills"] += 1
                if not p.resting_ok:
                    f["excl_resting"] += 1
                    continue
                f["scored"] += 1
                size, bv, bc = p.best(p.ca, p.cb, maxpass)
                if size <= 0 or size < thresh:
                    continue
                f["opportunity"] += 1
                if p.chosen_size(maxpass) > 0:
                    f["cashed_now"] += 1
                    continue
                f["declined"] += 1
                if k + window >= len(pills):
                    f["window_short"] += 1
                    continue
                qa, qb = (COLOUR_ROT[p.ca], COLOUR_ROT[p.cb]) if recolor else (p.ca, p.cb)
                jstar = None
                for j in range(1, window + 1):
                    if pills[k + j].best(qa, qb, maxpass)[0] < thresh:
                        jstar = j
                        break
                if jstar is None:
                    f["survived"] += 1
                    continue
                if any(cleared[k + i] for i in range(jstar)):
                    f["cashed_before_destroyed"] += 1
                    continue
                f["destroyed_uncashed"] += 1
                if alt_clause and any(cleared[k + i] for i in range(window + 1)):
                    f["alt_cashed"] += 1
                    continue
                f["flagged"] += 1
                _cc = np.zeros(NCELL, dtype=np.int8)
                _cv = np.zeros(NCELL, dtype=np.int8)
                _ok, nvir, _cells = CX._expand_core_casc(p.col, p.vir, bv, bc,
                                                         p.ca, p.cb, _cc, _cv, maxpass)
                fl.append(dict(match=p.match, pill_id=p.pill_id, lock=p.lock_frame,
                               size=size, nvir=int(nvir), variant=bv, column=bc,
                               jstar=jstar, colors=f"{p.ca}-{p.cb}", took=p.final_cells,
                               orient=p.variant, viruses_left=p.viruses_left))
        out[player], flags[player] = f, fl
    return out, flags


def totals(res, key="flagged"):
    return sum(res[p][key] for p in res)


# ---------------------------------------------------------------- mutants
def mutants(corpus, t_dec, base_dec, base_any):
    """Every mutant must CHANGE a published number. The two PUBLISHED flag counts are
    the TOP-DECILE band and the ANY-CLEAR band; a mutant is KILLED if it moves either.
    Both deltas are printed for every mutant, so no mutant is scored on a number the
    report does not also publish."""
    print("\nKILLED-MUTANT GATE -- each must CHANGE a published number")
    b_dec, b_any = totals(base_dec), totals(base_any)
    ok = True

    t1, _s1 = size_threshold(corpus, 1, TOP_DECILE)
    rows = [
        ("(a) cascade size = FIRST STEP only (maxpass 0->1)",
         f"threshold {t_dec:.0f}->{t1:.0f} cells",
         analyse(corpus, t1, maxpass=1)[0],
         analyse(corpus, ANY_CLEAR, maxpass=1)[0]),
        ("(b) top-decile -> MEDIAN threshold",
         f"threshold {t_dec:.0f}->{size_threshold(corpus, 0, 50.0)[0]:.0f} cells",
         analyse(corpus, size_threshold(corpus, 0, 50.0)[0])[0],
         analyse(corpus, ANY_CLEAR)[0]),
        ("(c) destruction window 3 -> 0 pills", "window 3->0",
         analyse(corpus, t_dec, window=0)[0],
         analyse(corpus, ANY_CLEAR, window=0)[0]),
        ("(d) drop 'alternative never cashed'", "clause off",
         analyse(corpus, t_dec, alt_clause=False)[0],
         analyse(corpus, ANY_CLEAR, alt_clause=False)[0]),
        ("(e) re-test with ROTATED colours (R->Y->B->R)", "colours rotated",
         analyse(corpus, t_dec, recolor=True)[0],
         analyse(corpus, ANY_CLEAR, recolor=True)[0]),
        ("(f) clear detector: drop the OCCUPANCY leg", "engine leg only",
         analyse(corpus, t_dec, use_occ=False)[0],
         analyse(corpus, ANY_CLEAR, use_occ=False)[0]),
    ]
    for label, note, m_dec, m_any in rows:
        g_dec, g_any = totals(m_dec), totals(m_any)
        hit = (g_dec != b_dec) or (g_any != b_any)
        ok &= hit
        print(f"  {label:46s} {'KILLED' if hit else '*** SURVIVED (EQUIVALENT?)'}")
        print(f"      top-decile flags {b_dec:3d} -> {g_dec:<3d}   "
              f"any-clear flags {b_any:3d} -> {g_any:<3d}   [{note}]")
        if g_dec == b_dec:
            print("      (no movement on the top-decile band -- that band's n is small;")
            print("       killed on the any-clear band, which this report also publishes)")
    return ok


# ---------------------------------------------------------------- main
def main():
    corpus, dropped = load_corpus()
    ctrl = control_block(corpus, dropped)

    t_dec, sizes = size_threshold(corpus, 0, TOP_DECILE)
    base_dec, flags_dec = analyse(corpus, t_dec)
    base_any, flags_any = analyse(corpus, ANY_CLEAR)

    gate = mutants(corpus, t_dec, base_dec, base_any)
    if not (ctrl and gate):
        print("\nGATE FAILED -- not publishing Tier O rates")
        return 1
    print("  GATE: PASS")

    arr = np.array(sizes)
    hist = dict(sorted(collections.Counter(sizes).items()))
    print("\nTOP-DECILE THRESHOLD")
    print("  corpus: BOTH players pooled; one sample per resting_ok pill that has at")
    print("  least one clearing placement = that pill's best cascade-summed clear size")
    print(f"  n={len(sizes)}  size histogram {hist}")
    print(f"  p{TOP_DECILE:.0f} = {t_dec:.1f} cells  ->  admits {(arr >= t_dec).sum()}/"
          f"{len(arr)} = {100*(arr >= t_dec).mean():.1f}% of the corpus")
    print(f"  (the distribution has a {hist.get(int(t_dec), 0)}-sample ATOM at exactly "
          f"{t_dec:.0f} cells, so '>= p90' admits the top {100*(arr >= t_dec).mean():.0f}%,")
    print(f"   not a literal tenth; strictly-greater would admit "
          f"{100*(arr > t_dec).mean():.1f}%. Stated, not hidden.)")

    for title, base, band in (("TIER O -- EVAPORATED OPPORTUNITY (top-decile band, the "
                               f"owner's tier: >= {t_dec:.0f} cells)", base_dec, "dec"),
                              ("REFERENCE BAND -- same logic, ANY available clear "
                               "(>= 1 cell): the follow-up to the adjudicated 47.9%",
                               base_any, "any")):
        print(f"\n{title}")
        print(f"  {'player':12s} {'pills':>6s} {'scored':>7s} | {'oppty':>6s} "
              f"{'declined':>9s} {'destr+unc':>10s} {'FLAG':>5s} | {'flags/100':>10s}")
        for player, f in base.items():
            n = f["scored"]
            print(f"  {player:12s} {f['pills']:>6d} {n:>7d} | {f['opportunity']:>6d} "
                  f"{f['declined']:>9d} {f['destroyed_uncashed']:>10d} {f['flagged']:>5d} "
                  f"| {100*f['flagged']/n:>10.2f}")
        print("  funnel losses:")
        for player, f in base.items():
            print(f"    {player:12s} resting_ok-excluded {f['excl_resting']:3d} | "
                  f"cashed it immediately {f['cashed_now']:3d} | window short "
                  f"{f['window_short']:3d} | opportunity survived {DESTROY_WINDOW} pills "
                  f"{f['survived']:3d} | cashed before destroyed "
                  f"{f['cashed_before_destroyed']:3d} | alternative cashed "
                  f"{f['alt_cashed']:3d}")

    print("\nFLAGGED CASES (for eyeball confirmation)")
    for band, flags in (("top-decile", flags_dec), ("any-clear", flags_any)):
        for player, fl in flags.items():
            for d in fl[:6]:
                print(f"  [{band:10s}] {player:12s} {d['match']} pill {d['pill_id']:>3d}  "
                      f"lock f{d['lock']:<6d} colours {d['colors']}  DECLINED a "
                      f"{d['size']:2d}-cell clear ({d['nvir']} of them viruses) at "
                      f"variant {d['variant']} col {d['column']} -> took {d['took']}, "
                      f"destroyed +{d['jstar']} pills  (viruses_left "
                      f"{d['viruses_left']})")
    where = collections.Counter()
    for player, fl in flags_any.items():
        for d in fl:
            where[(player, d["match"], "viruses left" if d["viruses_left"] else
                   "NO viruses left")] += 1
    print(f"  WHERE THE FLAGS LAND (any-clear band): {dict(where)}")
    print("  Read this before reading the rate: every flag in this corpus sits in m4's")
    print("  virus-free tail, where the tracker and the vision read AGREE that 0 viruses")
    print("  remain and the player has no reason to hurry. Tier O as built cannot tell")
    print("  'threw away a win condition' from 'stopped caring after the level was won'.")
    print("  HAND-CHECK of the one top-decile flag (m4 pill 108, board f14666, colours")
    print("  R-B): columns 0 and 1 both top out at row 6, so an H pill lands at row 5;")
    print("  that completes B@r5-r8 in column 1 (4 cells), and the three column-0 reds")
    print("  then fall to the floor and complete a second 4-run -- 4+4 = 8 summed across")
    print("  the cascade. The player instead played VERTICALLY INTO COLUMN 1, raising it")
    print("  to row 4, which is exactly what destroys the landing slot one pill later.")

    n_fail = sum(1 for _p, ms in corpus.items() for _n, ps in ms
                 for p in ps if not p.resting_ok)
    n_tuck = sum(1 for _p, ms in corpus.items() for _n, ps in ms for p in ps if p.tuck_like)
    print("\nNOT COMPUTED, and why:")
    print("  * WHETHER THE PLAYER COULD SEE OR REACH IT. Tier O measures the board, not")
    print("    the person. Conversely a clear that needs a TUCK is invisible to the")
    print(f"    naive-physics _resting model: {n_tuck} of the {n_fail} pooled resting_ok")
    print("    failures are tuck_like, and tuck-reachable clears on a resting_ok pill's")
    print("    board are neither counted nor excludable with this instrument.")
    print("  * THE EXACT CASCADE SIZE. cascade_x's own docstring states that its pass-2+")
    print("    gravity is COMPACT gravity (every non-virus cell falls independently,")
    print("    viruses anchor), not the ROM's link-aware body gravity -- a linked half")
    print("    whose partner is supported does not fall in the real game but does here,")
    print("    which that module calls 'a slight over-estimate of chaining'. The")
    print("    threshold and every size printed above inherit that bias. It shifts the")
    print("    top-decile CUT, not the ranking, since every pill is measured the same way.")
    print("  * INTENT. 'Destroyed uncashed' does not separate blocking your own clear")
    print("    from being forced to -- spawn pressure, or a colour pair with no legal")
    print("    non-destroying placement. Ranking the alternatives needs a counterfactual")
    print("    search, which is the engine-adjudicated tier, not this one.")
    print(f"  * THE LAST {DESTROY_WINDOW} PILLS OF EVERY MATCH are unscorable (window")
    print("    short): the following pills do not exist, so the destruction test has no")
    print("    input. That is precisely where a topout blunder lives, so Tier O is BLIND")
    print("    to the end of a match and must not be read as an endgame metric.")
    print("  * SIGNIFICANCE. dr. lulu is ONE match (74 pills, 69 scored). Her per-100")
    print("    rate is a point estimate with no second window to check it against; the")
    print("    two players' rates here are NOT a test of any difference between them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
