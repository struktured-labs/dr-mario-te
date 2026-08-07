#!/usr/bin/env python3
"""ws_sweep.py -- price the g_stranded dose (`ws`) on FAILURE RATE.

WHY THIS KNOB. The shipped champion uses ws=20 (memory: #47 g_stranded
SHIPPED TO SILICON), and that dose was selected on mirror margin (-9.85 REAL)
and VS win rate -- i.e. on SPEED and ATTACK. Nobody has ever priced ws on the
axis the owner actually judges the AI by at the TV: not topping out, and not
marooning halves. `terms47.g_stranded` literally counts marooned halves
(occupied non-virus cells with no same-colour orthogonal neighbour), so the
dose on that term is the most directly relevant single constant in the eval
for the failure axis -- and it is one constant, already live in silicon, so a
dose change is cheap to ship.

TWO-STAGE PROTOCOL (the design matters more than the numbers).

  Stage 1 SCREEN -- run candidate doses on the seeds where the champion
  ALREADY FAILS (harvested from the census). Cheap and high-signal: ~1% of
  seeds carry ~100% of the information about failures. Output = rescue count
  per dose.
  ⚠ Stage 1 is a BIASED objective by construction. Selecting on "rescues the
  champion's failures" says nothing about what a dose BREAKS elsewhere, and
  this project has repeatedly been burned by exactly that (memory:
  dr-mario-nes-pill-retune-negative, "tuning block = SEED BLOCK"). A stage-1
  win is a CANDIDATE, never a result.

  Stage 2 HOLDOUT -- take survivors to a large RANDOM seed sample, PAIRED
  (both arms on identical seeds) so the comparison is McNemar on discordant
  pairs rather than two noisy independent rates. At a ~1% base failure rate a
  paired design is the only affordable way to resolve the effect. Stage 2
  reports rescues AND breaks AND the pills-to-clear cost, because a dose that
  cuts topouts while slowing every clear is not obviously a win.

play_seed_ws() is a dose-parameterised copy of adversary_harness.play_seed.
It deliberately does NOT edit that shared module (a live local job imports
it). --selfcheck asserts this copy is bit-identical to the original at the
control dose ws=20, so the reimplementation cannot silently drift.
"""
from __future__ import annotations

import sys
import os
import json
import time
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")

import adversary_harness as AH  # noqa: E402

SHIPPED_WS = AH.WS   # 20


def play_seed_ws(seed, ws, pressure=None, max_pills=300,
                 g_k=None, g_period=None, g_min=None):
    """adversary_harness.play_seed with the g_stranded dose exposed.

    Mirrors that function exactly (same env construction, same NES pill
    source, same drip-pressure schedule, same termination taxonomy) except
    choose_base32 is called with the supplied `ws`. Verified against the
    original at ws=20 by --selfcheck, in BOTH pressure regimes.

    ⚠ The drip injection is keyed on (seed, pills_placed), so two arms that
    diverge in pill count see garbage on a different schedule. That is
    inherent to the pressure model (adversary_harness has the same property);
    it means the arms share a seed but not an identical garbage sequence once
    they diverge. Pairing is therefore on the SEED, which is the honest unit.
    """
    L = AH._lazy()
    RR, FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["RR"], L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    # Canonical drip = pressure_rig.py's (k=2, every 8 pills, after 25). The
    # knobs exist because at canonical strength the champion fails only ~2.5%
    # of the time, which cannot resolve a dose effect at affordable n. A
    # heavier schedule is a STRESS regime -- explicitly not the shipped one --
    # and any result from it must be labelled as such.
    g_k = AH.GARBAGE_K if g_k is None else g_k
    g_period = AH.GARBAGE_PERIOD if g_period is None else g_period
    g_min = AH.GARBAGE_MIN_PILLS if g_min is None else g_min

    pressure_fn = None
    if pressure is not None:
        base_fn = AH._PRESSURE_MODELS[pressure]
        pressure_fn = lambda b, s, p: base_fn(b, s, p, k=g_k)  # noqa: E731

    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    trace = []
    garbage_injected = 0
    for i in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a = RR.choose_base32(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), ws=ws)["action"]
        if a is None:
            res = "topout"
            break
        trace.append((i, int(a)))
        _, _, term, trunc, info = env.step(int(a))

        if pressure_fn is not None and not term and env.pills_placed >= g_min \
                and env.pills_placed % g_period == 0:
            garbage_injected += pressure_fn(env.board, seed, env.pills_placed)
            if env.board.virus_count() == 0:
                term, info = True, {"won": True}
            elif env.board.spawn_blocked():
                term, info = True, {"won": False}

        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            res = "stall"
            break

    vl = int(env.board.virus_count())
    return {"seed": seed, "ws": ws, "result": res, "pills": env.pills_placed,
            "viruses_left": vl,
            "dies_ahead": bool(res == "topout" and vl <= AH.DIES_AHEAD_VIRUS_THRESHOLD),
            "garbage_injected": garbage_injected,
            "n_moves": len(trace), "trace": trace}


def _job(args):
    seed, ws, pressure, g_k, g_period, g_min = args
    r = play_seed_ws(seed, ws, pressure=pressure,
                     g_k=g_k, g_period=g_period, g_min=g_min)
    r.pop("trace", None)
    return r


def selfcheck(n=6):
    """This copy must equal the shared harness at the control dose, or every
    number below is measuring my transcription instead of the dose.

    Checked in BOTH regimes: the clean path and the drip path exercise
    different code (the pressure branch, the mid-game spawn-block test), and
    a transcription error in the pressure branch would be invisible to a
    clean-only check -- which is precisely the arm the experiment runs in.
    """
    bad = []
    for pressure in (None, "drip"):
        for s in AH.SELFTEST_SEEDS[:n]:
            mine = play_seed_ws(s, SHIPPED_WS, pressure=pressure)
            theirs = AH.play_seed(s, pressure=pressure)
            same = (mine["result"] == theirs["result"]
                    and mine["pills"] == theirs["pills"]
                    and mine["viruses_left"] == theirs["viruses_left"]
                    and mine["garbage_injected"] == theirs["garbage_injected"]
                    and [list(t) for t in mine["trace"]] == [list(t) for t in theirs["trace"]])
            tag = pressure or "clean"
            print(f"  [{tag:5s}] seed {s}: {'MATCH' if same else 'DIVERGED'} "
                  f"({mine['result']}/{mine['pills']} vs {theirs['result']}/{theirs['pills']})",
                  flush=True)
            if not same:
                bad.append((tag, s))
    ok = not bad
    print(f"[selfcheck] {'PASS' if ok else 'FAIL ' + str(bad)} -- copy is "
          f"{'bit-identical to' if ok else 'DIFFERENT FROM'} adversary_harness "
          f"at ws={SHIPPED_WS} in both regimes")
    return ok


def load_done_pairs(path):
    """(seed, ws) pairs already on disk -- makes the sweep resumable, since it
    shares a box with a 15h census and will be interrupted."""
    done = set()
    if not os.path.exists(path):
        return done
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add((r["seed"], r["ws"]))
    return done


def run_grid(seeds, doses, workers, out_path, tag, pressure,
             g_k=None, g_period=None, g_min=None):
    all_jobs = [(s, w, pressure, g_k, g_period, g_min)
                for w in doses for s in seeds]
    done_pairs = load_done_pairs(out_path)
    jobs = [j for j in all_jobs if (j[0], j[1]) not in done_pairs]
    print(f"[{tag}] {len(seeds)} seeds x {len(doses)} doses = {len(all_jobs)} games "
          f"({len(done_pairs)} already done, {len(jobs)} to run), "
          f"pressure={pressure}, {workers} workers", flush=True)
    t0 = time.monotonic()
    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=workers, initializer=AH._lazy) as ex:
        futs = [ex.submit(_job, j) for j in jobs]
        with open(out_path, "a") as f:
            for fut in as_completed(futs):
                r = fut.result()
                rows.append(r)
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
                done += 1
                if done % 50 == 0:
                    f.flush()
                    os.fsync(f.fileno())
                    el = time.monotonic() - t0
                    print(f"[{tag}] {done}/{len(jobs)}  {done / el:.2f} g/s  "
                          f"ETA {(len(jobs) - done) / (done / el) / 60:.0f}m", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doses", type=int, nargs="+",
                    default=[0, 8, 20, 40, 80])
    ap.add_argument("--pressure", default="drip", choices=["drip", "clean"],
                    help="'drip' is the regime where failures actually occur; "
                         "the clean stream failure rate is <0.2% and cannot be "
                         "optimised against")
    ap.add_argument("--seed-lo", type=int, default=50000)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--garbage-k", type=int, default=None,
                    help="halves per injection (canonical 2)")
    ap.add_argument("--garbage-period", type=int, default=None,
                    help="inject every N pills (canonical 8)")
    ap.add_argument("--garbage-min", type=int, default=None,
                    help="first injection after N pills (canonical 25)")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    if a.selfcheck and not selfcheck():
        sys.exit("selfcheck failed -- refusing to produce numbers")

    pressure = None if a.pressure == "clean" else a.pressure

    # PAIRED design: every dose plays the SAME seeds, so the comparison is
    # within-seed (McNemar on discordant pairs) rather than two noisy rates.
    # At these effect sizes pairing is the only affordable way to resolve the
    # dose. Seeds are taken from high in this node's block; the census walks
    # UP from 32768 and will not reach them for many hours.
    seeds = list(range(a.seed_lo, a.seed_lo + a.n))
    run_grid(seeds, a.doses, a.workers, a.out, "sweep", pressure,
             a.garbage_k, a.garbage_period, a.garbage_min)


if __name__ == "__main__":
    main()
