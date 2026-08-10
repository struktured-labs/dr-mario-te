"""Shared board instrument for the blunder battery: per-pill boards + a VIRUS MAP.

WHY THIS EXISTS. Every seal/burial tier asks "which viruses are still alive, and
where". A single-frame vision read cannot answer that: red virus sprites intermittently
fall under vision.py's 0.10 colour-fraction threshold (blink animation), an artifact the
film review already had to hand-correct in eight cells in `recon/build_final.py`.
Measured here, the raw per-frame virus count misses the tracker's own `viruses_left_p1`
by >=1 on roughly half of every match's pills. A tier that fires on "this virus's last
route just closed" would inherit that noise as phantom seals.

WHAT FAILS, AND WHY THE OBVIOUS FIX ALSO FAILS. vision.py's virus test is a THRESHOLD on
the dark-pixel fraction of the cell's inner patch (`isvirus = dark_frac >= 0.12`),
calibrated 30/30 on hand-labelled cells from one frame. Voting that BOOLEAN across frames
does not repair the blink: on m4 the red at (13,2) -- a cell the film review's own seal
ledger names -- reads virus in only 9 of its 63 occupied samples and is REJECTED by any
majority rule. Its median dark fraction is 0.000.

THE FIX IS TO VOTE THE CONTINUOUS SCORE, NOT THE VERDICT. Averaged over the match, the
dark fraction separates cleanly and (13,2) comes back: pill halves score a mean of 0.000
(the calibration's own finding -- all 15 hand-labelled pills scored exactly zero), while
every known virus scores >= 0.138. (13,2) sits at 0.168 despite a zero median, because it
is BIMODAL, not dark: the mean survives the blink where the median and the majority vote
both destroy it. A virus never moves, never changes colour and never appears, so one
score per (cell, colour) for the whole match is the right shape for the estimate.

LIVENESS IS PER-PILL, NOT A TIMELINE. The obvious rule -- "live until the last board
that still shows the colour" -- was tried and REJECTED against measurement: on m4's
(13,2) the colour vanishes for runs of up to 20 consecutive pills and then reappears
after the cell is refilled by ordinary pill material, so no dropout tolerance can
separate a blink from a clear. Instead a site counts as live for a given pill only if
its own colour is actually READ THERE on that pill, unioned over WIDE_OFFSETS -- eight
samples spread over ~50 frames, far enough apart to catch different blink phases (that
union roughly doubles the detection rate of a blinking red: 27 -> 53 of m4's pills).
This direction of error is deliberate: a blink that survives all eight samples costs a
missed flag, never a phantom one, and precision is the whole design constraint.

THE CONTROL IS NOT A COUNT COMPARISON, AND THAT IS DELIBERATE. `viruses_left_p1` is not
an independent ground truth: tracker.py builds it as a majority vote of the SAME
`isvirus` boolean over a +-3 frame window (`count_viruses_smoothed`), and seven adjacent
frames is exactly the span the blink does not cross. Scoring a per-frame count against it
mostly scores an estimator against itself, which is why the naive per-frame count "wins"
that comparison. What the column does support is (a) its maximum -- the map must contain
at least that many virus sites -- and (b) the pill indices where its running minimum
DROPS, which is the timing a seal tier actually depends on. Both are gated. Its
impossible RISES (viruses cannot reappear inside a level) are printed as the reference's
own noise floor. The dark threshold was tuned on struktured's m1+m2 ONLY; m3, m4 and
dr. lulu's m3 are held out, and every seal label lives in m4.

BOARD CONVENTION matches the prior art (`scratch3/reconstruct2.py`): the board is read a
few frames BEFORE spawn (previous piece locked and resolved, this piece not yet on
screen), row-major idx = r*8 + c, row 0 = TOP, colours 1-based R/Y/B.
"""
import collections
import csv
import os
import re
import sys

import numpy as np
from PIL import Image

FILM = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804"
sys.path.insert(0, FILM)
from vision import P1          # noqa: E402
import tracker as T            # noqa: E402

QA = os.path.dirname(os.path.abspath(__file__))
LE = os.path.join(QA, "results", "latency_events")
CROP_DX, CROP_DY = 392, 348
P1_CROP = dict(P1, x0=P1["x0"] - CROP_DX, y0=P1["y0"] - CROP_DY)
_IDX = T.build_patch_index(P1_CROP)

ROWS, COLS, NCELL = 16, 8, 128
COLOR_ID = {".": 0, "R": 1, "Y": 2, "B": 3}
COLOR_CH = {0: ".", 1: "R", 2: "Y", 3: "B"}

PRE_SPAWN_OFFSETS = (3, 5, 7)   # three quiet frames before spawn -> the board itself
WIDE_OFFSETS = (3, 10, 17, 24, 31, 38, 45, 52)   # spread far enough to cross blink phases
DARK_MEAN_MIN = 0.12            # tuned on struktured m1+m2 only, m3/m4/lulu held out
MIN_READS = 2                   # a site must be seen occupied at least this often

SOURCES = {
    "struktured": [(m, os.path.join(LE, "film_20260804", f"{m}.csv"),
                    os.path.join(FILM, "p1_60fps", m)) for m in ("m1", "m2", "m3", "m4")],
    "dr. lulu": [("m3", os.path.join(LE, "film_20260808", "p1_m3.csv"),
                  os.path.join(QA, "tmp", "dr_lulu_20260808", "p1_60fps", "m3"))],
}

ORIENT_VARIANT = {"H": 0, "HF": 1, "V": 2, "VF": 3}


def idx(r, c):
    return r * COLS + c


def rc(i):
    return divmod(i, COLS)


def _classify(arr):
    """labels + isvirus from tracker (same instrument), plus the CONTINUOUS dark
    fraction that tracker thresholds away. Same patch index, one decode."""
    labels, isvirus = T.classify_frame_vectorized(arr, *_IDX)
    rows_idx, cols_idx = _IDX
    p = arr[rows_idx[:, None, :, None], cols_idx[None, :, None, :], :]
    r, g, b = (p[..., i].astype(int) for i in range(3))
    dark = ((r < 60) & (g < 60) & (b < 60)).sum(axis=(2, 3)) / (T.PATCH_H * T.PATCH_W)
    return labels, isvirus, dark


def _read_one(frames_dir, fno):
    path = os.path.join(frames_dir, f"f{fno:06d}.jpg")
    if not os.path.exists(path):
        return None
    return _classify(np.asarray(Image.open(path).convert("RGB")))


def read_board(frames_dir, spawn_frame, offsets=PRE_SPAWN_OFFSETS):
    """Per-cell majority colour over `offsets` quiet frames before spawn.

    -> (col[128], vir_raw[128], dark[128] mean over the reads that saw the winning
    colour, n_frames). vir_raw is tracker's own per-frame verdict, kept only so the
    mutant gate can show what voting the VERDICT instead of the SCORE would give.
    """
    reads = [x for x in (_read_one(frames_dir, max(1, spawn_frame - o)) for o in offsets)
             if x is not None]
    if not reads:
        return None, None, None, 0
    col = np.zeros(NCELL, dtype=np.int8)
    vraw = np.zeros(NCELL, dtype=np.int8)
    dark = np.zeros(NCELL, dtype=float)
    for r in range(ROWS):
        for c in range(COLS):
            cid = collections.Counter(
                COLOR_ID[lab[r, c]] for lab, _v, _d in reads).most_common(1)[0][0]
            i = idx(r, c)
            col[i] = cid
            if not cid:
                continue
            hits = [(v[r, c], d[r, c]) for lab, v, d in reads if COLOR_ID[lab[r, c]] == cid]
            vraw[i] = 1 if sum(1 for v, _d in hits) and sum(v for v, _d in hits) * 2 > len(reads) else 0
            dark[i] = float(np.mean([d for _v, d in hits]))
    return col, vraw, dark, len(reads)


def parse_cells(s):
    return [(int(a), int(b)) for a, b in re.findall(r"\((\d+),(\d+)\)", s)]


def placed_cells(row):
    """-> [((r,c), colour_id), ((r,c), colour_id)] for the pill as it locked.

    tracker's convention (reconstruct2.py): cell0/cell1 = left/top; H/V => cell0 is
    colourA, HF/VF => cell0 is colourB.
    """
    ca, _, cb = row["colors"].partition("-")
    cs = sorted(parse_cells(row["final_cells"]))
    if len(cs) != 2:
        return None
    first, second = (ca, cb) if row["final_orient"] in ("H", "V") else (cb, ca)
    return [(cs[0], COLOR_ID[first]), (cs[1], COLOR_ID[second])]


def drop_level_tail(rows):
    """The m4 pill-137 artifact: viruses_left jumps to the NEXT level's fresh board.
    Same running-min rule as analysis/endgame.md and reconstruct2.py."""
    running, kept, dropped = None, [], []
    for r in rows:
        v = int(r["viruses_left_p1"])
        if running is not None and v > running + 5:
            dropped.append(r)
            continue
        running = v if running is None else min(running, v)
        kept.append(r)
    return kept, dropped


class Match:
    """Per-pill boards plus the match's virus map."""

    def __init__(self, player, name, csv_path, frames_dir,
                 offsets=PRE_SPAWN_OFFSETS, wide=WIDE_OFFSETS, dark_min=DARK_MEAN_MIN,
                 min_reads=MIN_READS, vote_verdict=False):
        self.player, self.name, self.frames_dir = player, name, frames_dir
        rows = list(csv.DictReader(open(csv_path)))
        self.rows, self.dropped = drop_level_tail(rows)
        self.boards, self.darks, self.vraws, self.wide_seen = [], [], [], []
        for r in self.rows:
            sf = int(r["spawn_frame"])
            col, vraw, dark, _n = read_board(frames_dir, sf, offsets)
            self.boards.append(col)
            self.vraws.append(vraw)
            self.darks.append(dark)
            seen = collections.defaultdict(set)   # cell -> {colours read anywhere in the spread}
            for o in wide:
                got = _read_one(frames_dir, max(1, sf - o))
                if got is None:
                    continue
                lab = got[0]
                for rr in range(ROWS):
                    for cc in range(COLS):
                        cid = COLOR_ID[lab[rr, cc]]
                        if cid:
                            seen[idx(rr, cc)].add(cid)
            self.wide_seen.append(seen)
        self._build_virus_map(dark_min, min_reads, vote_verdict)
        self._clear_times()

    def _build_virus_map(self, dark_min, min_reads, vote_verdict):
        """Which CELLS host a virus, and of what colour. Says nothing about when."""
        scores = collections.defaultdict(list)
        for k, col in enumerate(self.boards):
            if col is None:
                continue
            for i in range(NCELL):
                if col[i]:
                    scores[(i, int(col[i]))].append(
                        float(self.vraws[k][i]) if vote_verdict else self.darks[k][i])
        self.virus_sites, self.rejected = {}, {}
        for (i, cid), vals in scores.items():
            mean = sum(vals) / len(vals)
            if len(vals) >= min_reads and mean >= dark_min:
                self.virus_sites[i] = cid
            else:
                self.rejected[(i, cid)] = (mean, len(vals))

    def _clear_times(self):
        """First pill at which a site's cell reads EMPTY across ALL wide samples.

        Monotone by construction, which is the point: a cleared cell is routinely
        refilled -- sometimes with the virus's own colour -- so "colour present" alone
        marks dead viruses live forever (measured: MAE 3.6 on m4 against the tracker's
        count, five times worse than this rule).
        """
        self.cleared_at = {}
        for i in self.virus_sites:
            self.cleared_at[i] = len(self.rows)
            for k, seen in enumerate(self.wide_seen):
                if not seen.get(i):
                    self.cleared_at[i] = k
                    break

    def live_viruses(self, k):
        """-> {cell_idx: colour_id} alive when pill k is about to be placed."""
        return {i: cid for i, cid in self.virus_sites.items() if k < self.cleared_at[i]}

    def raw_virus_count(self, k):
        return 0 if self.vraws[k] is None else int(self.vraws[k].sum())

    def control(self):
        """CIRCULARITY WARNING, and why the reference is the running MINIMUM.

        `viruses_left_p1` is not ground truth: tracker.py computes it as a majority
        vote of the SAME `isvirus` boolean over a +-3 frame window
        (`count_viruses_smoothed`). Seven adjacent frames is exactly the span the blink
        does NOT cross -- measured here, tight sampling finds a blinking red on 27 of
        m4's pills where samples spread over 50 frames find it on 53 -- so the column
        inherits the undercount it was meant to fix, and scoring a per-frame count
        against it mostly scores an estimator against itself.

        What the column DOES support: viruses can only be removed inside a level, so its
        running minimum is a denoised lower bound, and any RISE in it is impossible and
        measures the reference's own noise. Both are reported.
        """
        vl = [int(r["viruses_left_p1"]) for r in self.rows]
        rmin, running = [], None
        for v in vl:
            running = v if running is None else min(running, v)
            rmin.append(running)
        raw = [abs(self.raw_virus_count(k) - rmin[k]) for k in range(len(vl))]
        sm = [abs(len(self.live_viruses(k)) - rmin[k]) for k in range(len(vl))]
        n = len(vl)
        # The control that matters for a seal tier is EVENT TIMING, not the count:
        # when the map says a virus went away, did the reference drop there too?
        drops = [k for k in range(1, n) if rmin[k] < rmin[k - 1]]
        lags = [min((abs(k - d) for d in drops), default=None)
                for k in sorted(self.cleared_at.values()) if k < n]
        lags = [x for x in lags if x is not None]
        lags.sort()
        return dict(n=n, raw_mae=sum(raw) / n, sm_mae=sum(sm) / n,
                    raw_exact=sum(1 for e in raw if e == 0) / n,
                    sm_exact=sum(1 for e in sm if e == 0) / n,
                    n_sites=len(self.virus_sites), max_vl=max(vl),
                    impossible_rises=sum(1 for a, b in zip(vl, vl[1:]) if b > a),
                    n_clears=len(lags), lag_med=(lags[len(lags) // 2] if lags else None),
                    lag_within2=(sum(1 for x in lags if x <= 2) / len(lags)) if lags else None)


def load_all(sources=SOURCES, **kw):
    return {p: [Match(p, nm, cp, fd, **kw) for nm, cp, fd in srcs]
            for p, srcs in sources.items()}


def render(col, vir_cells, mark=()):
    out = []
    for r in range(ROWS):
        s = ""
        for c in range(COLS):
            i = idx(r, c)
            ch = COLOR_CH[int(col[i])]
            if i in vir_cells:
                ch = ch.lower()
            s += f"[{ch}]" if (r, c) in mark else ch
        out.append(f"r{r:2d} |{s}|")
    return out


def main():
    print("BOARD INSTRUMENT CONTROL -- virus map vs the tracker's virus column")
    print("  reference = RUNNING MIN of viruses_left_p1 (the column itself is the same")
    print("  blink-prone estimator; its rises are impossible and are counted below).")
    print("  dark threshold tuned on struktured m1+m2; m3/m4/dr. lulu are HELD OUT.")
    print(f"  {'match':16s} {'n':>4s} {'sites':>6s} {'maxvl':>6s} {'rises':>6s}  "
          f"{'map MAE':>8s} {'clr ev':>7s} {'lag med':>8s} {'lag<=2':>8s}")
    ok = True
    for player, ms in load_all().items():
        for m in ms:
            c = m.control()
            # sites must cover every virus the (undercounting) column ever saw, and
            # the map's clear events must land on the column's own drops
            good = c["n_sites"] >= c["max_vl"] - 1 and (c["lag_within2"] or 0) >= 0.60
            ok &= good
            print(f"  {player[:9]:9s}/{m.name:5s} {c['n']:>4d} {c['n_sites']:>6d} "
                  f"{c['max_vl']:>6d} {c['impossible_rises']:>6d}  "
                  f"{c['sm_mae']:>8.2f} {c['n_clears']:>7d} {c['lag_med']:>8} "
                  f"{c['lag_within2']:>8.1%}{'' if good else '   *** FAIL'}")
    print(f"  CONTROL: {'PASS' if ok else 'FAIL'}")
    print("  sites vs maxvl: the map must cover every virus the column ever saw, to")
    print("  within one site (struktured m3 is the single shortfall, 34 vs 35).")
    print("  lag: pills between a map clear event and the nearest drop in the column's")
    print("  running min -- the timing check a seal tier actually depends on.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
