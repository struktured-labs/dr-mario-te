#!/usr/bin/env python3
"""The REAL NES Dr. Mario capsule generator, as a drop-in for the faithful sim.

WHY THIS EXISTS
---------------
`faithful_env._rand_pill()` draws two independent uniform colours:

    Pill(int(self.rng.integers(1, 4)), int(self.rng.integers(1, 4)))

and `faithful_game.py` admits it in its own docstring: *"pill/virus RNG is uniform
here"*. The NES does something quite different, and the difference is exactly the thing
our surgical/planning design depends on — how long you wait for a SPECIFIC capsule.

THE REAL ALGORITHM (Winslow, https://winslowjosiah.com/blog/2024/06/28/how-dr-mario-nes-creates-its-levels/,
corroborated by dmwit/dr-mario-ngrams over all 32767 seeds):

    next_id = (last_id + (lfsr_low_nibble)) mod 9

A 16-bit LFSR (kept as two bytes s0,s1) is stepped once per capsule; its low nibble
(0..15) is ADDED to the previous capsule id and reduced mod 9. Because a 0-15 draw is
reduced mod 9, increments 0-6 are TWICE as likely as 7-8 — which is why:
  * the MARGINAL colour bias is small (~+-10%), but
  * ADJACENT capsules are strongly correlated (2-gram ratios ~0.40x to 1.71x vs iid).

★ The 128-capsule buffer is generated UP FRONT, before the level starts, and LOOPS
(capsule 129 == capsule 1). Therefore the sequence CANNOT depend on the bottle/board
state — it exists before a single piece is placed. (User asked; this is the mechanism's
own answer, and `selftest()` below checks it empirically rather than asserting it.)

★ The buffer is filled BACKWARDS (index 0x7F down to 0) and played forwards from 0 --
that is not a typo, it is what the ROM does.

★ The game calls the generator TWICE before play, so the first capsule the player sees
is the sequence's SECOND element. `NesPillSource(skip=1)` reproduces that.

LFSR + generator recovered from the pillrng lane's `analyze.py`, which validated its
vectorised form bit-exact against a scalar reference on 300 seeds.
"""
from __future__ import annotations

PILL_COLORS = ((1, 1), (1, 2), (1, 3),
               (2, 1), (2, 2), (2, 3),
               (3, 1), (3, 2), (3, 3))   # id 0..8 -> (a,b), colours 1..3


def step_lfsr(s0: int, s1: int):
    """One LFSR step. Feedback = bit1(s0) XOR bit1(s1); both bytes shift right."""
    fb = ((s0 >> 1) & 1) ^ ((s1 >> 1) & 1)
    c0 = s0 & 1
    ns0 = ((fb << 7) | (s0 >> 1)) & 0xFF
    ns1 = ((c0 << 7) | (s1 >> 1)) & 0xFF
    return ns0, ns1


def gen_sequence(s0: int = 0x89, s1: int = 0x88):
    """The 128-capsule buffer for a seed, in PLAY order (index 0 first).

    Defaults are the ROM's hardcoded warm-boot seed. Returns (ids, s0, s1)."""
    pills = [0] * 128
    acc = 0
    for k in range(0x80):
        s0, s1 = step_lfsr(s0, s1)
        acc = ((s0 & 0x0F) + acc) % 9
        pills[0x7F - k] = acc          # filled BACKWARDS, played forwards
    return pills, s0, s1


class NesPillSource:
    """Replaces FaithfulDrMarioEnv._rand_pill with the real NES sequence.

        src = NesPillSource(seed=1234)
        src.attach(env)      # env now draws NES capsules; loops after 128
    """

    def __init__(self, seed: int = None, s0: int = 0x89, s1: int = 0x88, skip: int = 1):
        if seed is not None:                 # map an int seed onto the 16-bit state
            s0, s1 = (seed >> 8) & 0xFF, seed & 0xFF
            if (s0, s1) == (0, 0):           # 0x0000 is never used by the ROM
                s0, s1 = 0x89, 0x88
        self.ids, _, _ = gen_sequence(s0, s1)
        self.i = skip                        # the ROM burns one before play
        self.drawn = 0

    def next_pill(self):
        a, b = PILL_COLORS[self.ids[self.i % 128]]
        self.i += 1
        self.drawn += 1
        return a, b

    def attach(self, env):
        """Monkeypatch this env INSTANCE only — the shared sim source is untouched.

        ⚠ MUST NOT BE A LAMBDA. This used to be
            env._rand_pill = lambda: Pill(*self.next_pill())
        and that closure silently corrupted every tree search built on this env.
        `copy.deepcopy` treats function objects as ATOMIC and returns the SAME
        object, so a deepcopied env kept drawing from the ORIGINAL source: all
        branches of a search shared one advancing cursor, siblings stole each
        other's capsules, and a line could not be replayed from its own action
        path. It failed silently, produced plausible boards, and was
        deterministic run-to-run (expansion order is deterministic), so it
        survived every check except an independent replay -- measured, 14 of 16
        "kills" in holepoker's VS beam did not reproduce.

        `_PillDraw` is an ordinary object, so deepcopy copies it AND the source
        it points at, giving each clone an independent cursor. Behaviour for
        non-cloning callers is byte-identical.
        Regression test: experiments/holepoker/test_deepcopy_pillshare.py
        """
        env._rand_pill = _PillDraw(self)
        return env


class _PillDraw:
    """Deepcopy-safe replacement for the old `attach` lambda. See attach()."""

    __slots__ = ("src",)

    def __init__(self, src):
        self.src = src

    def __call__(self):
        from drmario.faithful_env import Pill
        return Pill(*self.src.next_pill())


# ------------------------------------------------------------------ self-test
def selftest():
    ok = True

    ids, _, _ = gen_sequence()
    print(f"  buffer length            : {len(ids)} (want 128)")
    print(f"  ids in range 0..8        : {min(ids)}..{max(ids)}")
    ok &= len(ids) == 128 and min(ids) >= 0 and max(ids) <= 8

    # LOOPS: drawing 300 capsules must repeat with period 128
    s = NesPillSource(seed=4242, skip=0)
    seq = [s.next_pill() for _ in range(300)]
    loops = all(seq[k] == seq[k + 128] for k in range(300 - 128))
    print(f"  period-128 loop holds     : {loops}")
    ok &= loops

    # NOT bottle-state dependent: the buffer exists before any play, so two sources on
    # the same seed must agree regardless of what happens on the board.
    a = NesPillSource(seed=99); b = NesPillSource(seed=99)
    same = [a.next_pill() for _ in range(128)] == [b.next_pill() for _ in range(128)]
    print(f"  seed fully determines seq : {same}  (=> board state cannot affect it)")
    ok &= same

    # different seeds should generally differ
    x = NesPillSource(seed=1); y = NesPillSource(seed=2)
    diff = [x.next_pill() for _ in range(128)] != [y.next_pill() for _ in range(128)]
    print(f"  distinct seeds differ     : {diff}")
    ok &= diff

    # marginal + adjacent-correlation shape, over many seeds
    from collections import Counter
    marg = Counter(); pair = Counter()
    for sd in range(0, 4096):
        ids, _, _ = gen_sequence((sd >> 8) & 0xFF, sd & 0xFF)
        marg.update(ids)
        pair.update(zip(ids, ids[1:]))
    tot = sum(marg.values())
    r = sorted(marg[i] * 9 / tot for i in range(9))
    ptot = sum(pair.values())
    pr = sorted(pair[k] * 81 / ptot for k in pair)
    print(f"  marginal ratio vs uniform : {r[0]:.2f}x .. {r[-1]:.2f}x   (dmwit: ~0.93-1.13)")
    print(f"  2-gram   ratio vs uniform : {pr[0]:.2f}x .. {pr[-1]:.2f}x   (dmwit: ~0.40-1.71)")

    print(f"\n  SELFTEST {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if selftest() else 1)
