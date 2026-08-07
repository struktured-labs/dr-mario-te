#!/usr/bin/env python3
"""fixtures/runner.py -- replay ANY fixture in this directory against ANY
candidate config of the champion decide path.

WHAT A FIXTURE IS: a JSON dict with (at minimum) `seed` + `expected` (the
house failure-taxonomy outcome it must reproduce) plus EITHER nothing else
(a Hunt-A "solo play, no pressure" fixture -- replayed via
adversary_harness.play_seed) OR a `schedule` block (a Hunt-B adversarial
garbage schedule -- replayed via adversary_search.play_seed_adversarial,
the SAME function/mechanics ADVERSARIAL_PRESSURE.md's own holdout numbers
came from, not reimplemented here).

WHAT "ANY CANDIDATE CONFIG" MEANS HERE: this program's decide path
(eval47/reach_root.py::choose_base32) exposes exactly one tunable knob for
A/B'ing configs -- `ws` (the g_stranded root-only dose; ws=20 is the shipped
strand20 champion, ws=0 is the pre-#47 predecessor with no g_stranded term
at all -- TRANSFER_FILTER.md's own predecessor-A/B convention, reused
verbatim, not invented here). `--ws` on this runner threads straight into
that parameter. A genuinely different leaf/eval variant (not just a ws dose)
would need a new decide-path shim; that is out of scope for this runner and
is called out as a proposal follow-up in ADVERSARY_FINDINGS.md, not silently
assumed to work.

DETERMINISM: every fixture is fully reproducible from (seed, schedule, ws,
budget_halves, max_pills) alone -- adversary_harness.play_seed /
adversary_search.play_seed_adversarial both seed their internal RNGs off
`seed` (and `seed*1000+pills_placed` per-event), so no board/trace blob needs
to ship WITH a fixture for it to replay bit-identically; the `fatal_board`
field some fixtures carry is documentation/inspection material (what the
board looked like when this fixture was captured), not an input the runner
reads.

Usage:
    python runner.py                      # every *.json fixture in this dir, ws=20 (champion)
    python runner.py --ws 0               # same fixtures, pre-#47 predecessor config
    python runner.py --fixture fx_foo.json --ws 20
    python runner.py --json                # machine-readable summary to stdout

Exit code: 0 if every fixture's actual outcome matched its `expected` block,
1 otherwise (CI-usable: "every future core must pass this regression suite").
"""
from __future__ import annotations

import sys
import os
import json
import glob
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ADV = os.path.dirname(HERE)
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ADV, HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3", QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adversary_harness as AH   # noqa: E402
import adversary_search as ASX   # noqa: E402

BINS = ASX.BINS
SIZE_POOL = ASX.SIZE_POOL


def _schedule_from_fixture(sch):
    """fixture JSON stores fire/size_weights with STRING keys (JSON has no
    tuple keys) -- rebuild the (lo,hi)-tuple-keyed dict adversary_search.py's
    functions expect. Verbatim inverse of adversary_search.genome_to_jsonable."""
    fire = {}
    for lo, hi in BINS:
        fire[(lo, hi)] = sch["fire"][f"{lo}-{hi}"]
    size_weights = [sch["size_weights"][str(s)] for s in SIZE_POOL]
    return {"fire": fire, "size_weights": size_weights, "target_mode": sch["target_mode"]}


def replay_fixture(fixture, ws=20):
    """Replay one fixture at decide-path dose `ws`. Returns
    dict(result, pills, viruses_left, dies_ahead[, garbage_injected])."""
    old_ah_ws, old_as_ws = AH.WS, ASX.WS
    AH.WS = ws
    ASX.WS = ws
    try:
        max_pills = fixture.get("max_pills", 300)
        if fixture.get("schedule") is None:
            r = AH.play_seed(fixture["seed"], pressure=None, max_pills=max_pills)
            out = {"result": r["result"], "pills": r["pills"],
                   "viruses_left": r["viruses_left"], "dies_ahead": r["dies_ahead"]}
        else:
            schedule = _schedule_from_fixture(fixture["schedule"])
            budget = fixture.get("budget_halves", ASX.BUDGET_HALVES)
            r = ASX.play_seed_adversarial(fixture["seed"], schedule, budget=budget,
                                           max_pills=max_pills)
            out = {"result": r["result"], "pills": r["pills"],
                   "viruses_left": r["viruses_left"], "dies_ahead": r["dies_ahead"],
                   "garbage_injected": r["garbage_injected"]}
    finally:
        AH.WS, ASX.WS = old_ah_ws, old_as_ws
    return out


def _matches_expected(actual, expected):
    for k, v in expected.items():
        if actual.get(k) != v:
            return False
    return True


def load_fixtures(paths=None):
    if paths:
        files = paths
    else:
        files = sorted(glob.glob(os.path.join(HERE, "fx_*.json")))
    out = []
    for p in files:
        with open(p) as f:
            fx = json.load(f)
        fx["_path"] = p
        out.append(fx)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ws", type=int, default=20,
                     help="decide-path dose to replay against: 20=shipped strand20 "
                          "champion (default), 0=pre-#47 predecessor")
    ap.add_argument("--fixture", action="append", default=None,
                     help="specific fixture file(s); default = every fx_*.json here")
    ap.add_argument("--json", action="store_true", help="machine-readable summary only")
    a = ap.parse_args()

    fixtures = load_fixtures(a.fixture)
    if not fixtures:
        print("[runner] no fixtures found", file=sys.stderr)
        sys.exit(2)

    results = []
    n_pass = 0
    for fx in fixtures:
        actual = replay_fixture(fx, ws=a.ws)
        ok = _matches_expected(actual, fx["expected"])
        n_pass += int(ok)
        results.append({"id": fx.get("id", os.path.basename(fx["_path"])),
                         "ws": a.ws, "expected": fx["expected"], "actual": actual,
                         "pass": ok, "status": fx.get("status", "UNSPECIFIED")})
        if not a.json:
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] {fx.get('id', fx['_path'])} (ws={a.ws}, status={fx.get('status')}) "
                  f"expected={fx['expected']} actual={actual}")

    summary = {"ws": a.ws, "n": len(fixtures), "n_pass": n_pass,
               "n_fail": len(fixtures) - n_pass, "results": results}
    if a.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n[runner] {n_pass}/{len(fixtures)} fixtures reproduced their expected "
              f"failure at ws={a.ws}")

    sys.exit(0 if n_pass == len(fixtures) else 1)


if __name__ == "__main__":
    main()
