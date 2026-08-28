"""Killed-mutant battery for the A5 re-fit's decision machinery.

R28-corollary: a decision rule encoded in code can still route wrongly, so
drive it with synthetic tables sitting on BOTH sides of every threshold
BEFORE any real data exists. R21: also assert the SILENCE — a check that has
never been shown to stay quiet is not yet a check.

Run: python3 test_fit2_gates.py   (exits 1 on any failure)
"""
import sys
import numpy as np

sys.path.insert(0, ".")
import m2_screens as M

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
    if not ok:
        FAILS.append(name)


# ---------------------------------------------------------------- _verdict
print("[1] _verdict on both sides of every threshold "
      f"(GO>={M.GO_BAR} & LB>{M.LB_BAR}; KILL if UB<{M.LB_BAR})")
check("clear GO", M._verdict(0.20, 0.15, 0.25), "GO")
check("cap ok but LB at the bar (not above) -> not GO",
      M._verdict(0.20, M.LB_BAR, 0.25), "BETWEEN")
check("cap just under GO bar -> BETWEEN",
      M._verdict(M.GO_BAR - 1e-9, 0.15, 0.25), "BETWEEN")
check("cap exactly at GO bar with LB above -> GO",
      M._verdict(M.GO_BAR, 0.1, 0.25), "GO")
check("clear KILL", M._verdict(0.02, -0.01, 0.05), "KILL")
check("UB exactly at the bar -> not KILL",
      M._verdict(0.02, -0.01, M.LB_BAR), "BETWEEN")
check("UB just under the bar -> KILL",
      M._verdict(0.02, -0.01, M.LB_BAR - 1e-9), "KILL")
check("today's pre-A5 reading reproduces BETWEEN",
      M._verdict(0.0645, 0.0123, 0.1305), "BETWEEN")
check("A5's target: same point estimate, tightened CI -> KILL",
      M._verdict(0.0645, 0.0295, 0.0995), "KILL")
check("high cap but CI straddles zero -> BETWEEN",
      M._verdict(0.20, -0.05, 0.45), "BETWEEN")

# --------------------------------------------------------- P/S1 agreement
print("[2] sec 5.2 P-and-S1 agreement rule")


def route(p, s1):
    return p if p == s1 else "BETWEEN"


check("both GO", route("GO", "GO"), "GO")
check("both KILL", route("KILL", "KILL"), "KILL")
check("GO vs BETWEEN -> no verdict", route("GO", "BETWEEN"), "BETWEEN")
check("KILL vs BETWEEN -> no verdict", route("KILL", "BETWEEN"), "BETWEEN")
check("GO vs KILL -> no verdict", route("GO", "KILL"), "BETWEEN")

# ------------------------------------------------------------------ dedup
print("[3] dedup + label-identity gate")


def row(seed, ply, ev, danger=True, origin="L20", to_end=5):
    return {"seed": seed, "ply": ply, "ci": 0,
            "X": np.zeros((2, len(M.FEATS))),
            "s2full": np.array([1.0, 2.0]), "dec": np.array([1.0, 2.0]),
            "ev": np.array(ev, float), "val": np.array([0.0, 1.0]),
            "danger": danger, "origin": origin, "to_end": to_end}


base = [row(1, 10, [0, 1]), row(1, 90, [0, 1])]
bfsame = [row(1, 10, [0, 1], origin="L20_backfill"),
          row(1, 11, [0, 2], origin="L20_backfill")]
rows, rep = M.dedup(base, bfsame)
check("duplicate (seed,ply) detected", rep["dup"], 1)
check("only the NEW backfill state is added", rep["bf_new"], 1)
check("pooled size = base + new (no double count)", len(rows), 3)
check("identical labels -> gate SILENT (R21 non-fault)", rep["mismatch"], [])

bfbad = [row(1, 10, [0, 3], origin="L20_backfill")]   # corrupted duplicate
_, repbad = M.dedup(base, bfbad)
check("MUTANT: divergent labels on a duplicate are caught",
      len(repbad["mismatch"]), 1)

# ------------------------------------------------------------- poststrat
print("[4] post-stratification")


def const_score(X):
    return np.zeros(len(X))


# gains are 0 for every row under a never-firing guard => weighting is inert
dens_flat = {0: .25, 1: .25, 2: .25, 3: .25}
inert = M.poststrat(base, const_score, -1e9, 1e9, dens_flat)
check("never-firing guard -> capture 0 under any density", inert, 0.0)


def make(to_end, ev1):
    r = row(1, 10, [0, ev1], to_end=to_end)
    return r


# bucket 0 rows gain 3, bucket 3 rows gain 0; a guard that always fires
def always(X):
    return np.array([0.0, 1.0])


rows2 = [make(1, 3), make(1, 3), make(50, 0)]
plain_mean, dose = M.plain(rows2, always, 1e9, -1e9)
check("plain mean over 3 rows (2 gain 3, 1 gains 0)",
      round(plain_mean, 4), 2.0)
check("dose = fire rate", dose, 1.0)
# base density says the [30,inf) bucket is 90% of danger states
ps = M.poststrat(rows2, always, 1e9, -1e9, {0: .1, 1: 0, 2: 0, 3: .9})
check("post-strat down-weights the oversampled near-death bucket",
      round(ps, 4), round(.1 * 3 + .9 * 0, 4))
# CONTROL (R21): when the density matches the sample, post-strat == plain
ps2 = M.poststrat(rows2, always, 1e9, -1e9,
                  {0: 2 / 3, 1: 0, 2: 0, 3: 1 / 3})
check("CONTROL: matching density reproduces the plain mean",
      round(ps2, 4), round(plain_mean, 4))
check("empty buckets renormalise (weights need not sum to 1)",
      round(M.poststrat(rows2, always, 1e9, -1e9,
                        {0: .2, 1: .5, 2: .5, 3: 1.8}), 4),
      round((.2 * 3 + 1.8 * 0) / 2.0, 4))

print()
if FAILS:
    print(f"FAILED {len(FAILS)}: {FAILS}")
    sys.exit(1)
print("ALL GATES GREEN — fit2 decision machinery exercised on both sides "
      "of every threshold, with a killed mutant and a silence control.")
