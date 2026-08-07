#!/usr/bin/env python3
"""Merge Stage 1's 140 reused label records with the 2x run's new ones.

Stage 1's labeller predates the `terms`/`win` fields that stage2_fit.py consumes, so
those are BACKFILLED from out/feats.npz -- the same extraction that already passed its
own gate (1400/1400 boards recombining to the recorded leaf value exactly). Backfilling
from a gated artefact rather than recomputing avoids introducing a second code path
that could silently disagree with the first.

Records that cannot be completed are DROPPED with a count, never emitted half-filled:
a record missing `terms` would be silently skipped downstream and quietly shrink n.
"""
import json, sys
import numpy as np

old_p, new_p, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
f = np.load("out/feats.npz")
T = f["terms_search"]; W = f["win"]
key = {(int(p), int(a)): i for i, (p, a) in enumerate(zip(f["pos"], f["act"]))}

out, kept, dropped, new_n = [], 0, 0, 0
for line in open(old_p):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    i = r["idx"]
    terms, win = {}, {}
    ok = True
    for a in r["acts"]:
        k = key.get((i, a))
        if k is None:
            ok = False
            break
        terms[str(a)] = [int(x) for x in T[k]]
        win[str(a)] = int(W[k])
    if not ok:
        dropped += 1
        continue
    r["terms"] = terms
    r["win"] = win
    out.append(r)
    kept += 1

seen = {r["idx"] for r in out}
for line in open(new_p):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    if r["idx"] in seen:      # never double-count a position
        continue
    seen.add(r["idx"])
    out.append(r)
    new_n += 1

with open(out_p, "w") as fh:
    for r in out:
        fh.write(json.dumps(r) + "\n")
print(f"merged: {kept} reused (backfilled from feats.npz), {dropped} dropped, "
      f"{new_n} new -> {len(out)} total in {out_p}")
