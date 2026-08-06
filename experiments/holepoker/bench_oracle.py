#!/usr/bin/env python3
"""Size the search budget: how fast is one champion reply, and is the pill
(a,b)<->(b,a) swap a genuine symmetry (which would halve branching 9->6)?"""
from __future__ import annotations
import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import champion as CH


def main():
    CH.init_champion()
    # collect a corpus of real mid-game boards from champion self-play
    boards = []
    for s in range(6):
        b = CH.new_board(11, s)
        from drmario.faithful_env import FaithfulDrMarioEnv
        from nes_pills import NesPillSource
        env = FaithfulDrMarioEnv(level=11, seed=s, max_pills=300)
        env.reset(); NesPillSource(seed=s).attach(env)
        stream = [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(320))]
        for i in range(60):
            if b.virus_count() == 0 or b.spawn_blocked():
                break
            col, vir = CH.board_to_flat(b)
            a = CH.champion_move(col, vir, *stream[i], *stream[i + 1])
            if a is None:
                break
            if i >= 20:
                boards.append((b.clone(), stream[i][0], stream[i][1]))
            CH.apply_action(b, a, *stream[i])
    print(f"corpus: {len(boards)} mid-game boards")

    # --- swap symmetry: champion_move(...,ca,cb,..) == (...,cb,ca,..)?
    CH.memo_clear()
    n_cur = n_cur_bad = n_nxt = n_nxt_bad = 0
    for b, ca, cb in boards[:200]:
        col, vir = CH.board_to_flat(b)
        for na, nb in [(1, 2), (2, 3), (1, 1), (3, 1)]:
            a1 = CH.champion_move(col, vir, ca, cb, na, nb)
            a2 = CH.champion_move(col, vir, cb, ca, na, nb)
            n_cur += 1
            # a1/a2 differ only by the a-first/b-first variant bit when swapped
            if a1 is not None and a2 is not None:
                v1, c1_ = a1 // 8, a1 % 8
                v2, c2_ = a2 // 8, a2 % 8
                # swapping the pill should flip the variant parity, same column
                if not (c1_ == c2_ and (v1 ^ 1) == v2):
                    n_cur_bad += 1
            a3 = CH.champion_move(col, vir, ca, cb, nb, na)
            n_nxt += 1
            if a1 != a3:
                n_nxt_bad += 1
    print(f"cur-swap: {n_cur - n_cur_bad}/{n_cur} behave as pure variant-parity flip")
    print(f"nxt-swap: {n_nxt - n_nxt_bad}/{n_nxt} give the IDENTICAL action "
          f"({'SYMMETRIC -> 6 pills' if n_nxt_bad == 0 else 'NOT symmetric -> 9 pills'})")

    # --- raw speed (cold, memo off)
    CH.memo_clear()
    t0 = time.time()
    N = 0
    for b, ca, cb in boards[:400]:
        col, vir = CH.board_to_flat(b)
        for na, nb in [(1, 2), (2, 3), (3, 3)]:
            CH._choose_base_raw(col, vir, ca, cb, na, nb)
            N += 1
    dt = time.time() - t0
    print(f"\ncold oracle: {N} calls in {dt:.2f}s = {N/dt:,.0f} calls/s "
          f"({dt/N*1e6:.0f} us each)")
    print(f"  => depth-6 full tree (6^6=46656 nodes) ~ {46656/(N/dt):.1f}s")
    print(f"  => depth-8 full tree (6^8=1.68M nodes) ~ {6**8/(N/dt)/60:.1f} min")
    print(f"  => depth-10      (6^10=60.5M nodes)    ~ {6**10/(N/dt)/3600:.1f} h")

    # --- world-step speed
    t0 = time.time()
    for b, ca, cb in boards[:400]:
        bb = b.clone()
        CH.apply_action(bb, 16, ca, cb)
    dt2 = time.time() - t0
    print(f"world step (clone+place+resolve): {400/dt2:,.0f}/s ({dt2/400*1e6:.0f} us)")


if __name__ == "__main__":
    main()
