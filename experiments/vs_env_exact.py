#!/usr/bin/env python3
"""Two-player VS environment with an EXACT garbage trigger.

Supersedes `vs_env.py`, whose `cells >= 7` proxy was audited on 2026-07-31 and found to be
wrong in two independent ways (`garbage_trigger_audit.py`, `proxy_offby2_check.py`):

  1. OFF-BY-2. It measured `nonzero(before_step) - nonzero(after_step)`, but `env.step`
     PLACES THE PILL (+2 cells) before resolving, so that delta is `cleared - 2` and the
     `>=7` test actually demanded 9 raw cleared cells. Measured `raw - delta == 2` on
     1105/1105 clearing placements. Consequence: 15 of 19 REAL double-line clears silent.
  2. CASCADE CONFLATION. `resolve()` loops clear -> gravity -> clear and reports only the
     TOTAL, so a 4-cell line that cascades into another 4-cell line looks like an 8-cell
     event. Correcting the threshold does not fix this: a raw `>=7` test still falsely
     fires on 122 single-line clears, 118 of which are chain=2 cascades.

Net on the original: 89.4% false-fire, 82.1% miss, over-firing by 68%. Every self-play
number taken through that trigger was scoring the wrong game.

THE FIX: count MAXIMAL RUNS >= 4 directly, at each clear step, via a per-INSTANCE hook on
`_find_clears`. "Simultaneous" then means "in the same clear step", which is what the rule
actually says.

THE RULE (MECHANICS_NES.md sec.5; the column set is flagged UNVERIFIED there):
  * 1 line                    -> 0 garbage
  * >= 2 lines SIMULTANEOUSLY -> 2 tiles
  * colours                   = the cleared runs' colours
  * columns from {1,5}/{2,6}/{3,7}; ★ columns 0 and 4 are IMMUNE

MECHANICS_NES also says "more lines = more garbage", which the flat 2 does not model. Real
3-line clears were measured at 0 occurrences in 1598 clearing placements, so the flat cap is
harmless AT L11 -- `attack_table` exists to re-test that if it ever stops being true.

SIMULTANEITY vs CASCADES is the one live modelling choice. `chain_mode`:
  "first"  (default) -- only the first clear step can attack. Strictly "simultaneous".
  "all"              -- every clear step is scored. Models combos also sending.
Both are run in the sensitivity check; conclusions are only reported if they hold in both.
"""
from __future__ import annotations
import sys, random

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/.claude/worktrees/faithful-sim/src", ROOT + "/tmp/pillrng"):
    if p not in sys.path:
        sys.path.insert(0, p)

GARBAGE_PAIRS = ((1, 5), (2, 6), (3, 7))     # columns 0 and 4 are immune
EMPTY = 0


def count_runs(color):
    """(n_runs, colours) for maximal runs of >= 4 same-colour cells, H then V.

    Mirrors `FaithfulBoard._find_clears` scan order. Counts RUNS, not cells -- the clear
    mask loses run structure, and run structure is exactly what the garbage rule keys on.
    """
    rows, cols = color.shape
    n = 0
    cols_seen = []
    for r in range(rows):
        c = 0
        while c < cols:
            v = color[r, c]
            if v == EMPTY:
                c += 1
                continue
            c2 = c
            while c2 < cols and color[r, c2] == v:
                c2 += 1
            if c2 - c >= 4:
                n += 1
                cols_seen.append(int(v))
            c = c2
    for c in range(cols):
        r = 0
        while r < rows:
            v = color[r, c]
            if v == EMPTY:
                r += 1
                continue
            r2 = r
            while r2 < rows and color[r2, c] == v:
                r2 += 1
            if r2 - r >= 4:
                n += 1
                cols_seen.append(int(v))
            r = r2
    return n, cols_seen


class ClearTrace:
    """Per-INSTANCE hook on board._find_clears. Never touches the shared class."""

    def __init__(self, board):
        self.board = board
        self.steps = []                       # [(n_lines, [colours]), ...] per clear step
        self._orig = board._find_clears
        board._find_clears = self._hook

    def _hook(self):
        n, cols = count_runs(self.board.color)
        mask = self._orig()
        if mask.any():
            self.steps.append((n, cols))
        return mask

    def reset(self):
        self.steps = []


def attack_table(lines):
    """Garbage tiles sent for `lines` simultaneous lines. The spec'd rule, flat at 2."""
    return 2 if lines >= 2 else 0


class VsMatch:
    """Two FaithfulDrMarioEnv boards exchanging garbage. Deciders are callables
    (board, cur, nxt) -> action, exactly like the solo deciders.

    Both players SHARE the seed's capsule sequence (as the ROM does) but get DIFFERENT
    virus layouts (env seeds seed+0 / seed+1000, also as the ROM does -- the layouts come
    off the same RNG stream sequentially). Board luck is therefore the dominant variance
    term, which is why every comparison must be played from BOTH SIDES and paired by seed.
    """

    def __init__(self, seed, level=11, max_pills=300, nes_pills=True, chain_mode="first",
                 garbage=True):
        from drmario.faithful_env import FaithfulDrMarioEnv
        self.rng = random.Random(seed * 6151 + 7)
        self.chain_mode = chain_mode
        self.garbage = garbage
        self.env = []
        self.trace = []
        for k in range(2):
            e = FaithfulDrMarioEnv(level=level, seed=seed + 1000 * k, max_pills=max_pills)
            e.reset()
            if nes_pills:
                from nes_pills import NesPillSource
                NesPillSource(seed=seed).attach(e)
                e.cur = e._rand_pill(); e.nxt = e._rand_pill()
            self.env.append(e)
            self.trace.append(ClearTrace(e.board))
        self.pending = [[], []]
        self.pills = [0, 0]
        self.attacks_sent = [0, 0]            # attack EVENTS, not tiles

    def _drop_garbage(self, who, colours):
        """Insert 2 tiles at row 0 in one immune-safe column pair, then settle.

        ⚠ THE _apply_gravity() CALL IS LOAD-BEARING. `resolve()` is
            while True:
                mask = self._find_clears()
                if mask.sum() == 0: break     # <-- exits BEFORE any gravity
                ...; self._apply_gravity()
        i.e. gravity runs ONLY after a clear. Freshly dropped garbage almost
        never completes a line, so `resolve()` alone left the tiles FLOATING AT
        ROW 0 over empty space. Since `spawn_blocked()` is
        `any(color[0, c] for c in (3, 4))` and GARBAGE_PAIRS contains column 3,
        one third of all deliveries topped the receiver out INSTANTLY — on any
        board, at any height, with any number of legal moves available.
        Measured before the fix: one delivery onto a HEALTHY FRESH board ended
        the game 19/60 = 31.7% of the time. Every VS kill rate taken through
        this harness before 2026-08-06 is contaminated by that coin flip.
        Regression test: experiments/holepoker/test_garbage_gravity.py
        """
        b = self.env[who].board
        c1, c2 = self.rng.choice(GARBAGE_PAIRS)
        for c, col in ((c1, colours[0]), (c2, colours[-1])):
            if b.color[0, c] == EMPTY:        # column already full to the top
                b.color[0, c] = col
                b.link[0, c] = 0              # garbage is unlinked; falls as a single cell
                b.is_virus[0, c] = False
        b._apply_gravity()                    # tiles FALL to the stack, as on hardware
        b.resolve()                           # then honour any clears they complete

    def step(self, who, action):
        """Advance one player by one placement. Returns (done, result)."""
        e = self.env[who]
        tr = self.trace[who]
        tr.reset()
        _, _, term, trunc, info = e.step(int(action))
        self.pills[who] += 1

        steps = tr.steps if self.chain_mode == "all" else tr.steps[:1]
        for n_lines, colours in steps:
            tiles = attack_table(n_lines)
            if tiles:
                self.attacks_sent[who] += 1
                if self.garbage:
                    self.pending[1 - who].append(colours)

        if term:
            return True, ("clear" if info.get("won") else "topout")
        if trunc:
            return True, "stall"
        return False, None

    def deliver(self, who):
        """Apply garbage queued for `who` (called between their placements)."""
        n = 0
        while self.pending[who]:
            self._drop_garbage(who, self.pending[who].pop(0))
            n += 1
        return n


def play_match(seed, dec0, dec1, level=11, max_pills=300, nes_pills=True, chain_mode="first",
               garbage=True):
    """Run one VS match. Returns a dict; `margin` > 0 means player 0 ahead.

    `garbage=False` still COUNTS attacks but never delivers them, turning the match into two
    independent solo races. That is the control for "is VS a different objective from solo
    speed?": players alternate placements one-for-one, so with garbage off the winner is
    simply whoever clears in fewer placements -- i.e. the solo pills-to-clear objective.
    Any gap between the garbage-on and garbage-off rankings is what VS actually adds.
    """
    m = VsMatch(seed, level, max_pills, nes_pills, chain_mode, garbage)
    taken = [0, 0]
    for _ in range(max_pills * 2):
        for who, dec in ((0, dec0), (1, dec1)):
            taken[who] += m.deliver(who)
            e = m.env[who]
            a = dec(e.board, e.cur, e.nxt)
            if a is None:
                return _result(m, seed, 1 - who, "no-move", taken)
            done, res = m.step(who, a)
            if done:
                return _result(m, seed, who if res == "clear" else 1 - who, res, taken)
    return _result(m, seed, -1, "cap", taken)


def _result(m, seed, winner, reason, taken):
    v0 = m.env[0].board.virus_count(); v1 = m.env[1].board.virus_count()
    return {"seed": seed, "winner": winner, "reason": reason, "pills": list(m.pills),
            "garbage_taken": taken, "attacks_sent": list(m.attacks_sent),
            "virus": [v0, v1], "margin": v1 - v0}


if __name__ == "__main__":
    sys.path.insert(0, ROOT + "/tmp/combo_term")
    import fast_rtl_x as F
    import collections, time
    F.warmup_delta(topk2=8)
    w, fl = F.variant("winner")
    d = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)
    f = lambda b, c, n: d.choose(b, c, n)
    for mode in ("first", "all"):
        res = collections.Counter(); atk = 0; t0 = time.time()
        for s in range(12):
            r = play_match(s, f, f, chain_mode=mode)
            res[r["reason"]] += 1; atk += sum(r["attacks_sent"])
        dt = time.time() - t0
        print(f"chain_mode={mode:>5}  outcomes={dict(res)}  attacks={atk}"
              f"  ({atk/12:.2f}/match)  {dt/12:.2f}s/match")
