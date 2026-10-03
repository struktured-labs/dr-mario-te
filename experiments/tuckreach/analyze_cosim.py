#!/usr/bin/env python3
"""Read the co-sim publish timelines (cosim_run.py -> DIR/pubtrace_<game>_<arm>.jsonl) and report, per arm vs a
reference arm on the same boards:
  identity   final (col, o4) and tuck descriptor equal / different (list)
  tuck       how often the tuck extension commits (descriptor != $FF) and whether the DONE final is inside the
             reach_fw mask (python spec, decoded from the upload's DRREACHTX gravity + DRTAPP nibbles)
  DONE       GO -> DONE frames, and the per-board delta vs the reference (mean / median / p90 / p95 / max)
  at-gate    P(the live mailbox at GO + t == the DONE final) for t in 1.5 / 3 / 6 / 9 / 12.5 frames (the couch gate is
             GO + 6 f), and the frame the final answer is first visible (a pub, or DONE)
Usage: analyze_cosim.py DIR --games G2,G3,G4 --pairs off:ro,off:tr,off:tl,trtl:ship [--ref-lateflip]
  --ref-lateflip: use the late-flip lane's fw 1488e158 timelines (same upload bytes, verified) as arm "off" where this
  directory has none.
"""
import argparse
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "experiments", "reach"))
import reach_fw as RF  # noqa: E402

LF = "/home/struktured/projects/dr-mario-h16-wt/experiments/lateflip"
LF_FILES = {"G2": "pubtrace_g2_seed0_tuck.jsonl", "G3": "pubtrace_G3_seed0.jsonl", "G4": "pubtrace_G4_seed0.jsonl"}
SPEED_TABLE = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
               0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
               0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
               0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
               0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00]
SPEED_BASE = [0x0F, 0x19, 0x1F]
TS = (1.5, 3.0, 6.0, 9.0, 12.5)
_MASK = {}


def mask_of(upload):
    """reach_fw mask in copro o4 space (index o4*8+col) for the exact bytes uploaded, or None if R_FLT would be 0."""
    if upload in _MASK:
        return _MASK[upload]
    t = upload.split()
    na, nb = int(t[2]), int(t[3])
    nes = [int(x, 16) for x in t[4:]]
    nbh = (nb >> 4) & 0x0F
    sp = (nbh >> 2) - 1
    m = None
    if nbh and 0 <= sp <= 2:
        su = ((nbh & 3) << 4) | ((na >> 4) & 0x0F)
        thr = SPEED_TABLE[min(80, SPEED_BASE[sp] + su)]
        pp = ((na >> 2) & 3) | (((nb >> 2) & 3) << 2)
        color = [[0 if nes[r * 8 + c] in (0xFF, 0x00) else 1 for c in range(8)] for r in range(16)]
        mm = RF.reach_mask_fw(color, thr, pp if pp >= 2 else None)
        m = [mm[((i >> 3) ^ 2) * 8 + (i & 7)] for i in range(32)]
        if all(m):
            m = None               # all-ones = no filtering (the all-masked fallback)
    _MASK[upload] = m
    return m


def load(d, arm, games, ref_lateflip=False):
    out = {}
    for g in games:
        p = os.path.join(d, f"pubtrace_{g}_{arm}.jsonl")
        if os.path.exists(p):
            for l in open(p):
                r = json.loads(l); out[(g, r["p"])] = r
        elif arm == "off" and ref_lateflip:
            for l in open(os.path.join(LF, LF_FILES[g])):
                r = json.loads(l); r["game"] = g; out[(g, r["p"])] = r
    return out


def at(r, t):
    if r["done_f"] <= t:
        return tuple(r["final"][:2])
    a = None
    for tf, c, o, _ in r["pubs"]:
        if tf <= t:
            a = (c, o)
    return a


def first_final(r):
    f = tuple(r["final"][:2])
    for tf, c, o, _ in r["pubs"]:
        if (c, o) == f:
            return tf
    return r["done_f"]


def tucked(r):
    return bool(r.get("tuck")) and r["tuck"][0] != 255


def in_mask(r):
    m = mask_of(r["upload"])
    return True if m is None else bool(m[r["final"][1] * 8 + r["final"][0]])


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))] if xs else float("nan")


def summary(R, label):
    n = len(R)
    tk = [r for r in R.values() if tucked(r)]
    out = [f"[{label}] boards {n}: tuck commits {len(tk)} ({100 * len(tk) / max(1, n):.1f}%), of which DONE final outside "
           f"the reach mask {sum(1 for r in tk if not in_mask(r))}; finals outside the mask overall "
           f"{sum(1 for r in R.values() if not in_mask(r))}"]
    df = [r["done_f"] for r in R.values()]
    out.append(f"   DONE frames: median {st.median(df):.2f}  p90 {pct(df, .9):.2f}  max {max(df):.2f}")
    for t in TS:
        pass
    ff = [first_final(r) for r in R.values()]
    out.append("   P(mailbox == final) at GO + " + "  ".join(
        f"{t:g} f: {100 * sum(at(r, t) == tuple(r['final'][:2]) for r in R.values()) / n:.1f}%" for t in TS) +
        f"   | final first visible: median {st.median(ff):.2f} f, p75 {pct(ff, .75):.2f}, p90 {pct(ff, .9):.2f}")
    eg = {k: r for k, r in R.items() if (r.get("vc") or 99) <= 4}
    if eg:
        out.append(f"   endgame (<= 4 viruses, n={len(eg)}): P(final) at GO + 6 f "
                   f"{100 * sum(at(r, 6.0) == tuple(r['final'][:2]) for r in eg.values()) / len(eg):.1f}%")
    return out


def compare(A, B, la, lb):
    keys = sorted(set(A) & set(B))
    fin = [k for k in keys if tuple(A[k]["final"][:2]) == tuple(B[k]["final"][:2])]
    tk = [k for k in keys if tuple(A[k]["final"][:2]) == tuple(B[k]["final"][:2]) and
          (A[k].get("tuck") or [255])[0:2] == (B[k].get("tuck") or [255])[0:2]]
    dd = [B[k]["done_f"] - A[k]["done_f"] for k in keys]
    out = [f"{lb} vs {la}: boards {len(keys)}  final identical {len(fin)}/{len(keys)}  final+tuck identical "
           f"{len(tk)}/{len(keys)}",
           f"   DONE delta ({lb} - {la}) frames: mean {st.mean(dd):+.2f}  median {st.median(dd):+.2f}  p90 {pct(dd, .9):+.2f}  "
           f"p95 {pct(dd, .95):+.2f}  max {max(dd):+.2f}  min {min(dd):+.2f}"]
    for k in keys:
        if k not in tk:
            a, b = A[k], B[k]
            out.append(f"   DIFF {k[0]} p{k[1]}: {la} final {a['final']} tuck {a.get('tuck')} in-mask {in_mask(a)} | "
                       f"{lb} final {b['final']} tuck {b.get('tuck')} in-mask {in_mask(b)} | python a{a.get('sim_action')}")
    return out, keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir"); ap.add_argument("--games", default="G2")
    ap.add_argument("--pairs", default="off:ship"); ap.add_argument("--ref-lateflip", action="store_true")
    args = ap.parse_args()
    games = args.games.split(",")
    arms = sorted({a for p in args.pairs.split(",") for a in p.split(":")})
    D = {a: load(args.dir, a, games, args.ref_lateflip) for a in arms}
    for a in arms:
        if D[a]:
            print("\n".join(summary(D[a], a)))
    for p in args.pairs.split(","):
        a, b = p.split(":")
        if D[a] and D[b]:
            print("\n".join(compare(D[a], D[b], a, b)[0]))


if __name__ == "__main__":
    main()
