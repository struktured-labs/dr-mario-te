"""m2_features.py — replay-derive per-candidate guard features for M2.

The M1 bank stores tribunal labels but not candidate boards (pack() dropped
labelcore's `planes`). Champion-const replay is deterministic (proven by the
A5 replay gate), so features are re-derived: replay each banked game with a
fork-free arm; at each banked adjudication ply, enumerate_candidates again
and compute the FROZEN integer feature menu from each candidate's resolved
post-placement board + the pre-placement board. Output joins the bank by
(seed, ply, rep_slot). REPLAY GATE per game: height trace must equal the
banked trace exactly or nothing is emitted for that game.

Frozen feature menu (REGISTRATION_M2 sec 2; all 6502-computable ints):
  wide_post   max(H'[2..5]) after placement+resolution
  relief      wide_pre - wide_post  (spawn-neighborhood relief; <0 = worse)
  dsh_post    max(H'[3],H'[4])
  maxh_post   max(H')
  throat_occ  occupied cells in rows 0..3 x cols 2..5 (post)
  ridge       max adjacent |H'[c]-H'[c+1]| for c in 2..5 (narrow tower shape)
  lane_vir    viruses remaining in cols 2..5 (post)
  vir_left    total viruses remaining (post)
  topdist     16 - wide_post
Deferred (documented, not in v1): cur/next colour interactions.
"""
import base64
import glob
import gzip
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m1_harvest as MH  # noqa: E402  (wires paths)
from oracle_arm import OracleArm, heights  # noqa: E402

OUT = os.path.join(HERE, "out", "labels_m1")
FOUT = os.path.join(HERE, "out", "m2_features")
NCELL = 128
_W = {}


def feats_from_planes(planes_b64, pre_wide):
    raw = base64.b64decode(planes_b64)
    c1 = np.frombuffer(raw[:NCELL], dtype=np.int8).reshape(16, 8)
    v1 = np.frombuffer(raw[NCELL:2 * NCELL], dtype=np.int8).reshape(16, 8)
    occ = (c1 > 0) | (v1 > 0)
    hs = np.where(occ.any(axis=0), 16 - np.argmax(occ, axis=0), 0)
    wide = int(max(hs[2:6]))
    return {"wide_post": wide, "relief": int(pre_wide - wide),
            "dsh_post": int(max(hs[3], hs[4])), "maxh_post": int(hs.max()),
            "throat_occ": int(occ[0:4, 2:6].sum()),
            "ridge": int(max(abs(int(hs[c]) - int(hs[c + 1]))
                             for c in range(2, 6))),
            "lane_vir": int((v1[:, 2:6] > 0).sum()),
            "vir_left": int((v1 > 0).sum()), "topdist": 16 - wide}


class FeatureArm(OracleArm):
    """Champion-const replay; at banked plies, re-enumerate and featurize."""

    def __init__(self, plies, **kw):
        kw.setdefault("label_mode", "const")
        kw.setdefault("provenance", False)
        super().__init__(**kw)
        self.plies = set(plies)
        self.trace = []
        self.feats = {}

    def choose(self, env, seed, C, bmodel, w, fl, wt, ws, ply):
        H = heights(env.board.color)
        Hl = [int(x) for x in H]
        self.trace.append(Hl)
        if ply in self.plies:
            import labelcore as LC
            pre_wide = max(Hl[2:6])
            ents = LC.enumerate_candidates(env, dedup=True)
            self.feats[ply] = {
                str(e["rep_slot"]): feats_from_planes(e["planes"], pre_wide)
                for e in ents}
        return super().choose(env, seed, C, bmodel, w, fl, wt, ws, ply)


def _winit(level):
    os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                      NUMBA_NUM_THREADS="1")
    import oracle_arm as OA
    C, bmodel = OA.init_rig("lulu", level=level)
    _W.update(C=C, bmodel=bmodel)


def _work(item):
    seed, plies, banked_trace = item
    import oracle_arm as OA
    t0 = time.monotonic()
    arm = FeatureArm(plies)
    OA.play_one(seed, arm, _W["C"], _W["bmodel"], max_pills=400)
    if arm.trace != banked_trace:
        return {"seed": seed, "replay_gate": "FAIL"}
    return {"seed": seed, "replay_gate": "PASS", "feats": arm.feats,
            "secs": round(time.monotonic() - t0, 2)}


def run(src, level, workers):
    """src: 'L20' | 'L11M' | 'L11M_backfill' (banked segment dir)."""
    import multiprocessing as mp
    items = []
    for f in sorted(glob.glob(os.path.join(OUT, src, "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        if r.get("smoke"):
            continue
        plies = [a["ply"] for a in r["adjudications"]]
        if plies:
            items.append((r["seed"], plies, r["heights_trace"]))
    outdir = os.path.join(FOUT, src)
    os.makedirs(outdir, exist_ok=True)
    todo = [i for i in items if not os.path.exists(
        os.path.join(outdir, f"seed_{i[0]:06d}.json.gz"))]
    print(f"[m2-feat] {src}: {len(todo)}/{len(items)} games to derive",
          flush=True)
    fails = done = 0
    with mp.Pool(workers, initializer=_winit, initargs=(level,)) as pool:
        for rec in pool.imap_unordered(_work, todo):
            done += 1
            if rec["replay_gate"] != "PASS":
                fails += 1
                print(f"[m2-feat] REPLAY GATE FAIL seed={rec['seed']}",
                      flush=True)
                continue
            p = os.path.join(outdir, f"seed_{rec['seed']:06d}.json.gz")
            with gzip.open(p + ".tmp", "wt") as fh:
                json.dump(rec, fh)
            os.replace(p + ".tmp", p)
            if done % 50 == 0 or done == len(todo):
                print(f"[m2-feat] {src} {done}/{len(todo)} fails={fails}",
                      flush=True)
    print(f"[m2-feat] {src} DONE fails={fails}", flush=True)
    return 0 if fails == 0 else 3


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "L20"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    # Derive the level from the STRATUM PREFIX, not an exact match: the A5
    # segment dirs are "L20_unthin_held" / "L11M_backfill", and `src == "L20"`
    # silently rigged every A5 segment at L11. Caught only because the replay
    # gate failed 3/3 — a proxy (the exact string) standing in for a property
    # (the stratum), which is today's recurring defect.
    assert src.startswith(("L20", "L11M")), f"cannot infer level from {src!r}"
    level = 20 if src.startswith("L20") else 11
    sys.exit(run(src, level, workers))
