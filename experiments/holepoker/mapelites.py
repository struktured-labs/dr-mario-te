#!/usr/bin/env python3
"""MAP-ELITES ARCHIVE OF HOLES — coverage, not damage.

A best-first search always follows its most promising line, finds ONE hole
family, and presents it as "the champion's weakness". The deliverable is a
TAXONOMY, so diversity is the objective. This keeps an ARCHIVE binned by each
kill's CHARACTER (classify.py: escape depth x region x mechanism x virus bin),
retains the best exemplar PER CELL rather than the global best, and reports
COVERAGE alongside contents — an empty cell being a first-class result: it means
that kind of hole does not exist for this champion within the effort spent.

EXPLORATION OPERATOR. The natural mutation axis is the ADVERSARY'S OBJECTIVE:
different score weightings produce structurally different attacks (flood the
board, squeeze the spawn lane, rush, or stay alive and grind), which is what
reaches different mechanism cells. Each trial samples (seed, weights); weights
are mutated from a random elite most of the time and drawn fresh otherwise, so
the search cannot collapse into the first productive family.

QUALITY within a cell = shallowest kill (smallest K), tie-broken by less garbage
spent. A short kill is the cleanest demonstration of its mechanism.

⚠ BOUNDED, not hoped-for: an explicit per-worker RSS ceiling checked every beam
ply, and a bounded frontier. This box has been OOM-killed 5x by unbounded jobs;
an OOM that takes the owner's desktop is worse than a shallower search. The
persistent champion store means an early exit loses no computed work.
"""
from __future__ import annotations
import sys, os, json, time, random, argparse, copy, resource
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import champion as CH      # noqa: E402
import poker as PK         # noqa: E402
import vs_poker as VP      # noqa: E402
import classify as CL      # noqa: E402

OUT_DIR = os.environ.get("HP_ARCHIVE_DIR", "/mnt/data/drmario_adversary/archive")
RSS_LIMIT_GB = float(os.environ.get("HP_RSS_GB", "4.0"))   # PER WORKER


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2


# ------------------------------------------------------------------ objective
def sample_weights(rng, base=None):
    if base is None:
        return {"w_sent": rng.uniform(0.5, 6.0),
                "w_self": rng.uniform(0.0, 3.0),
                "w_champ_top": rng.uniform(0.5, 4.0),
                "w_champ_fill": rng.uniform(0.0, 2.0),
                "w_rush": rng.uniform(0.0, 2.0)}
    w = dict(base)
    for k in w:
        if rng.random() < 0.5:
            w[k] = max(0.0, w[k] * rng.uniform(0.5, 1.8) + rng.uniform(-0.3, 0.3))
    return w


def score_weighted(m, sent, w):
    """Continuous generalisation of vs_poker.score_state. Lower is better."""
    cb, ab = m.env[VP.CHAMP].board, m.env[VP.ADV].board
    return (-w["w_sent"] * sent
            - w["w_self"] * PK.spawn_top(ab)
            + w["w_champ_top"] * PK.spawn_top(cb)
            - w["w_champ_fill"] * int((cb.color != 0).sum()) * 0.01
            + w["w_rush"] * cb.virus_count() * 0.1)


# --------------------------------------------------------------- traced ply
def ply_traced(m, adv_action):
    """VP.ply, additionally recording the CHAMPION's per-ply signals so the
    mechanism can be classified afterwards (classify.mechanism_of)."""
    m.deliver(VP.ADV)
    if m.env[VP.ADV].board.spawn_blocked():
        return "adv_dead", 0, None
    before = m.attacks_sent[VP.ADV]
    done, res = m.step(VP.ADV, adv_action)
    sent = m.attacks_sent[VP.ADV] - before
    m.hp_cursor[VP.ADV] += 1
    if done:
        return ("adv_clear" if res == "clear" else "adv_dead"), sent, None
    VP.reseat(m, VP.ADV)

    e = m.env[VP.CHAMP]
    g_in = len(m.pending[VP.CHAMP])
    legal_pre = int(e.action_masks().sum())
    m.deliver(VP.CHAMP)
    if e.board.spawn_blocked():
        # DIED ON DELIVERY: the garbage itself blocked the spawn cells. Record
        # the legal count from BEFORE delivery -- after it there are none by
        # definition, and feeding that 0 to the classifier would make
        # "forced_overstack" fire on every death regardless of mechanism.
        return "champ_dead", sent, _rec(m, g_in, legal_pre, 0, 0,
                                        died_on_delivery=True)
    legal = int(e.action_masks().sum())
    a = VP.champ_decide(m)
    if a is None:
        return "champ_dead", sent, _rec(m, g_in, legal, 0, 0)
    v_before = e.board.virus_count()
    occ_before = int((e.board.color != 0).sum())
    done, res = m.step(VP.CHAMP, a)
    m.hp_cursor[VP.CHAMP] += 1
    cleared = max(0, occ_before + 2 - int((e.board.color != 0).sum()))
    chain = 2 if (cleared > 4 and v_before != e.board.virus_count()) else (1 if cleared else 0)
    rec = _rec(m, g_in, legal, cleared, chain)
    if done:
        return ("champ_clear" if res == "clear" else "champ_dead"), sent, rec
    VP.reseat(m, VP.CHAMP)
    return None, sent, rec


def _rec(m, g_in, legal, cleared, chain, died_on_delivery=False):
    from terms47 import g_stranded
    b = m.env[VP.CHAMP].board
    col, vir = CH.board_to_flat(b)
    return {"garbage_in": int(g_in), "legal": int(legal),
            "stranded": int(g_stranded(col, vir)), "cleared": int(cleared),
            "chain": int(chain), "spawn_top": int(PK.spawn_top(b)),
            "died_on_delivery": bool(died_on_delivery)}


# ------------------------------------------------------------------- search
def vs_beam_w(seed, level, w, width=12, max_plies=80):
    m0 = VP.new_match(seed, level)
    v_start = m0.env[VP.CHAMP].board.virus_count()
    frontier = [(m0, [], 0, [])]
    calls = 0
    for d in range(max_plies):
        nxt = []
        for m, path, sent, trace in frontier:
            for a in VP.adv_legal(m):
                mm = copy.deepcopy(m)
                calls += 1
                status, sd, rec = ply_traced(mm, a)
                ntrace = (trace + [rec])[-10:] if rec else trace
                if status == "champ_dead":
                    cb = mm.env[VP.CHAMP].board
                    return {"killed": True, "plies": d + 1, "path": path + [a],
                            "garbage_sent": sent + sd, "calls": calls,
                            "seed": seed, "level": level, "weights": w,
                            "trace": ntrace, "v_start": int(v_start),
                            "v_left": int(cb.virus_count()),
                            "final_col": CH.board_to_flat(cb)[0].tolist(),
                            "final_vir": CH.board_to_flat(cb)[1].tolist()}
                if status is not None:
                    continue
                nxt.append((mm, path + [a], sent + sd, ntrace))
        if not nxt:
            return {"killed": False, "plies": d, "reason": "no surviving lines",
                    "calls": calls, "seed": seed, "weights": w}
        nxt.sort(key=lambda t: score_weighted(t[0], t[2], w))
        frontier = nxt[:width]
        if rss_gb() > RSS_LIMIT_GB:
            return {"killed": False, "plies": d, "reason": "rss cap",
                    "calls": calls, "seed": seed, "weights": w}
    return {"killed": False, "plies": max_plies, "reason": "cap",
            "calls": calls, "seed": seed, "weights": w}


# --------------------------------------------------------------- worker side
_DB = None


def _init(use_db):
    CH.init_champion()
    global _DB
    if use_db:
        import memo_db
        _DB = memo_db.ChampionMemo(max_local=250_000, flush_every=20_000)
        CH.attach_db(_DB)


def _trial(spec):
    t0 = time.time()
    r = vs_beam_w(spec["seed"], spec["level"], spec["weights"],
                  width=spec["width"], max_plies=spec["max_plies"])
    r["secs"] = round(time.time() - t0, 1)
    if r.get("killed"):
        # escape depth on the SAME (now replayable) line
        import vs_escape as VE
        try:
            esc = VE.escape_for_kill(spec["seed"], spec["level"], r["path"],
                                     r["plies"], max_E=8,
                                     verify=True, verify_plies=10, verify_width=6)
        except Exception as e:                       # never lose a kill to this
            esc = {"E": None, "ply": None, "alt": None, "avoidable": False,
                   "error": repr(e)}
        r["E"] = esc["E"]
        r["escape_ply"] = esc["ply"]
        b = CH.board_from_flat(r["final_col"], r["final_vir"])
        r["descriptor"] = CL.descriptor(esc["E"], b, r["v_left"], r["v_start"],
                                        r.get("trace") or [])
    if _DB is not None:
        _DB.flush()
        r["db"] = _DB.info()
    r["rss_gb"] = round(rss_gb(), 2)
    return r


# ------------------------------------------------------------------ archive
class Archive:
    def __init__(self):
        self.cells = {}
        self.trials = 0
        self.kills = 0

    def consider(self, r):
        self.trials += 1
        if not r.get("killed") or not r.get("descriptor"):
            return None
        self.kills += 1
        k = CL.cell_key(r["descriptor"])
        cur = self.cells.get(k)
        better = (cur is None or r["plies"] < cur["plies"]
                  or (r["plies"] == cur["plies"]
                      and r.get("garbage_sent", 99) < cur.get("garbage_sent", 99)))
        if better:
            self.cells[k] = {key: r[key] for key in
                             ("seed", "level", "plies", "path", "garbage_sent",
                              "E", "escape_ply", "v_start", "v_left",
                              "descriptor", "weights", "final_col", "final_vir")
                             if key in r}
            return k
        return None

    def coverage(self):
        return len(self.cells), CL.total_cells()

    def elites(self):
        return list(self.cells.values())

    def under_filled_axes(self):
        """Which mechanism / escape bins are empty -- used to steer sampling."""
        have_m = {k[2] for k in self.cells}
        have_e = {k[0] for k in self.cells}
        return ([m for m in CL.MECHANISMS if m not in have_m],
                [e for e in CL.ESCAPE_BINS if e not in have_e])

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        filled, total = self.coverage()
        with open(path, "w") as fh:
            json.dump({"filled": filled, "total": total,
                       "trials": self.trials, "kills": self.kills,
                       "cells": [{"cell": list(k), **v}
                                 for k, v in self.cells.items()]}, fh, default=str)

    def report(self):
        filled, total = self.coverage()
        lines = [f"ARCHIVE: {filled}/{total} cells filled  "
                 f"({self.kills} kills / {self.trials} trials)"]
        from collections import Counter
        for axis, idx in (("escape", 0), ("region", 1), ("mechanism", 2),
                          ("virus", 3)):
            c = Counter(k[idx] for k in self.cells)
            lines.append(f"  {axis:9s}: " +
                         "  ".join(f"{a}={n}" for a, n in sorted(c.items())))
        return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--width", type=int, default=12)
    ap.add_argument("--max-plies", type=int, default=80)
    ap.add_argument("--no-db", action="store_true")
    ap.add_argument("--out", type=str, default=os.path.join(OUT_DIR, "archive.json"))
    a = ap.parse_args()

    rng = random.Random(20260806)
    arch = Archive()
    print(f"=== MAP-ELITES: {a.trials} trials, {a.workers} workers, "
          f"L{a.level}, {CL.total_cells()} cells ===", flush=True)
    t0 = time.time()

    pending = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(not a.no_db,)) as ex:
        def submit(n):
            for _ in range(n):
                elites = arch.elites()
                # 60% mutate from an elite, 40% fresh -- explicit exploration
                base = (rng.choice(elites)["weights"]
                        if elites and rng.random() < 0.6 else None)
                pending.append(ex.submit(_trial, {
                    "seed": rng.randrange(a.seeds), "level": a.level,
                    "weights": sample_weights(rng, base), "width": a.width,
                    "max_plies": a.max_plies}))

        submit(min(a.trials, a.workers * 3))
        done = 0
        while done < a.trials:
            nxt = []
            for f in as_completed(list(pending)):
                pending.remove(f)
                r = f.result()
                done += 1
                newcell = arch.consider(r)
                if newcell:
                    d = r["descriptor"]
                    print(f"  [{done}/{a.trials}] NEW CELL {newcell}  seed={r['seed']} "
                          f"K={r['plies']} E={r['E']} {r['secs']}s", flush=True)
                elif done % 20 == 0:
                    filled, total = arch.coverage()
                    dbi = r.get("db") or {}
                    print(f"  [{done}/{a.trials}] cov={filled}/{total} "
                          f"kills={arch.kills} memo={dbi.get('entries','-')} "
                          f"hit={dbi.get('hit_rate',0):.1%} rss={r.get('rss_gb')}GB "
                          f"{(time.time()-t0)/60:.0f}min", flush=True)
                if done % 25 == 0:
                    arch.save(a.out)
                    print(arch.report(), flush=True)
                if done + len(pending) < a.trials:
                    submit(1)
                break
            if not pending and done < a.trials:
                submit(min(a.workers, a.trials - done))
    arch.save(a.out)
    print("\n" + arch.report())
    print(f"wrote {a.out}  ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    main()
