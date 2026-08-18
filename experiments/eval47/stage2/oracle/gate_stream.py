"""S4 — the property `m_no_deepcopy` was MEANT to guard, checked directly.

The screen's whole reason to exist is that it prices flips on capsule streams
the arm never saw. If it accidentally forked on the TRUE stream it would
re-introduce the seed-peeking that killed 7 of 10 exhibits in
[[dr-mario-flip-fairness-screen]] — and it would do so SILENTLY, reporting a
confident, well-formed, tight-CI number the whole time.

That property is NOT an action-sequence property, which is why the
`m_no_deepcopy` mutant survived `gate_screen.py`'s S2 at 0/12: `_fork_label`
deepcopies its own input, so forking on the live env cannot change the game.
The mutant was pointed at the wrong observable. This checks the right one, at
unit level, in seconds instead of 48 games.

Each assertion has a stated failure mode — a check nobody can describe failing
is not a check.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def stream_of(env, n=8):
    c = copy.deepcopy(env)
    return [(int(p.a), int(p.b)) for p in (c._rand_pill() for _ in range(n))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+",
                    default=[90001, 90007, 71003, 41005])
    ap.add_argument("--alt-base", type=int, default=500000)
    ap.add_argument("--out", default="out/GATE_STREAM.json")
    a = ap.parse_args()

    import oracle_arm as O
    from run_screen import alt_stream_clone, _alt_seed
    C, bmodel = O.init_rig("lulu")

    checks = {
        "alt_differs_from_true": ("the screen would fork on the SAME capsule "
                                  "future the arm just saw = seed-peeking"),
        "alts_differ_from_each_other": ("the K streams would be one stream "
                                        "repeated; averaging would remove no "
                                        "luck at all"),
        "alt_seed_not_play_seed_canonical": ("2k and 2k+1 alias to ONE stream, "
                                             "so a raw-value check passes "
                                             "while the stream IS the game's"),
        "parent_cursor_unadvanced": ("cloning would steal the live game's "
                                     "capsules and corrupt the trajectory"),
        "nxt_redrawn_on_clone": ("the preview would come from the true stream "
                                 "while the rest came from the alternate"),
        "cur_preserved_on_clone": ("the capsule under decision would change, "
                                   "so the screened choice would not be the "
                                   "choice the arm actually made"),
    }
    results = {k: True for k in checks}
    rows = []

    for seed in a.seeds:
        env = O.make_env(seed, C["level"])
        for _ in range(6):
            r, _v = O._advance(env, 10, C, seed, bmodel)
            if r is not None:
                break
        true_s = stream_of(env)
        a1, a2 = _alt_seed(a.alt_base, seed, 0), _alt_seed(a.alt_base, seed, 1)
        c1, c2 = alt_stream_clone(env, a1), alt_stream_clone(env, a2)
        s1, s2 = stream_of(c1), stream_of(c2)
        row = {
            "seed": seed, "alt_seeds": [a1, a2],
            "alt_differs_from_true": s1 != true_s and s2 != true_s,
            "alts_differ_from_each_other": s1 != s2,
            "alt_seed_not_play_seed_canonical":
                (a1 & ~1) != (seed & 0xFFFF & ~1)
                and (a2 & ~1) != (seed & 0xFFFF & ~1),
            "parent_cursor_unadvanced": stream_of(env) == true_s,
            "nxt_redrawn_on_clone":
                (c1.nxt.a, c1.nxt.b) != (env.nxt.a, env.nxt.b)
                or (c2.nxt.a, c2.nxt.b) != (env.nxt.a, env.nxt.b),
            "cur_preserved_on_clone":
                (c1.cur.a, c1.cur.b) == (env.cur.a, env.cur.b)
                and (c2.cur.a, c2.cur.b) == (env.cur.a, env.cur.b),
        }
        rows.append(row)
        for k in checks:
            results[k] &= bool(row[k])

    ok = all(results.values())
    print(f"S4 UNSEEN-STREAM CHECK over seeds {a.seeds}\n")
    for k, why in checks.items():
        n = sum(bool(r[k]) for r in rows)
        print(f"  {k:36s} {n}/{len(rows)} {'PASS' if results[k] else 'FAIL'}")
        print(f"      if this failed: {why}")
    print(f"\nS4 {'PASS' if ok else 'FAIL'}")
    print("\nNOT COVERED: proves the streams are unseen and the clone is "
          "clean. Says nothing\nabout whether the fork VALUES are right "
          "(H12's machinery, gated upstream) or\nwhether the screened "
          "comparison is the right comparison (the prereg's job).")
    json.dump({"seeds": a.seeds, "checks": results, "rows": rows, "pass": ok,
               "supersedes": "gate_screen.py S2 m_no_deepcopy, which is "
                             "EQUIVALENT under an action-sequence observable "
                             "because _fork_label deepcopies its input"},
              open(a.out, "w"), indent=1)
    print(f"-> {a.out}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
