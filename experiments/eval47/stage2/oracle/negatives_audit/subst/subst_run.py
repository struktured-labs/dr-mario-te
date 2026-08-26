#!/usr/bin/env python3
"""SUBSTITUTION RUN — PREREG_H12_SUBSTITUTION.md. Segmented, resumable, per-seed atomic.

Plays certified H12 (instrumented, G-IDENTITY-passed) and banks every flip record WITH its
post-placement planes, so the LUT can be scored offline against H12's own choices.
Cap 400 to match the reference population (§11). One file per seed => resumable, no double-writers.
"""
import os
for _v in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS","NUMBA_NUM_THREADS"):
    os.environ[_v] = "1"
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/drm-numba-cache")
import argparse, glob, gzip, json, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
_R = {}


def _one(a):
    seed, level, max_pills, model, out = a
    dst = os.path.join(out, f"flips_{seed}.jsonl.gz")
    if os.path.exists(dst):
        return dict(seed=seed, skipped=True)
    import oracle_arm as OA
    from h12_boards import H12ArmWithBoards
    if "C" not in _R:
        _R["C"], _R["b"] = OA.init_rig(model=model, level=level)
    t0 = time.time()
    arm = H12ArmWithBoards(provenance=True)
    r = OA.play_one(seed, arm, _R["C"], _R["b"], max_pills)
    tmp = dst + ".tmp"
    with gzip.open(tmp, "wt") as fh:
        for f in arm.tie_log:            # EVERY tie ply, keeps included
            fh.write(json.dumps(f) + "\n")
        fh.write(json.dumps({"game": {k: v for k, v in r.items() if k != "_actions"},
                             "cap": max_pills, "level": level, "model": model}) + "\n")
    os.replace(tmp, dst)                      # atomic: a partial file is never visible
    nk = sum(1 for t in arm.tie_log if not t["is_flip"])
    return dict(seed=seed, res=r["res"], plies=r["n_plies"], ties=len(arm.tie_log),
                flips=len(arm.tie_log) - nk, keeps=nk,
                at_cap=int(r["n_plies"] >= max_pills), secs=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1666)
    ap.add_argument("--seed-lo", type=int, default=33000)   # free stream keys 16500+
    ap.add_argument("--level", type=int, default=20)
    ap.add_argument("--max-pills", type=int, default=400)     # §11: match the reference
    ap.add_argument("--model", default="lulu")
    ap.add_argument("--workers", type=int, default=12)        # measured config; 14 is unmeasured
    ap.add_argument("--out", default="/root/drm/subst/out_flips")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    seeds = []
    _s = a.seed_lo
    while len(seeds) < a.seeds:
        if _s not in (0, 35208, 35209):
            seeds.append(_s)
        _s += 2

    # ---- DISJOINTNESS ASSERTED ON STREAM KEYS, NOT LITERAL INTEGERS
    # Rule: fold mod 65536 BEFORE comparing (the seed space wraps), and reduce to a
    # STREAM KEY via >>1 because the pill-seed low bit is dead (2k and 2k+1 give
    # byte-identical capsule streams). A literal integer-range assertion CANNOT
    # represent either fault - it passes on a block that collides after folding.
    FOLD = 65536
    CONSUMED = [(30000, 32998), (41100, 50099), (42000, 45998), (52100, 53099),
                (53100, 59999), (61000, 62999), (70000, 80999), (16000, 16999),
                (33000, 36332),   # THIS lane's own substitution arm, consumed 2026-08-26
                (14000, 14999), (90000, 90499)]
    ALIAS = {0, 35208, 35209}      # absorbing state remaps to ROM warm-boot seed 0x8988
    occ = set()
    for lo, hi in CONSUMED:
        occ |= {((x % FOLD) >> 1) for x in range(lo, hi + 1)}
    K = [((x % FOLD) >> 1) for x in seeds]
    coll = set(K) & occ
    assert not coll, f"STREAM-KEY COLLISION with consumed blocks: {len(coll)} keys"
    assert len(set(K)) == len(seeds), (
        f"BLOCK IS INTERNALLY ALIASED: {len(seeds)} seeds -> only {len(set(K))} distinct "
        f"streams. N would silently mean half what it says.")
    assert not (ALIAS & set(seeds)), f"alias triple present: {ALIAS & set(seeds)}"
    print(f"seed disjointness ASSERTED ON STREAM KEYS: {len(seeds)} seeds "
          f"[{seeds[0]},{seeds[-1]}] -> {len(set(K))} distinct streams, keys "
          f"{min(K)}..{max(K)}, 0 collisions with {len(CONSUMED)} consumed blocks", flush=True)

    done = len(glob.glob(os.path.join(a.out, "flips_*.jsonl.gz")))
    print(f"subst run: N={len(seeds)} cap={a.max_pills} L{a.level} {a.workers} workers "
          f"(resuming, {done} already banked)", flush=True)

    t0 = time.time(); n = 0; nf = 0; nk = 0; cap = 0
    jobs = [(s, a.level, a.max_pills, a.model, a.out) for s in seeds]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(_one, j) for j in jobs]
        for f in as_completed(futs):
            r = f.result()
            if r.get("skipped"):
                continue
            n += 1; nf += r["flips"]; nk += r["keeps"]; cap += r["at_cap"]
            if n == 200:                       # §9 Amendment 4(c): REAL blocking interim
                import subprocess
                subprocess.run([sys.executable,
                                os.path.join(HERE, "interim_gate.py"),
                                "--dir", a.out, "--min-seeds", "200",
                                "--registered-n", str(a.seeds),
                                "--unit", "drm-subst", "--stop-on-fail"], check=False)
            if n % 25 == 0 or n <= 3:
                el = time.time() - t0
                print(f"  [{n}/{len(seeds)}] ties={nf+nk} (flips={nf} keeps={nk}, {(nf+nk)/n:.2f}/seed) at_cap={cap/n*100:.0f}% "
                      f"| {n/(el/3600):.0f} seeds/h | eta {(len(seeds)-n)/(n/el)/3600:.1f}h",
                      flush=True)
    print(f"\nDONE {n} seeds, {nf+nk} ties ({nf} flips + {nk} keeps, {(nf+nk)/max(n,1):.2f}/seed), "
          f"at_cap {cap/max(n,1)*100:.1f}%, wall {(time.time()-t0)/3600:.2f}h", flush=True)


if __name__ == "__main__":
    main()
