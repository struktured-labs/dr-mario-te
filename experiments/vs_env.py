#!/usr/bin/env python3
"""Two-player VS environment WITH GARBAGE -- the thing our evaluation has never had.

WHY THIS EXISTS (2026-07-30): the user beat the AI on real hardware by "combo stomping at
critical junctures", and the photo of the AI's loss shows it topped out with a narrow spire
in the SPAWN COLUMN while AHEAD 24 viruses to 32. Every number this project has measured is
from SOLO play -- there is no garbage model anywhere in the sim. So the eval's two largest
penalties, spawn(-150) and toprisk(-90), have only ever been exercised against SELF-inflicted
stacking, never against incoming garbage. That is precisely the regime the AI actually loses in.

THE RULE (MECHANICS_NES.md; extracted from the ROM and verified by probe_attack.lua, though
the column set is still flagged UNVERIFIED there -- treat as our best model, not gospel):
  * 1 line cleared            -> 0 garbage
  * >=2 lines SIMULTANEOUSLY  -> 2 tiles to the opponent
  * garbage colours           = the cleared runs' colours
  * enters at row 0, falls
  * columns come from the fixed pairs {1,5} / {2,6} / {3,7}
    ★ columns 0 and 4 are GARBAGE-IMMUNE -- structures built through them are protected.

PROXY: FB/FaithfulBoard.resolve() returns cells, not lines. Two simultaneous runs need >=7
distinct cells (4+4 minus a shared corner), so `cells >= 7` is the documented near-perfect
proxy for a double-line clear. Used here and flagged wherever it matters.
"""
from __future__ import annotations
import sys, random
ROOT="/home/struktured/projects/dr_mario_rl"
for p in (ROOT+"/.claude/worktrees/faithful-sim/src",):
    if p not in sys.path: sys.path.insert(0,p)

GARBAGE_PAIRS = ((1,5),(2,6),(3,7))     # columns 0 and 4 are immune
DOUBLE_CELLS  = 7                        # >=7 cells == 2+ simultaneous lines (see docstring)


class VsMatch:
    """Two FaithfulDrMarioEnv boards exchanging garbage. Deciders are callables
    (board, cur, nxt) -> action, exactly like the solo deciders."""

    def __init__(self, seed, level=11, max_pills=300, nes_pills=True):
        from drmario.faithful_env import FaithfulDrMarioEnv
        self.rng = random.Random(seed * 6151 + 7)
        self.env = []
        for k in range(2):
            e = FaithfulDrMarioEnv(level=level, seed=seed + 1000*k, max_pills=max_pills)
            e.reset()
            if nes_pills:
                sys.path.insert(0, ROOT+"/tmp/pillrng")
                from nes_pills import NesPillSource
                # BOTH players share the seed's capsule sequence, as the real game does
                NesPillSource(seed=seed).attach(e)
                e.cur = e._rand_pill(); e.nxt = e._rand_pill()
            self.env.append(e)
        self.pending = [[], []]          # garbage queued for each player
        self.pills = [0, 0]

    # ---------------------------------------------------------------- garbage
    def _drop_garbage(self, who, colours):
        """Insert 2 tiles at row 0 in one of the immune-safe column pairs, then settle."""
        b = self.env[who].board
        c1, c2 = self.rng.choice(GARBAGE_PAIRS)
        for c, col in ((c1, colours[0]), (c2, colours[-1])):
            if b.color[0, c] == 0:
                b.color[0, c] = col
                b.link[0, c] = 0          # garbage is unlinked -- falls as a single cell
                b.is_virus[0, c] = False
        b.resolve()                       # settle + honour any clears the garbage completes

    def _colours_of(self, board_before, board_after):
        """Colours present before but gone after -- i.e. what was cleared."""
        got = []
        for col in (1, 2, 3):
            if (board_before == col).sum() > (board_after == col).sum():
                got.append(col)
        return got or [1]

    # ------------------------------------------------------------------- play
    def step(self, who, action):
        """Advance one player by one placement; returns (done, result)."""
        e = self.env[who]
        before = e.board.color.copy()
        _, _, term, trunc, info = e.step(int(action))
        self.pills[who] += 1
        cells = int((before != 0).sum() - (e.board.color != 0).sum())
        if cells >= DOUBLE_CELLS:                     # >=2 simultaneous lines -> attack
            self.pending[1 - who].append(self._colours_of(before, e.board.color))
        if term:
            return True, ("clear" if info.get("won") else "topout")
        if trunc:
            return True, "stall"
        return False, None

    def deliver(self, who):
        """Apply any garbage queued for `who` (called between their placements)."""
        n = 0
        while self.pending[who]:
            self._drop_garbage(who, self.pending[who].pop(0)); n += 1
        return n


def play_match(seed, dec0, dec1, level=11, max_pills=300, nes_pills=True):
    """Run one VS match. Returns dict with winner, reason, pills, and attacks landed."""
    m = VsMatch(seed, level, max_pills, nes_pills)
    atk = [0, 0]
    for _ in range(max_pills * 2):
        for who, dec in ((0, dec0), (1, dec1)):
            atk[1-who] += m.deliver(who)
            e = m.env[who]
            a = dec(e.board, e.cur, e.nxt)
            if a is None:
                return {"seed": seed, "winner": 1-who, "reason": "no-move",
                        "pills": m.pills, "garbage_taken": atk}
            done, res = m.step(who, a)
            if done:
                win = who if res == "clear" else 1 - who
                # CONTINUOUS MARGIN, for variance reduction. Binary win/loss needs ~780
                # matches to separate 55% from 50%; the virus differential at match end is
                # the same objective with far less noise, so a sweep costs an order of
                # magnitude fewer matches for the same resolution.
                v0 = m.env[0].board.virus_count(); v1 = m.env[1].board.virus_count()
                return {"seed": seed, "winner": win, "reason": res,
                        "pills": m.pills, "garbage_taken": atk,
                        "virus": [v0, v1], "margin": v1 - v0}   # >0 == player 0 ahead
    v0 = m.env[0].board.virus_count(); v1 = m.env[1].board.virus_count()
    return {"seed": seed, "winner": -1, "reason": "cap", "pills": m.pills,
            "garbage_taken": atk, "virus": [v0, v1], "margin": v1 - v0}


if __name__ == "__main__":
    # smoke: shipped brain vs itself, garbage live
    sys.path.insert(0, ROOT+"/tmp/combo_term")
    import fast_rtl_x as NEW
    NEW.warmup_ship_eh(topk2=8)
    w, fl = NEW.variant("winner")
    d = NEW.FastShipD3DeciderEH(w, fl, topk2=8)
    f = lambda b, c, n: d.choose(b, c, n)
    import collections
    res = collections.Counter(); tot_atk = 0
    for s in range(12):
        r = play_match(s, f, f)
        res[r["reason"]] += 1; tot_atk += sum(r["garbage_taken"])
    print("VS env smoke (shipped brain vs itself, NES capsules, garbage ON)")
    print("  outcomes:", dict(res))
    print(f"  garbage volleys landed across 12 matches: {tot_atk}")
    print("  => garbage is", "FLOWING" if tot_atk else "NEVER FIRING (proxy or wiring bug)")
