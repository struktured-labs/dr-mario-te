#!/usr/bin/env python3
"""STAGE A2/A3 + STAGE B: is the champion's self-seal COSTLY and AVOIDABLE, and
does pricing it help?

Decider is eval47/ab47.py::_choose_base reused verbatim (wt=0, ws=20 --
fast_rtl_x.variant("winner") leaf + terms47.g_stranded root-only), i.e. the
shipped strand20 champion, exactly as portfolio/endgame-policy/seal_probe.py
used it.  The ONLY change per arm is an extra root-only cost added to each
candidate's value; arm "base" adds nothing and is bit-identical to the
champion.

ARMS
  base            champion, unmodified (control)
  pen_seal:W      value -= W * (new seals created by this candidate)
  pen_noopen:W    value -= W * (new no-open-window viruses created)
  veto_seal       hard veto: drop candidates creating a new seal, unless ALL
                  candidates do (equivalent to W=inf; the max dose)
  veto_noopen     ditto on the no-open-window metric
Gated on pre-placement virus_count <= --gate (the decider can see this).

AVOIDABILITY INSTRUMENTATION (recorded on every arm, read off "base"):
  at each gated decision we enumerate the full candidate set once and record
  best value, whether the argmax creates a new seal, the best value among
  candidates that do NOT, the resulting VALUE GAP, and -- as the scale
  reference the gap must be judged against -- the gap between the best and
  second-best candidate overall.  A seal is AVOIDABLE when a non-sealing
  candidate exists and costs little relative to that natural spread.

Board convention: flat int8[128], row-major idx = r*8+c, row 0 = TOP, colours
1-based, vir 1/0.  Candidate boards come from fast_sim_x._expand_core, which is
a CAP-1 resolve (single clear round), while env.step() runs full cascade
physics -- so candidate-level seal prediction can differ from the realised
board on cascading placements.  Realised per-game seal events are therefore
ALSO counted post-step off env.board with round-1's exact detector.
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3", QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SEAL_VC_THRESHOLD = 6      # round-1's post-placement counting threshold
H0 = 8
_C = {}


def parse_arm(arm):
    """-> (kind, weight). kind in {'base','seal','noopen'}; weight None = veto."""
    if arm == "base":
        return ("base", 0.0)
    if arm == "veto_seal":
        return ("seal", None)
    if arm == "veto_noopen":
        return ("noopen", None)
    if arm.startswith("pen_seal:"):
        return ("seal", float(arm.split(":", 1)[1]))
    if arm.startswith("pen_noopen:"):
        return ("noopen", float(arm.split(":", 1)[1]))
    raise ValueError("bad arm " + arm)


def _init(level, wt, ws, arm, gate):
    import numpy as np
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    from terms47 import g_tower, g_stranded
    import seal_terms as ST
    ST.warmup()
    z = np.zeros(128, dtype=np.int8)
    g_tower(z, z, H0)
    g_stranded(z, z)
    _C.update(level=level, wt=wt, ws=ws, w=w, fl=fl, arm=arm,
              kind=parse_arm(arm)[0], weight=parse_arm(arm)[1], gate=gate)


def _choose(col, vir, ca, cb, na, nb, w, fl, wt, ws, kind, weight, gated, instr):
    """Champion root search + optional seal cost.  Returns (action, rec) where
    rec is the per-decision avoidability record (or None when not gated)."""
    import numpy as np
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded
    from seal_terms import n_sealed, n_noopen

    # BOTH metrics are measured on every arm -- the arm only decides which one
    # (if any) steers the choice.  Measuring only the steering arm's metric
    # would make the control arm structurally incapable of reporting seals.
    base_seal = n_sealed(col, vir) if gated else 0
    base_noop = n_noopen(col, vir) if gated else 0

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    cands = []                      # (raw_val, new_seal, new_noopen, action)
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            ns = no = 0
            if gated:
                ns = max(0, int(n_sealed(c1, v1)) - base_seal)
                no = max(0, int(n_noopen(c1, v1)) - base_noop)
            cands.append((val, ns, no, var * 8 + cc))

    if not cands:
        return None, None

    # ---- instrumentation on the UNMODIFIED champion ranking ---------------
    rec = None
    if gated and instr:
        srt = sorted(cands, key=lambda t: -t[0])
        best_val = srt[0][0]
        gap2 = (best_val - srt[1][0]) if len(srt) > 1 else None
        rec = {"n_cands": len(cands), "best_val": float(best_val),
               "gap_to_2nd": (float(gap2) if gap2 is not None else None)}
        for tag, k in (("seal", 1), ("noopen", 2)):
            clean = [t for t in cands if t[k] == 0]
            best_clean = max((t[0] for t in clean), default=None)
            rec[tag] = {
                "n_clean": len(clean),
                "argmax_creates": int(srt[0][k] > 0),
                "argmax_new": int(srt[0][k]),
                "gap_to_clean": (float(best_val - best_clean)
                                 if best_clean is not None else None),
            }

    # ---- arm policy -------------------------------------------------------
    k = 1 if kind == "seal" else (2 if kind == "noopen" else None)
    if gated and k is not None:
        if weight is None:                       # hard veto = max dose
            clean = [t for t in cands if t[k] == 0]
            pool = clean if clean else cands
            return max(pool, key=lambda t: t[0])[3], rec
        return max(cands, key=lambda t: t[0] - weight * t[k])[3], rec
    return max(cands, key=lambda t: t[0])[3], rec


def play(seed):
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    level, wt, ws = _C["level"], _C["wt"], _C["ws"]
    w, fl, kind, weight, gate = _C["w"], _C["fl"], _C["kind"], _C["weight"], _C["gate"]
    instr = (kind == "base") or True

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    seal_state, seal_events, reopen_events = {}, [], []
    recs, actions = [], []
    final_vc = None

    for pill_idx in range(300):
        fb = FB.from_board(env.board)
        vc0 = fb.virus_count()
        final_vc = vc0
        if vc0 == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        gated = vc0 <= gate
        a, rec = _choose(col, vir, int(env.cur.a), int(env.cur.b),
                         int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws,
                         kind, weight, gated, instr)
        if a is None:
            break
        if rec is not None:
            rec["pill"] = pill_idx
            rec["vc"] = int(vc0)
            recs.append(rec)
        actions.append(int(a))
        _, _, term, trunc, info = env.step(int(a))

        # realised seal accounting -- round-1's detector, verbatim
        fb2 = FB.from_board(env.board)
        vc1 = fb2.virus_count()
        final_vc = vc1
        if 0 < vc1 <= SEAL_VC_THRESHOLD:
            col2, vir2 = fb2.col, fb2.vir
            live = set(i for i in range(128) if vir2[i])
            for vi in list(seal_state):
                if vi not in live:
                    del seal_state[vi]
            for i in live:
                r = i // 8
                covered, cover_j = False, -1
                if r > 0:
                    j = i - 8
                    if col2[j] != 0 and vir2[j] == 0 and col2[j] != col2[i]:
                        covered, cover_j = True, j
                was = i in seal_state
                if covered and not was:
                    seal_state[i] = cover_j
                    seal_events.append((pill_idx, vc1, i, cover_j))
                elif covered and was:
                    seal_state[i] = cover_j
                elif not covered and was:
                    del seal_state[i]
                    reopen_events.append((pill_idx, vc1, i))

        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    return {
        "seed": seed, "arm": _C["arm"], "won": int(res == "clear"),
        "topout": int(res == "topout"), "stall": int(res == "stall"),
        "pills": env.pills_placed,
        "final_virus_count": int(final_vc) if final_vc is not None else None,
        "n_seal_events": len(seal_events), "n_reopen_events": len(reopen_events),
        "still_sealed_at_end": len(seal_state),
        "seal_events": seal_events, "recs": recs, "actions": actions,
    }


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def run_arm(arm, seeds, level, wt, ws, gate, workers):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, wt, ws, arm, gate)) as ex:
        futs = {ex.submit(play, s): s for s in seeds}
        for f in as_completed(futs):
            try:
                rows.append(f.result())
            except Exception as e:
                import traceback
                rows.append({"seed": futs[f], "arm": arm, "error": str(e),
                             "tb": traceback.format_exc()[-800:]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--wt", type=int, default=0)
    ap.add_argument("--ws", type=int, default=20)
    ap.add_argument("--gate", type=int, default=8, help="apply term when virus_count <= gate")
    ap.add_argument("--arms", type=str, default="base,veto_seal")
    ap.add_argument("--out", type=str, default="results/seal_ab.json")
    a = ap.parse_args()

    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    arms = a.arms.split(",")
    print(f"=== SEAL A/B  L{a.level}  n={len(seeds)}  gate=vc<={a.gate}  "
          f"arms={arms}  (champion wt={a.wt} ws={a.ws}) ===", flush=True)

    out = {"args": vars(a), "arms": {}}
    for arm in arms:
        rows = run_arm(arm, seeds, a.level, a.wt, a.ws, a.gate, a.workers)
        err = [r for r in rows if "error" in r]
        ok = [r for r in rows if "error" not in r]
        if err:
            print(f"  [{arm}] {len(err)} ERRORED, e.g. {err[0].get('tb','')[:400]}", flush=True)
        pills = [r["pills"] for r in ok]
        won = sum(r["won"] for r in ok)
        seals = sum(r["n_seal_events"] for r in ok)
        lo, hi = boot_ci(pills)
        print(f"  [{arm:14s}] n={len(ok):3d}  won {won}/{len(ok)}  "
              f"topout {sum(r['topout'] for r in ok)}  stall {sum(r['stall'] for r in ok)}  "
              f"pills {st.mean(pills):6.2f} [{lo:.2f},{hi:.2f}]  "
              f"realised seals {seals} ({seals/max(1,len(ok)):.3f}/g)", flush=True)
        out["arms"][arm] = {"rows": ok, "errors": err}

    # ---- paired deltas vs base -------------------------------------------
    if "base" in out["arms"]:
        b = {r["seed"]: r for r in out["arms"]["base"]["rows"]}
        for arm in arms:
            if arm == "base":
                continue
            t = {r["seed"]: r for r in out["arms"][arm]["rows"]}
            common = sorted(set(b) & set(t))
            dp = [t[s]["pills"] - b[s]["pills"] for s in common]
            dw = [t[s]["won"] - b[s]["won"] for s in common]
            # a seed "moved" when the ACTION SEQUENCE diverges -- equal pill
            # counts do not imply equal play, so pill-count equality would
            # under-report divergence.
            moved = sum(1 for s in common if t[s]["actions"] != b[s]["actions"])
            lo, hi = boot_ci(dp)
            print(f"\n  PAIRED {arm} - base  (n={len(common)}, moved {moved} seeds "
                  f"= {moved/max(1,len(common)):.1%})", flush=True)
            print(f"    d_pills  {st.mean(dp):+.3f} [{lo:+.3f},{hi:+.3f}]  "
                  f"(negative = FEWER pills = better)", flush=True)
            print(f"    d_wins   {sum(dw):+d}  ({sum(t[s]['won'] for s in common)} vs "
                  f"{sum(b[s]['won'] for s in common)})", flush=True)
            out["arms"][arm]["paired"] = {
                "n": len(common), "moved": moved, "d_pills_mean": st.mean(dp),
                "d_pills_ci": [lo, hi], "d_wins": sum(dw)}

    # ---- avoidability, off the base arm ----------------------------------
    if "base" in out["arms"]:
        recs = [r for row in out["arms"]["base"]["rows"] for r in row["recs"]]
        gated = len(recs)
        g2 = [r["gap_to_2nd"] for r in recs if r["gap_to_2nd"] is not None]
        print(f"\n=== AVOIDABILITY (base arm, {gated} gated decisions) ===", flush=True)
        if g2:
            q = sorted(g2)
            print(f"  SCALE REFERENCE, champion best-to-2nd value gap: "
                  f"median {st.median(g2):.1f}  p90 {q[9*len(q)//10]:.1f}", flush=True)
        out["avoidability"] = {"gated_decisions": gated, "gap_to_2nd": g2}
        for tag, label in (("seal", "SEAL (cell directly above)"),
                           ("noopen", "NO-OPEN-WINDOW (colour reachability)")):
            creating = [r for r in recs if r[tag]["argmax_creates"]]
            forced = [r for r in creating if r[tag]["n_clean"] == 0]
            gaps = [r[tag]["gap_to_clean"] for r in creating
                    if r[tag]["gap_to_clean"] is not None]
            print(f"\n  -- {label} --", flush=True)
            print(f"    argmax creates a NEW one: {len(creating)}/{gated} "
                  f"({len(creating)/max(1,gated):.1%} of gated decisions)", flush=True)
            print(f"    FORCED (no clean candidate exists): {len(forced)}"
                  f"/{max(1,len(creating))} ({len(forced)/max(1,len(creating)):.1%})", flush=True)
            if gaps:
                gs = sorted(gaps)
                print(f"    value gap to best CLEAN alternative: median {st.median(gaps):.1f} "
                      f" mean {st.mean(gaps):.1f}  p10 {gs[len(gs)//10]:.1f}  "
                      f"p90 {gs[9*len(gs)//10]:.1f}", flush=True)
                if g2:
                    med2 = st.median(g2)
                    cheap = sum(1 for x in gaps if x <= med2)
                    print(f"    avoidable for <= the median best-to-2nd gap ({med2:.1f}): "
                          f"{cheap}/{len(gaps)} ({cheap/len(gaps):.1%})", flush=True)
            out["avoidability"][tag] = {
                "argmax_creates": len(creating), "forced": len(forced),
                "gap_to_clean": gaps}

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh)
    print(f"\nwrote {a.out}\nDONE", flush=True)


if __name__ == "__main__":
    main()
