#!/usr/bin/env python3
"""G5 — the persistent store must never change an answer.

A memo that returns a WRONG reply is worse than no memo: it would silently
rewrite the champion in every downstream search, and (being deterministic) it
would reproduce perfectly — the exact failure shape that cost this lane its VS
section. So this does not assert "the store works"; it tries to CATCH the store
disagreeing with a freshly computed reply.

Three properties:
  A round-trip   — every stored reply equals `_choose_base_raw` recomputed cold.
  B persistence  — replies survive closing and reopening the environment.
  C key hygiene  — distinct positions must not collide onto one key, and equal
                   positions must hit (the key must contain everything the
                   champion actually reads: board, viruses, cur AND next).
"""
from __future__ import annotations
import sys, os, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                       # noqa: E402
import champion as CH                    # noqa: E402
import memo_db                           # noqa: E402


def sample_positions(n=60):
    """Real positions from champion self-play, plus their pills."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    out = []
    for s in range(4):
        env = FaithfulDrMarioEnv(level=17, seed=s, max_pills=300)
        env.reset(); NesPillSource(seed=s).attach(env)
        stream = [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(80))]
        b = CH.new_board(17, s)
        for i in range(20):
            if b.virus_count() == 0 or b.spawn_blocked():
                break
            col, vir = CH.board_to_flat(b)
            out.append((col.copy(), vir.copy(), stream[i], stream[i + 1]))
            a = CH.champion_move(col, vir, *stream[i], *stream[i + 1])
            if a is None:
                break
            CH.apply_action(b, a, *stream[i])
            if len(out) >= n:
                return out
    return out


def main():
    CH.init_champion()
    pos = sample_positions(60)
    print(f"=== G5 memo integrity: {len(pos)} real positions ===")

    tmp = tempfile.mkdtemp(prefix="hpmemo_")
    try:
        # ---- truth, computed cold with NO store attached
        CH.memo_clear(); CH.detach_db()
        truth = [CH._choose_base_raw(c, v, *cur, *nxt)[0] for c, v, cur, nxt in pos]

        # ---- A round-trip through the store
        db = memo_db.ChampionMemo(path=tmp, flush_every=10)
        CH.memo_clear(); CH.attach_db(db)
        got = [CH.champion_move(c, v, *cur, *nxt) for c, v, cur, nxt in pos]
        a_bad = sum(1 for x, y in zip(truth, got) if x != y)
        print(f"  A round-trip     : {len(pos)-a_bad}/{len(pos)} agree with cold recompute"
              f"{'' if a_bad == 0 else f'  ** {a_bad} MISMATCH **'}")
        db.flush()
        ent = db.info()["entries"]

        # ---- B persistence across reopen (fresh process-local caches)
        db.close()
        CH.detach_db(); CH.memo_clear()
        db2 = memo_db.ChampionMemo(path=tmp)
        CH.attach_db(db2)
        got2 = [CH.champion_move(c, v, *cur, *nxt) for c, v, cur, nxt in pos]
        b_bad = sum(1 for x, y in zip(truth, got2) if x != y)
        served = db2.info()["hit_db"]
        print(f"  B persistence    : {len(pos)-b_bad}/{len(pos)} agree after reopen; "
              f"{served} served from disk, {ent} entries on disk"
              f"{'' if b_bad == 0 else f'  ** {b_bad} MISMATCH **'}")
        if served == 0:
            print("    ** nothing was served from disk -- the store is not being read **")

        # ---- C key hygiene: next-pill must be part of the key
        c0, v0, cur0, _n0 = pos[0]
        k1 = db2.key(c0, v0, cur0[0], cur0[1], 1, 1)
        k2 = db2.key(c0, v0, cur0[0], cur0[1], 3, 3)
        k3 = db2.key(c0, v0, cur0[0], cur0[1], 1, 1)
        vir_alt = v0.copy()
        nz = np.nonzero(vir_alt)[0]
        if len(nz):
            vir_alt[nz[0]] = 0
        k4 = db2.key(c0, vir_alt, cur0[0], cur0[1], 1, 1)
        c_ok = (k1 != k2) and (k1 == k3) and (k1 != k4) and len(k1) == memo_db.KEY_LEN
        print(f"  C key hygiene    : next-pill in key={k1 != k2}  stable={k1 == k3}  "
              f"virus-plane in key={k1 != k4}  len={len(k1)}")
        db2.close()

        ok = (a_bad == 0 and b_bad == 0 and c_ok and served > 0)
        print(f"\n{'PASS -- the store never changed an answer.' if ok else 'FAIL -- DO NOT USE THE STORE'}")
        return 0 if ok else 1
    finally:
        CH.detach_db()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
