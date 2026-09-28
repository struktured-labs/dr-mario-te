"""STEER6b provenance check after the Hetzner -> local rebalance: every job line ran in exactly ONE place, every job
file has exactly CNT rows with the planned seeds, and the union has no duplicate seed per (instrument, arm).

  python steer6_verify_holdout.py
"""
import os, json, glob, collections

P = "steer6/holdout/provenance"
LISTS = {"local": f"{P}/local_jobs.txt", "hetzner": f"{P}/hetzner_jobs_kept.txt", "moved->local": f"{P}/moved_jobs_as_run_locally.txt"}


def main():
    ok = True; where = {}; per_key = collections.defaultdict(list)
    for place, lst in LISTS.items():
        for line in open(lst):
            t = line.split()
            mode, arm, lo, cnt, step, outp = t[1], t[2], int(t[4]), int(t[5]), int(t[6]), t[7]
            base = os.path.basename(outp)
            if base in where:
                print("DUPLICATE JOB", base, where[base], place); ok = False
            where[base] = place
            local_path = f"steer6/holdout/{'remote' if place == 'hetzner' else 'local'}/{base}"
            if not os.path.exists(local_path):
                print("MISSING", local_path); ok = False; continue
            R = [json.loads(l) for l in open(local_path)]
            want = [lo + i * step for i in range(cnt)]
            if [r["seed"] for r in R] != want:
                print("ROWS/SEEDS MISMATCH", local_path, len(R), cnt); ok = False
            per_key[(mode, arm)].extend(r["seed"] for r in R)
    stray = [f for f in glob.glob("steer6/holdout/*/*.jsonl") if os.path.basename(f) not in where]
    if stray:
        print("STRAY FILES (not in any list):", stray); ok = False
    for (mode, arm), seeds in sorted(per_key.items()):
        d = [s for s, c in collections.Counter(seeds).items() if c > 1]
        print(f"  {mode:4s} {arm:18s} rows {len(seeds):5d}  unique {len(set(seeds)):5d}  duplicate seeds {len(d)}")
        ok &= not d
    print("jobs by place:", dict(collections.Counter(where.values())))
    print("PROVENANCE CHECK:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    raise SystemExit(0 if main() else 1)
