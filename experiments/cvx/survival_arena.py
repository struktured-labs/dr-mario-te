"""Tap-out survival screen.

The two-board race (`vs_sim.play_vs`) ends CLEAR on almost every game, so it
ranks a faster dirtier player above one that survives garbage. Couch losses
and the Hartford tape are tap-outs under bursts. This module plays one brain
against a garbage process fitted to data that is actually in the repo, and
reports tap-out rate, time-to-topout, and clear rate with intervals.

Default brain is the shipped θ400 search: winner leaf, DRCHAIN=180,
DRSTRAND=20. A holes-weight (or any other leaf) idea is scored on that search.
The unchained VsPolicy arms that gate (b) used are available only as a
diagnostic, behind `allow_legacy`, because that is the configuration that
crowned k_clock=40 and holes80 for the wrong reason.

Scenarios
---------
owner
    Couch-footage burst model. Fire probabilities and volley sizes are the
    pooled 2026-08-04 fit (61 volleys, 188 clears, 4 matches) committed under
    experiments/eval47/results/. This is the gate (b) pressure model.
hartford
    Expert-tape send model (`NutmegModel`) plus the clock stream at
    TRATE=0.020/s. The pinned calibration table in PREREG_GATEB.md calls
    0.020 the couch-equivalent rate on that path. 0.025 is harsher and is
    not the default.

The race arena's send-rule sweep (arena15/RESULT.md) is not a scenario.
It never reached the tape's top-out mix.

Usage
-----
    python3 experiments/cvx/survival_arena.py screen --arm fw_holes80 --n 40
    python3 experiments/cvx/survival_arena.py run --arm fw_winner --scenario owner --n 40
    python3 experiments/cvx/survival_arena.py retro --n 16 --workers 4

See SURVIVAL_ARENA.md.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import statistics
import sys
from collections import Counter

import repo_paths

repo_paths.install()

# Gate (b) block. Retro validation reuses it on purpose. A new candidate
# should use a seed block that does not overlap 36734..37932 or 40134..
GATE_B_SEED0 = 36734
GATE_B_STEP = 2
GATE_B_N = 600

GARBAGE_MIN_PILLS = 25
DIES_AHEAD_V = 12
T_LAT, FPR = 0.6, 0.35
DEFAULT_LEVEL = 11
DEFAULT_MAX_PILLS = 600
HARTFORD_TRATE = 0.020

# Point estimates printed in RESULT_GATEB.md / RESULT_FWLEAF.md (n=600).
PUBLISHED_TAPOUT = {
    "holes80": 146 / 600,
    "winner": 243 / 600,
    "kc40": 246 / 600,
    "fw_winner": 17 / 600,
    "fw_holes80": 33 / 600,
}

_ROOT = repo_paths.install()
_FIT_DIR = os.path.join(_ROOT, "experiments", "eval47", "results")
_BANKED_DIR = os.path.join(os.path.dirname(__file__), "gateb")


def _one_fit(pattern):
    hits = sorted(glob.glob(os.path.join(_FIT_DIR, pattern)))
    if len(hits) != 1:
        raise RuntimeError(f"expected one fit file for {pattern}, found {hits}")
    return hits[0]

# Published pooled fire table. The loader checks the JSON against these so a
# swapped fit file cannot silently become the screen.
_OWNER_FIRE = {
    "4-6": {"p": 0.32051282051282054, "n": 156, "hits": 50},
    "7-10": {"p": 0.7407407407407407, "n": 27, "hits": 20},
    "11-999": {"p": 0.4, "n": 5, "hits": 2},
}
_OWNER_SIZE_HIST = {2: 42, 3: 9, 4: 7, 5: 2, 6: 1}


class ArmError(ValueError):
    pass


def wilson_interval(k, n, z=1.959963984540054):
    """95% Wilson score interval for k successes in n trials."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    z2 = z * z
    den = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / den
    margin = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / den
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def bootstrap_median_ci(xs, n_boot=4000, seed=12345):
    """Median and percentile bootstrap CI. None when xs is empty."""
    if not xs:
        return None, (None, None)
    rng = random.Random(seed)
    k = len(xs)
    point = statistics.median(xs)
    meds = []
    for _ in range(n_boot):
        sample = [xs[rng.randrange(k)] for _ in range(k)]
        meds.append(statistics.median(sample))
    meds.sort()
    lo = meds[int(0.025 * n_boot)]
    hi = meds[min(n_boot - 1, int(0.975 * n_boot))]
    return point, (lo, hi)


def paired_diff_ci(a_flags, b_flags, n_boot=4000, seed=12345):
    """mean(b) - mean(a) with a seed-resampled 95% interval."""
    n = len(a_flags)
    if n == 0 or n != len(b_flags):
        raise ValueError("paired flags must be the same non-zero length")
    point = (sum(b_flags) - sum(a_flags)) / n
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        s = 0
        for _i in range(n):
            j = rng.randrange(n)
            s += b_flags[j] - a_flags[j]
        diffs.append(s / n)
    diffs.sort()
    lo = diffs[int(0.025 * n_boot)]
    hi = diffs[min(n_boot - 1, int(0.975 * n_boot))]
    return point, lo, hi


def mcnemar_p(b_only_a, b_only_b):
    """Two-sided exact McNemar p (binomial, p=0.5) on the discordant pairs."""
    n = b_only_a + b_only_b
    if n == 0:
        return 1.0
    k = min(b_only_a, b_only_b)
    if 2 * k == n:
        return 1.0
    log_term = -n * math.log(2.0)
    s = math.exp(log_term)
    for i in range(k):
        log_term += math.log(n - i) - math.log(i + 1)
        s += math.exp(log_term)
    return min(1.0, 2.0 * s)


def discordant(rows_a, rows_b, key="topout"):
    by_b = {r["seed"]: r for r in rows_b}
    only_a = only_b = 0
    flags_a = []
    flags_b = []
    for r in rows_a:
        if r["seed"] not in by_b:
            continue
        a = int(r[key])
        b = int(by_b[r["seed"]][key])
        flags_a.append(a)
        flags_b.append(b)
        if a and not b:
            only_a += 1
        elif b and not a:
            only_b += 1
    return only_a, only_b, flags_a, flags_b


def summarize(rows, n_boot=4000):
    n = len(rows)
    if n == 0:
        raise ValueError("no rows")
    top = sum(int(r["topout"]) for r in rows)
    won = sum(int(r["won"]) for r in rows)
    stall = sum(int(r.get("stall", 0)) for r in rows)
    ahead = sum(int(r.get("dies_ahead", 0)) for r in rows)
    tt = [float(r["elapsed_s"]) for r in rows if int(r["topout"])]
    tp = [int(r["pills"]) for r in rows if int(r["topout"])]
    med_s, ci_s = bootstrap_median_ci(tt, n_boot=n_boot)
    med_p, ci_p = bootstrap_median_ci(tp, n_boot=n_boot, seed=12346)
    w_lo, w_hi = wilson_interval(top, n)
    c_lo, c_hi = wilson_interval(won, n)
    return {
        "n": n,
        "tapout": top / n,
        "tapout_k": top,
        "tapout_ci95": [w_lo, w_hi],
        "clear": won / n,
        "clear_k": won,
        "clear_ci95": [c_lo, c_hi],
        "stall": stall / n,
        "dies_ahead": ahead / n,
        "dies_ahead_of_topouts": (ahead / top) if top else None,
        "time_to_topout_s_median": med_s,
        "time_to_topout_s_ci95": list(ci_s),
        "pills_to_topout_median": med_p,
        "pills_to_topout_ci95": list(ci_p),
        "n_topout": top,
    }


def _pp(x):
    if x is None:
        return "n/a"
    return f"{100.0 * x:.2f}%"


def _ci_pp(pair):
    if not pair or pair[0] is None:
        return "n/a"
    return f"[{100.0 * pair[0]:.2f}%, {100.0 * pair[1]:.2f}%]"


def _num(x, nd=1):
    if x is None:
        return "n/a"
    return f"{x:.{nd}f}"


def _seconds(x):
    text = _num(x)
    return text if text == "n/a" else f"{text} s"


def _span(pair):
    if not pair or pair[0] is None:
        return "n/a"
    return f"{_num(pair[0])}..{_num(pair[1])} s"


def format_summary(name, summary):
    s = summary
    lines = [
        f"{name}: n={s['n']}  tap-out {_pp(s['tapout'])} Wilson {_ci_pp(s['tapout_ci95'])}"
        f"  clear {_pp(s['clear'])} Wilson {_ci_pp(s['clear_ci95'])}",
        f"  time-to-topout median {_seconds(s['time_to_topout_s_median'])}"
        f" CI {_span(s['time_to_topout_s_ci95'])}"
        f"  (n_topout={s['n_topout']}; clears are censored and not in this median)",
        f"  pills-to-topout median {_num(s['pills_to_topout_median'], 0)}"
        f"  dies-ahead {_pp(s['dies_ahead'])}"
        f"  ({_pp(s['dies_ahead_of_topouts'])} of tap-outs)",
    ]
    return "\n".join(lines)


def format_paired(name_a, name_b, rows_a, rows_b):
    only_a, only_b, fa, fb = discordant(rows_a, rows_b)
    diff, lo, hi = paired_diff_ci(fa, fb)
    p = mcnemar_p(only_a, only_b)
    return (
        f"{name_b} - {name_a} tap-out {100.0 * diff:+.2f}pp"
        f" [{100.0 * lo:+.2f}, {100.0 * hi:+.2f}]"
        f"  McNemar {only_a}/{only_b} p={p:.4g}"
        f"  (paired n={len(fa)})"
    )


# --------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------

LEGACY_ARMS = {
    "winner": {"trunk": "winner", "k_clock": 0.0},
    "kc40": {"trunk": "winner", "k_clock": 40.0},
    "holes80": {"trunk": "winholes80", "k_clock": 0.0},
    "h80kc10": {"trunk": "winholes80", "k_clock": 10.0},
    "h80kc20": {"trunk": "winholes80", "k_clock": 20.0},
    "h80kc40": {"trunk": "winholes80", "k_clock": 40.0},
}

FIRMWARE_ARMS = {
    "fw_winner": {"leaf": "winner", "chain": 180, "strand": 20},
    "fw_holes80": {"leaf": "winholes80", "chain": 180, "strand": 20},
}


def parse_arm(name, allow_legacy=False, chain=None, strand=None):
    """Return a spec dict. Legacy names are refused unless allow_legacy."""
    if name in FIRMWARE_ARMS:
        spec = {"kind": "firmware", "arm": name, **FIRMWARE_ARMS[name]}
    elif name.startswith("leaf:"):
        leaf = name.split(":", 1)[1]
        if not leaf:
            raise ArmError("leaf: needs a fast_rtl_x variant name")
        spec = {"kind": "firmware", "arm": name, "leaf": leaf, "chain": 180, "strand": 20}
    elif name in LEGACY_ARMS:
        if not allow_legacy:
            hint = {
                "holes80": "fw_holes80",
                "winner": "fw_winner",
            }.get(name)
            extra = f" The shipping-search arm is {hint}." if hint else ""
            raise ArmError(
                f"{name} is the unchained VsPolicy search (no DRCHAIN, no DRSTRAND). "
                f"It is not a pre-hardware screen.{extra} "
                f"Pass allow_legacy only to reproduce gate (b)."
            )
        spec = {"kind": "legacy", "arm": name, **LEGACY_ARMS[name],
                "leaf": LEGACY_ARMS[name]["trunk"], "chain": 0, "strand": 0}
    else:
        raise ArmError(
            f"unknown arm {name!r}. Firmware arms: {sorted(FIRMWARE_ARMS)} "
            f"or leaf:<variant>. Legacy (diagnostic): {sorted(LEGACY_ARMS)}."
        )
    if spec["kind"] == "firmware":
        if chain is not None:
            spec["chain"] = int(chain)
        if strand is not None:
            spec["strand"] = int(strand)
        spec["k_clock"] = 0.0
    elif chain not in (None, 0) or strand not in (None, 0):
        raise ArmError("chain/strand overrides apply to the firmware brain, not a legacy arm")
    spec["theta400_search"] = spec["kind"] == "firmware" and spec["chain"] == 180 and spec["strand"] == 20
    spec["shipped_leaf"] = spec["theta400_search"] and spec["leaf"] == "winner"
    return spec


def assert_screenable(spec):
    if not spec["theta400_search"]:
        raise ArmError(
            f"{spec['arm']} is not on the shipped search "
            f"(need DRCHAIN=180 and DRSTRAND=20, got chain={spec['chain']} "
            f"strand={spec['strand']} kind={spec['kind']}). "
            f"Leaf ideas are screened as fw_<leaf> / leaf:<variant>."
        )


# --------------------------------------------------------------------------
# scenarios
# --------------------------------------------------------------------------

def load_owner_model():
    """Pooled couch-footage burst model. Distribution-matched to the committed fit.

    `sample()` draws a size by index into `volley_sizes`. The original footage
    order is not in the pooled summary (only the histogram). The per-side fit
    files hold the 61 observed sizes; concatenating them preserves that
    multiset. It is not the interleaved match order the September runs drew
    from, so a single seed need not replay a banked gate (b) row. The fire
    probabilities are the pooled table, checked against the published numbers.
    """
    from bursty_model import BurstyPressureModel

    pooled = json.load(open(_one_fit("*20260804_pooled_fit.json")))
    table = pooled["p_volley_within_k_by_clear_size"]
    for key, want in _OWNER_FIRE.items():
        got = table[key]
        if abs(got["p"] - want["p"]) > 1e-12 or got["n"] != want["n"] or got["hits"] != want["hits"]:
            raise RuntimeError(f"owner fit {key} drifted: {got} vs {want}")
    p1 = json.load(open(_one_fit("style_ensemble_v1/*20260804_P1_sending_fit.json")))
    p2 = json.load(open(_one_fit("style_ensemble_v1/*20260804_P2_sending_fit.json")))
    sizes = [int(x) for x in p1["volley_sizes"]] + [int(x) for x in p2["volley_sizes"]]
    hist = Counter(sizes)
    if dict(hist) != _OWNER_SIZE_HIST or len(sizes) != 61:
        raise RuntimeError(f"owner volley multiset drifted: {dict(hist)} n={len(sizes)}")
    return BurstyPressureModel(
        volley_sizes=sizes,
        gap_samples=[],
        p_within_k=table,
        k_seconds=float(pooled["k_seconds"]),
        n_volleys=int(pooled["n_volleys"]),
        n_clears=int(pooled["n_clears"]),
        n_matches=int(pooled["n_matches"]),
    )


def load_scenario(name):
    if name == "owner":
        return {"name": "owner", "trate": 0.0, "model": load_owner_model()}
    if name == "hartford":
        from nutmeg_model import NutmegModel
        return {"name": "hartford", "trate": HARTFORD_TRATE, "model": NutmegModel()}
    raise ArmError(f"unknown scenario {name!r}; want owner or hartford")


def _inject_halves(board, seed, pills_placed, k):
    """Same column/colour draw as pressure_rig_time._inject_garbage."""
    from drmario.faithful_game import EMPTY, LINK_NONE

    rng = random.Random(seed * 1000 + pills_placed)
    cols = rng.sample(range(board.cols), min(k, board.cols))
    placed = 0
    for c in cols:
        color = rng.randint(1, 3)
        if board.color[0, c] != EMPTY:
            continue
        r = 0
        while r < board.rows and board.color[r, c] != EMPTY:
            r += 1
        board.color[r, c] = color
        board.is_virus[r, c] = False
        board.link[r, c] = LINK_NONE
        placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed


def _clock_k(x):
    """Gate (b) / clock_play size draw. Kept bit-for-bit, including the gap."""
    return 2 if x < 0.73 else (3 if x < 0.90 else (4 if x < 0.95 else (8 if x >= 0.96 else 2)))


_DECIDERS = {}


def _decider_for(spec):
    repo_paths.install()
    key = (spec["kind"], spec.get("leaf"), spec.get("trunk"), spec.get("chain"),
           spec.get("strand"), float(spec.get("k_clock") or 0.0))
    if key in _DECIDERS:
        return _DECIDERS[key]
    if spec["kind"] == "firmware":
        from fw_brain import FirmwareBrain
        dec = FirmwareBrain(leaf=spec["leaf"], chain=spec["chain"], strand=spec["strand"])
        _DECIDERS[key] = ("fw", dec)
    else:
        from vs_choose import VsPolicy
        pol = VsPolicy(trunk=spec["trunk"], k_clock=float(spec["k_clock"]))
        _DECIDERS[key] = ("legacy", pol)
    return _DECIDERS[key]


def warmup(spec):
    repo_paths.install()
    kind, obj = _decider_for(spec)
    if kind == "fw":
        obj.warmup()
        return
    import numpy as np
    col = np.zeros(128, dtype=np.int8)
    vir = np.zeros(128, dtype=np.int8)
    col[15 * 8:(15 * 8 + 8)] = 1
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0,
           "opp_spawn_h": 0, "own_spawn_h": 0}
    obj.decide(col, vir, 1, 2, 1, 2, ctx)


def play_seed(seed, spec, scenario, level=DEFAULT_LEVEL, max_pills=DEFAULT_MAX_PILLS, choose=None):
    """One solo game. Garbage timing matches experiments/cvx/gate_b.py:play."""
    import numpy as np
    from bursty_model import inject_bursty_garbage
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    repo_paths.install()
    model = scenario["model"]
    trate = float(scenario["trate"])
    if choose is None:
        kind, obj = _decider_for(spec)
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    elapsed = 0.0
    garbage = 0
    res = "stall"
    v_at_topout = None
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0,
           "opp_spawn_h": 0, "own_spawn_h": 0}
    for _ in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        ctx["own_vleft"] = env.board.virus_count()
        ctx["own_t"] = elapsed
        if choose is not None:
            a = choose(env, col, vir, ctx)
        elif kind == "fw":
            a = obj.choose(env.board, env.cur, env.nxt)
        else:
            a = obj.decide(col, vir, int(env.cur.a), int(env.cur.b),
                           int(env.nxt.a), int(env.nxt.b), ctx)
        if a is None:
            break
        var, cc = a // 8, a % 8
        cols_involved = [cc] if var in (2, 3) else [cc, min(cc + 1, 7)]
        hmax = 0
        for tc in cols_involved:
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            h = 16 - min(filled) if filled else 0
            hmax = max(hmax, h)
        dt = T_LAT + FPR * max(0, 16 - hmax)
        elapsed += dt
        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_topout = env.board.virus_count()
            break
        if trunc:
            break
        landed = 0
        if env.pills_placed >= GARBAGE_MIN_PILLS:
            clear_size = max(0, occ_before + 2 - int(np.count_nonzero(env.board.color)))
            if clear_size > 0:
                landed += inject_bursty_garbage(env.board, model, seed, env.pills_placed, clear_size)
            if trate > 0.0:
                trng = random.Random(seed * 1000 + env.pills_placed + 777)
                if trng.random() < trate * dt:
                    k = _clock_k(trng.random())
                    landed += _inject_halves(env.board, seed, env.pills_placed + 500, k)
            garbage += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break
    vleft = v_at_topout if v_at_topout is not None else env.board.virus_count()
    row = {
        "seed": seed,
        "won": int(res == "clear"),
        "topout": int(res == "topout"),
        "stall": int(res == "stall"),
        "pills": env.pills_placed,
        "elapsed_s": round(elapsed, 1),
        "garbage": garbage,
        "vleft": int(vleft),
        "dies_ahead": int(res == "topout" and v_at_topout is not None and v_at_topout <= DIES_AHEAD_V),
        "how": res,
        "arm": spec["arm"],
        "scenario": scenario["name"],
        "brain": "theta400" if spec["theta400_search"] else spec["kind"],
        "leaf": spec["leaf"],
        "chain": spec["chain"],
        "strand": spec["strand"],
        "k_clock": spec.get("k_clock", 0.0),
        "trate": trate,
    }
    return row


def seeds_of(seed0, n, step):
    return [seed0 + i * step for i in range(n)]


def run_seeds(spec, scenario, seeds, workers=1):
    repo_paths.install()
    warmup(spec)
    if workers <= 1:
        return [play_seed(s, spec, scenario) for s in seeds]
    from concurrent.futures import ProcessPoolExecutor
    payload = [(s, spec, scenario["name"]) for s in seeds]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_play_job, payload, chunksize=1))


def _play_job(args):
    seed, spec, scenario_name = args
    repo_paths.install()
    scenario = load_scenario(scenario_name)
    return play_seed(seed, spec, scenario)


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def read_jsonl(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_banked(arm, directory=_BANKED_DIR):
    rows = []
    for path in sorted(glob.glob(os.path.join(directory, f"{arm}_*.jsonl"))):
        rows.extend(read_jsonl(path))
    by = {}
    for r in rows:
        by.setdefault(int(r["seed"]), r)
    return [by[s] for s in sorted(by)]


def how_agreement(live, banked):
    by = {int(r["seed"]): r for r in banked}
    n = match = 0
    for r in live:
        b = by.get(int(r["seed"]))
        if b is None:
            continue
        n += 1
        if r["how"] == b["how"] and int(r["topout"]) == int(b["topout"]):
            match += 1
    return match, n


def retro_report(live_by_arm=None, n_boot=2000):
    """Text report. Banked gate (b) is the recorded corpus. live_by_arm is optional."""
    lines = []
    lines.append("# Survival arena — retroactive check")
    lines.append("")
    lines.append("Banked rows are the gate (b) jsonl under `experiments/cvx/gateb/`")
    lines.append("(owner burst model, L11, cap 600, seeds 36734 step 2).")
    lines.append("Published tap-out rates: holes80 24.33%, winner 40.50%, kc40 41.00%,")
    lines.append("fw_winner 2.83%, fw_holes80 5.50% (RESULT_GATEB.md, RESULT_FWLEAF.md).")
    lines.append("Time-to-topout was not in those tables; it is computed here from the same rows.")
    lines.append("The median is conditional on tapping out. Clears are censored, not zeros.")
    lines.append("")
    banked = {}
    for arm in ("holes80", "winner", "kc40", "fw_winner", "fw_holes80"):
        rows = load_banked(arm)
        banked[arm] = rows
        s = summarize(rows, n_boot=n_boot)
        lines.append(format_summary(f"banked {arm}", s))
        pub = PUBLISHED_TAPOUT[arm]
        lines.append(f"  published tap-out {_pp(pub)}; banked minus published {100.0 * (s['tapout'] - pub):+.3f}pp")
        lines.append("")
    lines.append(format_paired("holes80", "kc40", banked["holes80"], banked["kc40"]))
    lines.append(format_paired("winner", "kc40", banked["winner"], banked["kc40"]))
    lines.append(format_paired("fw_winner", "fw_holes80", banked["fw_winner"], banked["fw_holes80"]))
    lines.append("")
    if not live_by_arm:
        lines.append("No fresh games in this report. Run `retro --live` to resimulate.")
        return "\n".join(lines) + "\n", banked
    lines.append("## Fresh games (this code, same seeds as the prefix of the banked block)")
    lines.append("")
    lines.append("Owner fire probabilities match the pooled fit. Volley-size draws use the")
    lines.append("committed 61-size multiset, not the original interleaved footage order, so")
    lines.append("seed-level identity with the September rows is not guaranteed. Firmware games")
    lines.append("use FirmwareBrain (link-faithful fixpoint + DRCHAIN + root DRSTRAND). The")
    lines.append("September fw_* rows used StrandedChainD3Decider from a module that is not in")
    lines.append("this checkout. Agreement below is the empirical check, not an assumption.")
    lines.append("")
    for arm, rows in live_by_arm.items():
        s = summarize(rows, n_boot=n_boot)
        lines.append(format_summary(f"live {arm}", s))
        if arm in banked:
            match, n = how_agreement(rows, banked[arm])
            same = [r for r in banked[arm] if int(r["seed"]) in {int(x["seed"]) for x in rows}]
            sb = summarize(same, n_boot=max(200, n_boot // 4))
            lines.append(
                f"  same-seed banked tap-out {_pp(sb['tapout'])} (n={sb['n']}); "
                f"how-agreement {match}/{n}"
            )
        if arm in PUBLISHED_TAPOUT:
            lines.append(f"  full-corpus published tap-out {_pp(PUBLISHED_TAPOUT[arm])}")
        lines.append("")
    if "kc40" in live_by_arm and "holes80" in live_by_arm:
        lines.append(format_paired("holes80", "kc40", live_by_arm["holes80"], live_by_arm["kc40"]))
    if "fw_winner" in live_by_arm and "fw_holes80" in live_by_arm:
        lines.append(format_paired("fw_winner", "fw_holes80", live_by_arm["fw_winner"], live_by_arm["fw_holes80"]))
    if "kc40" in live_by_arm and "winner" in live_by_arm:
        lines.append(format_paired("winner", "kc40", live_by_arm["winner"], live_by_arm["kc40"]))
    lines.append("")
    return "\n".join(lines) + "\n", banked


def _cmd_run(args):
    spec = parse_arm(args.arm, allow_legacy=args.legacy, chain=args.chain, strand=args.strand)
    if args.screen and not spec["theta400_search"]:
        raise ArmError("screen mode refuses a non-shipping search")
    scenario = load_scenario(args.scenario)
    seeds = seeds_of(args.seed0, args.n, args.step)
    rows = run_seeds(spec, scenario, seeds, workers=args.workers)
    if args.out:
        write_jsonl(args.out, rows)
    print(format_summary(args.arm, summarize(rows)))
    if not spec["theta400_search"]:
        print("NOTE: this arm is not the shipped θ400 search. Not a couch screen.")
    elif not spec["shipped_leaf"]:
        print("NOTE: search is θ400 (DRCHAIN=180, DRSTRAND=20); leaf is not the shipped winner leaf.")
    return rows


def _cmd_screen(args):
    spec = parse_arm(args.arm, allow_legacy=False, chain=args.chain, strand=args.strand)
    assert_screenable(spec)
    scenario = load_scenario(args.scenario)
    seeds = seeds_of(args.seed0, args.n, args.step)
    ref = parse_arm("fw_winner")
    print(f"screen {args.arm} vs fw_winner  scenario={args.scenario}  n={args.n}  seed0={args.seed0}", flush=True)
    cand = run_seeds(spec, scenario, seeds, workers=args.workers)
    base = run_seeds(ref, scenario, seeds, workers=args.workers)
    print(format_summary(args.arm, summarize(cand)))
    print(format_summary("fw_winner", summarize(base)))
    print(format_paired("fw_winner", args.arm, base, cand))
    if args.n < 200:
        print("NOTE: on the shipped brain these scenarios tap out only a few percent of games.")
        print("n<200 will not resolve a 2–3 point harm. The recorded holes-leaf result used n=600.")
    print("Bar used by the September firmware prereg: tap-out not worse than the reference")
    print("(upper 95% of the paired difference <= +2pp). Race clear-rate is not the bar.")
    if args.out:
        write_jsonl(args.out, cand)
        write_jsonl(os.path.splitext(args.out)[0] + ".fw_winner.jsonl", base)


def _cmd_summary(args):
    groups = {}
    for path in args.inputs:
        for r in read_jsonl(path):
            groups.setdefault(r.get("arm", path), []).append(r)
    names = list(groups)
    for name in names:
        print(format_summary(name, summarize(groups[name])))
    if len(names) == 2:
        print(format_paired(names[0], names[1], groups[names[0]], groups[names[1]]))


def _cmd_retro(args):
    live = None
    if args.live:
        seeds = seeds_of(GATE_B_SEED0, args.n, GATE_B_STEP)
        scenario = load_scenario("owner")
        live = {}
        arms = ["holes80", "winner", "kc40", "fw_winner", "fw_holes80"]
        for arm in arms:
            spec = parse_arm(arm, allow_legacy=True)
            print(f"live {arm} n={args.n}", flush=True)
            rows = run_seeds(spec, scenario, seeds, workers=args.workers)
            live[arm] = rows
            if args.out_dir:
                write_jsonl(os.path.join(args.out_dir, f"live_{arm}.jsonl"), rows)
    text, _banked = retro_report(live, n_boot=args.boot)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as fh:
            fh.write(text)
    print(text, end="")


def build_parser():
    p = argparse.ArgumentParser(description="Tap-out survival screen (not the race arena).")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="play one arm")
    r.add_argument("--arm", required=True)
    r.add_argument("--scenario", default="owner", choices=("owner", "hartford"))
    r.add_argument("--n", type=int, default=20)
    r.add_argument("--seed0", type=int, default=51000)
    r.add_argument("--step", type=int, default=2)
    r.add_argument("--workers", type=int, default=1)
    r.add_argument("--legacy", action="store_true")
    r.add_argument("--chain", type=int, default=None)
    r.add_argument("--strand", type=int, default=None)
    r.add_argument("--screen", action="store_true", help="refuse a non-shipping search")
    r.add_argument("--out")
    r.set_defaults(func=_cmd_run)

    s = sub.add_parser("screen", help="leaf-on-θ400 vs fw_winner")
    s.add_argument("--arm", required=True)
    s.add_argument("--scenario", default="owner", choices=("owner", "hartford"))
    s.add_argument("--n", type=int, default=40)
    s.add_argument("--seed0", type=int, default=51000)
    s.add_argument("--step", type=int, default=2)
    s.add_argument("--workers", type=int, default=1)
    s.add_argument("--chain", type=int, default=None)
    s.add_argument("--strand", type=int, default=None)
    s.add_argument("--out")
    s.set_defaults(func=_cmd_screen)

    m = sub.add_parser("summary", help="summarise jsonl")
    m.add_argument("inputs", nargs="+")
    m.set_defaults(func=_cmd_summary)

    t = sub.add_parser("retro", help="score the recorded gate (b) corpus; --live resimulates")
    t.add_argument("--live", action="store_true")
    t.add_argument("--n", type=int, default=16)
    t.add_argument("--workers", type=int, default=1)
    t.add_argument("--boot", type=int, default=2000)
    t.add_argument("--out-dir", default=None)
    t.add_argument("--out", default=None)
    t.set_defaults(func=_cmd_retro)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except ArmError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
