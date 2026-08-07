#!/usr/bin/env python3
"""REGRESSION TEST for a defect that silently corrupts ANY tree search built on
`vs_env_exact.VsMatch` (or on any FaithfulDrMarioEnv with NesPillSource attached)
that clones states with `copy.deepcopy`.

THE DEFECT
    NesPillSource.attach does:
        env._rand_pill = lambda: Pill(*self.next_pill())
    i.e. it stores a CLOSURE over the NesPillSource as an INSTANCE attribute.
    `copy.deepcopy` treats function objects as ATOMIC and returns the same
    object, so the copy's `_rand_pill` still points at the ORIGINAL source.
    Every cloned branch therefore draws from ONE SHARED, ADVANCING cursor.

CONSEQUENCE
    In a beam/DFS over VS states, sibling branches steal each other's capsules.
    Which pills a branch sees depends on how many other branches were expanded
    first, so:
      * the simulated game is not the game the seed defines;
      * a "kill" found by the search cannot be replayed from its own action
        path -- it depended on the interleaving, not on the moves.
    It fails SILENTLY: no exception, plausible-looking boards, deterministic
    run-to-run (the expansion order is deterministic), so it survives a
    determinism check and only a REPLAY catches it.

This test asserts the DEFECT (two deepcopies must draw the SAME next capsule,
because they are independent futures of one state) rather than asserting a guard.
"""
from __future__ import annotations
import sys, os, copy
HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def test_shared_cursor():
    from vs_env_exact import VsMatch
    m = VsMatch(3, level=11, max_pills=300, nes_pills=True)
    a = copy.deepcopy(m)
    b = copy.deepcopy(m)
    pa = a.env[0]._rand_pill()
    pb = b.env[0]._rand_pill()
    same_fn = (a.env[0]._rand_pill is m.env[0]._rand_pill)
    ok = (int(pa.a), int(pa.b)) == (int(pb.a), int(pb.b))
    print(f"  deepcopy shares the _rand_pill closure object : {same_fn}")
    print(f"  two independent clones drew  A={int(pa.a)},{int(pa.b)}  "
          f"B={int(pb.a)},{int(pb.b)}")
    print(f"  clones agree (they must, they are the same state): {ok}")
    return ok, same_fn


def test_replay_divergence():
    """The end-to-end symptom: play a fixed action list twice, once with sibling
    clones expanded in between and once without. Same actions, same seed --
    different boards."""
    import champion as CH
    import vs_poker as VP
    CH.init_champion()
    acts = [16, 17, 18, 19]

    def run(with_siblings):
        m = VP.new_match(3, 11)
        for a in acts:
            if with_siblings:                    # expand throwaway siblings
                for s in VP.adv_legal(m)[:4]:
                    VP.ply(copy.deepcopy(m), s)
            st, _ = VP.ply(m, a)
            if st is not None:
                break
        return CH.board_key(m.env[VP.CHAMP].board)

    clean = run(False)
    dirty = run(True)
    ok = clean == dirty
    print(f"  same actions, siblings expanded in between -> identical board: {ok}")
    return ok


def main():
    print("=== A. UPSTREAM substrate (raw vs_env_exact.VsMatch) ===")
    print("    informational -- documents the defect as it still exists for any")
    print("    caller that deepcopies a raw VsMatch.")
    ok1, _same_fn = test_shared_cursor()
    print(f"    upstream status: {'clean' if ok1 else 'DEFECT PRESENT'}")

    print("\n=== B. OUR wrapper (vs_poker.new_match) -- MUST PASS ===")
    ok2 = test_replay_divergence()
    print(f"    wrapper status: {'SOUND' if ok2 else 'CORRUPTED'}")

    print()
    if ok2:
        print("PASS -- vs_poker.new_match's list+cursor capsule supply survives")
        print("        deepcopy, so its tree search is replayable.")
        if not ok1:
            print("NOTE -- the UPSTREAM defect is still live in vs_env_exact:")
            print("        NesPillSource.attach stores a closure, deepcopy shares")
            print("        it, and any OTHER tier doing copy.deepcopy(VsMatch)")
            print("        without this fix is silently corrupted.")
        return 0
    print("FAIL -- our wrapper is still corrupted; no VS search result stands.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
