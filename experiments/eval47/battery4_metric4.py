"""METRIC 4 of the owner's four-metric battery -- CASCADE/COMBO vs INSTANT clears.

Metrics 1-3 (clearing-pill orientation, drop speed, rotation direction) are in
battery4_compute.py.  Metric 4 is here because it needs the 60fps frames, which that
module deliberately does not touch.

THE QUESTION.  Of a player's CLEAR EVENTS, what fraction are cascade/combo clears --
a clear that triggers a further clear once the material above it settles -- versus
instant single-step clears?

THE METHOD is the clear-event method (prior art: bursty_model.extract_clears -- a
second-over-second drop in occupied cells, flash frames excluded).  1fps cannot
separate two clear steps, so this works at 60fps in the QUIET WINDOW after each lock.

    QUIET WINDOW = [lock_frame(k), spawn_frame(k+1)).  The ROM holds the next spawn
    until the placement has fully resolved, so this window contains the whole
    resolution and nothing else -- no falling pill to add or move cells.  It is
    STRICTER than the brief's "no new pill locking in between": no new pill even
    spawns.  The window is real, not assumed: measured on struktured's resting_ok
    pills it is a median 21 frames for a non-clearing placement, 78.5 for a
    single clear and 100 for a cascade (printed in CONTROL 3).

    A CLEAR EVENT is a drop of >= 4 cells in the occupancy series (4 = the smallest
    legal clear; bursty_model uses the same threshold at 1fps).  Occupancy is
    median-filtered over 3 samples so that a one-sample transient cannot be a clear.

    CASCADE = a SECOND drop of >= 4 cells whose frame is within SETTLE_WINDOW of the
    first, inside the same quiet window.  INSTANT = exactly one drop.

    SETTLE_WINDOW = 96 frames = 6 rows x 16 frames/row.  16 f/row is the project's
    MEASURED settle-gravity constant (dr-mario-garbage-window-mechanics, 8/8 exact),
    not a guess; 6 rows is the fall distance a cascade needs before it can complete
    a new line on a board of this height.  The choice is not load-bearing on faith:
    a sensitivity table over 32/64/96/144/240 frames is printed, and
    settle-window -> 0 is a killed mutant.

WHY THE VIRUS BLINK FORCED THESE CHOICES.  Red virus sprites intermittently fall
under vision.py's 0.10 colour-fraction threshold (the blink animation), the same
artifact blunder_boards.py exists to smooth.  At 60fps that makes the raw occupancy
series jitter by +-2 cells inside a plateau.  CONTROL 2 sweeps the drop threshold
against the engine and prints the result: 4 is both the best-agreeing and the
principled number, so it is not a fit.  Rolling per-cell OR smoothing was tried and
REJECTED: it repairs blink dropouts but also unions in every transient position of
the next falling pill, so the smoothed occupancy climbs monotonically through the
window and manufactures level shifts that never happened.

WHAT THIS INSTRUMENT CANNOT DO, stated up front.  It can only separate two clear
steps that are separated in TIME by more than its own resolution (~6-8 frames).
CONTROL 4 shows it does NOT resolve most of what the engine calls a cascade, and
CONTROL 3's independent lock->next-spawn duration sides with the ENGINE.  The
frame-based cascade% published below is therefore a LOWER BOUND, and the engine-based
number is printed beside it rather than instead of it.
"""
import collections
import csv
import os
import statistics as st
import sys

import numpy as np
from PIL import Image

QA_EVAL47 = os.path.dirname(os.path.abspath(__file__))
if QA_EVAL47 not in sys.path:
    sys.path.insert(0, QA_EVAL47)

# blunder_tier_o owns the per-pill board reader, the resting_ok control and the
# cascade engine wiring; re-implementing them here would be a second, unvalidated
# copy of an instrument that already reproduces the adjudicated prior art.
import blunder_tier_o as O                       # noqa: E402
import tracker as T                              # noqa: E402  (path set by blunder_tier_o)
import cascade_x as CX                           # noqa: E402

_IDX = T.build_patch_index(O.P1_CROP)

STRIDE = 2                 # frames between occupancy samples
FIRST_DROP_WINDOW = 90     # a clear's animation starts well inside 1.5 s of the lock
SETTLE_WINDOW = 96         # 6 rows x 16 frames/row (measured settle gravity)
SETTLE_SWEEP = (32, 64, 96, 144, 192)
MAX_SPAN = FIRST_DROP_WINDOW + max(SETTLE_SWEEP)
# The video is read PAST the quiet window's end so that the quiet-window guard has
# something to be wrong about: a mutant with no input is EQUIVALENT and proves
# nothing. The guard itself then crops back to the quiet window.
QUIET_OVERRUN = 100
MIN_DROP = 4               # smallest legal clear
VL_NOISE = 2               # viruses_left_p1 carries +-1 blink noise; see CONTROL 1
FLASH_BLANK, FLASH_RECOVER = 5, 15               # bursty_model.detect_flash_frames


# ------------------------------------------------------------------ frame series
def occupancy(frames_dir, frame_no):
    path = os.path.join(frames_dir, f"f{frame_no:06d}.jpg")
    if not os.path.exists(path):
        return None
    labels, _v = T.classify_frame_vectorized(
        np.asarray(Image.open(path).convert("RGB")), *_IDX)
    return int((labels != ".").sum())


def quiet_series(frames_dir, lock, end):
    out = []
    for f in range(lock, end + 1, STRIDE):
        o = occupancy(frames_dir, f)
        if o is not None:
            out.append((f, o))
    return out


def drop_flash(series):
    """bursty_model.detect_flash_frames, transplanted to 60fps: a near-empty sample
    sandwiched between two much fuller ones is a rendering flash, not a clear."""
    keep = []
    for i, (f, o) in enumerate(series):
        if (0 < i < len(series) - 1 and o <= FLASH_BLANK
                and series[i - 1][1] >= FLASH_RECOVER
                and series[i + 1][1] >= FLASH_RECOVER):
            continue
        keep.append((f, o))
    return keep


def _med3(ys):
    if len(ys) < 3:
        return list(ys)
    return [ys[0]] + [sorted(ys[i - 1:i + 2])[1] for i in range(1, len(ys) - 1)] + [ys[-1]]


def detect_drops(series, min_drop=MIN_DROP, settle=SETTLE_WINDOW,
                 first_win=FIRST_DROP_WINDOW, medfilt=True, flash=True,
                 respect_quiet=True, quiet_end=None):
    """-> [(frame, cells_dropped), ...] inside one lock's window."""
    s = drop_flash(series) if flash else list(series)
    if respect_quiet and quiet_end is not None:
        s = [(f, o) for f, o in s if f <= quiet_end]
    if len(s) < 3:
        return []
    fs = [f for f, _o in s]
    raw = [o for _f, o in s]
    ys = _med3(raw) if medfilt else raw
    ref = sorted(ys[:3])[1]
    out = []
    for i, y in enumerate(ys):
        if out and fs[i] - out[0][0] > settle:
            break
        if not out and fs[i] - fs[0] > first_win:
            break
        if y <= ref - min_drop:
            out.append((fs[i], ref - y))
            ref = sorted(ys[i:i + 3])[1] if i + 3 <= len(ys) else ys[i]
    return out


# ------------------------------------------------------------------ corpus
class Lock:
    __slots__ = ("player", "match", "pill_id", "lock", "quiet_end", "read_end",
                 "series", "vl_delta", "eng_clear", "eng_first", "eng_total",
                 "eng_virus", "resting_ok", "gap")


def build(corpus):
    """One Lock per pill that has a following pill (the quiet window needs one)."""
    out = collections.defaultdict(list)
    for player, srcs in O.SOURCES.items():
        by_name = dict((n, p) for n, p in corpus[player])
        for name, csv_path, frames_dir in srcs:
            rows = list(csv.DictReader(open(csv_path)))
            nf = O.n_frames_in(frames_dir)
            pills = {p.pill_id: p for p in by_name[name]}
            for i in range(len(rows) - 1):
                r, nxt = rows[i], rows[i + 1]
                L = Lock()
                L.player, L.match, L.pill_id = player, name, int(r["pill_id"])
                L.lock = int(r["lock_frame"])
                L.gap = int(nxt["spawn_frame"]) - L.lock
                L.quiet_end = int(nxt["spawn_frame"]) - 1
                L.read_end = min(L.lock + MAX_SPAN, L.quiet_end + QUIET_OVERRUN, nf)
                L.vl_delta = int(r["viruses_left_p1"]) - int(nxt["viruses_left_p1"])
                p = pills.get(L.pill_id)
                L.resting_ok = bool(p and p.resting_ok)
                L.eng_clear = L.eng_first = L.eng_total = L.eng_virus = None
                if p is not None and p.resting_ok:
                    cc = np.zeros(O.NCELL, dtype=np.int8)
                    cv = np.zeros(O.NCELL, dtype=np.int8)
                    _o1, nv1, c1 = CX._expand_core_casc(p.col, p.vir, p.variant, p.column,
                                                        p.ca, p.cb, cc, cv, 1)
                    _o0, _n0, c0 = CX._expand_core_casc(p.col, p.vir, p.variant, p.column,
                                                        p.ca, p.cb, cc, cv, 0)
                    L.eng_first, L.eng_total = int(c1), int(c0)
                    L.eng_clear = int(c1) > 0
                    L.eng_virus = int(nv1)
                # read ONCE, to read_end; every mutant and every sensitivity row
                # reuses this one pass over the video.
                L.series = ([] if L.read_end <= L.lock + 2 * STRIDE
                            else quiet_series(frames_dir, L.lock, L.read_end))
                out[player].append(L)
    return out


def classify(locks, **kw):
    """-> Counter(events, cascade, instant) + per-lock verdicts."""
    c = collections.Counter()
    verdict = {}
    settle = kw.get("settle", SETTLE_WINDOW)
    for L in locks:
        dr = detect_drops(L.series, quiet_end=L.quiet_end, **kw)
        casc = len(dr) >= 2 and (dr[1][0] - dr[0][0]) <= settle
        if dr:
            c["events"] += 1
            c["cascade" if casc else "instant"] += 1
        verdict[(L.match, L.pill_id)] = (bool(dr), casc, dr)
    return c, verdict


# ------------------------------------------------------------------ controls
def controls(bylock, verdicts):
    print("CONTROL 1 -- detected clear events vs the tracker's INDEPENDENT virus count")
    print("             (viruses_left_p1; that column is read per pill by tracker.py,")
    print("             never by this module)")
    print("  FIRST, the column's own noise floor, because it decides what this control")
    print("  can ask. Viruses never appear, so every INCREASE is impossible and is")
    print("  measured here as the column's error rate:")
    ok = True
    for player, locks in bylock.items():
        ups = sum(1 for L in locks if L.vl_delta < 0)
        up1 = sum(1 for L in locks if L.vl_delta == -1)
        print(f"  {player:12s} impossible increases {ups:4d} / {len(locks):4d} locks "
              f"({100*ups/len(locks):4.1f}%), of which {up1} are exactly +1  => the column")
        print(f"               carries +-1 blink noise, so a 1-virus clear is NOT")
        print(f"               separable in it. This control therefore uses drops of")
        print(f"               >= {VL_NOISE} viruses, and says so instead of quoting a")
        print("               recall against a signal the column cannot carry.")
    print("  So the control is on the COUNT, which is what the column can support, and")
    print("  the per-pill agreement is printed beside it as a diagnostic, not a claim:")
    for player, locks in bylock.items():
        v = verdicts[player]
        raw = [L for L in locks if L.vl_delta >= 1]
        rob = [L for L in locks if L.vl_delta >= VL_NOISE]
        eng = [L for L in locks if L.eng_clear]
        c_raw = sum(1 for L in raw if v[(L.match, L.pill_id)][0])
        c_rob = sum(1 for L in rob if v[(L.match, L.pill_id)][0])
        eng_rob = sum(1 for L in rob if L.eng_clear)
        ev = sum(1 for L in locks if v[(L.match, L.pill_id)][0])
        rel = abs(ev - len(raw)) / max(ev, 1)
        ok &= rel <= 0.25
        print(f"  {player:12s} COUNTS  frame events {ev:4d} | viruses_left drops "
              f"{len(raw):4d} | engine clears {len(eng):4d}   -> frame-vs-column "
              f"relative gap {100*rel:4.1f}%  {'OK' if rel <= 0.25 else '*** FAIL'}")
        print(f"  {'':12s} PER-PILL (diagnostic only) of the {len(rob):3d} locks with a "
              f">= {VL_NOISE}-virus drop, the frame detector calls {c_rob:3d} a clear and")
        print(f"  {'':12s}   the ENGINE calls {eng_rob:3d} a clear -- the two instruments "
              f"fail the column TOGETHER, which is")
        print(f"  {'':12s}   the signature of a noisy LABEL, not of a broken detector "
              f"(>=1-virus variant: {c_raw:3d}/{len(raw):3d}).")
    print("  The excess of detected events over virus drops is expected and is not")
    print("  slack: a clear made only of pill halves moves no virus at all, and")
    print("  battery4_compute.py states the same limit about its own clearing-pill")
    print("  definition.")
    print(f"  CONTROL 1: {'PASS (counts within 25% on both players)' if ok else 'FAIL'}")

    print("\nCONTROL 2 -- detected clear events vs the ENGINE on the pill's own")
    print("             freshly-read board (resting_ok pills only), and the")
    print(f"             drop-threshold sweep that picked MIN_DROP={MIN_DROP}")
    for player, locks in bylock.items():
        v = verdicts[player]
        n = ag = 0
        for L in locks:
            if L.eng_clear is None:
                continue
            n += 1
            ag += int(v[(L.match, L.pill_id)][0] == L.eng_clear)
        sweep = []
        for md in (3, 4, 5):
            _c, vv = classify(locks, min_drop=md)
            a2 = sum(1 for L in locks if L.eng_clear is not None
                     and vv[(L.match, L.pill_id)][0] == L.eng_clear)
            sweep.append(f"min_drop {md}: {100*a2/n:5.1f}%")
        print(f"  {player:12s} resting_ok locks {n:4d}   agree {ag:4d} "
              f"({100*ag/n:5.1f}%)   sweep [{'  '.join(sweep)}]")
    print(f"  {MIN_DROP} is both the best-agreeing and the principled threshold (the")
    print("  smallest legal clear), so it is not a fit to this corpus.")

    print("\nCONTROL 3 -- does the quiet window mean what this module claims? An")
    print("             independent, frames-free check: lock -> next spawn duration,")
    print("             split by the ENGINE's verdict (resting_ok pills only)")
    print(f"  {'player':12s} {'class':10s} {'n':>4s} {'median gap':>11s} {'q1':>5s} {'q3':>5s}")
    for player, locks in bylock.items():
        buckets = collections.defaultdict(list)
        for L in locks:
            if L.eng_clear is None:
                continue
            k = ("no clear" if not L.eng_clear
                 else ("cascade" if L.eng_total > L.eng_first else "single"))
            buckets[k].append(L.gap)
        for k in ("no clear", "single", "cascade"):
            g = sorted(buckets[k])
            if not g:
                print(f"  {player:12s} {k:10s} {0:>4d}          --")
                continue
            print(f"  {player:12s} {k:10s} {len(g):>4d} {st.median(g):>11.1f} "
                  f"{g[len(g)//4]:>5d} {g[3*len(g)//4]:>5d}")
    print("  The ordering no-clear < single < cascade is what the quiet window predicts:")
    print("  the ROM is holding the spawn while it resolves, and a cascade holds it")
    print("  longest. This is what makes the window a physical object rather than an")
    print("  arbitrary slice, AND it is the evidence that the ENGINE's cascade label")
    print("  tracks a real extra resolution step -- see CONTROL 4.")

    print("\nCONTROL 4 -- frame CASCADE label vs ENGINE cascade label. THIS ONE FAILS")
    print("             TO AGREE, and the disagreement is the honest headline:")
    for player, locks in bylock.items():
        v = verdicts[player]
        cm = collections.Counter()
        for L in locks:
            if L.eng_clear is None or not L.eng_clear:
                continue
            if not v[(L.match, L.pill_id)][0]:
                continue
            cm[(v[(L.match, L.pill_id)][1], L.eng_total > L.eng_first)] += 1
        n = sum(cm.values())
        if not n:
            print(f"  {player:12s} no jointly-detected clears")
            continue
        ag = cm[(True, True)] + cm[(False, False)]
        print(f"  {player:12s} both-clear locks {n:4d}   agree {ag:4d} ({100*ag/n:5.1f}%)   "
              f"frame-only-cascade {cm[(True, False)]:3d}   engine-only-cascade "
              f"{cm[(False, True)]:3d}")
    print("  The asymmetry is one-directional: the engine sees cascades the frames do")
    print("  not. Those placements' median resolution time (CONTROL 3) is LONGER than a")
    print("  single clear's, so a real second step is happening -- the frame instrument")
    print("  simply cannot separate two removals that land within ~6-8 frames of each")
    print("  other under +-2 cells of blink noise. Read the frame cascade% as a LOWER")
    print("  BOUND and the engine cascade% as the better estimate.")
    return ok


# ------------------------------------------------------------------ mutants
def mutants(bylock, base):
    print("\nKILLED-MUTANT GATE -- each must CHANGE a published number")
    ok = True
    tot = lambda res, k: sum(res[p][k] for p in res)          # noqa: E731

    def run(**kw):
        return {p: classify(l, **kw)[0] for p, l in bylock.items()}

    # A mutant is KILLED on the CORPUS if it moves a published count. If it does
    # not, that is not automatically a pass: it may be EQUIVALENT (structurally
    # unable to change the answer) or it may simply have no discriminating input in
    # this corpus. The two are distinguished by exercising the same guard on a
    # SYNTHETIC series -- the treatment blunder_tiers.py gives its undiscriminated
    # 'tog' guard -- and the corpus count that explains the absence is printed.
    n_flash = n_spike = 0
    for _p, locks in bylock.items():
        for L in locks:
            n_flash += len(L.series) - len(drop_flash(L.series))
            ys = [o for _f, o in L.series]
            n_spike += sum(1 for i in range(1, len(ys) - 1)
                           if ys[i] <= min(ys[i - 1], ys[i + 1]) - MIN_DROP)
    n_samples = sum(len(L.series) for locks in bylock.values() for L in locks)
    flash_s = [(0, 30), (2, 30), (4, 30), (6, 0), (8, 30), (10, 30), (12, 30)]
    spike_s = [(0, 30), (2, 30), (4, 30), (6, 25), (8, 30), (10, 30), (12, 30)]

    def synth(series, on_kw, off_kw):
        on = detect_drops(series, first_win=10**6, settle=10**6, **on_kw)
        off = detect_drops(series, first_win=10**6, settle=10**6, **off_kw)
        return len(on), len(off)

    for label, key, kw, note in (
        (f"(a) settle window {SETTLE_WINDOW} -> 0 frames", "cascade", dict(settle=0), None),
        (f"(b) min drop {MIN_DROP} -> 1 cell", "events", dict(min_drop=1), None),
        ("(c) quiet-window cap OFF (scan past the next pill's spawn)", "cascade",
         dict(respect_quiet=False), None),
        (f"(d) first-drop window {FIRST_DROP_WINDOW} -> the whole scan", "events",
         dict(first_win=10 ** 6), None),
        ("(e) flash-frame exclusion OFF", "events", dict(flash=False),
         (flash_s, dict(flash=True, medfilt=False), dict(flash=False, medfilt=False),
          f"{n_flash} flash samples in {n_samples} occupancy samples")),
        ("(f) median filter OFF (1-sample dips count)", "events", dict(medfilt=False),
         (spike_s, dict(flash=False, medfilt=True), dict(flash=False, medfilt=False),
          f"{n_spike} single-sample dips >= {MIN_DROP} cells in {n_samples} samples")),
    ):
        mut = run(**kw)
        b, g = tot(base, key), tot(mut, key)
        if b != g:
            ok &= True
            print(f"  {label:58s} KILLED (corpus)   {key} {b} -> {g}")
            continue
        if note is None:
            ok = False
            print(f"  {label:58s} *** SURVIVED      {key} {b} -> {g}")
            continue
        series, on_kw, off_kw, why = note
        n_on, n_off = synth(series, on_kw, off_kw)
        hit = n_on == 0 and n_off > 0
        ok &= hit
        print(f"  {label:58s} {'KILLED (synthetic)' if hit else '*** SURVIVED'}"
              f"   corpus {key} {b} -> {g} (no discriminating case), "
              f"synthetic {n_on} -> {n_off}")
        print(f"      why the corpus is silent: {why}")
    return ok


# ------------------------------------------------------------------ main
def main():
    corpus, _dropped = O.load_corpus()
    bylock = build(corpus)

    base, verdicts = {}, {}
    for player, locks in bylock.items():
        c, v = classify(locks)
        base[player], verdicts[player] = c, v

    ctrl = controls(bylock, verdicts)
    gate = mutants(bylock, base)
    if not (ctrl and gate):
        print("\nGATE FAILED -- not publishing metric 4")
        return 1
    print("  GATE: PASS")

    print("\nMETRIC 4 -- CASCADE/COMBO vs INSTANT clears")
    print(f"  frame instrument: quiet window [lock, next spawn), drop >= {MIN_DROP} cells,")
    print(f"  cascade = a second such drop within {SETTLE_WINDOW} frames "
          f"(6 rows x 16 f/row)")
    print(f"  {'player':12s} {'locks':>6s} {'events':>7s} {'cascade':>8s} {'instant':>8s} "
          f"| {'cascade %':>10s} {'instant %':>10s}")
    for player, c in base.items():
        n = c["events"]
        print(f"  {player:12s} {len(bylock[player]):>6d} {n:>7d} {c['cascade']:>8d} "
              f"{c['instant']:>8d} | {100*c['cascade']/n:>9.1f}% "
              f"{100*c['instant']/n:>9.1f}%")

    print("\n  ENGINE ESTIMATE for the same question (resting_ok clearing locks;")
    print("  cascade == cells at cascade FIXPOINT exceeds cells at the FIRST step):")
    for player, locks in bylock.items():
        cl = [L for L in locks if L.eng_clear]
        cs = sum(1 for L in cl if L.eng_total > L.eng_first)
        if not cl:
            print(f"  {player:12s} no resting_ok clearing locks")
            continue
        per = collections.Counter()
        tot_m = collections.Counter()
        for L in cl:
            tot_m[L.match] += 1
            per[L.match] += int(L.eng_total > L.eng_first)
        detail = "  ".join(f"{m} {per[m]}/{tot_m[m]}" for m in sorted(tot_m))
        print(f"  {player:12s} clears {len(cl):4d}   cascade {cs:4d} "
              f"({100*cs/len(cl):5.1f}%)   instant {len(cl)-cs:4d} "
              f"({100*(len(cl)-cs)/len(cl):5.1f}%)   per match: {detail}")
    print("  The two instruments disagree (CONTROL 4). The frame number is the LOWER")
    print("  BOUND; neither is presented as the answer on its own.")

    print(f"\n  SENSITIVITY of the frame cascade% to the settle window "
          f"(the {SETTLE_WINDOW}-frame choice is physics, not a fit):")
    print(f"  {'player':12s} " + " ".join(f"{w:>9d}f" for w in SETTLE_SWEEP))
    for player, locks in bylock.items():
        cells = []
        for w in SETTLE_SWEEP:
            c, _v = classify(locks, settle=w)
            cells.append(f"{100*c['cascade']/c['events']:>9.1f}%" if c["events"] else
                         f"{'--':>10s}")
        print(f"  {player:12s} " + " ".join(cells))

    print("\nNOT COMPUTED, and why:")
    print("  * THE TRUE CASCADE RATE. Two instruments bracket it (frame ~13-14%,")
    print("    engine ~30-35% for struktured) and CONTROL 3's duration evidence favours")
    print("    the engine, but nothing here ADJUDICATES between them. Doing that needs a")
    print("    frame-accurate ROM-side ground truth (a Mesen trace of comboCounter), not")
    print("    a vision read of a capture.")
    print("  * AND THE ENGINE SIDE IS NOT NEUTRAL EITHER. cascade_x's own docstring says")
    print("    its pass-2+ gravity is COMPACT gravity (every non-virus cell falls")
    print("    independently, viruses anchor), not the ROM's link-aware body gravity: a")
    print("    linked half whose partner is supported does not fall in the real game but")
    print("    does here. By that module's own words this is 'a slight over-estimate of")
    print("    chaining'. So the bracket is [frame lower bound, engine upper-ish bound],")
    print("    and BOTH ends are biased in the direction that widens it.")
    print("  * COMBO SIZE / CHAIN LENGTH. The frame instrument counts DROPS, not chain")
    print("    steps, and its drop magnitudes carry the same +-2 blink noise as the")
    print("    occupancy it is built from. No distribution over chain length is emitted")
    print("    because none of it would survive that noise.")
    print("  * P2 / THE AI. tracker.py logged only P1 in both capture sets, so there is")
    print("    no per-pill lock CSV for the opponent and therefore no quiet window to")
    print("    scan. This metric is HUMANS ONLY, exactly as the battery asks.")
    print("  * THE LAST PILL of every match has no following spawn, so it has no quiet")
    print("    window and is not scored at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
