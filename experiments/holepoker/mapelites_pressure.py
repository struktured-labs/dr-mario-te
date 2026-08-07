#!/usr/bin/env python3
"""MAP-ELITES ARCHIVE OF DEATHS — coverage, not damage.

A best-first search follows its most promising line, finds ONE death family, and
presents it as "the champion's weakness". The deliverable is a TAXONOMY, so
DIVERSITY is the objective and an EMPTY CELL IS A RESULT.

GENOTYPE (what the search varies)  : the pressure schedule -- seed, halves per
    drip `k`, `period`, `after`, and a column bias that aims garbage at the
    spawn lane, the edges, or nowhere. Different schedules produce structurally
    different deaths, which is what reaches different cells.
PHENOTYPE (what a death IS)        : classify.descriptor --
    escape-depth bin x board region x mechanism x virus bin.
QUALITY within a cell              : FEWEST GARBAGE HALVES delivered before the
    death, tie-broken by the earlier death. A death that needed less help is the
    sharper demonstration of its mechanism.

TWO RULES THE LEAD ASKED FOR, both earned the hard way tonight:
  * REPLAY GATE IS A PRECONDITION FOR ADMISSION. An elite that cannot reproduce
    from its own (seed, schedule) is not an elite, it is an anecdote. Two of my
    results this session were selection effects of my own instrument.
  * COVERAGE AND NULL CELLS ARE REPORTED WITH THE CONTENTS. An archive reported
    by its winners is the same selection effect.

EXOGENEITY IS REQUIRED, not preferred: the drip schedule keys its RNG on
(seed, ply), so deviating the champion leaves future pressure identical and the
escape-depth counterfactual isolates the move. The bursty model keys on the
champion's own clear size and CANNOT be used here.
"""
from __future__ import annotations
import sys, os, json, time, random, argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, "/home/struktured/projects/dr-mario-qa-wt/experiments"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import champion as CH            # noqa: E402
import classify as CL            # noqa: E402
import pressure_escape as PE     # noqa: E402

OUT_DIR = os.environ.get("HP_ARCHIVE_DIR", "/mnt/data/drmario_adversary/archive")
ESC_BINS = ("1", "2", "3", "4", "5", "6", "7", "8+", "none")


def sample_genotype(rng, base=None):
    if base is None:
        return {"k": rng.choice([1, 2, 2, 3]),
                "period": rng.choice([3, 4, 5, 6, 8, 10]),
                "after": rng.choice([10, 15, 20, 25, 30])}
    g = dict(base)
    if rng.random() < 0.5:
        g["k"] = max(1, min(4, g["k"] + rng.choice([-1, 1])))
    if rng.random() < 0.5:
        g["period"] = max(2, min(12, g["period"] + rng.choice([-2, -1, 1, 2])))
    if rng.random() < 0.5:
        g["after"] = max(5, min(40, g["after"] + rng.choice([-5, 5])))
    return g


def _init():
    CH.init_champion()
    import memo_db
    db = memo_db.ChampionMemo(max_local=200_000, flush_every=20_000)
    CH.attach_db(db)
    globals()["_DB"] = db


def _trial(spec):
    seed, level = spec["seed"], spec["level"]
    k, period, after = spec["k"], spec["period"], spec["after"]
    t0 = time.time()
    res, plies, trace, v0 = PE.play(seed, level, k, period, after)
    out = {"seed": seed, "level": level, "k": k, "period": period,
           "after": after, "result": res, "plies": plies, "v0": v0,
           "secs": round(time.time() - t0, 1)}
    if res not in ("topout", "nomove"):
        return out

    # ---- ADMISSION GATE 1: the death must reproduce before anything else runs
    r2, p2, _t2, _v2 = PE.play(seed, level, k, period, after, record=False)
    out["reproduced"] = bool(r2 == res and p2 == plies)
    if not out["reproduced"]:
        out["reject"] = f"replay gave {r2}@{p2}, stored {res}@{plies}"
        return out

    esc = PE.escape_depth(seed, level, k, period, after, trace, plies)
    # ---- ADMISSION GATE 2: a claimed escape must survive an independent replay
    if esc["E"] is not None:
        ok = PE.survives_with(seed, level, k, period, after, esc["ply"],
                              esc["alt"], plies)
        out["escape_verified"] = bool(ok)
        if not ok:
            out["reject"] = "claimed escape did not survive replay"
            return out
    out.update(E=esc["E"], escape_ply=esc["ply"], alt=esc["alt"])

    withb = [t for t in trace if "col" in t]
    if not withb:
        out["reject"] = "no board recorded"
        return out
    b = CH.board_from_flat(withb[-1]["col"], withb[-1]["vir"])
    v_left = int(sum(withb[-1]["vir"]))
    tail = [{kk: t[kk] for kk in ("garbage_in", "legal", "stranded", "cleared",
                                  "chain", "spawn_top", "died_on_delivery")
             if kk in t} for t in trace[-10:]]
    out["v_left"] = v_left
    out["garbage_total"] = sum(t.get("garbage_in", 0) for t in trace)
    out["descriptor"] = CL.descriptor(esc["E"], b, v_left, v0, tail)
    out["col"] = withb[-1]["col"]
    out["vir"] = withb[-1]["vir"]
    db = globals().get("_DB")
    if db is not None:
        db.flush()
        out["db_entries"] = db.info()["entries"]
        out["db_hit_rate"] = round(db.info()["hit_rate"], 3)
    return out


class Archive:
    def __init__(self):
        self.cells = {}
        self.trials = self.deaths = self.rejected = 0

    def consider(self, r):
        self.trials += 1
        if r["result"] not in ("topout", "nomove"):
            return None
        self.deaths += 1
        if r.get("reject") or not r.get("descriptor"):
            self.rejected += 1
            return None
        key = CL.cell_key(r["descriptor"])
        cur = self.cells.get(key)
        better = (cur is None
                  or r["garbage_total"] < cur["garbage_total"]
                  or (r["garbage_total"] == cur["garbage_total"]
                      and r["plies"] < cur["plies"]))
        if better:
            self.cells[key] = {kk: r[kk] for kk in
                               ("seed", "level", "k", "period", "after",
                                "plies", "E", "escape_ply", "alt", "v0",
                                "v_left", "garbage_total", "descriptor",
                                "col", "vir") if kk in r}
            return key
        return None

    def report(self):
        L = [f"ARCHIVE  {len(self.cells)}/{CL.total_cells()} cells filled "
             f"({len(self.cells)/CL.total_cells():.1%})  |  trials={self.trials} "
             f"deaths={self.deaths} admitted={self.deaths-self.rejected} "
             f"rejected_by_gate={self.rejected}"]
        # readable 2D projection: mechanism x escape bin
        L.append("\nMECHANISM x ESCAPE-DEPTH (cells filled; '.' = NULL)")
        hdr = "  " + f"{'mechanism':<20s}" + "".join(f"{e:>6s}" for e in ESC_BINS)
        L.append(hdr)
        grid = defaultdict(set)
        for (e, reg, mech, vb) in self.cells:
            grid[mech].add(e)
        for mech in CL.MECHANISMS:
            row = "".join(f"{'X' if e in grid[mech] else '.':>6s}" for e in ESC_BINS)
            L.append(f"  {mech:<20s}{row}")
        # marginals
        L.append("\nMARGINALS (filled cells per axis value; 0 = NULL region)")
        for axis, idx, vals in (("escape", 0, ESC_BINS), ("region", 1, CL.REGIONS),
                                ("mechanism", 2, CL.MECHANISMS),
                                ("virus", 3, CL.VIRUS_BINS)):
            c = Counter(k[idx] for k in self.cells)
            L.append(f"  {axis:10s} " +
                     "  ".join(f"{v}={c.get(v,0)}" for v in vals))
        nulls = [v for v in CL.MECHANISMS if not grid[v]]
        if nulls:
            L.append(f"\n  NULL MECHANISMS (no death of this character found): {nulls}")
        return "\n".join(L)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump({"filled": len(self.cells), "total": CL.total_cells(),
                       "trials": self.trials, "deaths": self.deaths,
                       "rejected_by_gate": self.rejected,
                       "null_mechanisms": [m for m in CL.MECHANISMS
                                           if not any(k[2] == m for k in self.cells)],
                       "cells": [{"cell": list(k), **v}
                                 for k, v in self.cells.items()]}, fh, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=300)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--levels", type=int, nargs="+", default=[11, 17])
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--out", type=str, default=os.path.join(OUT_DIR, "deaths_archive.json"))
    a = ap.parse_args()
    rng = random.Random(20260807)
    arch = Archive()
    print(f"=== MAP-ELITES over DEATHS: {a.trials} trials, {a.workers} workers, "
          f"{CL.total_cells()} cells ===", flush=True)
    t0 = time.time()
    specs = []
    for _ in range(a.trials):
        elites = list(arch.cells.values())
        g = sample_genotype(rng)
        specs.append({"seed": rng.randrange(a.seeds),
                      "level": rng.choice(a.levels), **g})
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(_trial, s) for s in specs]
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            new = arch.consider(r)
            if new:
                d = r["descriptor"]
                print(f"  [{i+1}/{a.trials}] NEW CELL {new}  seed={r['seed']} "
                      f"L{r['level']} k{r['k']}/p{r['period']} K={r['plies']} "
                      f"E={r['E']} garbage={r['garbage_total']}", flush=True)
            elif r.get("reject"):
                print(f"  [{i+1}/{a.trials}] REJECTED BY GATE: {r['reject']}",
                      flush=True)
            if (i + 1) % 50 == 0:
                arch.save(a.out)
                print(f"\n--- {(time.time()-t0)/60:.0f} min ---\n{arch.report()}\n",
                      flush=True)
    arch.save(a.out)
    print("\n" + arch.report())
    print(f"\nwrote {a.out}  ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    main()
