#!/usr/bin/env python3
"""THE DECISIVE GATE: paired A/B where BOTH arms are driven by the REAL assembled
EMIT_TUCK_V3 firmware (py65-executed 6502 bytes from fpga/copro/tuck_v3.py +
build_copro_d3.py), not root_search.py's python approximation. Arm off = DRCOPRO_TUCKV3=0,
arm on = DRCOPRO_TUCKV3=1 -- both built from the exact same search code otherwise, so this
is a WITHIN-FIRMWARE comparison that never depends on matching root_search.py/fast_rtl_x.py's
absolute eval scale (which is a documented approximation of the real RTL-faithful firmware,
NOT meant to be bit-exact -- see fast_rtl_x.py's own "BOUNDARY / HONESTY" docstring and its
g_hang comment; confirmed via firmware_decider.py's diagnostic differential, not guessed).

Mirrors ab_root.py's game-stepping and statistics machinery as closely as possible
(FaithfulDrMarioEnv, boot_ci, sign_test_p, the same paired-pills/clear-rate/sign-test
report) so the two scripts' OUTPUT is directly comparable -- only the decision-maker
differs. Each worker process sets DRCOPRO_TUCKV3 via its OWN os.environ (ProcessPoolExecutor
initializer) BEFORE ever importing build_copro_d3/test_search_d3, avoiding the module-
import-time env-var caching hazard (build_copro_d3.EMIT_TUCK_V3 is a module-level constant
read ONCE at import; switching it within one process after import has no effect without a
force-reload, so each arm gets its OWN worker process instead).

Usage: ab_root_firmware.py --seeds 12 --level 11 --workers 4
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import hashlib
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/bitexact_gate"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_C = {}


# fixed, arbitrary reference board used ONLY to fingerprint a worker's assembled image --
# not a real game board, never passed through play()/decide()'s actual game loop.
_HASH_BOARD = bytes([0xFF] * (10 * 8 + 5) + [0xD1] + [0xFF] * (128 - 10 * 8 - 6))


def _init(level, tuck, drchain=180, drfix=1, arm=1, theta=150):
    """Runs once per WORKER PROCESS. Sets the env vars BEFORE any firmware module is
    imported in this process, then does the one-time (expensive) module load + assembly
    setup, stashed in _C for `play()` to reuse across all decisions in this worker."""
    os.environ["DRCOPRO_TUCKV3"] = "1" if tuck else "0"
    os.environ["DRCOPRO_ARM"] = "1" if arm else "0"
    os.environ["DRFIX"] = "1" if drfix else "0"
    os.environ["DRCHAIN"] = str(drchain)
    from firmware_decider import FirmwareDecider
    # `tuck` MUST also be passed here, not just set into os.environ above --
    # FirmwareDecider.__init__ used to hardcode DRCOPRO_TUCKV3="1" regardless of what the
    # caller had just set, silently forcing both A/B arms onto the same tuck-enabled
    # image (see firmware_decider.py's fix comment). Setting the env var here alone is
    # not sufficient defense against that class of bug recurring -- the constructor is
    # now the single source of truth for its own env var. `theta` is the same story
    # (DRCOPRO_TUCKV3_THETA), added for the theta mini-sweep (task #17 stage 3).
    fd = FirmwareDecider(drchain=drchain, drfix=drfix, arm=arm, tuck=tuck, theta=theta)
    img, _clen, _slen = fd.B.build_image(_HASH_BOARD, 0, 1, 1, 0)
    image_hash = hashlib.sha256(bytes(img)).hexdigest()
    _C.update(level=level, tuck=tuck, theta=theta, fd=fd, image_hash=image_hash)


def _report_hash():
    """Runs in a worker via ex.submit -- returns THIS worker's already-built image hash,
    proving what _init actually assembled (not just what env var was requested)."""
    return _C["image_hash"]


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource
    import root_search as RS

    fd = _C["fd"]
    env = FaithfulDrMarioEnv(level=_C["level"], seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    seg = {"open": [0, 0], "mid": [0, 0], "end": [0, 0]}
    fired = 0
    res = "stall"
    steps_total = 0

    while True:
        from fb import FB
        fb = FB.from_board(env.board)
        vc = env.board.virus_count()
        col, vir = RS.board_flat_from_fb(fb)

        pick = fd.decide(col, vir, env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
        if pick is None:
            res = "stall"
            break
        steps_total += pick.get("steps", 0)

        k = "open" if vc > 32 else ("mid" if vc > 8 else "end")

        if pick["kind"] == "tuck":
            r0, c0, r1, c1 = pick["placement"]["cells"]
            b = env.board
            b.color[r0, c0] = pick["ca"]
            b.color[r1, c1] = pick["cb"]
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT
                b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN
                b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            fired += 1
            seg[k][0] += 1
            seg[k][1] += vc - b.virus_count()
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                break
            if env.pills_placed >= 300:
                break
            continue

        a = pick["action"]
        _, _, term, trunc, info = env.step(int(a))
        seg[k][0] += 1
        seg[k][1] += vc - env.board.virus_count()
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    return {"seed": seed, "won": int(res == "clear"), "pills": env.pills_placed,
            "fired": fired, "seg": seg, "steps_total": steps_total}


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def sign_test_p(better, worse):
    from math import comb
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    p = sum(comb(n, i) for i in range(0, k + 1)) * (0.5 ** n) * 2
    return min(1.0, p)


def _log_rss(tag):
    """One-line RSS sum across every python process on the box -- per the team-lead's
    ruling: OOM incidents were unbounded detached jobs, not the worker count itself, so
    the mitigation is VISIBILITY (log growth in the log, not discover it via the kernel),
    not a smaller cap."""
    try:
        import subprocess
        out = subprocess.run(
            ["bash", "-c",
             "ps -o rss= -C python 2>/dev/null | awk '{s+=$1} END {print s+0}'"],
            capture_output=True, text=True, timeout=10)
        rss_kb = int(out.stdout.strip() or "0")
        print(f"  [RSS] {tag}: {rss_kb/1024:.0f} MB across all python processes", flush=True)
    except Exception as e:
        print(f"  [RSS] {tag}: measurement failed ({e})", flush=True)


def run_level(level, seeds, workers, seed_offset=0):
    R = {}
    arm_hashes = {}
    for tuck in (0, 1):
        rows = []
        with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                                 initargs=(level, tuck)) as ex:
            # STARTUP ASSERT (team-lead ruling, after the sanity-8-v3 arm-plumbing bug:
            # both A/B arms silently built the identical tuck-enabled image because
            # FirmwareDecider.__init__ hardcoded its env var, and nothing checked that
            # the two arms' images actually differed). Hash the FIRST worker's already-
            # assembled image for this arm and refuse to spend any compute on a run
            # where the arms are provably not different builds -- a 2-second check
            # instead of an hours-long run producing a degenerate delta-0.00 result.
            arm_hashes[tuck] = ex.submit(_report_hash).result()
            print(f"  L{level} tuck={tuck} image sha256={arm_hashes[tuck]}", flush=True)
            if tuck == 1:
                assert arm_hashes[0] != arm_hashes[1], (
                    f"REFUSING TO RUN: off-arm and on-arm assembled images hash "
                    f"IDENTICAL ({arm_hashes[1]}) -- the two A/B arms are not actually "
                    f"different builds. This is exactly the sanity-8-v3 arm-plumbing "
                    f"bug's signature (paired-pills delta stuck at 0.00 with nonzero "
                    f"fires/game); do not proceed until the images provably diverge.")
            futs = [ex.submit(play, s) for s in range(seed_offset, seed_offset + seeds)]
            for i, f in enumerate(as_completed(futs)):
                rows.append(f.result())
                if (i + 1) % max(1, seeds // 10) == 0 or (i + 1) == seeds:
                    _log_rss(f"L{level} tuck={tuck} after {i + 1}/{seeds} games")
        R[tuck] = {r["seed"]: r for r in rows}
        print(f"  L{level} FIRMWARE arm tuck={tuck} done ({len(rows)} games)", flush=True)

    off, on = R[0], R[1]
    all_seeds = sorted(set(off) & set(on))

    both = [s for s in all_seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)

    c_off = sum(off[s]["won"] for s in all_seeds) / len(all_seeds)
    c_on = sum(on[s]["won"] for s in all_seeds) / len(all_seeds)
    disc = [(off[s]["won"], on[s]["won"]) for s in all_seeds if off[s]["won"] != on[s]["won"]]
    won_only_on = sum(1 for o, n in disc if n)
    won_only_off = len(disc) - won_only_on
    p_clear = sign_test_p(won_only_on, won_only_off)

    fires = [on[s]["fired"] for s in all_seeds]

    out = {
        "level": level, "seeds": len(all_seeds),
        "paired_pills_delta_mean": st.mean(d) if d else float("nan"),
        "paired_pills_ci": [lo, hi],
        "paired_n": len(both), "better": better, "worse": worse, "tie": len(d) - better - worse,
        "clear_off": c_off, "clear_on": c_on,
        "discordant": len(disc), "tuck_only_wins": won_only_on, "tuck_only_losses": won_only_off,
        "sign_test_p": p_clear,
        "fires_per_game": st.mean(fires) if fires else 0.0,
    }

    verdict = "REAL (CI excludes 0)" if (hi < 0 or lo > 0) else "WASH (CI spans 0)"
    print(f"\n=== FIRMWARE-BACKED ROOT-ACTION TUCKS v3, L{level}, n={len(all_seeds)} paired seeds ===")
    print(f"1. PAIRED PILLS (both cleared, n={len(both)}/{len(all_seeds)})")
    print(f"   mean delta {out['paired_pills_delta_mean']:+.2f}   95% CI [{lo:+.2f}, {hi:+.2f}]")
    print(f"   better {better} / worse {worse} / tie {out['tie']}   => {verdict}")
    print(f"2. CLEAR RATE  off {c_off:.1%} -> on {c_on:.1%}   discordant {len(disc)} "
          f"(tuck-only wins {won_only_on}, tuck-only losses {won_only_off}, "
          f"sign-test p={p_clear:.4f})")
    print(f"3. FIRES/GAME  {out['fires_per_game']:.2f}")
    if level == 11:
        # off-arm cross-validation rider (team-lead): the OFF arm's clear rate through
        # firmware should land near the offline off-arm's ~95.8% -- grossly different
        # means the game-loop wiring (gravity/stream/topout handling) diverges from the
        # offline harness, and neither arm should be trusted until that's understood.
        flag = "" if abs(c_off - 0.958) < 0.10 else "  <-- FAR FROM OFFLINE ~95.8%, INVESTIGATE BEFORE TRUSTING EITHER ARM"
        print(f"4. OFF-ARM CROSS-VALIDATION  clear_off={c_off:.1%} vs offline reference ~95.8%{flag}")

    return out, R


def report(out, level):
    lo, hi = out["paired_pills_ci"]
    verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
    print(f"L{level}: paired pills {out['paired_pills_delta_mean']:+.2f} "
          f"[{lo:+.2f},{hi:+.2f}] {verdict}   clear {out['clear_off']:.1%}->"
          f"{out['clear_on']:.1%}   fires/g {out['fires_per_game']:.2f}")
    return verdict


def _write_json(out_prefix, level, out, R):
    if not out_prefix:
        return
    fn = f"{out_prefix}_L{level}.json"
    with open(fn, "w") as fh:
        json.dump({"summary": out,
                  "off": [R[0][s] for s in sorted(R[0])],
                  "on": [R[1][s] for s in sorted(R[1])]}, fh)
    print(f"wrote {fn}", flush=True)


def _merge_R(r_a, r_b):
    return {0: {**r_a[0], **r_b[0]}, 1: {**r_a[1], **r_b[1]}}


def run_pass1(workers, out_prefix):
    """Staged launch, per the team-lead's standing terms: L11 full n=120 (cheap, and the
    arm with the -10.03 claim) + L20 seeds 0-79 first. Acceptance: L11 CI excludes 0 in
    the right direction (negative -- fewer pills with tucks on) AND the L20 subset shows
    no clear-rate regression signal (on >= off, allowing float noise) -> auto-launch L20
    seeds 80-239 to complete the full n=240. If L11 fails to reproduce: STOP everything,
    report -- that is the firmware-vs-model divergence finding itself, not a tuning
    problem, and burning the L20 budget first would be waste."""
    print("=== PASS 1: L11 full n=120 ===", flush=True)
    out11, R11 = run_level(11, 120, workers, seed_offset=0)
    _write_json(out_prefix, 11, out11, R11)
    report(out11, 11)

    l11_ci_excludes_0_negative = out11["paired_pills_ci"][1] < 0   # hi < 0 -> tucks use fewer pills
    if not l11_ci_excludes_0_negative:
        print("\n" + "=" * 70)
        print("STOP: L11 did not reproduce (CI does not exclude 0 in the tuck-favourable")
        print("direction). Per standing instruction, this is a firmware-vs-model")
        print("divergence finding, not a tuning problem -- L20 is NOT launched.")
        print("=" * 70)
        return {11: out11}

    print("\n=== PASS 1: L20 seeds 0-79 (subset) ===", flush=True)
    out20a, R20a = run_level(20, 80, workers, seed_offset=0)
    _write_json(out_prefix, "20_subset", out20a, R20a)
    report(out20a, 20)

    l20_subset_no_regression = out20a["clear_on"] >= out20a["clear_off"] - 1e-9
    if not l20_subset_no_regression:
        print("\n" + "=" * 70)
        print("STOP: L20 subset (seeds 0-79) shows a clear-rate regression signal")
        print(f"(clear_off={out20a['clear_off']:.1%} clear_on={out20a['clear_on']:.1%}).")
        print("Per standing instruction, L20 seeds 80-239 are NOT auto-launched.")
        print("=" * 70)
        return {11: out11, 20: out20a}

    print("\n=== PASS 1: L11 reproduced + L20 subset clean -> auto-launching L20 seeds 80-239 ===", flush=True)
    out20b, R20b = run_level(20, 160, workers, seed_offset=80)
    _write_json(out_prefix, "20_remainder", out20b, R20b)

    R20_full = _merge_R(R20a, R20b)
    # re-derive the full-n=240 statistics from the merged raw results rather than trying
    # to combine two summary dicts (the bootstrap CI and sign test are not simply
    # additive across sub-batches).
    off, on = R20_full[0], R20_full[1]
    all_seeds = sorted(set(off) & set(on))
    both = [s for s in all_seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)
    c_off = sum(off[s]["won"] for s in all_seeds) / len(all_seeds)
    c_on = sum(on[s]["won"] for s in all_seeds) / len(all_seeds)
    disc = [(off[s]["won"], on[s]["won"]) for s in all_seeds if off[s]["won"] != on[s]["won"]]
    won_only_on = sum(1 for o, n in disc if n)
    won_only_off = len(disc) - won_only_on
    p_clear = sign_test_p(won_only_on, won_only_off)
    fires = [on[s]["fired"] for s in all_seeds]
    out20_full = {
        "level": 20, "seeds": len(all_seeds),
        "paired_pills_delta_mean": st.mean(d) if d else float("nan"),
        "paired_pills_ci": [lo, hi],
        "paired_n": len(both), "better": better, "worse": worse, "tie": len(d) - better - worse,
        "clear_off": c_off, "clear_on": c_on,
        "discordant": len(disc), "tuck_only_wins": won_only_on, "tuck_only_losses": won_only_off,
        "sign_test_p": p_clear,
        "fires_per_game": st.mean(fires) if fires else 0.0,
    }
    _write_json(out_prefix, "20_full", out20_full, R20_full)
    print(f"\n=== L20 FULL (n={len(all_seeds)}, merged 0-79 + 80-239) ===")
    report(out20_full, 20)

    print("\n=== PASS 1 SUMMARY ===")
    report(out11, 11)
    report(out20_full, 20)
    return {11: out11, 20: out20_full}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--levels", type=int, nargs="+", default=[11])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--pass1", action="store_true",
                     help="run the staged L11 full + L20 0-79/auto-continue launch "
                          "instead of the ad-hoc --seeds/--levels sweep")
    a = ap.parse_args()

    if a.pass1:
        run_pass1(a.workers, a.out)
        return

    results = {}
    for level in a.levels:
        out, R = run_level(level, a.seeds, a.workers)
        results[level] = out
        _write_json(a.out, level, out, R)

    print("\n=== SUMMARY ===")
    for level, out in results.items():
        report(out, level)


if __name__ == "__main__":
    main()
